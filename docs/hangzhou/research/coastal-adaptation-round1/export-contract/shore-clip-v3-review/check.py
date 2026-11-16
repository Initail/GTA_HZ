"""Independent actual GLB/CSG contract review; no Blender or shared writes."""
from pathlib import Path
import argparse,json,hashlib,struct,math,collections,ast
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).parent;bindings={}
def bind(p):
 p=Path(p);relative=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);absolute=ROOT/relative;bindings[relative]=hashlib.sha256(absolute.read_bytes()).hexdigest();return absolute
def read(p):return json.loads(bind(p).read_text())
def save(name,d):(OUT/name).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def import_functions(p,names):
 source=bind(p);tree=ast.parse(source.read_text());mod=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]);exec(compile(mod,str(source),'exec'),globals())
import_functions('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py',{'glb','topology'})
import_functions('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/intersections.py',{'intri','tri_intersection'})
ap=argparse.ArgumentParser();ap.add_argument('--new-glb',required=True);ap.add_argument('--manifest');args=ap.parse_args()
base='artifacts/cities/hangzhou/';previous,_=glb(base+'shore-glb-v2/coastal-shoreline.glb');current,_=glb(args.new_glb)
if args.manifest:manifest=read(args.manifest)
else:manifest=None
ownership='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-floor-v2-glb-review/';contract=read(ownership+'ownership-contract.json');clip=shape(contract['clipEnvelopeGame']);cap=contract['capTopYGame'];bottom=contract['originalShoreBottomYGame'];pier_parts=[Polygon(p['polygonGame']).buffer(p['subtractHorizontalToleranceGame'],join_style=2) for p in contract['sourcePiersToSubtract']];pier=shapely.union_all(pier_parts);mutmask=shapely.union_all([clip,pier]);frozen=read(ownership+'package-manifest.json');frozenChecks={row['path']:hashlib.sha256(bind(row['path']).read_bytes()).hexdigest()==row['sha256'] for row in frozen['files']}
for r in contract['maskFiles']:
 assert hashlib.sha256(bind(r['path']).read_bytes()).hexdigest()==r['sha256'],'Changed frozen mask'
oldbal,_=glb(base+'landmarks/city-balcony-v1/city-balcony.glb');newbal,_=glb(base+'landmarks/city-balcony-floor-v2/city-balcony.glb')
assert bindings[base+'landmarks/city-balcony-floor-v2/city-balcony.glb']==contract['actualBalconyArtifactSha256']
city=read(base+'water-data-v3/city.json');wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']]);prop=next(p for p in read('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-source-proposal/proposals.json')['proposals'] if p['id']=='qianjiang-city-balcony');sourceLine=LineString(prop['geometryGame']['coordinates'])
# Primitive regrouping: topological seam duplicated for UV/normals must weld by actual coordinates, not vertex index.
def groups(parts):
 out={}
 for p in parts:
  if p['name'] not in out:out[p['name']]={'triangles':[],'materials':set(),'uvFinite':True,'normalFinite':True}
  q=out[p['name']];q['triangles'].append(p['triangles']);q['materials'].add(p['material']);q['uvFinite']&=p['uv'] is not None and bool(np.isfinite(p['uv']).all());q['normalFinite']&=p['normals'] is not None and bool(np.isfinite(p['normals']).all())
 for q in out.values():q['triangles']=np.concatenate(q['triangles'])
 return out
old=groups(previous);new=groups(current);target='coastal_shore_5_-4_land';topologyRows=[]
def canonical(t):
 ps=[tuple(p) for p in t];return min(tuple(ps),tuple(ps[1:]+ps[:1]),tuple(ps[2:]+ps[:2]))
for name,q in new.items():
 original=old.get(name);row={'name':name,'materials':sorted(q['materials']),'topology':topology(q['triangles']),'uvFinite':q['uvFinite'],'normalFinite':q['normalFinite']}
 if original is not None:row['exactOriginalOrientedWorldTriangleSetUnchanged']=collections.Counter(canonical(t) for t in original['triangles'])==collections.Counter(canonical(t) for t in q['triangles'])
 topologyRows.append(row)
save('topology-and-preservation.json',topologyRows);print('topology',json.dumps(topologyRows),flush=True)
assert target in old and target in new,'Target name changed/missing'
oldts=old[target]['triangles'];newts=new[target]['triangles']
def footprint(ts):return shapely.union_all([Polygon(t[:,:2]) for t in ts if Polygon(t[:,:2]).area>1e-12])
oldfp=footprint(oldts);newfp=footprint(newts);expectedfp=oldfp.difference(pier)
# Ray intervals in a source-registered XY solid are stronger than face equality when Boolean re-triangulates unchanged faces.
class Rays:
 def __init__(self,ts):
  self.tri=[];self.polys=[]
  for t in ts:
   p=Polygon(t[:,:2])
   if p.area>1e-12:self.tri.append(t);self.polys.append(p)
  self.tree=STRtree(self.polys)
 def at(self,p):
  q=Point(p);values=[]
  for i in map(int,self.tree.query(q)):
   t=self.tri[i];a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);u=((b[1]-c[1])*(p[0]-c[0])+(c[0]-b[0])*(p[1]-c[1]))/den;v=((c[1]-a[1])*(p[0]-c[0])+(a[0]-c[0])*(p[1]-c[1]))/den;w=1-u-v
   if min(u,v,w)>=-1e-7:values.append(float(u*a[2]+v*b[2]+w*c[2]))
  values.sort();unique=[]
  for v in values:
   if not unique or abs(v-unique[-1])>1e-5:unique.append(v)
  return unique
r_old=Rays(oldts);r_new=Rays(newts);samples=[]
for a,b in zip(sourceLine.coords,sourceLine.coords[1:]):
 a,b=np.array(a),np.array(b);d=b-a;length=np.linalg.norm(d);n=np.array([-d[1],d[0]])/length;mid=(a+b)/2;sign=-1 if wet.covers(Point(mid+n*.3)) else 1;count=math.ceil(length/.5)
 for i in range(count):
  c=a+d*(i+.5)/count
  for offset in [.01,.06,.11]:
   q=c+n*sign*offset
   if oldfp.covers(Point(q)):samples.append(q)
# Test explicit near-cut points and pier-hole interior in addition to uniform bank samples.
for geometry in [clip.boundary,pier.boundary]:
 geoms=list(geometry.geoms) if hasattr(geometry,'geoms') else [geometry]
 for line in geoms:
  for i in range(max(1,math.ceil(line.length/.05))+1):
   q=line.interpolate(min(line.length,i*.05));x,z=q.x,q.y
   if oldfp.distance(q)>.2:continue
   for dx,dz in [(0,0),(.002,0),(-.002,0),(0,.002),(0,-.002)]:
    p=Point(x+dx,z+dz)
    if oldfp.covers(p):samples.append(np.array([p.x,p.y]))
if not pier.is_empty:
 xmin,zmin,xmax,zmax=pier.intersection(oldfp).bounds
 for x in np.arange(xmin,xmax+.01,.025):
  for z in np.arange(zmin,zmax+.01,.025):
   if oldfp.covers(Point(x,z)):samples.append(np.array([x,z]))
rayRows=[];counts=collections.Counter();maxOutside=0.;maxInside=0.;fail=[]
for p in samples:
 point=Point(p);oldv=r_old.at(p);newv=r_new.at(p);near=min(point.distance(clip.boundary),point.distance(pier.boundary))<.001
 if len(oldv)!=2:
  fail.append({'point':p.tolist(),'reason':'old-ray-not-one-interval','old':oldv});continue
 if near:counts['boundaryToleranceSkipped']+=1;continue
 if pier.covers(point):kind='pillar-hole';expected=[]
 elif clip.covers(point):kind='cap';expected=[oldv[0],min(oldv[-1],cap)]
 else:kind='unchanged';expected=oldv
 counts[kind]+=1;error=max((abs(a-b) for a,b in zip(newv,expected)),default=0.) if len(newv)==len(expected) else math.inf
 if kind=='unchanged':maxOutside=max(maxOutside,error)
 else:maxInside=max(maxInside,error)
 if error>.001:fail.append({'point':p.tolist(),'kind':kind,'old':oldv,'new':newv,'expected':expected,'error':error})
 rayRows.append({'point':p.tolist(),'kind':kind,'old':oldv,'new':newv,'expected':expected,'error':error})
save('ray-intervals.json',rayRows)
# Source front remains wherever the actual pillar owns no gap. Quantization tolerance is explicit.
frontDistances=[]
for i in range(math.ceil(sourceLine.length/.25)+1):
 q=sourceLine.interpolate(min(i*.25,sourceLine.length))
 if pier.distance(q)<.002:continue
 frontDistances.append(q.distance(newfp.boundary))
vertexRows=[]
for p in np.unique(newts.reshape(-1,3),axis=0):
 q=Point(p[:2]);inside=clip.covers(q) and q.distance(clip.boundary)>.001
 if inside and p[2]>cap+.001:vertexRows.append({'point':p.tolist(),'reason':'above-cap-inside-mask'})
 if not oldfp.buffer(.001).covers(q):vertexRows.append({'point':p.tolist(),'reason':'new-horizontal-geometry-outside-old-strip'})
 if p[2]<bottom-.001:vertexRows.append({'point':p.tolist(),'reason':'below-original-bottom'})
normalizedExpected=shapely.set_precision(expectedfp,1e-10);normalizedNew=shapely.set_precision(newfp,1e-10)
normalizedBoundaryError=normalizedNew.boundary.hausdorff_distance(normalizedExpected.boundary)
geometry={'normalizedDerivedProjectionGridGame':1e-10,'normalizedExpectedFootprintBoundaryHausdorffGame':normalizedBoundaryError,'sampleCounts':dict(counts),'rayFailureCount':len(fail),'rayFailures':fail[:100],'maxOutsideHeightErrorGame':maxOutside,'maxInsideHeightErrorGame':maxInside,'expectedFootprintBoundaryHausdorffGame':newfp.boundary.hausdorff_distance(expectedfp.boundary),'footprintSymmetricDifferenceGame2':newfp.symmetric_difference(expectedfp).area,'newFootprintOutsideOriginalGame2':newfp.difference(oldfp).area,'sourceFrontMaxBoundaryDistanceExcludingPillarGame':max(frontDistances),'pillarResidualProjectedAreaGame2':newfp.intersection(pier.buffer(-.001)).area,'vertexViolationCount':len(vertexRows),'vertexViolations':vertexRows[:100],'newVsOriginalOutsideMaskProjectedSymDiffGame2':newfp.difference(mutmask).symmetric_difference(oldfp.difference(mutmask)).area}
save('csg-geometry.json',geometry);print('geometry',json.dumps(geometry),flush=True)
# Reproduce original 836/625 pair evidence, then evaluate actual new candidate against the actual floor-v2.
def intersections(shores,bal,record):
 rows=[]
 for name,q in shores.items():
  sts=q['triangles'];tree=STRtree([Polygon(t[:,:2]) for t in sts]);parts=[]
  for part in bal:
   pairs=[]
   for i,t in enumerate(part['triangles']):
    for j in map(int,tree.query(Polygon(t[:,:2]))):
     s=sts[j]
     if t[:,2].min()>s[:,2].max()+1e-6 or t[:,2].max()<s[:,2].min()-1e-6:continue
     hit=tri_intersection(t,s)
     if hit:pairs.append({'balconyTriangle':i,'shoreTriangle':j,**hit})
   parts.append({'name':part['name'],'count':len(pairs),'pairs':pairs if record else []})
  rows.append({'shore':name,'parts':parts,'total':sum(p['count'] for p in parts)})
 return rows
baselineOld=intersections(old,oldbal,False);baselineCurrent=intersections(old,newbal,False);candidate=intersections(new,newbal,True)
save('three-way-actual-intersections.json',{'oldShoreNeutralBalcony':baselineOld,'oldShoreFloorV2':baselineCurrent,'newShoreFloorV2':candidate})
manifestChecks={}
if manifest is not None:
 for key,path in [('sourceManifestSha256',manifest['sourceManifest']),('ownershipContractSha256',manifest['ownershipContract']),('exporterSha256','scripts/build_hangzhou_shores_clipped.py'),('triangleHasherSha256','scripts/build_hangzhou_foundations.py')]:
  manifestChecks[key]=hashlib.sha256(bind(path).read_bytes()).hexdigest()==manifest[key]
 manifestChecks['actualAssetSha256']=manifest['assets'][0]['sha256']==bindings[args.new_glb]
 manifestChecks['actualTriangleCount']=manifest['assets'][0]['triangles']==sum(len(q['triangles']) for q in new.values())
save('producer-manifest-checks.json',manifestChecks)
unchanged=[r for r in topologyRows if r['name']!=target];allTopology=all(r['topology']['zeroArea']==r['topology']['badEdges']==0 and r['topology']['signedVolume']>0 and r['uvFinite'] and r['normalFinite'] for r in topologyRows);before1=sum(r['total'] for r in baselineOld);before2=sum(r['total'] for r in baselineCurrent);after=sum(r['total'] for r in candidate)
checks={'actualProducerManifestMatches':bool(manifestChecks) and all(manifestChecks.values()),'allFrozenInputHashesMatch':all(frozenChecks.values()),'sameFourMeshNames':set(old)==set(new) and len(new)==4,'allActualMeshesClosedNondegeneratePositiveVolume':allTopology,'threeUnchangedGroupsExactOrientedTriangleGeometry':all(r.get('exactOriginalOrientedWorldTriangleSetUnchanged') for r in unchanged) and len(unchanged)==3,'old836Reproduced':before1==836,'old625Reproduced':before2==625,'newActualBalconySurfaceIntersectionPairsZero':after==0,'rayIntervalsMatchCsgRule':len(fail)==0,'heightCapAndSourceFootprintVertexChecks':len(vertexRows)==0,'footprintBoundaryMatchesExpectedWithin1mm':geometry['normalizedExpectedFootprintBoundaryHausdorffGame']<=.001,'pillarResidualAreaZeroAt1mmInterior':geometry['pillarResidualProjectedAreaGame2']<1e-10,'sourceFrontPreservedWithin1mm':geometry['sourceFrontMaxBoundaryDistanceExcludingPillarGame']<=.001}
save('validation.json',{'checks':checks,'boundedCpuChecksPass':all(checks.values()),'oldNeutralPairs':before1,'oldFloorV2Pairs':before2,'newFloorV2Pairs':after,'newGlb':args.new_glb,'newGlbSha256':bindings[args.new_glb],'status':'actual GLB geometry checks only; terrain, body, browser, visual and performance unaccepted','browserOrBlenderRun':False});save('input-bindings.json',bindings);print(json.dumps(checks,indent=2));
