"""Independent serialized GEOS/PIL/NumPy audit; no producer imports or shared writes."""
from pathlib import Path
from collections import defaultdict,deque,Counter
import json,hashlib,math,struct,itertools,zlib
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent;bindings={}
def read(path):
 p=ROOT/path;bindings[path]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def save(name,d):(OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def bind(path):bindings[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
base='artifacts/cities/hangzhou/';inp=base+'render-input-v5/';placement=base+'runtime-data-v4/';asset=base+'coastal-data-v1/'
c=read(inp+'city.json');a=read(asset+'infrastructure.json');report=read(asset+'manifest.json');roads={r['id']:r for r in c['roads']};polys=[Polygon(w['rings'][0],w['rings'][1:]) for w in c['water']];wet=unary_union(polys);domain=box(*c['meta']['extent']);dry=domain.difference(wet)
producer_hash_checks=[]
for p,h in report['inputs'].items():
 now=hashlib.sha256((ROOT/p).read_bytes()).hexdigest();producer_hash_checks.append({'path':p,'recorded':h,'actual':now,'match':h==now})
for name,m in report['files'].items():
 now=hashlib.sha256((ROOT/asset/name).read_bytes()).hexdigest();producer_hash_checks.append({'path':asset+name,'recorded':m['sha256'],'actual':now,'match':m['sha256']==now})
errors=[];perroad=defaultdict(list);max_position=0;max_height=0;max_scalar=0;max_length=0
for cr in a['crossings']:
 r=roads[cr['sourceRoadId']];line=LineString(r['points']);g=LineString(cr['points']);perroad[r['id']].append(g)
 if cr['nodeIds']!=r['nodeIds'] or cr['sourceId']!=r['sourceId']:errors.append({'id':cr['id'],'error':'source-lineage'})
 chain=[0.]
 for p,q in zip(r['points'],r['points'][1:]):chain.append(chain[-1]+math.dist(p,q))
 stations=[]
 for p,y,s in zip(cr['points'],cr['pointHeightsGame'],cr['pointStationsGame']):
  station=line.project(Point(p));stations.append(station);position=line.interpolate(s).distance(Point(p));expected=float(np.interp(station,chain,r['heights']));max_position=max(max_position,position,abs(station-s));max_height=max(max_height,abs(y-expected))
  if position>1e-7 or abs(station-s)>1e-7 or abs(y-expected)>1e-7:errors.append({'id':cr['id'],'error':'point-profile'})
 scalar=abs(cr['height']-float(np.interp((stations[0]+stations[-1])/2,chain,r['heights'])));length=abs(cr['length']-g.length);max_scalar=max(max_scalar,scalar);max_length=max(max_length,length)
 if scalar>1e-7 or length>1e-7 or any(x>=y for x,y in zip(stations,stations[1:])):errors.append({'id':cr['id'],'error':'scalar-or-order'})
 if cr['ramp']!=0 or cr['width']!=r['width'] or g.difference(wet).length>1e-6:errors.append({'id':cr['id'],'error':'width-ramp-wet'})
missing=[];set_difference=[]
for r in c['roads']:
 if r['bridge'] in ['no','false','0',''] or r['tunnel'] not in ['no','false','0','']:continue
 expected=LineString(r['points']).intersection(wet)
 if expected.length<=.1:continue
 if r['id'] not in perroad:missing.append(r['id']);continue
 # GEOS symmetric_difference on numerically interpolated collinear lines can
 # report both copies; a narrow tolerance corridor checks source coverage too.
 actual=unary_union(perroad[r['id']]);outside=actual.difference(expected.buffer(1e-7)).length;lost=expected.difference(actual.buffer(1e-7)).length
 if outside>1e-6 or lost>.100001:set_difference.append({'road':r['id'],'outside':outside,'lost':lost})
save('crossings.json',{'crossings':len(a['crossings']),'sourceRoads':len(perroad),'maxPointOrStationErrorGame':max_position,'maxPointHeightErrorGame':max_height,'maxScalarHeightErrorGame':max_scalar,'maxLengthErrorGame':max_length,'errors':errors,'missingSourceBridgeRoads':missing,'coverageErrors':set_difference,'noInventedNodeIds':not any(x['error']=='source-lineage' for x in errors),'status':'serialized-source-geometry-only'})
print('crossings complete',len(errors),flush=True)

# Independent terrain triangulation and all nearby road influence via GEOS;
# does not import the producer's Surface implementation or spatial cells.
gm=read(inp+'geography/manifest.json');rl=read(inp+'geography/road-levels.json');bind(inp+'geography/terrain-game.bin');grid=gm['grid'];values=np.fromfile(ROOT/inp/'geography/terrain-game.bin',dtype='<f4').reshape(grid['rows'],grid['columns']);segments=[];spec=[]
for r in rl['roads']:
 if r['tier']!=0:continue
 for i in range(len(r['points'])-1):segments.append(LineString(r['points'][i:i+2]));spec.append((r['heights'][i],r['heights'][i+1],r['width']))
st=STRtree(segments);transition=gm['roadTerrainTransitionGame'];max_margin=max(s[2]/2+transition for s in spec)
def ground(x,z):
 u=(x-grid['x0'])/grid['step'];v=(z-grid['z0'])/grid['step'];i,j=math.floor(u),math.floor(v);fx,fz=u-i,v-j
 corners=np.array([[0,0,1],[1,0,1],[0,1,1]]) if fx+fz<=1 else np.array([[1,1,1],[0,1,1],[1,0,1]])
 heights=[values[j+int(dz),i+int(dx)] for dx,dz,_ in corners];weights=np.linalg.solve(corners.T,np.array([fx,fz,1.]));baseheight=float(np.dot(weights,heights));weights=[];levels=[];q=Point(x,z)
 for k in map(int,st.query(q,predicate='dwithin',distance=max_margin)):
  line=segments[k];ya,yb,width=spec[k];dist=q.distance(line)
  if dist>=width/2+transition:continue
  t=line.project(q)/line.length if line.length else 0;edge=np.clip((dist-width/2)/transition,0,1);weight=float(1-3*edge**2+2*edge**3);weights.append(weight);levels.append(ya+(yb-ya)*t)
 return baseheight+(float(np.average(levels,weights=weights))-baseheight)*max(weights) if weights else baseheight

# Public path reachability uses stricter walking-access ground-road seeds.
raw=read('data/processed/hangzhou-261011-extended/roads.geojson');rawmap={f['id']:f for f in raw['features']};geo=c['meta']
def project(p):return [(p[0]-geo['originWGS84'][0])*geo['eastMetresPerDegree']*.6,(p[1]-geo['originWGS84'][1])*geo['northMetresPerDegree']*.6]
def public(tags):return tags.get('access') not in ['no','private'] and tags.get('foot') not in ['no','private']
seed_owner={}
for r in c['roads']:
 f=rawmap.get(r['sourceId']);tags=f['properties']['tags'] if f else {}
 if r['grade']!='0' or r['bridge'] not in ['no','false','0',''] or r['tunnel'] not in ['no','false','0',''] or tags.get('highway') in ['motorway','motorway_link','trunk','trunk_link','construction'] or not public(tags):continue
 for n in r['nodeIds']:
  if not n.startswith('clip:'):seed_owner[n]=r['sourceId']
graph=defaultdict(list);paths={}
for f in raw['features']:
 tags=f['properties']['tags']
 if tags.get('highway') not in ['footway','path','pedestrian','cycleway'] or not public(tags) or tags.get('bridge','no') not in ['no','false','0',''] or tags.get('tunnel','no') not in ['no','false','0','']:continue
 refs=list(map(str,f['properties']['nodeIds']));paths[f['id']]=(LineString(list(map(project,f['geometry']['coordinates']))),refs)
 for n,m in zip(refs,refs[1:]):graph[n].append(m);graph[m].append(n)
parent={n:None for n in seed_owner};queue=deque(n for n in seed_owner if n in graph)
while queue:
 n=queue.popleft()
 for m in graph[n]:
  if m not in parent:parent[m]=n;queue.append(m)
path_geoms=[x[0] for x in paths.values()];path_tree=STRtree(path_geoms)

# All producer obstacle classes plus omitted details and refined collisions.
categories={};category_ids={}
def add(name,geoms,ids=None):categories[name]=geoms;category_ids[name]=ids or [str(i) for i in range(len(geoms))]
add('base-buildings',[Polygon(b['rings'][0],b['rings'][1:]).buffer(2) for b in c['buildings']],[b['id'] for b in c['buildings']]);add('all-source-roads',[LineString(r['points']).buffer(r['width']/2+1.5) for r in c['roads']],[r['id'] for r in c['roads']]);add('landmark-arrivals',[Point(m['arrival']).buffer(7) for m in c['landmarks']],[m['id'] for m in c['landmarks']])
canopy=read(placement+'landscape/canopy-trees.json');plant=read(placement+'landscape/planting.json')
add('canopy-producer-envelope',[Point(p[:2]).buffer(4) for p in canopy['trees']]);add('canopy-scaled-crown-envelope',[Point(p[:2]).buffer(canopy['species'][p[2]]['crown']*.5*p[3]) for p in canopy['trees']]);add('base-tree-producer-envelope',[Point(p[:2]).buffer(3) for p in plant['trees']])
for name,file,key,rad in [('benches','street/manifest.json','placements',2.5),('signals','signals/traffic-signals.json','junctions',2.5)]:
 d=read(placement+file);pts=d[key] if name=='benches' else [p for j in d[key] for p in j['arms']];add(name,[Point(p['x'],p['z']).buffer(rad) for p in pts])
add('street-lamps',[Point(p[:2]).buffer(2) for p in read(inp+'lamps.json')]);add('parked-ebikes',[Point(p[:2]).buffer(2.5) for p in read(base+'ebikes-v4/parked.json')['bikes']])
sites=read(base+'life-sites-v3/life-sites.json')['sites']+[read(base+'cafe-v3/report.json')['site']];add('life-cafe-footprints',[Polygon(s['footprint']).buffer(3) for s in sites]);add('life-cafe-arrivals',[Point(s['arrival']).buffer(7) for s in sites])
detail=read(base+'detail-collision-v4/detail-collision-manifest.json')['collisionFootprints'];detail_geoms=[Polygon(d['rings'][0],d['rings'][1:]) for d in detail];detail_tree=STRtree(detail_geoms)
# Actual GLB accessor/node transformed bounding boxes, used as conservative
# original detail/model envelopes, not claimed triangle-perfect collision.
def glb_bounds(rel):
 bind(rel);data=(ROOT/rel).read_bytes();ln=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+ln]);pts=[]
 def visit(idx,parent):
  n=g['nodes'][idx]
  if 'matrix' in n:local=np.array(n['matrix']).reshape(4,4).T
  else:
   x,y,z,w=n.get('rotation',[0,0,0,1]);rot=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]);local=np.eye(4);local[:3,:3]=rot@np.diag(n.get('scale',[1,1,1]));local[:3,3]=n.get('translation',[0,0,0])
  world=parent@local
  if 'mesh' in n:
   for primitive in g['meshes'][n['mesh']]['primitives']:
    ac=g['accessors'][primitive['attributes']['POSITION']]
    for p in itertools.product(*zip(ac['min'],ac['max'])):pts.append((world@np.r_[p,1])[:3])
  for child in n.get('children',[]):visit(child,world)
 for idx in g['scenes'][g.get('scene',0)]['nodes']:visit(idx,np.eye(4))
 points=np.array(pts);return {'radiusXZ':float(np.linalg.norm(points[:,[0,2]],axis=1).max()),'minY':float(points[:,1].min()),'maxY':float(points[:,1].max())}
model_bounds={}
cfg=read('config/cities/hangzhou.json');base_names=cfg['vegetation']['baseTreeNames'];open_vegetation=read(placement+'open-vegetation/manifest.json')
assert not open_vegetation['eligibleIndices']['islandTree'] and not open_vegetation['eligibleIndices']['palm'],'Additional open-model occupied envelopes require explicit extraction before acceptance'
for name in base_names:model_bounds[name]=glb_bounds(placement+'landscape/canopy/'+name+'.glb')
add('base-tree-scaled-model-envelope',[Point(p[:2]).buffer(model_bounds[base_names[p[2]]]['radiusXZ']*p[3]) for p in plant['trees']])
for name in ['lawn-tuft','flower-shrub','fountain-grass','drain-grate','manhole']:
 model_bounds[name]=glb_bounds(placement+'landscape/'+name+'.glb')
for key,names in [('details',['lawn-tuft','flower-shrub','fountain-grass']),('roadDetails',['drain-grate','manhole'])]:
 add('original-'+key,[Point(p[:2]).buffer(model_bounds[names[p[2]]]['radiusXZ']*p[3]) for p in plant.get(key,[])])
trees={name:STRtree(gs) for name,gs in categories.items()};parks={g['id']:Polygon(g['rings'][0],g['rings'][1:]) for g in c['green']};lightrows=[]
for light in a['parkLights']:
 x,z=light['x'],light['z'];q=Point(x,z);support=q.buffer(.8,quad_segs=64);hits={}
 for name,tree in trees.items():
  inds=list(map(int,tree.query(support,predicate='intersects')))
  if inds:hits[name]=[{'index':i,'id':category_ids[name][i],'distanceToCenterGame':q.distance(categories[name][i])} for i in inds]
 detailed=[]
 for i in map(int,detail_tree.query(support,predicate='intersects')):
  d=detail[i];lo=d.get('minY',0);hi=d.get('maxY',d.get('height',float('inf')))
  if hi>=light['groundYGame'] and lo<=light['groundYGame']+12:detailed.append({'id':d['id'],'minY':lo,'maxY':hi,'kind':d.get('kind')})
 path,refs=paths[light['sourcePathId']];start=next((n for n in refs if n in parent),None);witness=[]
 if start:
  n=start
  while n is not None:witness.append(n);n=parent[n]
 baseheight=ground(x,z);polar=[(r*math.cos(t),r*math.sin(t)) for r in [.4,.8,1.] for t in np.linspace(0,2*math.pi,33)[:-1]];samples=[{'dx':dx,'dz':dz,'height':ground(x+dx,z+dz)} for dx,dz in polar];maxslope=max(abs(s['height']-baseheight)/math.hypot(s['dx'],s['dz']) for s in samples)
 nearest=path.interpolate(path.project(q));connector=LineString([q,nearest]);row={'id':light['id'],'sourceAreaId':light['sourceAreaId'],'supportRadiusGame':.8,'parkCoversSupport':parks[light['sourceAreaId']].covers(support),'dryCoversSupport':dry.covers(support),'waterClearanceFromSupportGame':support.distance(wet),'obstacleHits':hits,'refinedCollisionHits':detailed,'sourcePathId':light['sourcePathId'],'pathDistanceGame':q.distance(path),'supportToAnyPublicPathDistanceGame':support.distance(path_geoms[int(path_tree.nearest(q))]),'strictPublicPathAllNodesReachable':all(n in parent for n in refs),'witnessSourceNodes':witness,'witnessGroundRoadId':seed_owner.get(witness[-1]) if witness else None,'connectorDry':dry.covers(connector),'nearestOtherLightDistanceGame':min(math.hypot(x-l['x'],z-l['z']) for l in a['parkLights'] if l['id']!=light['id']),'serializedGroundErrorGame':abs(baseheight-light['groundYGame']),'maxSampledSlope':maxslope,'maxSampledHeightDeltaGame':max(abs(s['height']-baseheight) for s in samples),'slopeSamples':samples};lightrows.append(row)
save('lights.json',{'lights':lightrows,'modelEnvelopes':model_bounds,'obstacleCounts':{k:len(v) for k,v in categories.items()},'refinedCollisionCount':len(detail),'method':'Independent GEOS disks/obstacle envelopes, stricter public source-node BFS, GEOS segment road/triangle ground sampler, 96 polar slope samples per light. Envelope hits require geometry/visual interpretation.'})
print('lights complete',[(r['id'],list(r['obstacleHits']),len(r['refinedCollisionHits']),r['maxSampledSlope']) for r in lightrows if r['obstacleHits'] or r['refinedCollisionHits'] or r['maxSampledSlope']>.12],flush=True)

# Independently decode actual PNG and derive physical shoreline segment set.
bind(asset+'shore-distance.png');pngbytes=(ROOT/asset/'shore-distance.png').read_bytes();assert pngbytes[:8]==b'\x89PNG\r\n\x1a\n';offset=8;idat=[]
while offset<len(pngbytes):
 size=struct.unpack_from('>I',pngbytes,offset)[0];kind=pngbytes[offset+4:offset+8];payload=pngbytes[offset+8:offset+8+size];crc=struct.unpack_from('>I',pngbytes,offset+8+size)[0];assert zlib.crc32(kind+payload)&0xffffffff==crc
 if kind==b'IHDR':w,h,depth,color,compression,filter_method,interlace=struct.unpack('>IIBBBBB',payload);assert (depth,color,compression,filter_method,interlace)==(8,2,0,0,0)
 if kind==b'IDAT':idat.append(payload)
 offset+=size+12
decoded=np.frombuffer(zlib.decompress(b''.join(idat)),dtype='u1').reshape(h,1+w*3);assert np.all(decoded[:,0]==0),'This independent decoder only accepts actual unfiltered PNG rows; no silent assumption';image=decoded[:,1:].reshape(h,w,3)
ext=a['shoreDistance']['extent'];sx=(ext[2]-ext[0])/w;sz=(ext[3]-ext[1])/h;shore=[];crop=[]
def lineparts(g):
 if g.geom_type=='LineString':return [g]
 return sum((lineparts(x) for x in getattr(g,'geoms',[])),[])
for line in lineparts(wet.boundary):
 for p,q in zip(line.coords,line.coords[1:]):
  segment=LineString([p,q]);on_crop=any(abs(p[axis]-v)<1e-7 and abs(q[axis]-v)<1e-7 for axis,v in [(0,ext[0]),(0,ext[2]),(1,ext[1]),(1,ext[3])]);(crop if on_crop else shore).append(segment)
shore_tree=STRtree(shore);rng=np.random.default_rng(20261111);indices=set(zip(rng.integers(0,h,5000).tolist(),rng.integers(0,w,5000).tolist()));wet_pixels=np.argwhere(image[:,:,1]==255)
for k in rng.choice(len(wet_pixels),4000,replace=False):indices.add(tuple(map(int,wet_pixels[k])))
# Deliberately sample all four image-edge strips, not only lucky interior pixels.
for row in [0,1,h-2,h-1]:
 for col in range(0,w,23):indices.add((row,col))
for col in [0,1,w-2,w-1]:
 for row in range(0,h,17):indices.add((row,col))
samples=[];mask_errors=[];distance_errors=[]
for row,col in sorted(indices):
 q=Point(ext[0]+(col+.5)*sx,ext[1]+(row+.5)*sz);inside=wet.covers(q);actual=image[row,col];expected_distance=min(120,q.distance(shore[int(shore_tree.nearest(q))])) if inside else 0;expected=int(np.rint(expected_distance/120*255));mask_ok=int(actual[1])==255*inside;distance_ok=abs(int(actual[0])-expected)<=1
 if not mask_ok:mask_errors.append({'row':row,'col':col,'actual':int(actual[1]),'expected':255*inside,'boundaryDistanceGame':q.distance(wet.boundary)})
 if not distance_ok:distance_errors.append({'row':row,'col':col,'actualR':int(actual[0]),'expectedR':expected,'distanceGame':expected_distance})
 if (row in [0,1,h-2,h-1] or col in [0,1,w-2,w-1]) and inside:samples.append({'row':row,'col':col,'r':int(actual[0]),'actualDistanceGame':int(actual[0])*120/255,'expectedDistanceGame':expected_distance,'cropEdgeDistanceGame':q.distance(domain.boundary)})
known=[]
for name,lon,lat in [('WestLake-center',120.143,30.244),('Qiantang-center',120.204,30.227),('Wulin-dry',120.164,30.273),('WestLake-Xiaoyingzhou-island',120.14065,30.2411)]:
 x,z=project([lon,lat]);col=int((x-ext[0])/sx);row=int((z-ext[1])/sz);center=Point(ext[0]+(col+.5)*sx,ext[1]+(row+.5)*sz);known.append({'name':name,'wgs84':[lon,lat],'game':[x,z],'row':row,'col':col,'RGB':image[row,col].tolist(),'centerWet':wet.covers(center),'verticallyFlippedRGB':image[h-1-row,col].tolist()})
pngresult={'dimensions':[w,h],'decodedWetPixels':int((image[:,:,1]==255).sum()),'greenOtherValues':np.unique(image[:,:,1]).tolist(),'blueMaximum':int(image[:,:,2].max()),'sampleCount':len(indices),'maskErrors':mask_errors,'distanceEncodingErrorsBeyondOneRedLevel':distance_errors,'physicalBoundaryLengthGame':sum(g.length for g in shore),'omittedCropLengthGame':sum(g.length for g in crop),'edgeWetSamples':samples,'knownAxisSamples':known,'distanceQuantizationGame':120/255,'acceptedToleranceRedLevels':1,'scope':'CPU decoding and pixel-center samples only; GPU orientation/filter/readiness still needs browser'}
save('png.json',pngresult);save('input-bindings.json',{'files':[{'path':p,'sha256':v} for p,v in sorted(bindings.items())]});save('producer-hash-checks.json',producer_hash_checks)
print('png complete',len(indices),len(mask_errors),len(distance_errors),'hash mismatches',sum(not p['match'] for p in producer_hash_checks),flush=True)
