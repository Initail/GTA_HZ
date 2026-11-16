"""Pure CPU geometry, projection, scale, and single-open-arch checks."""
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


def main():
    spec=json.loads((OUT/'spec.json').read_text());city=load_city('hangzhou');scale=city['geography']['scale']
    module_path=ROOT/'scripts/landmarks/broken_bridge.py'
    ms=importlib.util.spec_from_file_location('broken_bridge_candidate',module_path)
    mod=importlib.util.module_from_spec(ms);ms.loader.exec_module(mod)
    x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city)
    lm={'x':x,'z':z,'y':13.25};rec=BRecorder();previous=rec.frame
    report=mod.build(rec,lm,spec,scale)
    assert rec.frame==previous
    assert report['archCount']==1 and report['waterMeshes']==0 and 'water' not in rec.groups
    assert set(rec.groups)==set(report['materials']) and len(rec.groups)<=spec['budget']['maxMaterials']
    assert report['lights']==0
    triangles=[];minimum=math.inf
    for material,face in rec.faces:
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):
            a,b,c=face[0],face[i],face[i+1];area=math.sqrt(dot(cross(sub(b,a),sub(c,a)),cross(sub(b,a),sub(c,a))))/2
            assert area>1e-10,('degenerate triangle',material,face)
            minimum=min(minimum,area);triangles.append((a,b,c))
    assert len(triangles)<=spec['budget']['maxTriangles'],len(triangles)
    assert len(rec.faces)==report['faces']
    angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle)
    def local(u,v,h):return(x+(u*ca-v*sa)*scale,z+(u*sa+v*ca)*scale,lm['y']+h*scale)
    length=spec['bridgeLengthM'];center=report['archCenterRelativeM'];radius=spec['clearArchSpanM']/2
    for u,wgs in zip([-length/2,length/2],spec['endpointsWGS84']):
        expected=project(*wgs,city);p=local(u,0,mod.deck_height_metres(u,spec))
        assert max(abs(expected[i]-p[i]) for i in range(2))<1e-6, 'source endpoints/projection/direction mismatch'
        assert abs(p[2]-lm['y'])<1e-10,'endpoint gameY was rescaled or joins have a step'
    profile=report['deckProfileMetres']
    assert all(profile[i][0]<=profile[i+1][0] for i in range(len(profile)-1))
    assert max(abs(mod.deck_height_metres(u,spec)-h) for u,h in profile)<1e-9
    assert max(h for u,h in profile)>.5,'bridge deck unexpectedly flat'
    spring=spec['estimates']['archSpringRelativeM']['value']
    # A real ray crossing both side faces must remain clear below the crown.
    direction=(-sa,ca,0)
    opening_origin=local(center,-20,spring+radius*.8)
    opening_hits=[d for a,b,c in triangles if (d:=ray_triangle(opening_origin,direction,a,b,c)) is not None]
    assert not opening_hits, 'the single arch opening was filled by body/rail/joint geometry'
    solid_origin=local(center+radius+1,-20,spring+.5)
    solid_hits=[d for a,b,c in triangles if (d:=ray_triangle(solid_origin,direction,a,b,c)) is not None]
    assert solid_hits,'abutment beside the arch is missing'
    down_origin=local(center,0,report['candidateCrestM']+10)
    down_hits=[d for a,b,c in triangles if (d:=ray_triangle(down_origin,(0,0,-1),a,b,c)) is not None]
    assert down_hits and abs(min(down_hits)-10*scale)<1e-8,'no continuous deck over the arch'
    shifted=BRecorder();delta=[23,-45,7]
    mod.build(shifted,{**lm,'x':lm['x']+delta[0],'z':lm['z']+delta[1],'y':lm['y']+delta[2]},spec,scale)
    for (_,a),(_,b) in zip(rec.faces,shifted.faces):
        for p,q in zip(a,b):assert max(abs(q[i]-p[i]-delta[i]) for i in range(3))<1e-8
    invalid=BRecorder()
    try:mod.build(invalid,lm,spec,scale*scale)
    except ValueError:pass
    else:raise AssertionError('repeated scale accepted')
    assert not invalid.faces and invalid.frame==(11,22,.3)
    result={'schemaVersion':1,'status':'passed-host-contract-only','reviewedBy':'landmark_evidence CPU recorder',
        'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sourceModuleSha256':hashlib.sha256(module_path.read_bytes()).hexdigest(),
        'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
        'faces':len(rec.faces),'trianglesBeforeBlenderExport':len(triangles),'materials':sorted(rec.groups),
        'lights':0,'waterMeshes':0,'minimumFanTriangleAreaGameUnits2':minimum,
        'sourceEndpointNodes':spec['sourceRoadNodeIds'],'archCount':1,'clearArchSpanM':radius*2,
        'candidateCrestM':report['candidateCrestM'],'openingRayHits':0,
        'deckDownRayHeightGameAboveEndpoints':report['candidateCrestM']*scale,
        'checks':['finite/nondegenerate triangle fans','exact source endpoint WGS84 placement',
            '0.60 dimensions once','game-unit endpoint/baseY translation','B frame restored','reject repeated scale',
            'single clear semicircular opening','solid adjacent abutment','continuous deck above arch',
            'non-flat gradual deck profile','no water/park material geometry','provisional budgets'],
        'limitations':['No Blender or browser was started.','Triangle fan count is not an actual exported GLB stat.',
            'Ray checks are geometry checks, not runtime collision/walking acceptance.',
            'Arch position and all vertical ground/water parameters are estimated, not surveyed.',
            'Lamps, pavilions, full ornament and current visual/night/performance checks pending.']}
    (OUT/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
