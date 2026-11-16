from pathlib import Path
import json,math,hashlib,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).parent;bindings={}
def read(p):
 f=ROOT/p;bindings[p]=hashlib.sha256(f.read_bytes()).hexdigest();return json.loads(f.read_text())
def save(n,x):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
previous='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal/'
walk=read(previous+'public-walk-surfaces.json');occ=read(previous+'occupancy.json');upper=next(l for l in walk['levels'] if l['id']=='city-balcony:upper');lower=next(l for l in walk['levels'] if l['id']=='city-balcony:lower');domain=Polygon(upper['ringsXZ'][0],upper['ringsXZ'][1:]);sources=[]
for t in upper['triangles']:
 vs=np.array([[x,z,y] for x,y,z in t['verticesGameXYZ']]);sources.append({'id':t['id'],'kind':'main-source-deck','t':vs,'polygon':Polygon(vs[:,:2]),'actualGlbFaces':t['actualGlbFaces']})
for light in occ['skylights']:
 for t in light['actualTopOverlayTriangles']:
  vs=np.array([[x,z,y] for x,y,z in t['verticesGameXYZ']]);sources.append({'id':t['id'],'kind':'actual-detail-top','t':vs,'polygon':Polygon(vs[:,:2]),'actualGlbFaces':[{'mesh':t['actualGlbMesh'],'triangleIndex':t['actualGlbTriangleIndex']}]})
# All covers/rims are exactly horizontal actual GLB top planes. Clip them highest first.
overlayGroups=collections.defaultdict(list)
for s in sources:
 if s['kind']=='actual-detail-top':
  assert np.ptp(s['t'][:,2])<1e-10;overlayGroups[float(s['t'][0,2])].append(s)
# One noded line network gives both sides exactly the same step edges.
# 1-micrometre grid only regularizes sub-float32 Boolean detail boundaries; public domain stays original.
planeGroups=[(h,shapely.union_all([q['polygon'] for q in ss]),ss) for h,ss in sorted(overlayGroups.items(),reverse=True)]
network=shapely.union_all([g.boundary for h,g,ss in planeGroups],grid_size=1e-6)
faces=list(shapely.polygonize(list(shapely.get_parts(network))).geoms);regions=[]
for cell in faces:
 point=cell.representative_point();chosen=next(((h,ss) for h,g,ss in planeGroups if g.covers(point)),None)
 h,ss=chosen if chosen is not None else (upper['baseYGame'],[])
 regions.append({'height':h,'geometry':cell,'sourceIds':[q['id'] for q in ss],'sourceKind':'actual-detail-top' if chosen else 'original-deck-between-detail-edges'})
covered=shapely.union_all(faces)

def polygons(g):
 if g.geom_type=='Polygon':return [g] if g.area>0 else []
 return [q for p in g.geoms for q in polygons(p)] if hasattr(g,'geoms') else []
def tri_poly(p):
 out=[]
 for q in shapely.constrained_delaunay_triangles(p).geoms:
  xy=list(q.exterior.coords)[:-1];a,b,c=xy
  if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:xy.reverse()
  if q.area<=5e-13:raise ValueError('Triangle below runtime determinant budget '+str(q.area))
  out.append(xy)
 return out
triangles=[];provenance=[]
for ri,r in enumerate(regions):
 for p in polygons(r['geometry']):
  for xy in tri_poly(p):triangles.append([[x,z,r['height']] for x,z in xy]);provenance.append({'kind':'highest-actual-detail','region':ri,'sourceCandidateIds':r['sourceIds']})
mainSources=[s for s in sources if s['kind']=='main-source-deck' and s['id'].startswith('upper-main-')]
mainRegion=Polygon(lower['ringsXZ'][0],lower['ringsXZ'][1:]).difference(covered)
for p in polygons(mainRegion):
 for xy in tri_poly(p):triangles.append([[x,z,upper['baseYGame']] for x,z in xy]);provenance.append({'kind':'coplanar-main-source-deck-uncovered','sourceCandidateIds':[s['id'] for s in mainSources]})
for s in sources:
 if s['kind']!='main-source-deck' or s['id'].startswith('upper-main-'):continue
 assert s['polygon'].intersection(covered).area==0
 triangles.append(s['t'].tolist());provenance.append({'kind':'source-finger-deck','sourceId':s['id'],'actualGlbFaces':s['actualGlbFaces']})
# Consolidate all projected mesh edges/vertices. Coordinates shared by Boolean subdivision may differ at ~1e-12.
# No model or domain snapping here; keys only classify adjacency, retaining all original emitted coordinates.
def key(p):return tuple(round(float(x),8) for x in p[:2])
edge_map=collections.defaultdict(list);vertex_map=collections.defaultdict(list)
for i,t in enumerate(triangles):
 for k,p in enumerate(t):vertex_map[key(p)].append((i,k))
 for j in range(3):edge_map[tuple(sorted([key(t[j]),key(t[(j+1)%3])]))].append((i,j))
openEdges=[[False]*3 for t in triangles];step_edges=[]
for ek,refs in edge_map.items():
 if len(refs)<2:continue
 heights=[]
 for i,j in refs:heights.append((sum(triangles[i][k][2] for k in [j,(j+1)%3])/2,i,j))
 hi=max(h for h,_,_ in heights)
 if hi-min(h for h,_,_ in heights)>.001:
  for h,i,j in heights:
   if h<hi-.001:openEdges[i][j]=True
  step_edges.append({'edgeXZ':ek,'levels':[h for h,_,_ in heights],'references':refs})
# Include cases where one side's edge is subdivided by a different source triangulation.
allpoly=[Polygon(np.array(t)[:,:2]) for t in triangles];tree=STRtree(allpoly)
for i,t in enumerate(triangles):
 for j in range(3):
  mid=(np.array(t[j])+t[(j+1)%3])/2;point=Point(mid[:2]);own=mid[2];higher=False
  for k in map(int,tree.query(point,predicate='dwithin',distance=1e-8)):
   if k==i:continue
   other=np.array(triangles[k]);coeff=np.linalg.solve(np.c_[other[:,:2],np.ones(3)],other[:,2]);h=float(coeff@np.array([mid[0],mid[1],1.]));
   if h>own+.001 and allpoly[k].distance(point)<1e-8:higher=True
  if higher:openEdges[i][j]=True
# Solve the half-open edge fan constraints together, including vertex ownership.
# Boolean variable = whether a particular directed triangle edge is open.
clauses=[];nvars=3*len(triangles)
def var(i,j):return i*3+j+1
def unit(lit):clauses.append((lit,lit))
for i,row in enumerate(openEdges):
 for j,value in enumerate(row):
  if value:unit(var(i,j))
for ek,refs in edge_map.items():
 if len(refs)==1:
  i,j=refs[0]
  if not openEdges[i][j]:unit(-var(i,j))
 for n,(i,j) in enumerate(refs):
  for oi,oj in refs[n+1:]:clauses.append((-var(i,j),-var(oi,oj)))
vertex_steps=[];vertexHighest=[]
for vk,refs in vertex_map.items():
 maxh=max(triangles[i][k][2] for i,k in refs);low=[(i,k) for i,k in refs if triangles[i][k][2]<maxh-.001]
 vertexHighest.append((vk,[(i,k) for i,k in refs if abs(triangles[i][k][2]-maxh)<.001]))
 if low:
  vertex_steps.append({'pointXZ':vk,'highestY':maxh,'lowerReferences':low})
  for i,k in low:clauses.append((var(i,k),var(i,(k-1)%3)))
# Highest actual rim cells need no open edge; this also makes corner ownership explicit.
for i,t in enumerate(triangles):
 if all(abs(p[2]-max(overlayGroups))<1e-8 for p in t):
  for j in range(3):unit(-var(i,j))
def solve(extra=()):
 count=2*nvars;graph=[[] for _ in range(count)];reverse=[[] for _ in range(count)]
 def node(lit):return 2*(abs(lit)-1)+(lit<0)
 for a,b in [*clauses,*extra]:
  x,y=node(a),node(b)
  for u,v in [(x^1,y),(y^1,x)]:graph[u].append(v);reverse[v].append(u)
 visited=set();order=[]
 for start in range(count):
  if start in visited:continue
  stack=[(start,0)];visited.add(start)
  while stack:
   u,k=stack[-1]
   if k<len(graph[u]):
    v=graph[u][k];stack[-1]=(u,k+1)
    if v not in visited:visited.add(v);stack.append((v,0))
   else:order.append(u);stack.pop()
 component=[-1]*count;cid=0
 for start in reversed(order):
  if component[start]>=0:continue
  stack=[start];component[start]=cid
  while stack:
   u=stack.pop()
   for v in reverse[u]:
    if component[v]<0:component[v]=cid;stack.append(v)
  cid+=1
 if any(component[2*i]==component[2*i+1] for i in range(nvars)):return None
 result=[component[2*i]>component[2*i+1] for i in range(nvars)]
 assert all((result[abs(a)-1] if a>0 else not result[abs(a)-1]) or (result[abs(b)-1] if b>0 else not result[abs(b)-1]) for a,b in [*clauses,*extra])
 return result
assignment=solve();assert assignment is not None,'Initial open-edge topology constraints unsatisfiable'
vertexPins=[];unresolved=[]
for vk,refs in vertexHighest:
 if any(not assignment[var(i,k)-1] and not assignment[var(i,(k-1)%3)-1] for i,k in refs):continue
 resolved=False
 for i,k in sorted(refs,key=lambda q:sum(assignment[var(q[0],j)-1] for j in [q[1],(q[1]-1)%3])):
  pins=[(-var(i,k),-var(i,k)),(-var(i,(k-1)%3),-var(i,(k-1)%3))];attempt=solve([*vertexPins,*pins])
  if attempt is not None:vertexPins.extend(pins);assignment=attempt;resolved=True;break
 if not resolved:unresolved.append({'pointXZ':vk,'kind':'no consistent closed highest vertex owner','refs':refs})
# A later choice may remove an earlier accidental owner; iterate explicit pins for all uncovered vertices.
for iteration in range(5):
 changed=False
 for vk,refs in vertexHighest:
  if any(not assignment[var(i,k)-1] and not assignment[var(i,(k-1)%3)-1] for i,k in refs):continue
  for i,k in refs:
   pins=[(-var(i,k),-var(i,k)),(-var(i,(k-1)%3),-var(i,(k-1)%3))];attempt=solve([*vertexPins,*pins])
   if attempt is not None:vertexPins.extend(pins);assignment=attempt;changed=True;break
 if not changed:break
openEdges=[[assignment[var(i,j)-1] for j in range(3)] for i in range(len(triangles))]
unresolved=[]
for r in vertex_steps:
 for i,k in r['lowerReferences']:
  if not any(openEdges[i][j] for j in [k,(k-1)%3]):unresolved.append({'pointXZ':r['pointXZ'],'triangle':i,'vertex':k,'kind':'lower vertex still closed'})
for vk,refs in vertexHighest:
 if not any(not openEdges[i][k] and not openEdges[i][(k-1)%3] for i,k in refs):unresolved.append({'pointXZ':vk,'kind':'highest vertex uncovered'})
solid=[]
for level in [lower,upper]:solid.append({'id':level['id']+'-slab','thicknessGame':.39,'triangles':[[[x,z,y] for x,y,z in t['verticesGameXYZ']] for t in level['triangles']]})
result={'cityId':'hangzhou','units':'game east/north/up; scale applied once','terrainCuts':[],'walkFloors':[{'id':'city-balcony:upper','triangles':triangles,'openEdges':openEdges}],'solidSlabs':solid}
save('site-surfaces-envelope.json',result);save('triangle-provenance.json',provenance);save('step-boundaries.json',{'stepEdges':step_edges,'stepVertices':vertex_steps,'unresolvedLowerVertexOwners':unresolved});save('input-bindings.json',bindings)
print(json.dumps({'triangles':len(triangles),'overlayPlanes':sorted(set(r['height'] for r in regions)),'arrangementCells':len(regions),'stepEdges':len(step_edges),'stepVertices':len(vertex_steps),'openEdges':sum(sum(e) for e in openEdges),'unresolvedVertices':len(unresolved)},indent=2))
