"""Read-only input audit and serialized global/local boundary contract."""
from pathlib import Path
import json,hashlib,ast,struct,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box,mapping,shape
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;BASE=OUT.parent.parent
bindings={}
def bind(p):
 p=Path(p);p=p if p.is_absolute() else ROOT/p;bindings[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
helper=bind(BASE/'shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(helper),'exec'),globals())
old=BASE/'city-balcony-terrain-partition-v1';new=OUT.parent/'bounded-overlay-v1';bbox=read(old/'candidate-contract.json')['bboxGame'];crop=box(*bbox);x0,y0,x1,y1=bbox;w=x1-x0;h=y1-y0
def station(p):
 x,y=p
 if abs(y-y0)<1e-7:return x-x0
 if abs(x-x1)<1e-7:return w+y-y0
 if abs(y-y1)<1e-7:return w+h+x1-x
 if abs(x-x0)<1e-7:return 2*w+h+y1-y
 raise ValueError(p)
def boundary(directory):
 mesh=np.load(bind(directory/'local-terrain.npz'));rows=[];vertices={}
 for e in read(directory/'vertical-boundaries.json')['openBoundary']:
  if e['kind']!='local-crop-open':continue
  tri=mesh['top'][e['topFace']];ps=[]
  for xy in e['edge']:
   ds=np.linalg.norm(tri[:,:2]-xy,axis=1);j=int(np.argmin(ds));assert ds[j]<1e-7
   p=[*map(float,xy),float(tri[j,2])];ps.append(p);vertices[tuple(xy)]=p
  ps.sort(key=lambda p:station(p[:2]));a,b=[station(p[:2]) for p in ps]
  # Lower-left is station zero but terminal left-edge representation is perimeter.
  if b-a>max(w,h)*1.5:ps.reverse();a=station(ps[0][:2]);b=2*(w+h)
  rows.append({'stationStart':a,'stationEnd':b,'enu':ps,'sourceTopTriangle':e['topFace']})
 rows.sort(key=lambda r:r['stationStart']);chains=[]
 for r in rows:
  if chains and abs(chains[-1]['stationEnd']-r['stationStart'])<1e-7:
   assert np.linalg.norm(np.array(chains[-1]['enu'][-1])-r['enu'][0])<1e-7
   chains[-1]['enu'].append(r['enu'][1]);chains[-1]['stationEnd']=r['stationEnd']
  else:chains.append({'stationStart':r['stationStart'],'stationEnd':r['stationEnd'],'enu':r['enu'].copy()})
 return {'vertexCount':len(vertices),'edgeCount':len(rows),'orderedUniqueVerticesENU':sorted(vertices.values(),key=lambda p:station(p[:2])),'orderedSegments':rows,'orderedPolylines':chains}
original=boundary(old);current=boundary(new)
parts,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');bank=next(p for p in parts if p['name']=='coastal_shore_5_-4_land');tops=[]
for i,t in enumerate(bank['triangles']):
 n=np.cross(t[1]-t[0],t[2]-t[0]);length=np.linalg.norm(n)
 if length and n[2]/length>.99:tops.append({'actualTriangleIndex':i,'enu':np.array(t).tolist()})
raw=shapely.union_all([Polygon(np.array(r['enu'])[:,:2]) for r in tops]);city=read('artifacts/cities/hangzhou/render-input-v7/city.json');wet=shapely.union_all([Polygon(r['rings'][0],r['rings'][1:]) for r in city['water']]);owner=raw.difference(wet)
save('shore-top-owner-full.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'city-balcony:actual-shore-top-full','role':'render-only upward top ownership; physics unchanged'},'geometry':mapping(owner)},{'type':'Feature','properties':{'id':'city-balcony:actual-shore-top-outside-crop'},'geometry':mapping(owner.difference(crop))}]})
save('shore-top-actual-triangles.json',{'mesh':'coastal_shore_5_-4_land','classification':'ENU normal z / norm > 0.99','triangles':tops})
save('original-crop-boundary.json',original);save('candidate-terrain-owned-crop-boundary.json',current)
lines=shapely.union_all([LineString(r['enu'][i][:2] for i in [0,1]) for r in original['orderedSegments']]);newlines=shapely.union_all([LineString(r['enu'][i][:2] for i in [0,1]) for r in current['orderedSegments']]);handoff=lines.difference(newlines)
save('bank-handoff-crop-intervals.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'original terrain edge transferred to actual bank; linear ENU height comes from adjacent terrain segments or actual bank triangles'},'geometry':mapping(handoff)}]})
oldlookup={tuple(p[:2]):p[2] for p in original['orderedUniqueVerticesENU']};shared=[abs(p[2]-oldlookup[tuple(p[:2])]) for p in current['orderedUniqueVerticesENU'] if tuple(p[:2]) in oldlookup]
save('contract.json',{'schema':1,'status':'boundary contract; entire replacement not yet accepted','units':'game ENU','bboxGame':bbox,'stationRule':'counterclockwise from southwest, bottom then right then top then left','cropMovement':0,'sourceBoundaryVertices':original['vertexCount'],'candidateBoundaryVertices':current['vertexCount'],'sharedVertexCount':len(shared),'sharedVertexMaximumHeightChange':max(shared),'shoreAssetSha256':bindings['artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb'],'bankTopAreaFull':owner.area,'bankTopAreaOutsideCrop':owner.difference(crop).area,'bankHandoffLength':handoff.length,'terrainHeightRule':'Reuse orderedSegments ENU endpoints and linear segment height, do not resample outside F1 at these shared edges. Original 391 source nodes retained separately; bank-owned intervals must not be restored as duplicate terrain.','ownership':'Subtract full upward top mask from global render terrain, including outside crop. Keep original physical support. Bank side projections are coverage evidence only, not a terrain removal mask.','limitations':['Candidate generated before final geometry freeze; bind input NPZ SHA and replace this contract if final crop changes','Full outside-crop bank height compatibility remains a separate check','No browser/GPU or global crop insertion acceptance'],'inputSha256':bindings})
print(json.dumps({'original':original['vertexCount'],'candidate':current['vertexCount'],'shared':len(shared),'fullArea':owner.area,'outsideArea':owner.difference(crop).area,'handoffLength':handoff.length},indent=2))
