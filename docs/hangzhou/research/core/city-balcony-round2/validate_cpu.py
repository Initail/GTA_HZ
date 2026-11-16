"""CPU B geometry and source-contact checks, not runtime acceptance."""
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
class BRecorder:
    def __init__(self):self.frame=(11,22,.3);self.faces=[];self.groups=defaultdict(list)
    def face(self,mat,points,uv=None):
        x,y,a=self.frame;ca,sa=math.cos(a),math.sin(a);q=[(u*ca-v*sa+x,u*sa+v*ca+y,z) for u,v,z in points]
        self.faces.append((mat,q));self.groups[mat].append(q)
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def load():
    spec=json.loads((OUT/'spec.json').read_text());p=ROOT/'scripts/landmarks/city_balcony.py';ms=importlib.util.spec_from_file_location('balcony',p);mod=importlib.util.module_from_spec(ms);ms.loader.exec_module(mod);return spec,p,mod
def main():
    from shapely.geometry import Polygon
    spec,path,mod=load();city=load_city('hangzhou');scale=city['geography']['scale'];x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city);lm={'x':x,'z':z,'y':13.25}
    b=BRecorder();frame=b.frame;report=mod.build(b,lm,spec,scale);assert b.frame==frame
    ts=[];minimum=math.inf
    for mat,face in b.faces:
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):
            a,c,d=face[0],face[i],face[i+1];n=cross(sub(c,a),sub(d,a));area=math.sqrt(dot(n,n))/2
            assert area>1e-10,(mat,face);minimum=min(area,minimum);ts.append((mat,[a,c,d]))
    assert len(ts)<=spec['budget']['maxTriangles'],len(ts)
    assert len(b.groups)<=spec['budget']['maxMaterials']
    assert report['waterMeshes']==report['lights']==report['stairsRampsLiftMeshes']==0
    assert report['mappedGlazedParts']==3 and report['shoreApproachCount']==2
    roof_z=lm['y']+(spec['estimates']['levels']['value']['upperM']+spec['estimates']['glazedHeads']['value']['roofRiseM'])*scale
    head_roofs=[face for mat,face in b.faces if mat=='landmarkglass' and len(face)==4 and all(abs(p[2]-roof_z)<1e-8 for p in face)]
    assert len(head_roofs)==3
    assert all(cross(sub(ps[1],ps[0]),sub(ps[2],ps[0]))[2]>0 for ps in head_roofs),'source interior ring winding inverted glass head roofs'
    assert not any(m in ('water','park') for m in b.groups)
    angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle)
    def local(u,v):return [x+(u*ca-v*sa)*scale,z+(u*sa+v*ca)*scale]
    for uv,wgs in zip(spec['upperOuterUVMetres'],spec['upperOuterWGS84']):assert max(abs(a-b) for a,b in zip(local(*uv),project(*wgs,city)))<1e-6
    for level in ('upper','lower'):
        polygon=Polygon(spec[level+'OuterUVMetres'],spec['glazedFootprintsUVMetres']);tr=spec[level+'TrianglesUVMetres']
        assert all(polygon.covers(Polygon(t)) for t in tr)
        assert abs(sum(Polygon(t).area for t in tr)-polygon.area)<1e-6
        assert all((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0])>0 for t in tr),'deck top normals point down'
        for i,t in enumerate(tr):
            center=Polygon(t).centroid;u,v=center.x,center.y;h=mod.deck_height_metres(u,v,spec,level)
            assert h==spec['estimates']['levels']['value'][level+'M']
            game=local(u,v);assert abs(mod.deck_height_game(*game,lm,spec,scale,level)-(lm['y']+h*scale))<1e-8
        for ring in spec['glazedFootprintsUVMetres']:
            center=Polygon(ring).centroid;assert mod.deck_height_metres(center.x,center.y,spec,level) is None
        assert mod.deck_height_metres(9999,9999,spec,level) is None
    # A rear source bridge has an upper surface but deliberately no lower slab.
    upper_only=0
    for t in spec['upperTrianglesUVMetres']:
        p=Polygon(t).centroid
        if mod.deck_height_metres(p.x,p.y,spec,'lower') is None and not any(Polygon(r).covers(p) for r in spec['glazedFootprintsUVMetres']):upper_only+=1
    assert upper_only>0,'shore bridge ground was closed by a duplicated full lower slab'
    footprints=mod.ground_footprints(lm,spec,scale)
    assert footprints and not any(f['kind']=='whole-platform' for f in footprints)
    for f in footprints:
        assert Polygon(f['polygonGame']).area>0 and f['maxYGame']>f['minYGame']
        assert set(f['sourceFeatureIds']).issubset(set(spec['sourceFeatureIds']))
    shifted=BRecorder();delta=(23,-45,7);mod.build(shifted,{**lm,'x':x+delta[0],'z':z+delta[1],'y':lm['y']+delta[2]},spec,scale)
    for (_,a),(_,c) in zip(b.faces,shifted.faces):
        for p,q in zip(a,c):assert max(abs(q[i]-p[i]-delta[i]) for i in range(3))<1e-8
    moved=mod.ground_footprints({**lm,'x':x+23,'z':z-45,'y':lm['y']+7},spec,scale)
    for a,c in zip(footprints,moved):
        for p,q in zip(a['polygonGame'],c['polygonGame']):assert max(abs(q[i]-p[i]-delta[i]) for i in [0,1])<1e-8
        assert abs(c['minYGame']-a['minYGame']-7)<1e-8
    invalid=BRecorder()
    try:mod.build(invalid,lm,spec,scale*scale)
    except ValueError:pass
    else:raise AssertionError('double scaling accepted')
    assert not invalid.faces and invalid.frame==frame
    result={'schemaVersion':1,'status':'passed-host-contract-only','at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'sourceModuleSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
      'faces':len(b.faces),'trianglesBeforeBlenderExport':len(ts),'materials':sorted(b.groups),'minimumTriangleAreaGameUnits2':minimum,
      'publicLevelsMetres':report['publicLevelsMetres'],'representativePierCount':report['representativePierCount'],
      'solidGroundFootprints':len(footprints),'upperOnlyRearBridgeTriangles':upper_only,'waterMeshes':0,'lights':0,
      'checks':['finite/nondegenerate geometry','fixed28000triangle/7material ceiling','fixed WGS84 footprint vertices/projection',
        '.60 scale once/game-unit baseY and translation','B frame restored','public floor queries agree with constrained triangulation',
        'glazed-room voids excluded from public-floor API','upper approach bridges have no full lower slab','explicit piers/glass strips rather than whole platform obstacles',
        'ground-footprint world translation and source ID binding','no invented stairs/ramps/lifts','no park/water thin slabs'],
      'limitations':['No Blender/browser invoked; no exported GLB/runtime performance or visual acceptance.',
        '6m upper level/3m glazed heads/structure/paving/skylight positions estimated; absolute grade/river datum unknown.',
        'Candidate glass skylight circles are raised surface representations; slab shaft section not reconstructed.',
        'Source shore mouths remain entry candidates. No genuine stairs/ramps/lifts/road-to-foot arrival verification.']}
    (OUT/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','faces','trianglesBeforeBlenderExport','materials','solidGroundFootprints']}))
if __name__=='__main__':main()
