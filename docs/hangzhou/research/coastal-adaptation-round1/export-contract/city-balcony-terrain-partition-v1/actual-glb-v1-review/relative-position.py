"""Height-resolved actual GLB overlap; retain ownership/contact failures."""
from pathlib import Path
import json,hashlib,ast,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');mod=ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]);exec(compile(mod,str(p),'exec'),globals())
actual,_=glb('artifacts/cities/hangzhou/city-balcony-terrain-glb-v1/city-balcony-terrain.glb');floor,_=glb('artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb');shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb')
ground=[]
for part in actual:
 for i,t in enumerate(part['triangles']):
  if np.cross(t[1]-t[0],t[2]-t[0])[2]>0:ground.append(t)
ground=np.array(ground);gpolys=[Polygon(t[:,:2]) for t in ground];tree=STRtree(gpolys)
def height(t,x,z):
 a,b,c=t;den=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);u=((x-a[0])*(c[1]-a[1])-(z-a[1])*(c[0]-a[0]))/den;v=((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0]))/den;return a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
def parts(g):
 if g.geom_type=='Polygon':yield g
 else:
  for p in getattr(g,'geoms',[]):yield from parts(p)
def overlap_rows(targets,polygons=None):
 rows=[]
 for i,t in enumerate(targets):
  p=Polygon(t[:,:2]) if polygons is None else polygons[i]
  if p.area<=0:continue
  for j in map(int,tree.query(p,predicate='intersects')):
   over=p.intersection(gpolys[j])
   for poly in parts(over):
    if poly.area<=1e-12:continue
    ds=[height(t,x,z)-height(ground[j],x,z) for x,z in list(poly.exterior.coords)[:-1]]
    rows.append({'target':i,'ground':j,'area':poly.area,'minTargetMinusGround':min(ds),'maxTargetMinusGround':max(ds),'geometry':shapely.geometry.mapping(poly)})
 return rows
links=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2/slab-glb-correspondence.json');bymesh={p['name']:p for p in floor};site=read('artifacts/cities/hangzhou/render-input-v7/geography/site-surfaces.json');floorrows=[]
for slab,sourcegroup in zip(links,site['solidSlabs']):
 target=[]
 for link in slab['actualFaceLinks']:
  f=link['actualBottomFaces'][0];target.append(bymesh[f['mesh']]['triangles'][f['triangleIndex']])
 p=shapely.union_all([Polygon(t[:,:2]) for t in target]);interior=p.buffer(-.001);rows=overlap_rows(target);inside=overlap_rows(target,[Polygon(t[:,:2]).intersection(interior) for t in target]);bad=[r for r in rows if r['minTargetMinusGround']<-.00001];insidebad=[r for r in inside if r['minTargetMinusGround']<-.00001]
 floorrows.append({'id':slab['id'],'actualBottomFaces':len(target),'overlapPairs':len(rows),'projectedOverlapArea':sum(r['area'] for r in rows),'minimumBottomClearanceGame':min((r['minTargetMinusGround'] for r in rows),default=None),'maximumBottomClearanceGame':max((r['maxTargetMinusGround'] for r in rows),default=None),'penetratingPairsBeyond1eMinus5':len(bad),'penetratingPairProjectionArea':sum(r['area'] for r in bad),'interiorErosionGame':.001,'interiorMinimumBottomClearanceGame':min((r['minTargetMinusGround'] for r in inside),default=None),'interiorPenetratingPairsBeyond1eMinus5':len(insidebad),'failures':bad,'interiorFailures':insidebad})
 print('floor',slab['id'],len(bad),len(insidebad),flush=True)
targetpart=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');st=targetpart['triangles'];shoretop=np.array([t for t in st if np.cross(t[1]-t[0],t[2]-t[0])[2]/np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>.99]);srows=overlap_rows(shoretop);coplanar=[r for r in srows if max(abs(r['minTargetMinusGround']),abs(r['maxTargetMinusGround']))<.00001];above=[r for r in srows if r['maxTargetMinusGround']>.00001];below=[r for r in srows if r['minTargetMinusGround']<-.00001]
sreport={'actualTopTriangles':len(shoretop),'classification':'actual upward-normal cluster >.99; 159 near-vertical source side faces (<.001) excluded from top comparison only, retained in raw side report','terrainShoreTopProjectedOverlapArea':sum(r['area'] for r in srows),'overlapPairs':len(srows),'minimumShoreTopMinusTerrainGame':min(r['minTargetMinusGround'] for r in srows),'maximumShoreTopMinusTerrainGame':max(r['maxTargetMinusGround'] for r in srows),'coplanarWithin1eMinus5Pairs':len(coplanar),'coplanarWithin1eMinus5Area':sum(r['area'] for r in coplanar),'shoreAboveTerrainPairs':len(above),'shoreBelowTerrainPairs':len(below),'interpretation':'Both actual GLBs contain a narrow dry-side top strip. Overlap/flush geometry is not unique rendering ownership; do not call z-fighting or seam visually accepted.'}
save('floor-relative-position.json',floorrows);save('shore-relative-position.json',{**sreport,'pairs':srows});save('relative-position-summary.json',{'floors':[{k:v for k,v in r.items() if k not in ['failures','interiorFailures']} for r in floorrows],'shore':sreport,'sourceBindings':bindings,'pending':['Precise shore/terrain top ownership or justified hidden join','Actual finger perimeter soil/slab contacts if any','Full GLB column/guard solid and body traces','No crop merge or full soil closure accepted']});print(json.dumps(sreport,indent=2),flush=True)
