from pathlib import Path
import json,hashlib,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review';bindings={}
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
import ast,importlib.util
candidate='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2/'
cpum=read(candidate+'cpu-validation.json');specb=read(candidate+'candidate-spec.json');placement=specb['floorPlacement'];frozen=read(candidate+'package-manifest.json');frozenchecks={r['path']:hashlib.sha256(bind(r['path']).read_bytes()).hexdigest()==r['sha256'] for r in frozen['files']}
newroot=base+'landmarks/city-balcony-floor-v2/';delivery=read(newroot+'model-delivery.json');bal,bg=glb(newroot+'city-balcony.glb');source=bind('scripts/landmarks/city_balcony_floor_v2.py');modspec=importlib.util.spec_from_file_location('floor_v2',source);mod=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(mod)
actual,g=glb(exp+'coastal-shoreline.glb');ax,az=placement['anchorGame'];lm={'x':ax,'z':az,'y':placement['baseYGame']};ca,sa=math.cos(placement['axisRadiansEastCCW']),math.sin(placement['axisRadiansEastCCW'])
expected=np.load(bind(candidate+'cpu-triangles.npz'))['positions'];expectedVertices=np.unique(expected.reshape(-1,3),axis=0);evtree=STRtree([Point(p[:2]) for p in expectedVertices]);actualVertices=np.unique(np.concatenate([a['triangles'].reshape(-1,3) for a in bal]),axis=0);avtree=STRtree([Point(p[:2]) for p in actualVertices])
def nearest_errors(vertices,target,tree):
 errors=[];missing=[]
 for p in vertices:
  inds=tree.query(Point(p[:2]),predicate='dwithin',distance=.002)
  d=min((np.linalg.norm(target[i]-p) for i in inds),default=math.inf)
  errors.append(float(d))
  if d>.002:missing.append(p.tolist())
 return {'maxErrorGame':max(errors),'overToleranceCount':len(missing),'examples':missing[:20]}
vertexChecks={'actualToCpu':nearest_errors(actualVertices,expectedVertices,evtree),'cpuToActual':nearest_errors(expectedVertices,actualVertices,avtree)}
# Exact expected top triangles from source main/finger parameter list; actual triangles use float32 world positions.
actualTop=collections.Counter();sourceTop=collections.Counter()
def key(t):return tuple(sorted(tuple(round(float(v),6) for v in p) for p in t))
# Float32 whole-world coordinates are emitted by B.finish, then Blender axis conversion.
def expected_glb(t):
 ps=[]
 for u,v,h in t:
  x=np.float32(ax+(u*ca-v*sa)*.6);z=np.float32(az+(u*sa+v*ca)*.6);y=np.float32(lm['y']+h*.6);ps.append([float(x),float(z),float(y)])
 return ps
for t in placement['mainUpperTrianglesUVMetres']:sourceTop[key(expected_glb([[p[0],p[1],6.] for p in t]))]+=1
for f in placement['fingers']:
 for t in f['trianglesUVHMetres']:sourceTop[key(expected_glb(t))]+=1
for part in bal:
 for t in part['triangles']:actualTop[key(t)]+=1
missingTop=sum((sourceTop-actualTop).values())
terminal=[]
for f in placement['fingers']:
 rows=[]
 for edge in f['boundary']:
  if edge['kind'] not in ['terminal','inner-seam']:continue
  for u,v,h in edge['samplesUVHMetres']:
   p=np.array([ax+(u*ca-v*sa)*.6,az+(u*sa+v*ca)*.6,lm['y']+h*.6]);inds=avtree.query(Point(p[:2]),predicate='dwithin',distance=.002);d=min((np.linalg.norm(actualVertices[i]-p) for i in inds),default=math.inf);rows.append({'kind':edge['kind'],'expectedENU':p.tolist(),'nearestActualVertexErrorGame':float(d),'runtimeFloorQueryErrorGame':abs(mod.deck_height_game(p[0],p[1],lm,specb,.6,'upper')-p[2])})
 terminal.append({'id':f['id'],'points':rows,'maxActualVertexErrorGame':max(r['nearestActualVertexErrorGame'] for r in rows)})
save('actual-terminal-contacts.json',terminal)
summary={'deliveryBaseYGame':delivery['baseYGame'],'expectedBaseYGame':lm['y'],'artifactHashMatches':delivery['artifactSha256']==bindings[newroot+'city-balcony.glb'],'moduleHashMatches':delivery['sourceModuleSha256']==bindings['scripts/landmarks/city_balcony_floor_v2.py'],'specHashMatches':delivery['specSha256']==bindings[candidate+'candidate-spec.json'],'allFrozenCandidateFilesMatch':all(frozenchecks.values()),'actualTriangles':sum(len(p['triangles']) for p in bal),'cpuTriangles':len(expected),'actualMeshes':[p['name'] for p in bal],'materials':[p['material'] for p in bal],'vertexChecks':vertexChecks,'expectedUpperTopTriangles':sum(sourceTop.values()),'missingExactFloat32UpperTopTriangles':missingTop,'actualAllUvsFinite':all(p['uv'] is not None and np.isfinite(p['uv']).all() for p in bal),'actualAllNormalsFinite':all(np.isfinite(p['normals']).all() for p in bal),'actualNondegenerateTriangles':all(np.all(np.linalg.norm(np.cross(p['triangles'][:,1]-p['triangles'][:,0],p['triangles'][:,2]-p['triangles'][:,0]),axis=1)>0) for p in bal),'noBrowserOrBlenderRun':True}
save('actual-glb-validation.json',summary);print(json.dumps(summary,indent=2),flush=True)
# Re-evaluate actual file against all four shore objects, not CPU shifted old model.
previous=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/intersections.py';bind(previous.relative_to(ROOT));tree0=ast.parse(previous.read_text());functions=ast.Module(body=[n for n in tree0.body if isinstance(n,ast.FunctionDef) and n.name in ['intri','tri_intersection']],type_ignores=[]);exec(compile(functions,str(previous),'exec'),globals())
rows=[]
for shore in actual:
 sts=shore['triangles'];tree=STRtree([Polygon(t[:,:2]) for t in sts]);parts=[]
 for part in bal:
  pairs=[]
  for i,t in enumerate(part['triangles']):
   for j in map(int,tree.query(Polygon(t[:,:2]))):
    st0=sts[j]
    if t[:,2].min()>st0[:,2].max()+1e-6 or t[:,2].max()<st0[:,2].min()-1e-6:continue
    hit=tri_intersection(t,st0)
    if hit:pairs.append({'balconyTriangle':i,'shoreTriangle':j,'balconyYRange':[float(t[:,2].min()),float(t[:,2].max())],**hit})
  parts.append({'name':part['name'],'pairCount':len(pairs),'pairs':pairs})
 rows.append({'shore':shore['name'],'parts':parts,'totalPairCount':sum(p['pairCount'] for p in parts)})
 print('actual shore',shore['name'],rows[-1]['totalPairCount'],flush=True)
save('actual-four-shore-intersections.json',rows);save('input-bindings.json',bindings)
