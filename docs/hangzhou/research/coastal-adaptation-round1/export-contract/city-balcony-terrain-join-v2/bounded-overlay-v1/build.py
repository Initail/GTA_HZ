"""Independent CPU local terrain candidate; no Blender and no shared writes."""
from pathlib import Path
import sys,json,math,hashlib,time
from collections import defaultdict,Counter
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box,mapping
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface,digest
from hangzhou_site_partition import SitePartition,polygon_parts,plane
SRC=ROOT/'artifacts/cities/hangzhou/render-input-v7'
read=lambda p:json.loads(p.read_text())
write=lambda n,d:(OUT/n).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
began=time.monotonic();city=read(SRC/'city.json');sites=read(OUT.parent/'site-surfaces-repair.json');field=Surface(SRC);partition=SitePartition(sites)
cutgroups=[g for g in sites['terrainCuts'] if g['id'].startswith('city-balcony:')]
cutpolys=[shapely.union_all([Polygon([p[:2] for p in t]) for t in g['triangles']]) for g in cutgroups]
cut=shapely.union_all(cutpolys);frozen_crop=read(ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-terrain-partition-v1/candidate-contract.json')['bboxGame'];domain=box(*frozen_crop)
wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]).intersection(domain) for w in city['water']]);dry=domain.difference(wet)
land=shapely.union_all([Polygon(p[0],p[1:]).intersection(domain) for p in city['land']])
green=shapely.union_all([Polygon(g['rings'][0],g['rings'][1:]).intersection(domain) for g in city['green']]).intersection(dry)
raw_mask=shapely.geometry.shape(read(OUT.parent/'bank-top-render-owner-mask.geojson')['features'][0]['geometry']);render_mask=shapely.set_precision(raw_mask,1e-4)
print('partition source',flush=True)
# Split globally before any height sampling. The base remains F1, not ground().
pieces=partition.split(dry,field.uncut_ground);ptree=STRtree([p.shape for p in pieces])
lines=[poly.boundary for poly in cutpolys]+[dry.boundary,green.boundary,domain.boundary,render_mask.boundary]
x0,z0,x1,z1=domain.bounds
# Two game-unit grid aligned to existing 30g DSM boundaries; add original b-d diagonals.
g=field.grid
for x in np.arange(g['x0']+math.ceil((x0-g['x0'])/1)*1,x1,1):lines.append(LineString([(x,z0),(x,z1)]))
for z in np.arange(g['z0']+math.ceil((z0-g['z0'])/1)*1,z1,1):lines.append(LineString([(x0,z),(x1,z)]))
for i in range(math.floor((x0-g['x0'])/30),math.floor((x1-g['x0'])/30)+1):
 for j in range(math.floor((z0-g['z0'])/30),math.floor((z1-g['z0'])/30)+1):
  x,z=g['x0']+30*i,g['z0']+30*j
  lines.append(LineString([(x+30,z),(x,z+30)]).intersection(domain))
clip_dry=shapely.set_precision(dry,1e-4)
network=shapely.union_all(lines,grid_size=1e-4);raw_cells=list(shapely.get_parts(shapely.polygonize(shapely.get_parts(network))))
cells=[p for cell in raw_cells for p in polygon_parts(shapely.set_precision(cell.intersection(clip_dry),1e-4))]
print('pieces',len(pieces),'network cells',len(cells),flush=True)
# Each top cell uses the owner-specific height closure, including its boundary.
top=[];meta=[];face_polys=[];cell_records=[];missing=[];ambiguous=[]
rounding_error=0
dimension_reduced=[]
from shapely.ops import nearest_points
restore_cache={}
source_vertices=[]
for poly in polygon_parts(dry):
 for ring in [poly.exterior]+list(poly.interiors):source_vertices.extend(list(ring.coords)[:-1])
frozen_crop_edges=read(ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-terrain-partition-v1/vertical-boundaries.json')['openBoundary']
for r in frozen_crop_edges:
 if r['kind']=='local-crop-open':source_vertices.extend(r['edge'])
mask_vertices=[]
for poly in polygon_parts(raw_mask):
 for ring in [poly.exterior]+list(poly.interiors):mask_vertices.extend(list(ring.coords)[:-1])
source_vertices.extend(mask_vertices)
mask_points=[Point(v) for v in mask_vertices];mask_tree=STRtree(mask_points)
source_vertex_points=[Point(p) for p in source_vertices];source_vertex_tree=STRtree(source_vertex_points)
def restore_boundary(x,z):
 key=(x,z)
 if key in restore_cache:return restore_cache[key]
 p=Point(x,z);nearest=source_vertex_points[int(source_vertex_tree.nearest(p))]
 if p.distance(nearest)<=2e-4:q=(nearest.x,nearest.y)
 elif dry.boundary.distance(p)<=2e-4:
  nearest=nearest_points(dry.boundary,p)[0];q=(nearest.x,nearest.y)
 elif raw_mask.boundary.distance(p)<=2e-4:
  nearest=nearest_points(raw_mask.boundary,p)[0];q=(nearest.x,nearest.y)
 else:q=key
 restore_cache[key]=q;return q
# Adjacent precision-grid nodes can project to the same source straight bank within 1e-8g.
# Canonicalize those boundary-only duplicates before triangulation; never merge an interior cut vertex.
node_keys=sorted({tuple(p) for cell in cells for ring in [cell.exterior]+list(cell.interiors) for p in list(ring.coords)[:-1]})
for x,z in node_keys:restore_boundary(x,z)
bank_keys=[k for k in node_keys if dry.boundary.distance(Point(restore_cache[k]))<1e-10]
bank_points=[Point(restore_cache[k]) for k in bank_keys];bank_tree=STRtree(bank_points);parent=list(range(len(bank_keys)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i,p in enumerate(bank_points):
 for j in bank_tree.query(p.buffer(1e-4)):
  j=int(j)
  if p.distance(bank_points[j])<=1e-4:parent[find(j)]=find(i)
clusters=defaultdict(list)
for i,k in enumerate(bank_keys):clusters[find(i)].append(k)
bank_merge_max=0.;bank_merge_count=0
for ks in clusters.values():
 if len(ks)<2:continue
 source_matches=[restore_cache[k] for k in ks if restore_cache[k] in source_vertices]
 chosen=min(source_matches or [restore_cache[k] for k in ks])
 for k in ks:
  bank_merge_max=max(bank_merge_max,math.dist(restore_cache[k],chosen));restore_cache[k]=chosen
 bank_merge_count+=len(ks)-1
def restored_ring(coords):
 ps=[restore_boundary(x,z) for x,z in coords[:-1]];out=[]
 for a,b in zip(ps,ps[1:]+ps[:1]):
  out.append(a);line=LineString([a,b]);ll=line.length
  if ll==0:continue
  if raw_mask.boundary.distance(Point(a))>.001 or raw_mask.boundary.distance(Point(b))>.001 or raw_mask.boundary.distance(line.interpolate(.5,normalized=True))>.001:continue
  extra=[]
  for i in mask_tree.query(line,predicate='dwithin',distance=2e-4):
   point=mask_points[int(i)];station=line.project(point)
   if 1e-9<station<ll-1e-9:extra.append((station,(point.x,point.y)))
  out.extend(q for _,q in sorted(set(extra)))
 return out
source_faces={g['id']:[(Polygon([p[:2] for p in t]),plane(t)) for t in g['triangles']] for g in cutgroups}
source_trees={k:STRtree([p for p,_ in rows]) for k,rows in source_faces.items()}
height_cache={}
source_sample_distance=0.
def stable_height(owners,x,z):
 global source_sample_distance
 groups=tuple(sorted(set(o.rsplit(':',1)[0] for o in owners)));key=(groups,x,z)
 if key not in height_cache:
  values=[field.uncut_ground(x,z)];point=Point(x,z)
  for group in groups:
   tree=source_trees[group];ids=list(tree.query(point.buffer(2e-4)))
   if not ids:ids=[tree.nearest(point)]
   accepted=[int(i) for i in ids if source_faces[group][int(i)][0].distance(point)<=2e-4]
   if not accepted:accepted=[int(tree.nearest(point))]
   source_sample_distance=max(source_sample_distance,min(source_faces[group][i][0].distance(point) for i in accepted))
   if source_sample_distance>2e-4:raise ValueError('Source owner too far from node '+str((source_sample_distance,group,x,z,owners)))
   values.append(min(source_faces[group][i][1](x,z) for i in accepted))
  height_cache[key]=min(values)
 return height_cache[key]

for cell_i,p in enumerate(cells):
 point=p.representative_point()
 if render_mask.covers(point):continue
 if clip_dry.distance(point)>2e-4:raise ValueError('Clipped cell representative outside normalized dry')
 candidates=[int(i) for i in ptree.query(point,predicate='intersects')]
 if not candidates:
  nearest=int(ptree.nearest(point))
  if pieces[nearest].shape.distance(point)>2e-4:missing.append({'cell':cell_i,'point':list(point.coords)[0],'area':p.area});continue
  candidates=[nearest]
 # Exact representative-point ambiguity only occurs for numerical boundary residuals.
 if len(candidates)>1:ambiguous.append({'cell':cell_i,'owners':[pieces[i].owners for i in candidates],'area':p.area})
 part=min((pieces[i] for i in candidates),key=lambda q:q.height(point.x,point.y));material='park' if green.covers(point) else 'land';indices=[]
 mapped=Polygon(restored_ring(list(p.exterior.coords)),[restored_ring(list(ring.coords)) for ring in p.interiors])
 if not mapped.is_valid:mapped=shapely.make_valid(mapped)
 surviving=[]
 for mp in polygon_parts(mapped):
  rawpts=np.asarray(mp.exterior.coords[:-1]);best_pair=max(((i,j) for i in range(len(rawpts)) for j in range(i)),key=lambda ij:np.linalg.norm(rawpts[ij[0]]-rawpts[ij[1]]),default=None)
  if best_pair is not None:
   aa,bb=rawpts[list(best_pair)];direction=bb-aa;ll=np.linalg.norm(direction);distances=np.abs(direction[0]*(rawpts[:,1]-aa[1])-direction[1]*(rawpts[:,0]-aa[0]))/(ll or 1)
   if max(distances,default=0)<=1e-10:
    dimension_reduced.append({'cell':cell_i,'mappedArea':mp.area,'maximumLineDistanceGame':float(max(distances,default=0)),'mappedVertices':rawpts.tolist(),'owners':part.owners});continue
  surviving.append(mp)
 for tri in polygon_parts(shapely.constrained_delaunay_triangles(shapely.GeometryCollection(surviving))):
  coords=list(tri.exterior.coords)[:3]
  if Polygon(coords).area==0:continue
  if not Polygon(coords).exterior.is_ccw:coords.reverse()
  vertices=[]
  for x,z in coords:
   h=stable_height(part.owners,x,z);y=round(h,12);rounding_error=max(rounding_error,abs(y-h));vertices.append([x,z,y])
  if tri.area<=0:raise ValueError('Nonpositive top')
  indices.append(len(top));top.append(vertices);meta.append({'owners':part.owners,'material':material,'cell':cell_i});face_polys.append(Polygon(coords))
 cell_records.append({'cell':cell_i,'owners':part.owners,'material':material,'geometry':mapping(p),'topIndices':indices})
print('top triangles',len(top),'missing',len(missing),'ambiguous',len(ambiguous),flush=True)
# Exact noded XY edges. Top heights are rounded only to 1e-12g for stable shared vertices.
edges=defaultdict(list);vertex_heights=defaultdict(set)
for i,t in enumerate(top):
 for p in t:vertex_heights[tuple(p[:2])].add(p[2])
 for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted([tuple(a[:2]),tuple(b[:2])]))].append((i,a,b))
seams=[];wall=[];wallmeta=[];boundary=[];edgefail=[];tinyheight=[]
for key,uses in edges.items():
 if len(uses)>2:edgefail.append({'edge':key,'uses':len(uses)});continue
 if len(uses)==1:
  a,b=key;mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
  kind='local-crop-open' if domain.boundary.distance(mid)<1e-7 else 'shore-visible-mask-owned' if raw_mask.boundary.distance(mid)<.001 else 'waterfront-owned-by-shore-v3' if wet.boundary.distance(mid)<1e-7 else 'unexpected-open'
  boundary.append({'edge':key,'topFace':uses[0][0],'kind':kind});continue
 f,a,b=uses[0];h,c,d=uses[1];other={tuple(c[:2]):c[2],tuple(d[:2]):d[2]};delta=[p[2]-other[tuple(p[:2])] for p in [a,b]]
 if max(abs(v) for v in delta)<=1e-10:
  if any(v!=0 for v in delta):tinyheight.append(max(map(abs,delta)))
  continue
 if min(delta)<-1e-9 and max(delta)>1e-9:edgefail.append({'edge':key,'heightCrossing':delta});continue
 high=(f,a,b) if sum(delta)>0 else (h,c,d);low=(h,c,d) if sum(delta)>0 else(f,a,b)
 hi,ha,hb=high;lo,la,lb=low;lowy={tuple(la[:2]):la[2],tuple(lb[:2]):lb[2]};length=math.dist(ha[:2],hb[:2]);left=sorted(y for y in vertex_heights[tuple(ha[:2])] if lowy[tuple(ha[:2])]-1e-10<=y<=ha[2]+1e-10);right=sorted(y for y in vertex_heights[tuple(hb[:2])] if lowy[tuple(hb[:2])]-1e-10<=y<=hb[2]+1e-10)
 # Wall parameter domain (station,height) shares all incident top heights at its ends.
 coords=[(0,y) for y in reversed(left)]+[(length,y) for y in right]
 profile=Polygon(coords)
 if not profile.is_valid or profile.area<=0:edgefail.append({'edge':key,'invalidWall':True});continue
 indices=[]
 for t in polygon_parts(shapely.constrained_delaunay_triangles(profile)):
  ps=list(t.exterior.coords)[:3]
  if not t.exterior.is_ccw:ps.reverse()
  verts=[]
  for station,y in ps:
   # End points remain exact shared XY, never interpolated through an invented bank.
   q=ha if station==0 else hb
   verts.append([q[0],q[1],y])
  indices.append(len(wall));wall.append(verts);wallmeta.append({'highTop':hi,'lowTop':lo,'material':'land'})
 seams.append({'edge':[ha[:2],hb[:2]],'highTop':hi,'lowTop':lo,'highOwners':meta[hi]['owners'],'lowOwners':meta[lo]['owners'],'highY':[ha[2],hb[2]],'lowY':[lowy[tuple(ha[:2])],lowy[tuple(hb[:2])]],'wallTriangles':indices})
print('vertical seams',len(seams),'walls',len(wall),'edge failures',len(edgefail),flush=True)
np.savez_compressed(OUT/'local-terrain.npz',top=np.asarray(top,dtype='<f8'),walls=np.asarray(wall,dtype='<f8'))
write('dimension-reduced-cells.json',dimension_reduced);write('top-provenance.json',meta);write('partition-cells.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU, not WGS84','features':[{'type':'Feature','geometry':r.pop('geometry'),'properties':r} for r in cell_records]})
write('vertical-boundaries.json',{'units':'game east/north/up','seams':seams,'wallProvenance':wallmeta,'openBoundary':boundary})
write('local-domains.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU, not WGS84','features':[{'type':'Feature','properties':{'id':n},'geometry':mapping(p)} for n,p in [('local-crop',domain),('dry',dry),('water',wet),('green',green),('cut-union',cut)]+[(g['id'],p) for g,p in zip(cutgroups,cutpolys)]]})
union=shapely.union_all(face_polys)
report={'status':'bounded 1e-4g render-only overlay candidate; physics unchanged; validation pending','renderNodingGridGame':1e-4,'rawVisibleShoreMaskArea':raw_mask.area,'bboxGame':list(domain.bounds),'sourceCutTriangles':{q['id']:len(q['triangles']) for q in cutgroups},'dimensionReducedRestoredBoundaryCells':len(dimension_reduced),'maximumReducedCellLineDistanceGame':max((r['maximumLineDistanceGame'] for r in dimension_reduced),default=0),'boundaryDuplicateMergeCount':bank_merge_count,'maximumBoundaryDuplicateMergeGame':bank_merge_max,'maxSourceFaceEvaluationOutsideDistanceGame':source_sample_distance,'sourcePartitionPieces':len(pieces),'networkCells':len(cells),'topTriangles':len(top),'wallTriangles':len(wall),'verticalSeamSegments':len(seams),'cropArea':domain.area,'landArea':land.area,'waterArea':wet.area,'cutUnionArea':cut.area,'sourceLandWaterOverlapArea':land.intersection(wet).area,'sourceLandWaterGapArea':domain.difference(land.union(wet)).area,'rendererDryVsSourceLandSymmetricDifferenceArea':dry.symmetric_difference(land).area,'cutWaterOverlapArea':cut.intersection(wet).area,'topDomainSymmetricDifferenceArea':union.symmetric_difference(dry).area,'topAreaSumMinusUnion':sum(p.area for p in face_polys)-union.area,'topWaterOverlapArea':union.intersection(wet).area,'cutGroupOverlaps':[{'a':cutgroups[i]['id'],'b':cutgroups[j]['id'],'area':cutpolys[i].intersection(cutpolys[j]).area} for i in range(len(cutpolys)) for j in range(i)],'missingCells':missing,'ambiguousCells':ambiguous,'edgeFailures':edgefail,'unexpectedOpenEdges':sum(x['kind']=='unexpected-open' for x in boundary),'boundaryKinds':dict(Counter(x['kind'] for x in boundary)),'heightSerializationRoundGame':1e-12,'maxHeightSerializationDifference':rounding_error,'maxContinuousEdgeRoundDifference':max(tinyheight,default=0),'seconds':time.monotonic()-began,'limitations':['Finite 1g tessellation still needs sampled height/solid intersection and closure audit','Waterfront is existing shore-glb-v3 ownership, no duplicate generic sidewall','Local crop edges intentionally open; production integration needs matching adjacent original terrain','No real foundation measurement; source is DSM-derived plus explicit bounded game adaptation']}
write('build-report.json',report)
inputs=[OUT.parent/'bank-top-render-owner-mask.geojson',OUT.parent/'bank-top-render-owner-contract.json',OUT.parent/'site-surfaces-repair.json',OUT.parent/'prepare-physics.py',SRC/'city.json',SRC/'geography/manifest.json',SRC/'geography/site-surfaces.json',SRC/'geography/road-levels.json',SRC/'geography/terrain-game.bin',ROOT/'scripts/hangzhou_site_partition.py',ROOT/'scripts/hangzhou_surface.py',ROOT/'scripts/hangzhou_site_surfaces.py',Path(__file__)]
write('input-bindings.json',{str(p.relative_to(ROOT)):digest(p) for p in inputs});print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
