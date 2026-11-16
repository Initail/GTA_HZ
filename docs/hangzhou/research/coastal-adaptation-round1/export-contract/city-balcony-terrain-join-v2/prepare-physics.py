"""New isolated physical cut adaptation; preserve source geodata and old v7."""
from pathlib import Path
import sys,json,hashlib,ast,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,shape,mapping
from shapely.ops import nearest_points
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_site_surfaces import SiteSurfaces
from hangzhou_site_partition import polygon_parts,plane
bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);bindings[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();return ROOT/rel
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
p=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(p),'exec'),globals())
old=read('artifacts/cities/hangzhou/render-input-v7/geography/site-surfaces.json');new=json.loads(json.dumps(old));previous=OUT.parent/'city-balcony-terrain-partition-v1';domain={f['properties']['id']:shape(f['geometry']) for f in read(previous/'local-domains.geojson')['features']};dry=domain['dry'];sampler=SiteSurfaces(old);shore,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');shore=next(p for p in shore if p['name']=='coastal_shore_5_-4_land');cap=1.5579020031420152;tops=[];cap_tops=[]
for t in shore['triangles']:
 n=np.cross(t[1]-t[0],t[2]-t[0]);nz=n[2]/np.linalg.norm(n)
 if nz>.99:
  tops.append(Polygon(t[:,:2]))
  if max(abs(t[:,2]-cap))<1e-5:cap_tops.append(Polygon(t[:,:2]))
shorefp=shapely.union_all(tops);capfp=shapely.union_all(cap_tops);rows=[];features=[]
def tris(poly,height):
 out=[]
 for part in polygon_parts(shapely.constrained_delaunay_triangles(poly)):
  ps=list(part.exterior.coords)[:3]
  if not part.exterior.is_ccw:ps.reverse()
  out.append([[x,z,height(x,z)] for x,z in ps])
 return out
for group in new['terrainCuts']:
 original=next(g for g in old['terrainCuts'] if g['id']==group['id']);source=shapely.union_all([Polygon([p[:2] for p in t]) for t in original['triangles']])
 if group['id']=='city-balcony:dry-main':
  updated=source.difference(shorefp).union(capfp.intersection(dry));changed=updated.symmetric_difference(source);outside_band=changed.difference(source.boundary.buffer(.001)).area
  if outside_band>1e-10:raise ValueError('Shore alignment exceeds bounded 1mm source seam band')
  group['triangles']=tris(updated,lambda x,z:cap)
  rows.append({'id':group['id'],'rule':'inside actual shore top projection, low actual cap owns low terrain; high actual shore top owns original F1; actual closed shoreline GLB bound','originalArea':source.area,'updatedArea':updated.area,'symmetricDifferenceArea':changed.area,'addedArea':updated.difference(source).area,'removedArea':source.difference(updated).area,'changeAreaOutside1mmSourceBoundaryBand':outside_band,'capGame':cap,'triangles':len(group['triangles'])})
 else:
  updated=source.buffer(.0005,quad_segs=16,join_style=1).intersection(dry);ring=updated.difference(source);source_faces=[(Polygon([p[:2] for p in t]),plane(t)) for t in original['triangles']]
  def height(x,z):
   q=nearest_points(source.boundary,Point(x,z))[0];matches=[r['height'] for r in sampler.at('terrainCuts',q.x,q.y) if r['id']==group['id']]
   if matches:return min(matches)
   p,fn=min(source_faces,key=lambda r:r[0].distance(q));return fn(q.x,q.y)
  additions=tris(ring,height);group['triangles']=original['triangles']+additions
  rows.append({'id':group['id'],'rule':'original triangles byte values retained; added .0005g dry ring height from nearest original boundary source cut; min with other cuts/F1','radiusGame':.0005,'originalArea':source.area,'updatedArea':updated.area,'additionalArea':ring.area,'originalTriangles':len(original['triangles']),'addedTriangles':len(additions),'triangles':len(group['triangles'])})
 for name,p in [('original',source),('updated',updated),('added',updated.difference(source)),('removed',source.difference(updated))]:features.append({'type':'Feature','properties':{'id':group['id'],'kind':name},'geometry':mapping(p)})
SiteSurfaces(new)
for kind in ['walkFloors','solidSlabs','terrainPatches','roadSurfaces']:
 if new[kind]!=old[kind]:raise ValueError('Unrelated site surface changed')
save('site-surfaces-repair.json',new);save('physics-cut-changes.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU XY, not WGS84','features':features});save('physics-cut-report.json',{'status':'new bounded game-adaptation candidate, not measured nor activated','sourceSitesSha256':bindings['artifacts/cities/hangzhou/render-input-v7/geography/site-surfaces.json'],'rows':rows,'unrelatedSiteSurfacesUnchanged':True,'sourceOSMAndRoadCoordinatesUnchanged':True,'existingRoadHeightConflictStillBlocker':True,'pending':['terrain ownership mesh','road profile and tunnel clearance separate package','actual GLB and body/browser checks']});save('physics-input-bindings.json',bindings);print(json.dumps(rows,indent=2),flush=True)
