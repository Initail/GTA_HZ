"""Subtract only visible actual shoreline-solid coverage from local terrain rendering.
Physical support remains in the separate site-surfaces-repair.json contract.
"""
from pathlib import Path
import json,hashlib,ast,struct,math,collections,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape,mapping
from shapely.strtree import STRtree
from shapely.ops import nearest_points
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_site_partition import polygon_parts,plane
bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'),default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
source=np.load(bind(OUT/'local-terrain.npz'));tops=source['top'];walls=source['walls'];meta=read(OUT/'top-provenance.json');domain={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']};shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');shore=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');shore_ids=[i for i,t in enumerate(shore['triangles']) if np.cross(t[1]-t[0],t[2]-t[0])[2]/np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>.99];st=shore['triangles'][shore_ids];sp=[Polygon(t[:,:2]) for t in st];sh=[plane(t) for t in st];tree=STRtree(sp);bottom=.6000000238418579;epsilon=1e-5
# Convex triangle/triangle overlap clipped against the exact difference of affine planes.
def clip_height(poly,difference,threshold):
 ps=list(poly.exterior.coords)[:-1];result=[]
 for a,b in zip(ps,ps[1:]+ps[:1]):
  da,db=difference(*a)-threshold,difference(*b)-threshold
  if da>=0:result.append(a)
  if (da>=0)!=(db>=0):
   t=da/(da-db);result.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
 return Polygon(result) if len(result)>=3 else Polygon()
removals=[];by_top=collections.defaultdict(list);source_overlap=[]
for i,t in enumerate(tops):
 poly=Polygon(t[:,:2]);h=plane(t)
 for j in map(int,tree.query(poly,predicate='intersects')):
  over=poly.intersection(sp[j])
  for piece in polygon_parts(over):
   diff=lambda x,z,hs=sh[j],ht=h:hs(x,z)-ht(x,z)
   ds=[diff(x,z) for x,z in piece.exterior.coords];source_overlap.append({'terrainTop':i,'shoreTop':j,'area':piece.area,'min':min(ds),'max':max(ds)})
   selected=clip_height(piece,diff,-epsilon)
   if selected.area<=0:continue
   # The existing v3 bank has a constant bottom and one top at this interior XY.
   if min(h(x,z) for x,z in selected.exterior.coords)<bottom-epsilon:raise ValueError('Terrain lies below bank bottom; no volume coverage')
   by_top[i].append(selected);removals.append({'terrainTop':i,'shoreActualTriangle':shore_ids[j],'minShoreMinusTerrain':min(ds),'maxShoreMinusTerrain':max(ds),'geometry':mapping(selected)})
mask=shapely.union_all([shape(r['geometry']) for r in removals]);print('selected top mask',mask.area,'fragments',len(removals),flush=True)
# Preserve original exterior boundary; internal cut nodes share the same 1e-8g key.
restore={};dry=domain['dry'];crop=domain['local-crop']
def xy(x,z):
 key=(round(x,8),round(z,8))
 if key not in restore:
  q=Point(key)
  if dry.boundary.distance(q)<=2e-8:
   p=nearest_points(dry.boundary,q)[0];restore[key]=(p.x,p.y)
  else:restore[key]=key
 return restore[key]
render_top=[];render_meta=[];render_walls=[];wall_meta=[];zero_fragments=0
for i,t in enumerate(tops):
 h=plane(t);original=Polygon(t[:,:2]);remaining=original.difference(shapely.union_all(by_top[i])) if i in by_top else original
 for tri in polygon_parts(shapely.constrained_delaunay_triangles(remaining)):
  ps=[xy(x,z) for x,z in list(tri.exterior.coords)[:3]]
  if Polygon(ps).area<=0:zero_fragments+=1;continue
  if not Polygon(ps).exterior.is_ccw:ps.reverse()
  render_top.append([[x,z,h(x,z)] for x,z in ps]);render_meta.append({**meta[i],'sourceTop':i})
# A source vertical terrain wall is also hidden only where the actual closed bank occupies its volume.
wall_removed=0.;wall_before=0.;wall_after=0.
for i,t in enumerate(walls):
 ends=sorted({tuple(p[:2]) for p in t});a,b=map(np.asarray,ends);length=np.linalg.norm(b-a);direction=(b-a)/length;line=LineString([a,b]);param=lambda p:float(np.dot(np.asarray(p)-a,direction));profile=Polygon([(param(p[:2]),p[2]) for p in t]);wall_before+=profile.area;occluders=[]
 for j in map(int,tree.query(line,predicate='intersects')):
  over=line.intersection(sp[j]);segments=[over] if over.geom_type=='LineString' else [p for p in getattr(over,'geoms',[]) if p.geom_type=='LineString']
  for segment in segments:
   if segment.length==0:continue
   aa,bb=list(segment.coords)[0],list(segment.coords)[-1];sa,sb=sorted([param(aa),param(bb)]);p,q=a+direction*sa,a+direction*sb;occluders.append(Polygon([(sa,bottom),(sb,bottom),(sb,sh[j](*q)),(sa,sh[j](*p))]))
 remaining=profile.difference(shapely.union_all(occluders));wall_after+=remaining.area;wall_removed+=profile.area-remaining.area
 # Profile orientation maps station/up onto the original wall orientation.
 source_normal=np.cross(t[1]-t[0],t[2]-t[0])
 for tri in polygon_parts(shapely.constrained_delaunay_triangles(remaining)):
  ps=[]
  for station,y in list(tri.exterior.coords)[:3]:
   x,z=xy(*(a+direction*station));ps.append([x,z,y])
  normal=np.cross(np.array(ps[1])-ps[0],np.array(ps[2])-ps[0])
  if np.linalg.norm(normal)==0:zero_fragments+=1;continue
  if np.dot(normal,source_normal)<0:ps.reverse()
  render_walls.append(ps);wall_meta.append({'sourceWall':i,'material':'land'})
np.savez_compressed(OUT/'render-terrain.npz',top=np.asarray(render_top,dtype='<f8'),walls=np.asarray(render_walls,dtype='<f8'))
save('render-top-provenance.json',render_meta);save('render-wall-provenance.json',wall_meta);save('shore-owned-top-removals.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':[{'type':'Feature','properties':{k:v for k,v in r.items() if k!='geometry'},'geometry':r['geometry']} for r in removals]});save('shore-owned-top-mask.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':[{'type':'Feature','properties':{'renderOnly':True,'minimumShoreMinusTerrainGame':-epsilon},'geometry':mapping(mask)}]})
union=shapely.union_all([Polygon(np.array(t)[:,:2]) for t in render_top]);banktop=shapely.union_all(sp);covered=union.union(banktop.intersection(dry));remaining_overlap=union.intersection(banktop)
report={'status':'prepared render ownership candidate; validation pending','sourceLocalMeshSha256':bindings[str((OUT/'local-terrain.npz').relative_to(ROOT))],'actualShoreSha256':bindings['artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb'],'topTriangles':len(render_top),'wallTriangles':len(render_walls),'removedTopMaskArea':mask.area,'sourceActualTopProjectedOverlapArea':sum(r['area'] for r in source_overlap),'retainedTerrainBankProjectionOverlapArea':remaining_overlap.area,'retainedOverlapMeaning':'shore top below terrain by more than 1e-5; bank is buried, not a second visible top','unionTerrainPlusBankTopDryDomainSymmetricDifferenceArea':covered.symmetric_difference(dry).area,'terrainIntrusionIntoWaterArea':union.intersection(domain['water']).area,'wallProfileAreaBefore':wall_before,'wallProfileAreaAfter':wall_after,'wallProfileAreaRemovedInsideActualBank':wall_removed,'collapsedNumericalFragments':zero_fragments,'physicsGroundRemoved':False,'heightRules':{'terrainTopRemoval':'within actual upward bank top triangles only, shoreY>=terrainY-1e-5 and terrainY>=bankBottom-1e-5','wallRemoval':'source wall plane intersect constant-bottom actual closed bank volume, retain uncovered vertical remainder'},'pending':['source-face and actual-bank coverage validation','residual boundary topology and localFloat actual export','floor clearance after new physical cuts','source crop boundary compatibility','separate tunnel/service-road profile blocker','body/browser/visual/performance']}
save('render-ownership-report.json',report);save('render-ownership-input-bindings.json',bindings);save('source-shore-top-overlap.json',source_overlap);print(json.dumps(report,indent=2),flush=True)
