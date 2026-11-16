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
from hangzhou_site_partition import SitePartition,polygon_parts
SRC=ROOT/'artifacts/cities/hangzhou/render-input-v7'
read=lambda p:json.loads(p.read_text())
write=lambda n,d:(OUT/n).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
began=time.monotonic();city=read(SRC/'city.json');sites=read(SRC/'geography/site-surfaces.json');field=Surface(SRC);partition=SitePartition(sites)
cutgroups=[g for g in sites['terrainCuts'] if g['id'].startswith('city-balcony:')]
cutpolys=[shapely.union_all([Polygon([p[:2] for p in t]) for t in g['triangles']]) for g in cutgroups]
cut=shapely.union_all(cutpolys);domain=box(*cut.buffer(6).bounds)
wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]).intersection(domain) for w in city['water']]);dry=domain.difference(wet)
land=shapely.union_all([Polygon(p[0],p[1:]).intersection(domain) for p in city['land']])
green=shapely.union_all([Polygon(g['rings'][0],g['rings'][1:]).intersection(domain) for g in city['green']]).intersection(dry)
print('partition source',flush=True)
# Split globally before any height sampling. The base remains F1, not ground().
pieces=partition.split(dry,field.uncut_ground);ptree=STRtree([p.shape for p in pieces])
lines=[p.shape.boundary for p in pieces]+[dry.boundary,green.boundary,domain.boundary]
x0,z0,x1,z1=domain.bounds
# Two game-unit grid aligned to existing 30g DSM boundaries; add original b-d diagonals.
g=field.grid
for x in np.arange(g['x0']+math.ceil((x0-g['x0'])/2)*2,x1,2):lines.append(LineString([(x,z0),(x,z1)]))
for z in np.arange(g['z0']+math.ceil((z0-g['z0'])/2)*2,z1,2):lines.append(LineString([(x0,z),(x1,z)]))
for i in range(math.floor((x0-g['x0'])/30),math.floor((x1-g['x0'])/30)+1):
 for j in range(math.floor((z0-g['z0'])/30),math.floor((z1-g['z0'])/30)+1):
  x,z=g['x0']+30*i,g['z0']+30*j
  lines.append(LineString([(x+30,z),(x,z+30)]).intersection(domain))
network=shapely.union_all(lines);raw_cells=list(shapely.get_parts(shapely.polygonize(shapely.get_parts(network))))
cells=[p for cell in raw_cells for p in polygon_parts(cell.intersection(dry))]
print('pieces',len(pieces),'network cells',len(cells),flush=True)
# Each top cell uses the owner-specific height closure, including its boundary.
top=[];meta=[];face_polys=[];cell_records=[];missing=[];ambiguous=[]
rounding_error=0
for cell_i,p in enumerate(cells):
 point=p.representative_point()
 if not dry.covers(point):raise ValueError('Clipped cell representative outside dry')
 candidates=[int(i) for i in ptree.query(point,predicate='intersects')]
 if not candidates:missing.append({'cell':cell_i,'point':list(point.coords)[0],'area':p.area});continue
 # Exact representative-point ambiguity only occurs for numerical boundary residuals.
 if len(candidates)>1:ambiguous.append({'cell':cell_i,'owners':[pieces[i].owners for i in candidates],'area':p.area})
 part=pieces[candidates[0]];material='park' if green.covers(point) else 'land';indices=[]
 for tri in polygon_parts(shapely.constrained_delaunay_triangles(p)):
  coords=list(tri.exterior.coords)[:3]
  if not tri.exterior.is_ccw:coords.reverse()
  vertices=[]
  for x,z in coords:
   h=part.height(x,z);y=round(h,12);rounding_error=max(rounding_error,abs(y-h));vertices.append([x,z,y])
  if tri.area<=0:raise ValueError('Nonpositive top')
  indices.append(len(top));top.append(vertices);meta.append({'owners':part.owners,'material':material,'cell':cell_i});face_polys.append(tri)
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
  kind='waterfront-owned-by-shore-v3' if wet.boundary.distance(mid)<1e-7 else 'local-crop-open' if domain.boundary.distance(mid)<1e-7 else 'unexpected-open'
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
write('top-provenance.json',meta);write('partition-cells.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU, not WGS84','features':[{'type':'Feature','geometry':r.pop('geometry'),'properties':r} for r in cell_records]})
write('vertical-boundaries.json',{'units':'game east/north/up','seams':seams,'wallProvenance':wallmeta,'openBoundary':boundary})
write('local-domains.geojson',{'type':'FeatureCollection','coordinateFrame':'game ENU, not WGS84','features':[{'type':'Feature','properties':{'id':n},'geometry':mapping(p)} for n,p in [('local-crop',domain),('dry',dry),('water',wet),('green',green),('cut-union',cut)]+[(g['id'],p) for g,p in zip(cutgroups,cutpolys)]]})
union=shapely.union_all(face_polys)
report={'status':'CPU local partition candidate, no GLB/browser acceptance','bboxGame':list(domain.bounds),'sourceCutTriangles':{q['id']:len(q['triangles']) for q in cutgroups},'sourcePartitionPieces':len(pieces),'networkCells':len(cells),'topTriangles':len(top),'wallTriangles':len(wall),'verticalSeamSegments':len(seams),'cropArea':domain.area,'landArea':land.area,'waterArea':wet.area,'cutUnionArea':cut.area,'sourceLandWaterOverlapArea':land.intersection(wet).area,'sourceLandWaterGapArea':domain.difference(land.union(wet)).area,'rendererDryVsSourceLandSymmetricDifferenceArea':dry.symmetric_difference(land).area,'cutWaterOverlapArea':cut.intersection(wet).area,'topDomainSymmetricDifferenceArea':union.symmetric_difference(dry).area,'topAreaSumMinusUnion':sum(p.area for p in face_polys)-union.area,'topWaterOverlapArea':union.intersection(wet).area,'cutGroupOverlaps':[{'a':cutgroups[i]['id'],'b':cutgroups[j]['id'],'area':cutpolys[i].intersection(cutpolys[j]).area} for i in range(len(cutpolys)) for j in range(i)],'missingCells':missing,'ambiguousCells':ambiguous,'edgeFailures':edgefail,'unexpectedOpenEdges':sum(x['kind']=='unexpected-open' for x in boundary),'boundaryKinds':dict(Counter(x['kind'] for x in boundary)),'heightSerializationRoundGame':1e-12,'maxHeightSerializationDifference':rounding_error,'maxContinuousEdgeRoundDifference':max(tinyheight,default=0),'seconds':time.monotonic()-began,'limitations':['Finite 2g tessellation still needs sampled height/solid intersection and closure audit','Waterfront is existing shore-glb-v3 ownership, no duplicate generic sidewall','Local crop edges intentionally open; production integration needs matching adjacent original terrain','No real foundation measurement; source is DSM-derived plus explicit bounded game adaptation']}
write('build-report.json',report)
inputs=[SRC/'city.json',SRC/'geography/manifest.json',SRC/'geography/site-surfaces.json',SRC/'geography/road-levels.json',SRC/'geography/terrain-game.bin',ROOT/'scripts/hangzhou_site_partition.py',ROOT/'scripts/hangzhou_surface.py',ROOT/'scripts/hangzhou_site_surfaces.py',Path(__file__)]
write('input-bindings.json',{str(p.relative_to(ROOT)):digest(p) for p in inputs});print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
