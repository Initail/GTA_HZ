"""Independent CPU contract/ray checks for ICC; not exported/runtime acceptance."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
OUT=Path(__file__).resolve().parent


class BRecorder:
    def __init__(self):self.frame=(11,22,.3);self.faces=[];self.groups=defaultdict(list)
    def face(self,material,points,uv=None):
        x,y,a=self.frame;ca,sa=math.cos(a),math.sin(a)
        q=[(u*ca-v*sa+x,u*sa+v*ca+y,z) for u,v,z in points]
        self.faces.append((material,q));self.groups[material].append(q)


def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(a[i]*b[i] for i in range(3))


def ray_triangle(origin,direction,a,b,c):
    e,f=sub(b,a),sub(c,a);p=cross(direction,f);det=dot(e,p)
    if abs(det)<1e-10:return None
    inv=1/det;t=sub(origin,a);u=dot(t,p)*inv
    if not(-1e-9<=u<=1+1e-9):return None
    q=cross(t,e);v=dot(direction,q)*inv
    if v<-1e-9 or u+v>1+1e-9:return None
    distance=dot(f,q)*inv
    return distance if distance>=0 else None


def load():
    spec=json.loads((OUT/'spec.json').read_text());path=ROOT/'scripts/landmarks/international_conference_center.py'
    ms=importlib.util.spec_from_file_location('icc_candidate',path)
    mod=importlib.util.module_from_spec(ms);ms.loader.exec_module(mod)
    return spec,path,mod


def main():
    spec,path,mod=load();city=load_city('hangzhou');scale=city['geography']['scale']
    x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city);lm={'x':x,'z':z,'y':13.25}
    rec=BRecorder();old=rec.frame;report=mod.build(rec,lm,spec,scale)
    assert rec.frame==old and len(rec.faces)==report['faces']
    assert report['lights']==report['waterMeshes']==0 and report['shallowGlassSkylight']
    assert 'water' not in rec.groups and set(rec.groups)==set(report['materials'])
    assert len(rec.groups)<=spec['budget']['maxMaterials']
    triangles=[];minimum=math.inf
    for material,face in rec.faces:
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):
            a,b,c=face[0],face[i],face[i+1];n=cross(sub(b,a),sub(c,a));area=math.sqrt(dot(n,n))/2
            assert area>1e-10,('degenerate triangle',material,face)
            minimum=min(minimum,area);triangles.append((material,a,b,c))
    assert len(triangles)<=spec['budget']['maxTriangles'],len(triangles)
    angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle)
    def local(u,v,h):return(x+(u*ca-v*sa)*scale,z+(u*sa+v*ca)*scale,lm['y']+h*scale)
    for uv,wgs in [('outerPodiumUVMetres','outerPodiumWGS84'),('sphereBaseUVMetres','sphereBaseWGS84'),
                   ('frontEntryUVMetres','frontEntryWGS84'),('rearEntryUVMetres','rearEntryWGS84')]:
        for p,q in zip(spec[uv],spec[wgs]):
            expected=project(*q,city);actual=local(*p,0)
            assert max(abs(expected[i]-actual[i]) for i in range(2))<1e-6
    high=max(p[2] for material,face in rec.faces for p in face)
    assert abs((high-lm['y'])/scale-spec['heightM'])<1e-8,'85m roof datum/scale mismatch'
    sec=spec['estimates']['sphereSection']['value']
    assert abs(mod.sphere_radius_metres(sec['centerHeightM'],spec)-spec['diameterM']/2)<1e-12
    # Above the20m estimated cut all sphere vertices must stay near85m diameter;
    # the unverified108m source ring is not being reused as a sphere radius.
    for material,face in rec.faces:
        for p in face:
            if (p[2]-lm['y'])/scale>sec['lowerCutM']+.2:
                assert math.hypot(p[0]-x,p[1]-z)/scale<spec['diameterM']/2+.7
    def hits(origin,direction):
        return sorted((d,m) for m,a,b,c in triangles if (d:=ray_triangle(origin,direction,a,b,c)) is not None)
    # Theatre-facing ray at the equator finds recessed glass, not the gold bands
    # wrapped across the actual large C-facing opening.
    # Off-centre3m ray crosses glass between mullions; the exact centre has a
    # legitimate narrow steel mullion and should not be mistaken for a gold wall.
    curtain_origin=local(3,-90,sec['centerHeightM']);direction=(-sa,ca,0)
    glass_hits=hits(curtain_origin,direction)
    assert glass_hits and glass_hits[0][1]=='landmarkglass',('front glazed face missing',glass_hits[:2])
    glass_r=90-glass_hits[0][0]/scale
    expected=spec['diameterM']/2*math.cos(report['glazedFaceHalfRadians'])-spec['estimates']['glazedFace']['value']['recessM']
    assert abs(glass_r-expected)<.3,'curtain is not recessed/registered to source front axis'
    sky_hits=hits(local(0,0,100),(0,0,-1))
    assert sky_hits and sky_hits[0][1]=='landmarkglass' and abs(sky_hits[0][0]-15*scale)<1e-8
    # Two adjoining sphere band heights must show the terrace/recess geometry.
    bands=spec['estimates']['floorBands']['value'];step=(sec['goldSkinTopM']-sec['lowerCutM'])/bands['bands']
    k=int((sec['centerHeightM']-sec['lowerCutM'])/step);lo=sec['lowerCutM']+k*step
    radial_samples=[]
    for height in [lo+step*.16,lo+step*.78]:
        ray=hits(local(0,90,height),(sa,-ca,0));assert ray
        radial_samples.append({'heightM':height,'outerRadiusM':90-ray[0][0]/scale,'material':ray[0][1]})
    assert radial_samples[0]['outerRadiusM']-radial_samples[1]['outerRadiusM']>.4,'sphere has no actual stepped/recessed bands'
    ro=mod.radial_boundary_metres(spec['outerPodiumUVMetres'],0);ri=spec['estimates']['podium']['value']['innerRoofRadiusM']
    roof_samples=[]
    for fraction in [.35,.6,.9]:
        u=ri+(ro-ri)*fraction;ray=hits(local(u,0,25),(0,0,-1));assert ray
        roof_samples.append({'uM':u,'highestSurfaceM':25-ray[0][0]/scale,'material':ray[0][1]})
    assert max(p['highestSurfaceM'] for p in roof_samples)-min(p['highestSurfaceM'] for p in roof_samples)>2
    assert all(p['highestSurfaceM']<14 for p in roof_samples),'podium flattened or over-height'
    for u,v in [(0,-35),(-4,43)]:
        origin=local(u,v,30);roof_hit=hits(origin,(0,0,-1));assert roof_hit and roof_hit[0][1]=='landmarkglass'
        upward=[]
        for material,a,b,c in triangles:
            d=ray_triangle(origin,(0,0,-1),a,b,c)
            if d is not None and abs(d-roof_hit[0][0])<1e-7 and cross(sub(b,a),sub(c,a))[2]>0:upward.append(d)
        assert upward,'estimated entry connector has reversed exterior roof normal'
    assert 626838819 not in spec['baseBuildingIdsToExclude'] and 1023947435 not in spec['baseBuildingIdsToExclude']
    assert len(spec['baseBuildingIdsToExclude'])==32
    shifted=BRecorder();delta=[23,-45,7]
    mod.build(shifted,{**lm,'x':x+delta[0],'z':z+delta[1],'y':lm['y']+delta[2]},spec,scale)
    for (_,a),(_,b) in zip(rec.faces,shifted.faces):
        for p,q in zip(a,b):assert max(abs(q[i]-p[i]-delta[i]) for i in range(3))<1e-8
    invalid=BRecorder()
    try:mod.build(invalid,lm,spec,scale*scale)
    except ValueError:pass
    else:raise AssertionError('repeated scale accepted')
    assert not invalid.faces and invalid.frame==(11,22,.3)
    result={'schemaVersion':1,'status':'passed-host-contract-only','reviewedBy':'landmark_evidence CPU recorder',
      'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'sourceModuleSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),'faces':len(rec.faces),
      'trianglesBeforeBlenderExport':len(triangles),'materials':sorted(rec.groups),'lights':0,'waterMeshes':0,
      'minimumFanTriangleAreaGameUnits2':minimum,'sourceAxisRadiansEastCCW':angle,'sourceExclusions':32,
      'candidateHighestGeometryAboveBaseM':(high-lm['y'])/scale,'reportedSphereDiameterM':85,
      'frontGlassRay':{'radiusM':glass_r,'expectedM':expected},'terraceRaySamples':radial_samples,'roundedPodiumRaySamples':roof_samples,
      'checks':['finite/nondegenerate fan triangles','exact main/sphere/entry WGS84 projection','0.60 dimensions once',
        'game-unit XYZ translation','B frame restored','reject repeated scale','85m overall cap height',
        '85m reported sphere envelope rather than108m unverified source layer','theatre-facing recessed glass ray',
        'shallow glass skylight down ray','gold terrace/recess geometry rays','rounded rather than flat podium',
        'front/rear connector roof rays and outward upper normals',
        '32object-specific exclusions, no theatre orN2','26000triangle/7material ceilings','no water or lights'],
      'limitations':['CPU fan count is not an exported GLB stat.','No Blender/browser/runtime collision was run.',
        'Sphere centre/cuts, podium section, levels and arrivals are estimates with unknown real ground datum.',
        'Gold-tinted glass/material, exact floor scope, full facade shape, night and performance remain pending.']}
    (OUT/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
