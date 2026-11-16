from pathlib import Path
import json,hashlib,struct,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2';bindings={}
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
specb=read('docs/hangzhou/research/core/city-balcony-round2/spec.json');source_spec_hash=bindings['docs/hangzhou/research/core/city-balcony-round2/spec.json'];delivery=read(base+'landmarks/city-balcony-v1/model-delivery.json');bind('scripts/landmarks/city_balcony.py');bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-datum-proposal/package-manifest.json')
baseY=1.9579020031420153;upper=baseY+3.6;scale=.6;ax,az=delivery['anchorGame'];angle=specb['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle);ring=specb['upperOuterUVMetres']
def world(p):u,v=p;return ax+(u*ca-v*sa)*scale,az+(u*sa+v*ca)*scale
def hground(p):return (ground(*world(p))-baseY)/scale
def dense(chain):
 result=[]
 for a,b in zip(chain,chain[1:]):
  n=math.ceil(math.dist(a,b)*scale/1.)
  result.extend([tuple(a[k]+(b[k]-a[k])*i/n for k in range(2)) for i in range(n)])
 return result+[tuple(chain[-1])]
def uptri(poly):
 result=[]
 for t in shapely.constrained_delaunay_triangles(poly).geoms:
  ps=list(t.exterior.coords)[:-1]
  if Polygon(ps).area<1e-12:raise ValueError('Zero generated constrained triangle')
  a,b,c=ps
  if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:ps.reverse()
  result.append(ps)
 return result
fingers=[];finger_polys=[];boundaryBySourceEdge={};seamPoints=[]
for ident,indices,terminal,seam,sides in [('west',[12,13,14,15,16,17],[(13,14),(14,15),(15,16)],(17,12),[[12,13],[16,17]]),('east',[7,8,9,10,11],[(9,10)],(11,7),[[7,8,9],[10,11]])]:
 polygon=Polygon([ring[i] for i in indices]);finger_polys.append(polygon);data=[];samples={};terminalset=set(terminal);sideHeight={}
 # Entire side polyline arc length; source corner8 remains on its original side.
 for chainids in sides:
  chain=[ring[i] for i in chainids];line=LineString(chain);h0=6. if chainids[0] in seam else hground(chain[0]);h1=6. if chainids[-1] in seam else hground(chain[-1])
  for a,b in zip(chainids,chainids[1:]):sideHeight[(a,b)]=(line,h0,h1)
 for a,b in zip(indices,indices[1:]+indices[:1]):
  pts=dense([ring[a],ring[b]]);kind='terminal' if (a,b) in terminalset else 'inner-seam' if (a,b)==seam else 'side';edgeSamples=[]
  for p in pts:
   if kind=='terminal':h=hground(p)
   elif kind=='inner-seam':h=6.
   else:
    line,h0,h1=sideHeight[(a,b)];t=line.project(Point(p))/line.length;h=h0+(h1-h0)*t
   key=tuple(round(x,12) for x in p)
   if key in samples and abs(samples[key][2]-h)>1e-8:raise ValueError('Discontinuous boundary endpoint')
   samples[key]=[*p,h];edgeSamples.append([*p,h])
  data.append({'sourceVertexIndices':[a,b],'kind':kind,'samplesUVHMetres':edgeSamples,'maxStepGame':max(math.dist(p[:2],q[:2])*scale for p,q in zip(edgeSamples,edgeSamples[1:]))})
  if kind=='inner-seam':seamPoints.extend([p[:2] for p in edgeSamples])
  else:boundaryBySourceEdge[(a,b)]=[p[:2] for p in edgeSamples]
 outline=[p[:2] for edge in data for p in edge['samplesUVHMetres'][:-1]];triangles=[]
 for t in uptri(Polygon(outline)):
  triangles.append([samples[tuple(round(x,12) for x in p)] for p in t])
 fingers.append({'id':ident,'sourceRelation':'relation/8718551','sourceIndices':indices,'polygonUVMetres':[ring[i] for i in indices],'innerSeamIndices':list(seam),'terminalSourceEdges':[list(e) for e in terminal],'boundary':data,'trianglesUVHMetres':triangles,'basis':'source footprint and whole terminal ground samples; estimated upper transition, no surveyed ramp claim'})
# Retain all original main-deck triangle materials; split only edges at identical new seam coordinates.
upperpoly=Polygon(ring,specb['glazedFootprintsUVMetres']);main=upperpoly.difference(shapely.union_all(finger_polys));maintris=[];materials=[]
def addseams(poly):
 new=[];rs=list(poly.exterior.coords)
 for a,b in zip(rs,rs[1:]):
  line=LineString([a,b]);ps=[(0.,a),(1.,b)]
  for p in seamPoints:
   if line.distance(Point(p))<1e-8:
    t=line.project(Point(p))/line.length
    if 1e-9<t<1-1e-9:ps.append((t,tuple(p)))
  ps.sort();new.extend([q for t,q in ps[:-1]])
 return Polygon(new)
def polylist(g):
 if isinstance(g,Polygon):return [g]
 return [q for p in g.geoms for q in polylist(p)] if hasattr(g,'geoms') else []
for old,mat in zip(specb['upperTrianglesUVMetres'],specb['upperTriangleMaterials']):
 for p in polylist(Polygon(old).intersection(main)):
  if p.area<1e-10:continue
  for t in uptri(addseams(p)):maintris.append(t);materials.append(mat)
# Include every existing material-triangle boundary vertex on source rim; avoid inherited slab T-junctions.
allTrianglePoints=[p for t in maintris for p in t]+[p[:2] for f in fingers for t in f['trianglesUVHMetres'] for p in t]
def refinerim(original):
 result=[];owners=[]
 for i,a in enumerate(original):
  b=original[(i+1)%len(original)];line=LineString([a,b]);pts=[(0.,tuple(a)),(1.,tuple(b))]
  for p in allTrianglePoints:
   if line.distance(Point(p))<1e-8:
    t=line.project(Point(p))/line.length
    if 1e-10<t<1-1e-10:pts.append((t,tuple(p)))
  pts.sort();unique=[]
  for t,p in pts:
   if not unique or math.dist(p,unique[-1][1])>1e-8:unique.append((t,p))
  result.extend(p for t,p in unique[:-1]);owners.extend([i]*(len(unique)-1))
 return result,owners
refined,refinedEdgeKinds=refinerim(ring);refinedHoles=[refinerim(h)[0] for h in specb['glazedFootprintsUVMetres']]
placement={'schemaVersion':1,'id':'city-balcony-floor-v2','cityId':'hangzhou','sourceSpecSha256':source_spec_hash,'sourceModuleSha256':bindings['scripts/landmarks/city_balcony.py'],'baseYGame':baseY,'upperYGame':upper,'anchorGame':delivery['anchorGame'],'axisRadiansEastCCW':angle,'scaleOnce':scale,'units':'footprint/profile in unscaled local metres; lm and absolute datum in game units','upperRelativeMetres':6.,'upperAssemblyDeformMinimumRelativeMetres':4.35,'fingers':fingers,'mainUpperTrianglesUVMetres':maintris,'mainUpperTriangleMaterials':materials,'refinedUpperOuterUVMetres':refined,'refinedUpperHoleUVMetres':refinedHoles,'refinedOuterOriginalEdgeIndices':refinedEdgeKinds,'originalOpenUpperSourceEdgeIndices':[9,13,14,15],'status':'candidate estimated source-finger profile; terrain and shore ownership pending','inputHashes':bindings.copy()}
save('placement.json',placement)
newSpec=json.loads(json.dumps(specb));newSpec['floorPlacement']=placement;newSpec['scope']=specb['scope']+' Absolute lower datum and bounded source-finger upper transition candidate; no stairs/lifts or terrain fill.';save('candidate-spec.json',newSpec)
print(json.dumps({'fingers':[(f['id'],len(f['trianglesUVHMetres'])) for f in fingers],'mainTriangles':len(maintris),'refinedOuterVertices':len(refined),'sourceUpperMinusLowerEqualsTwoFingersArea':upperpoly.difference(Polygon(specb['lowerOuterUVMetres'],specb['glazedFootprintsUVMetres'])).symmetric_difference(shapely.union_all(finger_polys)).area},indent=2))
save('input-bindings.json',bindings)
