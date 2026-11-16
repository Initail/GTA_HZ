from pathlib import Path
import json,hashlib,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-datum-proposal';bindings={}
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
contracts=read('docs/hangzhou/audit/landmark-floor-integration-20261111/contracts.json');contract=next(o for o in contracts['objects'] if o['id']=='city-balcony');specb=read('docs/hangzhou/research/core/city-balcony-round2/spec.json');delivery=read(base+'landmarks/city-balcony-v1/model-delivery.json');bind('scripts/landmarks/city_balcony.py')
axis=specb['axisRadiansEastCCW'];ca,sa=math.cos(axis),math.sin(axis);ax,az=delivery['anchorGame'];upring=specb['upperOuterUVMetres'];scale=.6;upperRel=specb['estimates']['levels']['value']['upperM']*scale

def xy(p):u,v=p;return (ax+(u*ca-v*sa)*scale,az+(u*sa+v*ca)*scale)
def sampleline(coords):
 line=LineString(coords);n=math.ceil(line.length);return [(*line.interpolate(line.length*i/n).coords[0],) for i in range(n+1)]
def sample(p):return {'x':p[0],'z':p[1],'groundYGame':ground(*p),'wet':bool(wet.covers(Point(p)))}
rows=[];polygons={}
for ident,indices,innerIndices,outerIndices in [('west',[12,13,14,15,16,17],[17,12],[16,15,14,13]),('east',[7,8,9,10,11],[11,7],[10,9])]:
 poly=Polygon([xy(upring[i]) for i in indices]);polygons[ident]=poly;inner=np.array([xy(upring[i]) for i in innerIndices]);outer=np.array([xy(upring[i]) for i in outerIndices]);start=inner.mean(axis=0);end=np.array(xy(next(e for e in specb['shoreApproachEdges'] if e['id']==ident)['outerUVMetres']));centerline=sampleline([start,end]);outer_samples=[sample(p) for p in sampleline(outer)];inner_samples=[sample(p) for p in sampleline(inner)];center_samples=[sample(p) for p in centerline]
 # Full footprint grid at <=1g spacing plus <=1g source boundary, not just two midpoints.
 xmin,zmin,xmax,zmax=poly.bounds;gridpoints=[(x,z) for x in np.arange(xmin,xmax+1,1.) for z in np.arange(zmin,zmax+1,1.) if poly.covers(Point(x,z))];gridpoints+=sampleline(list(poly.exterior.coords));grid_samples=[sample(p) for p in gridpoints]
 rows.append({'id':ident,'sourceRelation':'relation/8718551','sourceUpperIndices':indices,'polygonGame':list(poly.exterior.coords),'innerEdgeGame':inner.tolist(),'outerEdgeGame':outer.tolist(),'innerCenter':sample(start),'outerCenter':sample(end),'centerlineLengthGame':math.dist(start,end),'outerEdgeLengthGame':LineString(outer).length,'innerEdgeSamples':inner_samples,'outerEdgeSamples':outer_samples,'centerlineSamples':center_samples,'footprintSamples1Game':grid_samples,'groundRangeGame':[min(p['groundYGame'] for p in grid_samples),max(p['groundYGame'] for p in grid_samples)],'outerGroundRangeGame':[min(p['groundYGame'] for p in outer_samples),max(p['groundYGame'] for p in outer_samples)],'sampleCount':len(grid_samples),'wetSampleCount':sum(p['wet'] for p in grid_samples)})
 print(ident,'center',rows[-1]['outerCenter'],'outerRange',rows[-1]['outerGroundRangeGame'],'length',rows[-1]['centerlineLengthGame'],flush=True)
save('finger-samples.json',rows)
outerGround=[r['outerCenter']['groundYGame'] for r in rows];chosenUpper=sum(outerGround)/len(outerGround);baseY=chosenUpper-upperRel
candidates=[{'id':'current-neutral','baseYGame':0.,'upperYGame':upperRel,'basis':'current isolated model; rejected by source approach mismatch and 3D intersection'}, {'id':'equal-mouth-minimax','baseYGame':baseY,'upperYGame':chosenUpper,'basis':'estimated common main deck; minimizes maximum absolute residual of two sampled source mouth midpoints'}, {'id':'higher-mouth','baseYGame':max(outerGround)-upperRel,'upperYGame':max(outerGround),'basis':'estimated upper deck anchored to higher of two source mouth midpoint grounds'}, {'id':'all-mouth-extrema-minimax','baseYGame':(min(r['outerGroundRangeGame'][0] for r in rows)+max(r['outerGroundRangeGame'][1] for r in rows))/2-upperRel,'upperYGame':(min(r['outerGroundRangeGame'][0] for r in rows)+max(r['outerGroundRangeGame'][1] for r in rows))/2,'basis':'estimated common upper deck minimizing extrema of full two mouth width ground sample set'}]
for c in candidates:
 c['lowerAboveWaterGame']=c['baseYGame']-.9;c['mouths']=[{'id':r['id'],'centerGroundMinusUpperGame':r['outerCenter']['groundYGame']-c['upperYGame'],'fullOuterGroundMinusUpperRangeGame':[q-c['upperYGame'] for q in r['outerGroundRangeGame']],'centerRampGrade':(r['outerCenter']['groundYGame']-c['upperYGame'])/r['centerlineLengthGame'],'mainDeckAboveInnerGroundRangeGame':[c['upperYGame']-max(p['groundYGame'] for p in r['innerEdgeSamples']),c['upperYGame']-min(p['groundYGame'] for p in r['innerEdgeSamples'])]} for r in rows]
save('datum-candidates.json',{'chosenForCPUProposal':'equal-mouth-minimax','chosenBaseYGame':baseY,'chosenUpperYGame':chosenUpper,'anchorGroundNotUsedAsBase':contract['candidateAnchorGroundYGame'],'candidates':candidates,'status':'estimated integration proposal, not measured building datum or accepted access'})
# Proposed bounded upper finger adaptation: main edge common upper; exact source outer cap follows sampled current ground.
# A scalar heightfield over the existing finger plan; no new footprint or lower-floor fill.
profile_rows=[]
for r in rows:
 inner=np.array(r['innerEdgeGame']);outer=np.array(r['outerEdgeGame']);a=inner.mean(axis=0);b=np.array([r['outerCenter']['x'],r['outerCenter']['z']]);d=b-a;length=np.linalg.norm(d);d/=length;left=np.array([-d[1],d[0]])
 outerline=LineString(outer)
 def height(p):
  s=max(0.,min(1.,np.dot(np.array(p)-a,d)/length));q=outerline.interpolate(outerline.project(Point(p)));endY=ground(q.x,q.y);return chosenUpper*(1-s)+endY*s
 ps=[]
 for sample0 in r['footprintSamples1Game']:
  p=[sample0['x'],sample0['z']];h=height(p);ps.append({'x':p[0],'z':p[1],'upperYGame':h,'groundYGame':sample0['groundYGame'],'upperMinusGroundGame':h-sample0['groundYGame']})
 # In-footprint 0.25g finite differences for slope estimate, not legal accessibility certification.
 slopes=[]
 for p in ps:
  q=np.array([p['x'],p['z']]);dx=dz=None
  for axis0 in [np.array([.25,0]),np.array([0,.25])]:
   if polygons[r['id']].covers(Point(q+axis0)) and polygons[r['id']].covers(Point(q-axis0)):
    derivative=(height(q+axis0)-height(q-axis0))/.5
    if axis0[0]:dx=derivative
    else:dz=derivative
  if dx is not None and dz is not None:slopes.append(math.hypot(dx,dz))
 profile_rows.append({'id':r['id'],'basis':'estimated upper-only source-footprint transition; independent per mouth; not asserted surveyed ramp','upperProfileSamples':ps,'maxSampledGradient':max(slopes,default=None),'profileMinusGroundRange':[min(p['upperMinusGroundGame'] for p in ps),max(p['upperMinusGroundGame'] for p in ps)],'outerCapExactGroundRequiresPolylineHeightInterpolation':True,'notASharedWholeBuildingWarp':True})
save('upper-finger-profile-proposal.json',profile_rows)
save('input-bindings.json',bindings)
