from pathlib import Path
import json,math,hashlib,ast,struct,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).parent;bindings={}
def bind(p):p=Path(p);bindings[str(p)]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest();return ROOT/p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
data=read(str(OUT/'site-surfaces-envelope.json'));floor=data['walkFloors'][0];T=np.array(floor['triangles']);O=floor['openEdges'];polys=[Polygon(t[:,:2]) for t in T];tree=STRtree(polys);old=read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal/public-walk-surfaces.json');up=next(x for x in old['levels'] if x['id']=='city-balcony:upper');domain=Polygon(up['ringsXZ'][0],up['ringsXZ'][1:]);union=shapely.union_all(polys)
def at(x,z,closed=False):
 matches=[];p=Point(x,z)
 for i in map(int,tree.query(p,predicate='dwithin',distance=1e-9)):
  a,b,c=T[i];dx=x-a[0];dz=z-a[1];det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]);u=(dx*(c[1]-a[1])-dz*(c[0]-a[0]))/det;v=((b[0]-a[0])*dz-(b[1]-a[1])*dx)/det
  if u< -1e-9 or v< -1e-9 or u+v>1+1e-9:continue
  if not closed and any(flag and abs(w)<=1e-9 for flag,w in zip(O[i],[v,1-u-v,u])):continue
  h=a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]);matches.append({'triangle':i,'height':float(h),'bary':[float(1-u-v),float(u),float(v)]})
 return matches
pairs=[]
for i,p in enumerate(polys):
 for j in map(int,tree.query(p)):
  if j<=i:continue
  area=p.intersection(polys[j]).area
  if area>1e-12:pairs.append({'a':i,'b':j,'area':area})
# Every emitted vertex, edge quarters/midpoint and interior barycentric sample.
samples={}
for i,t in enumerate(T):
 for w in [[1,0,0],[0,1,0],[0,0,1],[.25,.75,0],[.5,.5,0],[.75,.25,0],[0,.25,.75],[0,.5,.5],[0,.75,.25],[.25,0,.75],[.5,0,.5],[.75,0,.25],[1/3]*3,[.1,.3,.6]]:
  q=np.array(w)@t;key=(round(float(q[0]),11),round(float(q[1]),11));samples.setdefault(key,(float(q[0]),float(q[1])))
fail=[];maxSpread=0;case=[]
for x,z in samples.values():
 matches=at(x,z)
 if not matches:fail.append({'pointXZ':[x,z],'reason':'no-owned-height','closedMatches':at(x,z,True)});continue
 spread=max(r['height'] for r in matches)-min(r['height'] for r in matches);maxSpread=max(maxSpread,spread)
 if spread>.0001:fail.append({'pointXZ':[x,z],'reason':'height-disagreement','matches':matches})
 case.append({'x':x,'z':z,'height':matches[0]['height']})
# Compare actual source GLB top/bottom slabs and envelope height planes within fixed .001g XY and Y tolerances.
helper=bind('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py');treeAst=ast.parse(helper.read_text());exec(compile(ast.Module(body=[n for n in treeAst.body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(helper),'exec'),globals());parts,g=glb(old['sourceArtifact']);actual=[]
for p in parts:
 for i,t in enumerate(p['triangles']):
  n=np.cross(t[1]-t[0],t[2]-t[0])
  if n[2]>1e-12:actual.append((p['name'],i,t,Polygon(t[:,:2])))
actualTree=STRtree([p[3] for p in actual]);sourceErrors=[];strictWrong=0;maxProjection=0;maxHeight=0
for x,z in samples.values():
 matches=at(x,z)
 if not matches:continue
 h=matches[0]['height'];q=Point(x,z);options=[];strict=[]
 for i in map(int,actualTree.query(q,predicate='dwithin',distance=.001)):
  name,index,t,p=actual[i];a,b,c=t;coeff=np.linalg.solve(np.c_[t[:,:2],np.ones(3)],t[:,2]);y=float(coeff@np.array([x,z,1]));dist=p.distance(q)
  if p.covers(q):strict.append(y)
  options.append((abs(y-h),dist,name,index))
 valid=[r for r in options if r[0]<=.001]
 if not valid:sourceErrors.append({'pointXZ':[x,z],'height':h,'options':options[:10]});continue
 best=min(valid);maxHeight=max(maxHeight,best[0]);maxProjection=max(maxProjection,best[1])
 # On exact step boundaries the actual float32 edge can be micrometres away; report separate fixed-XY comparison.
 if strict and min(abs(y-h) for y in strict)>.001:strictWrong+=1
faces={}
def key(t):return tuple(sorted(tuple(round(float(x),6) for x in p) for p in t))
for p in parts:
 for i,t in enumerate(p['triangles']):faces.setdefault(key(t),[]).append({'mesh':p['name'],'triangleIndex':i})
slabs=[]
for slab in data['solidSlabs']:
 hits=[];missing=[]
 for i,t in enumerate(slab['triangles']):
  ts=np.array(t);top=ts.astype('<f4').astype('f8');bot=ts.copy();bot[:,:,] if False else None
  bot[:,2]-=slab['thicknessGame'];bot=bot.astype('<f4').astype('f8');th=faces.get(key(top),[]);bh=faces.get(key(bot),[])
  if not th or not bh:missing.append(i)
  hits.append({'triangle':i,'actualTopFaces':th,'actualBottomFaces':bh})
 slabs.append({'id':slab['id'],'thicknessGame':slab['thicknessGame'],'triangles':len(slab['triangles']),'missingTopOrBottomTriangles':missing,'actualFaceLinks':hits})
save('slab-glb-correspondence.json',slabs);save('query-cases.json',case);save('ownership-query-failures.json',fail);save('source-height-failures.json',sourceErrors)
report={'triangles':len(T),'domainSymmetricDifferenceGame2':union.symmetric_difference(domain).area,'triangleAreaSumMinusUnionGame2':sum(p.area for p in polys)-union.area,'positiveAreaOverlapsAbove1e12':pairs,'sampleCount':len(samples),'ownershipFailures':len(fail),'maximumOwnedHeightSpreadGame':maxSpread,'sourceGlbHeightFailuresWithin1mmXY':len(sourceErrors),'maxMatchedSourceGlbHeightErrorGame':maxHeight,'maxMatchedSourceGlbProjectionDistanceGame':maxProjection,'fixedXyHeightDifferencesOver1mmAtStepSamples':strictWrong,'slabMissingActualFaces':sum(len(s['missingTopOrBottomTriangles']) for s in slabs),'onlyOneUpperWalkId':len(data['walkFloors'])==1 and floor['id']=='city-balcony:upper','lowerStillNotWalkEnabled':not any(g['id']=='city-balcony:lower' for g in data['walkFloors']),'noBrowserOrBlender':True}
save('validation.json',report);save('validation-input-bindings.json',bindings);print(json.dumps(report,indent=2))
