"""Independent bounded render-overlay audit; source physics stays separate."""
from pathlib import Path
import json,hashlib,math,ast,struct,collections,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface,digest
from hangzhou_site_surfaces import SiteSurfaces
from hangzhou_site_partition import plane,polygon_parts
bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
site=read(OUT.parent/'site-surfaces-repair.json');physical=SiteSurfaces(site);field=Surface(ROOT/'artifacts/cities/hangzhou/render-input-v7');field.sites=physical;mesh=np.load(bind(OUT/'local-terrain.npz'));top=mesh['top'];walls=mesh['walls'];meta=read(OUT/'top-provenance.json');domain={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']};mask=shape(read(OUT.parent/'bank-top-render-owner-mask.geojson')['features'][0]['geometry']);expected=domain['dry'].difference(mask);polys=[Polygon(t[:,:2]) for t in top];actual=shapely.union_all(polys);tree=STRtree(polys);shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');shore=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');st=np.array([t for t in shore['triangles'] if np.cross(t[1]-t[0],t[2]-t[0])[2]/np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>.99]);bank=shapely.union_all([Polygon(t[:,:2]) for t in st])
def topology(ts):
 edges=collections.defaultdict(list);zero=0
 for i,t in enumerate(ts):
  zero+=np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))==0
  for a,b in zip(t,np.roll(t,-1,axis=0)):
   a,b=tuple(round(float(v),9) for v in a),tuple(round(float(v),9) for v in b)
   if a!=b:edges[tuple(sorted([a,b]))].append((i,a<b))
 opens=[];non=[];rev=[]
 for key,uses in edges.items():
  if len(uses)==1:
   p=Point((np.array(key[0][:2])+key[1][:2])/2);kind='crop' if domain['local-crop'].boundary.distance(p)<1e-7 else 'shore-mask' if mask.boundary.distance(p)<.001 else 'source-waterfront' if domain['water'].boundary.distance(p)<1e-7 else 'unexpected';opens.append({'edge':key,'kind':kind})
  elif len(uses)!=2:non.append({'edge':key,'uses':uses})
  elif uses[0][1]==uses[1][1]:rev.append({'edge':key,'uses':uses})
 return {'zero':int(zero),'openCounts':dict(collections.Counter(p['kind'] for p in opens)),'nonmanifold':len(non),'sameDirectionShared':len(rev)},opens,non,rev
topo,openedges,non,rev=topology(np.concatenate([top,walls]));source_edges=shapely.union_all([domain[g['id']].boundary for g in site['terrainCuts']]);smooth=[];narrow=[];maxsmooth=0;fail=[];croperr=0
for i,t in enumerate(top):
 for weights in [[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3]*3]:
  p=np.array(weights)@t;point=Point(p[:2]);distance=source_edges.distance(point);h=field.ground(*p[:2]);err=abs(h-p[2])
  if distance<=.001:narrow.append(err)
  else:
   maxsmooth=max(maxsmooth,err);smooth.append(err)
   if err>.01:fail.append({'triangle':i,'point':p.tolist(),'physics':h,'error':err})
  if domain['local-crop'].boundary.distance(point)<1e-9:croperr=max(croperr,abs(field.uncut_ground(*p[:2])-p[2]))
# Component/hole changes are exposed rather than hidden by area-only metrics.
def summary(poly):
 ps=list(polygon_parts(poly));return {'components':len(ps),'holes':sum(len(p.interiors) for p in ps),'componentAreas':sorted([p.area for p in ps]),'holeAreas':sorted([Polygon(r).area for p in ps for r in p.interiors])}
expected_n=shapely.set_precision(expected,1e-8);actual_n=shapely.set_precision(actual,1e-8);outside=actual.difference(expected.buffer(.001));missing=expected.difference(actual.buffer(.001));supported=actual.union(bank.intersection(domain['dry']));raw_gap=domain['dry'].difference(supported);gapfar=raw_gap.difference(bank.boundary.buffer(.001))
# Actual floor underside coverage uses linked actual GLB faces, never an AABB-only check.
floor,_=glb('artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb');fby={p['name']:p for p in floor};links=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/slab-glb-correspondence.json');floorrows=[]
for slab in links:
 minimum=math.inf;bad=[];area=0
 for ref in slab['actualFaceLinks']:
  link=ref['actualBottomFaces'][0];t=fby[link['mesh']]['triangles'][link['triangleIndex']];q=Polygon(t[:,:2]);h=plane(list(reversed(t)) if not q.exterior.is_ccw else t)
  for j in map(int,tree.query(q,predicate='intersects')):
   over=q.intersection(polys[j]);gh=plane(top[j])
   for poly in polygon_parts(over):
    if poly.area<=1e-12:continue
    ds=[h(x,z)-gh(x,z) for x,z in poly.exterior.coords];minimum=min(minimum,min(ds));area+=poly.area
    if min(ds)<-1e-5:bad.append({'floorFace':link,'terrainFace':j,'area':poly.area,'minBottomMinusTerrain':min(ds)})
 floorrows.append({'id':slab['id'],'minimumActualSlabBottomClearanceGame':minimum,'overlapArea':area,'penetratingPairs':len(bad),'failures':bad})
# Remaining actual top-sheet intersections: near-coincidence is separate from safely buried bank.
remaining=[];visiblebad=[]
for k,t in enumerate(st):
 q=Polygon(t[:,:2]);h=plane(t)
 for j in map(int,tree.query(q,predicate='intersects')):
  for p in polygon_parts(q.intersection(polys[j])):
   if p.area<=1e-12:continue
   gh=plane(top[j]);ds=[h(x,z)-gh(x,z) for x,z in p.exterior.coords];r={'shoreTop':k,'terrainFace':j,'area':p.area,'minShoreMinusTerrain':min(ds),'maxShoreMinusTerrain':max(ds)};remaining.append(r)
   if max(ds)>=-1e-5:visiblebad.append(r)
report={'meshSha256':bindings[str((OUT/'local-terrain.npz').relative_to(ROOT))],'physicsSha256':bindings[str((OUT.parent/'site-surfaces-repair.json').relative_to(ROOT))],'topTriangles':len(top),'wallTriangles':len(walls),'topology':topo,'boundaryBudgetGame':.001,'rawDomainSymmetricDifferenceArea':actual.symmetric_difference(expected).area,'normalizedBoundaryHausdorffGame':expected_n.boundary.hausdorff_distance(actual_n.boundary),'addedAreaBeyond1mmBudget':outside.area,'missingAreaBeyond1mmBudget':missing.area,'sourceAndResultDomainTopology':{'expected':summary(expected),'actual':summary(actual),'normalizedExpected':summary(expected_n),'normalizedActual':summary(actual_n)},'combinedDryBoundaryHausdorffGame':shapely.set_precision(supported,1e-8).boundary.hausdorff_distance(shapely.set_precision(domain['dry'],1e-8).boundary),'combinedDomainTopology':summary(supported),'rawTerrainPlusActualBankGapArea':raw_gap.area,'gapAreaAwayFromActualBankBoundary1mmBand':gapfar.area,'terrainWaterOverlapArea':actual.intersection(domain['water']).area,'smoothSampleCount':len(smooth),'smoothMaximumSourcePhysicsErrorGame':maxsmooth,'smoothFailuresAbovePoint01':len(fail),'sourceDiscontinuityBandGame':.001,'bandSampleCount':len(narrow),'bandMaximumHeightDifferenceGame':max(narrow,default=0),'cropSourceF1MaxSampleErrorGame':croperr,'floorChecks':[{k:v for k,v in r.items() if k!='failures'} for r in floorrows],'remainingBankProjectedOverlapArea':sum(r['area'] for r in remaining),'remainingVisibleOrNearCoplanarPairs':len(visiblebad),'remainingVisibleOrNearCoplanarArea':sum(r['area'] for r in visiblebad),'minimumRemainingShoreMinusTerrain':min((r['minShoreMinusTerrain'] for r in remaining),default=None),'maximumRemainingShoreMinusTerrain':max((r['maxShoreMinusTerrain'] for r in remaining),default=None),'notAccepted':['Actual GLB export','Global crop insertion','Body/road/navigation/browser','Separate tunnel and service-road height blocker']}
save('validation.json',report);save('validation-details.json',{'smoothFailures':fail,'openEdges':openedges,'nonmanifold':non,'reversedEdges':rev,'floor':floorrows,'remainingVisibleOverlap':visiblebad});save('input-bindings-review.json',bindings);print(json.dumps({k:v for k,v in report.items() if k!='sourceAndResultDomainTopology'},indent=2),flush=True)
