"""Fit the existing source path footprint to exact shipped terrain triangles.

No terrain model changes and no raised walk-only fiction: the small ground
patch and the visible/physical paving share the same source plane. This is a
mesh-derived game surface, not a more accurate topographic measurement.
"""
from pathlib import Path
import json,hashlib,sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles,set_precision
root=Path(__file__).resolve().parents[1]
surface_file,mesh_file,out=map(Path,sys.argv[1:]);assert not out.exists();out.resolve().relative_to(root/'artifacts/cities/hangzhou')
def read(p):return json.loads(p.read_text())
def record(p):
 b=p.read_bytes();return {'file':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
old=read(surface_file);mesh=read(mesh_file);assert old['units']==mesh['units'];assert not old.get('terrainPatches')
for r in mesh['sources']:assert record(root/r['path'])['sha256']==r['sha256']
assert len(old['walkFloors'])==1
original_area=unary_union([Polygon([v[:2] for v in t]) for t in old['walkFloors'][0]['triangles']]);assert original_area.is_valid
# A shared grid at the actual Float32 world-coordinate spacing prevents tiny
# source-tile edge slivers from becoming zero-area GPU triangles. This does not
# relax contact heights or walking rules; record the bounded footprint change.
grid=2**-12
assert all(abs(v)<4096 for v in original_area.bounds)
area=set_precision(original_area,grid);assert original_area.hausdorff_distance(area)<=grid*2**.5
ground=[];floor=[];owners=[];fragments=[]
for source in mesh['triangles']:
 t=source['vertices'];triangle=set_precision(Polygon([v[:2] for v in t]),grid);cut=triangle.intersection(area)
 if cut.is_empty or cut.area<1e-12:continue
 fragments.append(cut);a,b,c=t;det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]);assert abs(det)>1e-10
 def h(x,z):
  u=((x-a[0])*(c[1]-a[1])-(z-a[1])*(c[0]-a[0]))/det;v=((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0]))/det
  return a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
 for p in constrained_delaunay_triangles(cut).geoms:
  if p.area<1e-12:continue
  q=list(p.exterior.coords)[:-1];assert len(q)==3
  if (q[1][0]-q[0][0])*(q[2][1]-q[0][1])-(q[2][0]-q[0][0])*(q[1][1]-q[0][1])<0:q.reverse()
  g=[[x,z,h(x,z)] for x,z in q];ground.append(g);floor.append([[x,z,y+.015] for x,z,y in g]);owners.append({k:source[k] for k in ['tile','node','primitiveTriangle']})
covered=unary_union(fragments);new_area=unary_union([Polygon([v[:2] for v in t]) for t in ground]);difference=set_precision(area,0).symmetric_difference(set_precision(new_area,0)).area
print(json.dumps({'targetArea':area.area,'clippedUnionArea':covered.area,'triangulatedArea':new_area.area,'symmetricDifference':difference,'sumTriangleArea':sum(Polygon([v[:2] for v in t]).area for t in ground)}))
assert difference<=area.length*grid*2**.5
assert abs(sum(Polygon([v[:2] for v in t]).area for t in ground)-new_area.area)<1e-7,'Source triangle domains overlap'
assert original_area.hausdorff_distance(new_area)<=grid*2**.5
assert len(floor)<20000
# Shipped terrain has a few unwelded source seams. A single walking vertex must
# have one height on both incident triangles. Stitch to the midpoint of the
# actual source planes, with an explicit bound inside the unchanged contact
# envelope; the independent mesh-contact audit still decides acceptance.
heights={}
for t in ground:
 for x,z,y in t:heights.setdefault((x,z),[]).append(y)
seam_range=max(max(v)-min(v) for v in heights.values());assert seam_range<=.03,'Native terrain seam needs a separate mesh repair'
stitched={k:(min(v)+max(v))*.5 for k,v in heights.items()}
ground=[[[x,z,stitched[(x,z)]] for x,z,y in t] for t in ground]
floor=[[[x,z,y+.015] for x,z,y in t] for t in ground]
result=dict(old);floor_id='lingyin-source-approach-stone-v2';result['walkFloors']=[{'id':floor_id,'triangles':floor}];result['terrainPatches']=[{'id':'lingyin-shipped-terrain-contact-v1','triangles':ground}];result['pathDisplays']=[dict(old['pathDisplays'][0],floorIds=[floor_id])]
out.mkdir(parents=True);(out/'site-surfaces-candidate.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
report={'schemaVersion':1,'inputs':[record(surface_file),record(mesh_file)],'output':record(out/'site-surfaces-candidate.json'),'triangles':len(floor),'pavingAreaGame2':area.area,'footprintSymmetricDifferenceGame2':difference,'sourceTriangleOwners':owners,
 'float32GridGame':grid,'originalFootprintHausdorffDeltaGame':original_area.hausdorff_distance(new_area),'originalFootprintSymmetricDifferenceGame2':set_precision(original_area,0).symmetric_difference(set_precision(new_area,0)).area,
 'maximumNativeSeamRangeGame':seam_range,'maximumVertexSeamCorrectionGame':seam_range*.5,
 'method':'clip OSM-owned paving footprint to actual decoded shipped terrain triangles on the recorded Float32 grid; join common vertices at the midpoint of source seam heights; physical and visible stone are both +.015g above the identical footprint-limited ground patch; retain original contact limits for independent validation',
 'classification':'mesh-measured game geometry; earth source remains 30m DSM estimate; stone thickness and source path widths remain estimated',
 'unchanged':['all base GLB bytes','source access restrictions','source path footprint within recorded Float32 quantization','original actor scale and movement/step rules','all existing city surfaces outside this pending addition'],
 'pending':['Float32 nondegeneracy','independent actual terrain intersections','walking and collision replay','real browser visibility','full-world integration']}
(out/'fit-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['triangles','pavingAreaGame2','footprintSymmetricDifferenceGame2','output']}))
