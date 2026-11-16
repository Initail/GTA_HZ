from pathlib import Path
import json,hashlib,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review';bindings={}
def bind(p):
 p=Path(p);bindings[str(p)]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest();return ROOT/p
def read(p):return json.loads(bind(p).read_text())
def save(n,x):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base='artifacts/cities/hangzhou/';prep=base+'shore-meshes-v2/';exp=base+'shore-glb-v2/';inp=base+'render-input-v6/'
m=read(prep+'manifest.json');em=read(exp+'asset-manifest.json');props=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/proposals.json')['proposals'];city=read(inp+'city.json');wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']])
sourcechecks={p:hashlib.sha256(bind(p).read_bytes()).hexdigest()==sha for p,sha in m['inputs'].items()}
# Independent GEOS projection/STRtree and linear algebra terrain sampler, not producer Surface.
gm=read(inp+'geography/manifest.json');rl=read(inp+'geography/road-levels.json');grid=gm['grid'];values=np.fromfile(bind(inp+'geography/'+gm['terrainFile']),dtype='<f4').reshape(grid['rows'],grid['columns']);segments=[];spec=[]
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

def topology(ts):
 edges=collections.defaultdict(lambda:[0,0]);vs=set();zero=0
 for t in ts:
  ps=[tuple(p) for p in t];vs.update(ps);zero+=np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))==0
  for a,b in zip(ps,ps[1:]+ps[:1]):
   key=tuple(sorted([a,b]));edges[key][0]+=1;edges[key][1]+=1 if a<b else -1
 volume=float(np.einsum('ij,ij->i',ts[:,0]-ts[0,0],np.cross(ts[:,1]-ts[0,0],ts[:,2]-ts[0,0])).sum()/6)
 return {'vertices':len(vs),'edges':len(edges),'triangles':len(ts),'euler':len(vs)-len(edges)+len(ts),'zeroArea':int(zero),'badEdges':sum(c!=2 or b!=0 for c,b in edges.values()),'signedVolume':volume}
def glb(p):
 raw=bind(p).read_bytes();magic,v,length=struct.unpack_from('<4sII',raw);assert magic==b'glTF' and length==len(raw);off=12;g=None;blob=None
 while off<len(raw):
  n,k=struct.unpack_from('<II',raw,off);chunk=raw[off+8:off+8+n];off+=8+n
  if k==0x4E4F534A:g=json.loads(chunk)
  if k==0x004E4942:blob=chunk
 def acc(i):
  a=g['accessors'][i];bv=g['bufferViews'][a['bufferView']];dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];size=np.dtype(dtype).itemsize;stride=bv.get('byteStride',n*size);offset=bv.get('byteOffset',0)+a.get('byteOffset',0)
  return np.ndarray((a['count'],n),dtype=dtype,buffer=blob,offset=offset,strides=(stride,size)).copy()
 out=[]
 def walk(i,parent):
  node=g['nodes'][i]
  if 'matrix' in node:local=np.array(node['matrix']).reshape(4,4).T
  else:
   local=np.eye(4);x,y,z,w=node.get('rotation',[0,0,0,1]);local[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(node.get('scale',[1,1,1]));local[:3,3]=node.get('translation',[0,0,0])
  world=parent@local
  if 'mesh' in node:
   mesh=g['meshes'][node['mesh']]
   for p in mesh['primitives']:
    a=p['attributes'];pos=acc(a['POSITION']);ind=acc(p['indices']).ravel() if 'indices' in p else np.arange(len(pos));wp=(np.c_[pos,np.ones(len(pos))]@world.T)[:,:3];enu=wp[:,[0,2,1]]*np.array([1,-1,1]);uv=acc(a['TEXCOORD_0']) if 'TEXCOORD_0' in a else None;norm=acc(a['NORMAL']) if 'NORMAL' in a else None
    out.append({'name':mesh['name'],'material':g['materials'][p['material']]['name'],'triangles':enu[ind.reshape(-1,3)],'uv':None if uv is None else uv[ind.reshape(-1,3)],'normals':norm,'world':world.tolist()})
  for child in node.get('children',[]):walk(child,world)
 for i in g['scenes'][g.get('scene',0)]['nodes']:walk(i,np.eye(4))
 return out,g
actual,g=glb(exp+'coastal-shoreline.glb');rows=[];footprints={};all_npz={}
for rec,prop in zip(m['objects'],props):
 arr=np.load(bind(prep+rec['file']));ts=arr[rec['material']];all_npz[rec['id']]=ts;line=LineString(prop['geometryGame']['coordinates']);verts=np.unique(ts.reshape(-1,3),axis=0);tops=verts[verts[:,2]>rec['bottomYGame']+1e-8];xy=np.unique(verts[:,:2],axis=0)
 # source/front coordinate classification against full frozen line
 front=[p for p in tops if Point(p[:2]).distance(line)<1e-8];back=[p for p in tops if Point(p[:2]).distance(line)>=1e-8];front=sorted(front,key=lambda p:line.project(Point(p[:2])));back=sorted(back,key=lambda p:line.project(Point(p[:2])));footprint=shapely.union_all([Polygon(t[:,:2]) for t in ts if Polygon(t[:,:2]).area>1e-12]);footprints[rec['id']]=footprint
 top_errors=[abs(p[2]-ground(*p[:2])) for p in tops];frontline=LineString([p[:2] for p in front]);f_errors=[];b_errors=[];maxseg=0
 for chain,errs in [(front,f_errors),(back,b_errors)]:
  for a,b in zip(chain,chain[1:]):
   maxseg=max(maxseg,math.dist(a[:2],b[:2]))
   for f in [.125,.25,.375,.5,.625,.75,.875]:
    p=a*(1-f)+b*f;errs.append(p[2]-ground(*p[:2]))
 normal=np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);topmask=(np.min(ts[:,:,2],axis=1)>rec['bottomYGame']+1e-8)&(np.abs(normal[:,2])>1e-10)
 gl=next(a for a in actual if a['name']==rec['name']+'_'+rec['material']);gt=gl['triangles']
 # Blender exporter reorders triangles; nearest exact expected float32 positions then unordered face map.
 vertex_tree=STRtree([Point(p[:2]) for p in verts]);maxround=0
 for p in np.unique(gt.reshape(-1,3),axis=0):
  inds=vertex_tree.query(Point(p[:2]),predicate='dwithin',distance=.001);maxround=max(maxround,min(np.linalg.norm(verts[k]-p) for k in inds))
 def signature(t):return tuple(sorted(tuple(np.round(p,3)) for p in t))
 npfaces=collections.Counter(signature(t) for t in ts);glfaces=collections.Counter(signature(t) for t in gt)
 uv=gl['uv'];uvarea=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0])) if uv is not None else np.array([])
 rows.append({'id':rec['id'],'sourceLineHashMatches':hashlib.sha256(line.wkb).hexdigest()==rec['sourceLineSha256'],'npzHashMatches':bindings[prep+rec['file']]==rec['sha256'],'material':rec['material'],'npzTopology':topology(ts),'glbTopology':topology(gt),'frontStations':len(front),'backStations':len(back),'frontHausdorffGame':frontline.hausdorff_distance(line),'dryFootprintAreaGame2':footprint.area,'wetIntrusionAreaGame2':footprint.intersection(wet).area,'allBackVerticesDry':all(not wet.covers(Point(p[:2])) for p in back),'sourceVertexGroundMaxErrorGame':max(top_errors),'frontInteriorAbsErrorGame':max(map(abs,f_errors)),'frontInteriorHeightMinusGroundRangeGame':[min(f_errors),max(f_errors)],'backInteriorAbsErrorGame':max(map(abs,b_errors)),'backInteriorHeightMinusGroundRangeGame':[min(b_errors),max(b_errors)],'maxSegmentLengthGame':maxseg,'topNormalsAllUp':bool(np.all(normal[topmask,2]>0)),'minTopAboveWaterGame':float(tops[:,2].min()-rec['waterYGame']),'bottomErrorGame':abs(float(verts[:,2].min())-(rec['waterYGame']-.3)),'actualGlbMaterial':gl['material'],'maxGlbNearestVertexErrorGame':maxround,'rounded1mmTriangleSetsEqual':npfaces==glfaces,'actualUvFinite':uv is not None and bool(np.isfinite(uv).all()),'actualUvZeroAreaFaces':int((uvarea==0).sum()),'actualUvMinDoubleArea':float(uvarea.min()),'actualNormalFinite':bool(np.isfinite(gl['normals']).all()),'actualNodeWorldMatrix':gl['world']})
 print(rec['id'],json.dumps(rows[-1]),flush=True)
save('geometry.json',rows)
# Actual balcony GLB, source coordinate world transform; no planar bounding-box-only clearance claim.
bal,bg=glb(base+'landmarks/city-balcony-v1/city-balcony.glb');shore=footprints['qianjiang-city-balcony'];balrows=[]
for part in bal:
 hits=[]
 for i,t in enumerate(part['triangles']):
  p=Polygon(t[:,:2]);over=p.intersection(shore)
  if over.is_empty:continue
  # Surface projection overlap with actual vertical range; separately report low and high faces.
  hits.append({'triangle':i,'xyIntersectionAreaGame2':over.area,'minYGame':float(t[:,2].min()),'maxYGame':float(t[:,2].max()),'bounds':list(over.bounds)})
 balrows.append({'name':part['name'],'material':part['material'],'projectedFaceHits':len(hits),'hits':hits})
save('city-balcony-projection-overlap.json',{'status':'potential vertical conflict needs height-resolved interpretation; raw actual GLB projection evidence','parts':balrows,'shoreHeightRangeGame':next(r for r in m['objects'] if r['id']=='qianjiang-city-balcony')['heightRangeGame']})
save('input-bindings.json',bindings);save('validation.json',{'allProducerInputsMatch':all(sourcechecks.values()),'producerInputChecks':sourcechecks,'geometryObjects':len(rows),'actualGlbTriangles':sum(len(a['triangles']) for a in actual),'noBrowserOrBlenderRun':True,'cityBalconyPending':True})
