"""CPU B contract checks; never imports city_mesh or initializes Blender."""
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
    spec=json.loads((OUT/'spec.json').read_text());path=ROOT/'scripts/landmarks/big_lotus.py'
    ms=importlib.util.spec_from_file_location('big_lotus_candidate',path)
    mod=importlib.util.module_from_spec(ms);ms.loader.exec_module(mod)
    return spec,path,mod


def main():
    spec,module_path,mod=load();city=load_city('hangzhou');scale=city['geography']['scale']
    x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city)
    lm={'x':x,'z':z,'y':13.25};rec=BRecorder();old=rec.frame
    report=mod.build(rec,lm,spec,scale)
    assert rec.frame==old and len(rec.faces)==report['faces']
    assert report['petalCounts']=={'large':28,'small':27} and report['seatingTiers']==3
    assert report['waterMeshes']==report['roofCenterClosureMeshes']==report['lights']==0
    assert 'water' not in rec.groups and set(rec.groups)==set(report['materials'])
    assert len(rec.groups)<=spec['budget']['maxMaterials']
    triangles=[];minimum=math.inf
    for material,face in rec.faces:
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):
            a,b,c=face[0],face[i],face[i+1];normal=cross(sub(b,a),sub(c,a))
            area=math.sqrt(dot(normal,normal))/2
            assert area>1e-10,('degenerate fan triangle',material,face)
            minimum=min(minimum,area);triangles.append((a,b,c))
    assert len(triangles)<=spec['budget']['maxTriangles'],len(triangles)
    angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle)
    def local(u,v,h):return(x+(u*ca-v*sa)*scale,z+(u*sa+v*ca)*scale,lm['y']+h*scale)
    # Exact original source vertices are reconstructed by radial functions and
    # canonical projection; the render lip is a separate84-segment approximation.
    for ring_key,wgs_key in [('innerUVMetres','innerRoofOpeningWGS84'),('outerUVMetres','outerFootprintWGS84')]:
        for p,wgs in zip(spec[ring_key],spec[wgs_key]):
            theta=math.atan2(p[1],p[0]);r=mod.radial_boundary_metres(spec[ring_key],theta)
            assert abs(r-math.hypot(*p))<1e-7,'source boundary radial reconstruction differs'
            world=local(*p,0);expected=project(*wgs,city)
            assert max(abs(expected[i]-world[i]) for i in range(2))<1e-6
    top=max(p[2] for material,face in rec.faces for p in face)
    top_m=(top-lm['y'])/scale
    assert abs(top_m-spec['heightM'])<.5,('height/source datum mismatch',top_m)
    # Real vertical rays must find only the field at the core, never a roof disk.
    open_rays=[]
    for u,v in [(0,0),(20,10),(-20,-10),(25,-20),(-25,20)]:
        start=local(u,v,70)
        hits=[d for a,b,c in triangles if (d:=ray_triangle(start,(0,0,-1),a,b,c)) is not None]
        assert hits,'representative field missing'
        first_height=70-min(hits)/scale
        assert first_height<.2,('central opening obstructed',u,v,first_height)
        open_rays.append({'uvM':[u,v],'highestSurfaceAboveIsolatedBaseM':first_height})
    # A down ray on a large canopy blade confirms roof geometry actually exists.
    p=mod.petal_point_metres(spec,0,.88,0,False);start=local(p[0],p[1],70)
    hits=[d for a,b,c in triangles if (d:=ray_triangle(start,(0,0,-1),a,b,c)) is not None]
    assert hits and 70-min(hits)/scale>45,'annular roof blade missing'
    # No full opaque entrance cylinder at the neutral base. This is not a
    # current-ground/approach collision pass.
    ro=mod.radial_boundary_metres(spec['outerUVMetres'],0)
    entrance_start=local(ro+20,0,1);direction=(-ca,-sa,0)
    hits=[d for a,b,c in triangles if (d:=ray_triangle(entrance_start,direction,a,b,c)) is not None and d<55*scale]
    assert not hits,'candidate ground-level façade slot filled by solid wall'
    shifted=BRecorder();delta=[23,-45,7]
    mod.build(shifted,{**lm,'x':lm['x']+delta[0],'z':lm['z']+delta[1],'y':lm['y']+delta[2]},spec,scale)
    for (_,a),(_,b) in zip(rec.faces,shifted.faces):
        for p,q in zip(a,b):assert max(abs(q[i]-p[i]-delta[i]) for i in range(3))<1e-8
    invalid=BRecorder()
    try:mod.build(invalid,lm,spec,scale*scale)
    except ValueError:pass
    else:raise AssertionError('repeated scale accepted')
    assert not invalid.faces and invalid.frame==(11,22,.3)
    assert 626826731 not in spec['baseBuildingIdsToExclude']
    result={'schemaVersion':1,'status':'passed-host-contract-only','reviewedBy':'landmark_evidence CPU recorder',
      'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'sourceModuleSha256':hashlib.sha256(module_path.read_bytes()).hexdigest(),
      'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
      'faces':len(rec.faces),'trianglesBeforeBlenderExport':len(triangles),'materials':sorted(rec.groups),
      'lights':0,'waterMeshes':0,'minimumFanTriangleAreaGameUnits2':minimum,
      'petalCounts':report['petalCounts'],'seatingTiers':3,'sourceFeatureIds':spec['sourceFeatureIds'],
      'sourceAxisRadiansEastCCW':angle,'candidateHighestGeometryAboveBaseM':top_m,
      'openingDownRays':open_rays,'isolatedGroundSlotRayHits':0,
      'checks':['finite/nondegenerate triangle fans','reported28+27 independent shell loops','three open seating tiers',
        'exact source WGS84 vertex/projection/direction agreement','0.60 dimensions once','game-unit base and XY translation',
        'B frame restored','reject repeated scale','central vertical rays reach field without a roof disk',
        'annular petal roof ray hits','provisional neutral-base façade slot','no water meshes or lights',
        'unchanged28000 triangle/10material ceiling','no tennis-way626826731 in exclusions'],
      'limitations':['No Blender export or browser was run.','CPU fan triangle count is not actual GLB statistics.',
        'Geometry rays are not runtime collision/entrance validation.','Ground and platform datum unknown.',
        'Curves, exact petals phase, reduced seat rows, track and field dimensions are estimates.',
        'Official-photo material matching, sign labels, night, site context, export and performance pending.']}
    (OUT/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
