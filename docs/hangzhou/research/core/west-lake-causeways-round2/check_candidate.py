"""Substantive CPU/source checks; no Blender and no final game acceptance claim."""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
    ref=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(ref);ref.loader.exec_module(mod);return mod

class Collector:
    def __init__(self):self.frame=(17,29,.7);self.faces=[]
    def face(self,material,ps):
        x,y,angle=self.frame;ca,sa=math.cos(angle),math.sin(angle)
        out=[(p[0]*ca-p[1]*sa+x,p[0]*sa+p[1]*ca+y,p[2]) for p in ps]
        self.faces.append((material,out))

def main():
    spec=json.loads((HERE/'spec.json').read_text());path=ROOT/'scripts/landmarks/west_lake_causeways.py'
    mod=load('west_lake_causeways_cpu',path);g=load_city('hangzhou')['geography']
    lm={'x':0,'z':0,'y':7.25,'lon':spec['anchor']['lon'],'lat':spec['anchor']['lat']}
    c=Collector();old=c.frame;report=mod.build(c,lm,spec,.6);assert c.frame==old
    checks=[]
    def check(name,ok,detail):
        assert ok,name;checks.append({'id':name,'status':'pass','scope':'CPU structural only','detail':detail})
    imports=[]
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
        if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
    check('no-scene-import',not any('bpy' in i or 'city_mesh' in i for i in imports),imports)
    check('finite-scope',report['pathCount']==19 and report['bridgeCount']==7 and report['landStripCount']==7 and report['waterMeshes']==0,
          '19 source path objects, seven distinct bridge bodies, seven mapped land strips; no candidate lake plane')
    check('external-broken-bridge-preserved',28538289 not in [p['wayId'] for p in spec['paths']] and report['externalWayIds']==[28538289],
          'source graph reference only; external bridge mesh not rebuilt or marked for exclusion')
    fixed=json.loads((HERE/'source-geometry.geojson').read_text());fs={(f['properties']['osm_type'],f['properties']['osm_id']):f for f in fixed['features']}
    check('source-paths-exact',all(p['coordinatesWGS84']==fs['way',p['wayId']]['geometry']['coordinates'] and p['nodes']==fs['way',p['wayId']]['properties']['nodeIds'] for p in spec['paths']),
          'all original road coordinates and node IDs preserved verbatim')
    check('source-land-rings-exact',all(l['ringsWGS84']==fs[tuple(l['sourceId'].split('/'))[0],int(l['sourceId'].split('/')[1])]['geometry']['coordinates'][0] for l in spec['landStrips']),
          'land caps retain mapped rings; no parcel/city-wide land exclusion')
    chains=json.loads((HERE/'path-connectivity.json').read_text())['chains']
    check('source-continuous-chains',all(all(p['endNode']==q['startNode'] and p['endWGS84']==q['startWGS84'] for p,q in zip(ch['sequence'],ch['sequence'][1:])) for ch in chains),
          'Bai/Su exact node chains including six Su bridge gaps and external Broken Bridge; no geometric-only join')
    check('bridge-endpoint-height',all(abs(mod.bridge_height_metres(0,p))<1e-10 and abs(mod.bridge_height_metres(p['sourceLengthM'],p))<1e-10 for p in spec['paths'] if p['bridge']),
          'each bridge starts/ends exactly at neutral road endpoint lm.y; world terrain integration still pending')
    bridge_lookup=[];voids=[];face0=0
    for part,count in report['partTriangles'].items():
        faces=[];accum=0
        while accum<count:
            material,ps=c.faces[face0];faces.append((material,ps));accum+=len(ps)-2;face0+=1
        assert accum==count
        if not part.startswith('bridge-'):continue
        i=int(part.split('-')[1]);p=next(p for p in spec['paths'] if p['wayId']==i);v=mod._bridge_sections(p,mod._context(lm,spec));a=mod._context(lm,spec)['xy'](p['coordinatesWGS84'][0])
        for _,ps in faces:
            for x,y,z in ps:
                x,y,z=x/.6-a[0],y/.6-a[1],(z-lm['y'])/.6
                s=x*v['axis'][0]+y*v['axis'][1]
                if abs(s-v['center'])<v['radius']-1e-6:
                    assert z>=mod.arch_soffit_metres(s,p)-.06, ('Vertex intrudes into arch void',i,s,z)
        for q in p['coordinatesWGS84']:
            h=mod.bridge_height_at(q[0],q[1],lm,spec,.6);assert h is not None and abs(h-lm['y'])<1e-7
        mid=[(p['coordinatesWGS84'][0][k]+p['coordinatesWGS84'][-1][k])/2 for k in (0,1)]
        h=mod.bridge_height_at(mid[0],mid[1],lm,spec,.6)
        assert math.isclose(h,lm['y']+mod.bridge_height_metres(p['sourceLengthM']/2,p)*.6,abs_tol=1e-7)
        bridge_lookup.append(i);voids.append({'wayId':i,'checkedVertices':sum(len(ps) for _,ps in faces),'archCount':1,'clearSpanM':p['bridge']['clearArchSpanM']})
    check('seven-open-arch-voids',len(voids)==7,voids)
    check('source-aware-height-lookup',len(bridge_lookup)==7,'every bridge source endpoint and midpoint returns the same profile used by the mesh')
    check('grass-minus-travel-union',0<report['candidateGrassCapAreaM2']<report['sourceLandAreaM2'],
          {'sourceLandAreaM2':report['sourceLandAreaM2'],'grassAfterTravelSubtractionM2':report['candidateGrassCapAreaM2']})
    # A land square with overlapping travel exclusion rectangles detects XOR fills.
    square=[[(0,0),(10,0),(10,10),(0,10)]];cuts=[[(2,0),(6,0),(6,10),(2,10)],[(4,0),(8,0),(8,10),(4,10)]]
    residual=sum(abs(mod._area(q)) for q in mod._caps_minus(square,cuts))
    check('union-not-XOR-overlaps',math.isclose(residual,40,abs_tol=1e-8),'overlapping excluded ribbons remain empty (union), unlike odd/even XOR holes')
    d=Collector();lm2=dict(lm,y=lm['y']+10);mod.build(d,lm2,spec,.6)
    check('game-height-not-rescaled',all(math.isclose(q[2]-p[2],10,abs_tol=1e-8) for (_,ps),(_,qs) in zip(c.faces,d.faces) for p,q in zip(ps,qs)),
          'adding ten game units to lm.y adds exactly ten to every generated vertex')
    lm3=dict(lm,lon=lm['lon']+.001,lat=lm['lat']-.001,x=0,z=0);z=Collector();mod.build(z,lm3,spec,.6)
    dx=-.001*g['eastMetresPerDegree']*.6;dy=.001*g['northMetresPerDegree']*.6
    check('source-offset-scaled-once',all(math.isclose(q[0]-p[0],dx,abs_tol=1e-6) and math.isclose(q[1]-p[1],dy,abs_tol=1e-6) for (_,ps),(_,qs) in zip(c.faces,z.faces) for p,q in zip(ps,qs)),
          'offset for a changed WGS84 anchor follows canonical projection and a single0.60 factor')
    canonical=Collector();canonical_lm={'x':(spec['anchor']['lon']-g['originWGS84'][0])*g['eastMetresPerDegree']*.6,'z':(spec['anchor']['lat']-g['originWGS84'][1])*g['northMetresPerDegree']*.6,'y':lm['y']};mod.build(canonical,canonical_lm,spec,.6)
    check('blender-frame-game-anchor',all(math.isclose(q[0]-p[0],canonical_lm['x'],abs_tol=1e-6) and math.isclose(q[1]-p[1],canonical_lm['z'],abs_tol=1e-6) for (_,ps),(_,qs) in zip(c.faces,canonical.faces) for p,q in zip(ps,qs)),
          'x/z anchor is translated in B.frame without another0.60 factor; no extra root rotation')
    class Fail(Collector):
        def face(self,mat,pts):raise RuntimeError('injected CPU collector failure')
    fail=Fail();before=fail.frame
    try:mod.build(fail,lm,spec,.6)
    except RuntimeError:pass
    check('frame-restored-success-and-error',c.frame==old and fail.frame==before,'B.frame always restored with finally')
    check('budget',report['triangles']<=60000 and len(report['materials'])<=12 and report['newTextures']==report['newLights']==0,
          {'triangles':report['triangles'],'materials':report['materials'],'newLights':0,'newTextures':0,'actualGLBBytes':'unknown until export'})
    check('finite-geometry',all(all(math.isfinite(x) for x in p) for _,ps in c.faces for p in ps),'all generated B vertices finite')
    result={'stage':'CPU candidate only; not game silhouette/collision/browser/performance acceptance','sourceModuleSha256':sha(path),'specSha256':sha(HERE/'spec.json'),
        'checks':checks,'report':report,'command':'python3 -B docs/hangzhou/research/core/west-lake-causeways-round2/check_candidate.py',
        'limitations':spec['pendingSubscopes'],'modelExported':False,'actualInGameScreenshots':[]}
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':len(checks),'triangles':report['triangles'],'materials':report['materials'],'bridges':7,'sourceModuleSha256':sha(path)}))

if __name__=='__main__':main()
