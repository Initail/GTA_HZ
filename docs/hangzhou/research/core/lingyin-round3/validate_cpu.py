"""Pure B geometry and independent-height API checks; no Blender/browser."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city, project


class Recorder:
    def __init__(self):
        self.frame=(11.,22.,.3)
        self.faces=[]
        self.groups=defaultdict(list)
    def face(self,material,points,uv=None):
        ox,oz,angle=self.frame
        ca,sa=math.cos(angle),math.sin(angle)
        pts=[(ox+x*ca-y*sa,oz+x*sa+y*ca,z) for x,y,z in points]
        self.faces.append((material,pts))
        self.groups[material].append(pts)


def module(name,path):
    loader=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


def triangle_area(a,b,c):
    u=[b[i]-a[i] for i in range(3)]
    v=[c[i]-a[i] for i in range(3)]
    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    return math.sqrt(sum(t*t for t in cross))/2


def fixture():
    spec=json.loads((OUT/'spec.json').read_text())
    site=module('lingyin_site_candidate_cpu',ROOT/'scripts/landmarks/lingyin_site.py')
    city=load_city('hangzhou')
    scale=city['geography']['scale']
    x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city)
    # Deliberately synthetic and not tied to the DSM/actual hall floor heights.
    heights={'kings':37.5,'grand':39.75,'medicine':45.25,'dharma':54.375,'huayan':63.5}
    lm={'x':x,'z':z,'y':9999.75,'hallBaseYGame':heights}
    b=Recorder()
    report=site.build(b,lm,spec,scale)
    return spec,site,city,scale,lm,b,report


def main():
    from shapely.geometry import Polygon
    spec,site,city,scale,lm,b,report=fixture()
    assert b.frame==(11.,22.,.3)
    old=module('lingyin_original_cpu',ROOT/'scripts/landmarks/lingyin_temple.py')
    original=Recorder()
    old_lm={**lm,'y':13.25}
    old.build(original,old_lm,spec['baseHallSpec'],scale)
    neutral=Recorder()
    site.build_with_hall_bases(neutral,lm,spec,{h:13.25 for h in site.HALL_IDS},scale,include_details=False)
    assert neutral.faces==original.faces,'Frozen shell face stream changed'
    triangles=0
    minimum=math.inf
    for mat,face in b.faces:
        assert len(face)>=3 and all(math.isfinite(v) for pt in face for v in pt)
        for i in range(1,len(face)-1):
            area=triangle_area(face[0],face[i],face[i+1])
            assert area>1e-10,(mat,face)
            minimum=min(minimum,area)
            triangles+=1
    assert triangles<=spec['budget']['maxTriangles'],(triangles,spec['budget'])
    assert len(b.groups)<=spec['budget']['maxMaterials'] and set(b.groups)==set(report['materials'])
    assert report['lmYUsed'] is False and report['absoluteGameBaseYUnscaled'] is True
    rows=[]
    cursor=0
    for hall,r in zip(spec['baseHallSpec']['halls'],report['halls']):
        chunk=b.faces[cursor:cursor+r['faces']]
        cursor+=r['faces']
        plinth=[p for _,face in chunk[:6] for p in face]
        center=[sum(p[i] for p in plinth)/len(plinth) for i in [0,1]]
        expected=project(*hall['centroidWGS84'],city)
        assert max(abs(a-c) for a,c in zip(center,expected))<1e-6
        assert abs(min(p[2] for p in plinth)-lm['hallBaseYGame'][hall['id']])<1e-9
        assert r['thresholdYGame']==lm['hallBaseYGame'][hall['id']]+.5*scale
        rows.append({'id':hall['id'],'sourceFeatureIds':hall['sourceFeatureIds'],'baseYGame':r['baseYGame'],
                     'baseBasis':'synthetic CPU fixture, not a factual elevation','centerGame':center,
                     'frozenShellFaces':r['frozenShellFaces'],'facesIncludingDetails':r['faces'],
                     'proceduralStairs':r['estimatedStairCount'],'realStepCount':None})
        ent=spec['terraces'][hall['id']]
        left,right,front,back=site._terrace_bounds(hall,ent)
        x,z=site._to_game(0,(front+back)/2,lm,hall,scale)
        assert abs(site.floor_height_game(x,z,lm,spec,hall['id'],scale)-r['thresholdYGame'])<1e-9
        for _,far,near,_,top in site._stairs(hall,ent):
            x,z=site._to_game(0,(far+near)/2,lm,hall,scale)
            measured=site.floor_height_game(x,z,lm,spec,hall['id'],scale)
            assert abs(measured-(r['baseYGame']+top*scale))<1e-9
        x,z=site._to_game(right+3.,(front+back)/2,lm,hall,scale)
        assert site.floor_height_game(x,z,lm,spec,hall['id'],scale) is None
        x,z=site._to_game(0,0,lm,hall,scale)
        assert site.floor_height_game(x,z,lm,spec,hall['id'],scale) is None,'closed hall must not gain fictional interior surface'
    assert cursor==len(b.faces)
    # One hall can move without moving any other hall or changing triangles.
    changed=Recorder()
    raised={**lm['hallBaseYGame'],'medicine':lm['hallBaseYGame']['medicine']+7.125}
    site.build_with_hall_bases(changed,lm,spec,raised,scale)
    cursor=0
    for r in report['halls']:
        for oldface,newface in zip(b.faces[cursor:cursor+r['faces']],changed.faces[cursor:cursor+r['faces']]):
            assert oldface[0]==newface[0]
            for p,q in zip(oldface[1],newface[1]):
                assert abs(q[0]-p[0])<1e-9 and abs(q[1]-p[1])<1e-9
                assert abs(q[2]-p[2]-(7.125 if r['id']=='medicine' else 0))<1e-9
        cursor+=r['faces']
    shifted=Recorder()
    dx,dz=21.5,-33.75
    site.build(shifted,{**lm,'x':lm['x']+dx,'z':lm['z']+dz,'y':-99999},spec,scale)
    for (_,face),(_,newface) in zip(b.faces,shifted.faces):
        for p,q in zip(face,newface):
            assert max(abs(q[i]-p[i]-[dx,dz,0][i]) for i in range(3))<1e-8
    rejection_cases=[('missing explicit bases',{k:v for k,v in lm.items() if k!='hallBaseYGame'},scale),
                     ('unknown base',{**lm,'hallBaseYGame':{**lm['hallBaseYGame'],'grand':None}},scale),
                     ('nonfinite base',{**lm,'hallBaseYGame':{**lm['hallBaseYGame'],'grand':math.nan}},scale),
                     ('double scale',lm,scale*scale)]
    for name,test_lm,s in rejection_cases:
        rejected=Recorder()
        try:site.build(rejected,test_lm,spec,s)
        except ValueError:pass
        else:raise AssertionError('accepted '+name)
        assert not rejected.faces and rejected.frame==(11.,22.,.3)
    solids=site.ground_footprints(lm,spec,scale)
    for ent in solids:
        p=Polygon(ent['polygonGame'])
        assert p.is_valid and p.area>1e-8 and not p.interiors
        assert ent['maxYGame']>ent['minYGame'] and ent['sourceFeatureIds']
        assert not ent['entranceVerified']
    # A central opening through front balustrades stays clear at walking height;
    # stone terrace/stair solids themselves are intentionally below the floor.
    for hall in spec['baseHallSpec']['halls']:
        left,right,front,back=site._terrace_bounds(hall,spec['terraces'][hall['id']])
        x,z=site._to_game(0,front,lm,hall,scale)
        from shapely.geometry import Point
        assert not any(ent['kind'].startswith('estimated-stone-rail') and ent['hallId']==hall['id'] and Polygon(ent['polygonGame']).covers(Point(x,z)) for ent in solids)
    result={'schemaVersion':1,'status':'passed-host-contract-only','at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'sourceModuleSha256':hashlib.sha256((ROOT/'scripts/landmarks/lingyin_site.py').read_bytes()).hexdigest(),
      'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
      'hallCount':5,'faces':len(b.faces),'trianglesBeforeBlenderExport':triangles,'materials':sorted(b.groups),'lights':0,
      'minimumFanTriangleAreaGameUnits2':minimum,'collisionPolygons':len(solids),'hallRows':rows,
      'frozenShellStreamSha256':hashlib.sha256(json.dumps(original.faces,separators=(',',':')).encode()).hexdigest(),
      'checks':['frozen .5m-plinth/five shell B.face stream exactly identical at equal heights',
        'five independently translated absolute game base Y values; lm.y ignored',
        'fixed WGS84 centroid placement and single .60 dimension scaling','caller B frame restored',
        'finite nondegenerate fans and declared budget','floor terrace/stair heights match actual generated solids',
        'source-bound finite valid CCW solid polygons and vertical bounds','central front balustrade stair mouths remain open',
        'reject missing/null/nonfinite hall bases and repeated scaling before mutations'],
      'limitations':['Synthetic heights are API test data, not factual floor elevations.',
        'No Blender/browser/GLB/game screenshot/current collision or performance acceptance.',
        'Front terrace lengths/drops/steps are openly estimated and need surveyed terrain/path joining.',
        'No whole-monastery boundary, continuous walkway or accessible-arrival assertion.',
        'Original walls/doors remain closed; this does not create temple interiors.']}
    (OUT/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
