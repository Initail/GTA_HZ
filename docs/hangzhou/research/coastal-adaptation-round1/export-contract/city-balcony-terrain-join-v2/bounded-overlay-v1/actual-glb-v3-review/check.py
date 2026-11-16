"""Read actual glTF binary + source arrays; no producer or Blender execution."""
from pathlib import Path
import json,hashlib,ast,struct,math,collections,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;bindings={}
def bind(p):
 p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_absolute() else str(p);p=ROOT/rel;bindings[rel]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
def funcs(p,names):
 path=bind(p);mod=ast.Module(body=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]);exec(compile(mod,str(path),'exec'),globals())
funcs('docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/check.py',{'glb'})
base=OUT.parent;contract=read(base/'candidate-contract.json');manifest=read('artifacts/cities/hangzhou/city-balcony-terrain-glb-v3/asset-manifest.json');actual,gltf=glb('artifacts/cities/hangzhou/city-balcony-terrain-glb-v3/city-balcony-terrain.glb')
arr=np.load(bind(contract['mesh']));source=np.concatenate([arr['top'],arr['walls']]);topcount=len(arr['top']);provenance=read(base/'top-provenance.json');bounds=read(base/'vertical-boundaries.json');origin=np.asarray(manifest['frame']['originENU']);angle=manifest['frame']['angleRadians'];assert np.array_equal(origin,origin.astype('f4').astype('f8'))
basis=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
local=((source-origin)@basis).astype('f4').astype('f8');gltf_local=local[:,:,[0,2,1]]*np.array([1,1,-1]);wm=np.array(actual[0]['world']);wp=(np.c_[gltf_local.reshape(-1,3),np.ones(len(source)*3)]@wm.T)[:,:3];expected=(wp[:,[0,2,1]]*np.array([1,-1,1])).reshape(-1,3,3)
actualRotationENU=wm[:3,:3][[0,2,1]][:,[0,2,1]]*np.array([1,-1,1])[:,None]*np.array([1,-1,1])[None,:];rotationError=float(np.max(np.abs(actualRotationENU-basis)))
assert rotationError<1e-6

expectedmat=[p['material'] for p in provenance]+['land']*len(arr['walls'])
def canonical(t):
 p=[tuple(v) for v in t];return min(tuple(p),tuple(p[1:]+p[:1]),tuple(p[2:]+p[:2]))
source_by_key={canonical(t):i for i,t in enumerate(expected)}
actualfaces=[];faceinfo=[];unmatched=[];row=[];matchedcounts=collections.Counter();uvfails=[];uvnegative=[];maxvertex=0;exact_uv_mismatch=0;maximum_uv_error=0
for part in actual:
 ts=part['triangles'];uv=part['uv'];area=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0]));zeros=np.flatnonzero(area==0)
 row.append({'name':part['name'],'material':part['material'],'triangles':len(ts),'uvFinite':bool(np.isfinite(uv).all()),'normalFinite':bool(np.isfinite(part['normals']).all()),'uvZeroAreaTriangles':len(zeros),'uvMinimumDoubleArea':float(area.min()),'worldMatrix':part['world']})
 for j,t in enumerate(ts):
  key=canonical(t);idx=source_by_key.get(key)
  if idx is None:unmatched.append({'part':part['name'],'face':j,'triangle':t.tolist()});continue
  matchedcounts[idx]+=1;axes=[0,1];expected_uv=source[idx][:,axes]/8
  if idx>=topcount:
   normal=np.cross(source[idx,1]-source[idx,0],source[idx,2]-source[idx,0]);axes=[1,2] if abs(normal[0])>=abs(normal[1]) else [0,2];expected_uv=source[idx][:,axes]/8
  expected_uv-=np.floor(origin[axes]/8)
  # glTF exporter flips V; compare each matched actual corner against its source corner.
  source_uv=expected_uv.astype('f4').astype('f8');source_uv[:,1]=(1-source_uv[:,1]).astype('f4').astype('f8');corner_order=[next(k for k,p in enumerate(expected[idx]) if np.array_equal(p,v)) for v in t];uv_error=float(np.max(np.abs(uv[j].astype('f8')-source_uv[corner_order])))
  maximum_uv_error=max(maximum_uv_error,uv_error)
  exact_uv_mismatch+=not np.array_equal(uv[j].astype('f8'),source_uv[corner_order])
  if uv_error>1e-5:uvfails.append({'sourceFace':idx,'error':uv_error})
  if area[j]==0:uvnegative.append({'sourceFace':idx,'kind':'top' if idx<topcount else 'wall','triangleENU':t.tolist(),'uv':uv[j].tolist(),'sourceArea':float(np.linalg.norm(np.cross(source[idx,1]-source[idx,0],source[idx,2]-source[idx,0]))/2)})
  maxvertex=max(maxvertex,float(np.max(np.linalg.norm(t-source[idx,corner_order],axis=1))));actualfaces.append(t);faceinfo.append({'sourceIndex':idx,'material':part['material'],'part':part['name'],'face':j})
previous,_=glb('artifacts/cities/hangzhou/city-balcony-terrain-glb-v1/city-balcony-terrain.glb');same_geometry=collections.Counter(canonical(t) for p in previous for t in p['triangles'])==collections.Counter(canonical(t) for t in actualfaces)
faces=np.asarray(actualfaces);normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]);edges=collections.defaultdict(list);zero=int(np.sum(np.linalg.norm(normals,axis=1)==0));materialmismatch=[]
for i,(t,info) in enumerate(zip(faces,faceinfo)):
 idx=info['sourceIndex']
 if info['material']!=expectedmat[idx]:materialmismatch.append(info)
 for a,b in zip(t,np.roll(t,-1,axis=0)):
  a,b=tuple(a),tuple(b);edges[tuple(sorted([a,b]))].append((i,a<b))
mask=shape(read(base.parent/'bank-top-render-owner-mask.geojson')['features'][0]['geometry']);domain={f['properties']['id']:shape(f['geometry']) for f in read(base/'local-domains.geojson')['features']};opens=[];nonmanifold=[];winding=[];kinds=collections.Counter()
for key,uses in edges.items():
 if len(uses)==1:
  q=Point((np.array(key[0][:2])+key[1][:2])/2);kind='shore-v3-owned' if min(domain['water'].boundary.distance(q),mask.boundary.distance(q))<.001 else 'crop-open' if domain['local-crop'].boundary.distance(q)<.001 else 'unexpected';kinds[kind]+=1;opens.append({'edge':key,'face':faceinfo[uses[0][0]],'kind':kind})
 elif len(uses)!=2:nonmanifold.append({'edge':key,'uses':[faceinfo[i] for i,_ in uses]})
 elif uses[0][1]==uses[1][1]:winding.append({'edge':key,'uses':[faceinfo[i] for i,_ in uses]})
actualtops=np.asarray([t for t,m in zip(faces,faceinfo) if m['sourceIndex']<topcount]);actualwalls=np.asarray([t for t,m in zip(faces,faceinfo) if m['sourceIndex']>=topcount]);polys=[Polygon(t[:,:2]) for t in actualtops];footprint=shapely.union_all(polys)
checks={'manifestContractMatches':bindings[str((base/'candidate-contract.json').relative_to(ROOT))]==manifest['sourceContractSha256'],'manifestMeshMatches':bindings[contract['mesh']]==manifest['sourceMeshSha256'],'manifestProvenanceMatches':bindings[str((base/'top-provenance.json').relative_to(ROOT))]==manifest['sourceProvenanceSha256'],'actualGlbMatchesManifest':bindings['artifacts/cities/hangzhou/city-balcony-terrain-glb-v3/city-balcony-terrain.glb']==manifest['assets'][0]['sha256']}
report={'actualGlbSha256':bindings['artifacts/cities/hangzhou/city-balcony-terrain-glb-v3/city-balcony-terrain.glb'],'triangles':len(faces),'sourceTriangles':len(source),'topTriangles':len(actualtops),'wallTriangles':len(actualwalls),'orientedWorldGeometryExactlyEqualsV1':same_geometry,'actualNodeRotationVsExpectedMaximumError':rotationError,'uvIntegerPeriodOriginENU':manifest['uv']['integerPeriodOriginENU'],'uvPeriodGame':manifest['uv']['periodGame'],'allSourceTrianglesMatchedOnce':len(matchedcounts)==len(source) and all(n==1 for n in matchedcounts.values()),'unmatchedActualFaces':len(unmatched),'zeroArea3dTriangles':zero,'allTopNormalsUp':bool(np.all(np.cross(actualtops[:,1]-actualtops[:,0],actualtops[:,2]-actualtops[:,0])[:,2]>0)),'wallHorizontalProjectionMaxDoubleArea':float(np.max(np.abs(np.cross(actualwalls[:,1]-actualwalls[:,0],actualwalls[:,2]-actualwalls[:,0])[:,2]))),'maxSourceVertexErrorGame':maxvertex,'exactUnpairedEdgesByOwnership':dict(kinds),'nonmanifoldEdges':len(nonmanifold),'sameDirectionSharedEdges':len(winding),'materialMismatches':len(materialmismatch),'uvExactSerializedFaceMismatches':int(exact_uv_mismatch),'uvMaximumSerializedValueError':maximum_uv_error,'uvMappingErrorsAbove1eMinus5':len(uvfails),'uvZeroAreaTriangles':len(uvnegative),'topDomainSymmetricDifferenceArea':float(footprint.symmetric_difference(domain['dry']).area),'topWaterIntrusionArea':float(footprint.intersection(domain['water']).area),'sourceDomainBoundaryHausdorffGame':float(footprint.boundary.hausdorff_distance(domain['dry'].boundary)),'meshRows':row,'inputChecks':checks,'passedGeometryUvGate':not(exact_uv_mismatch or unmatched or zero or nonmanifold or winding or materialmismatch or uvfails or uvnegative) and kinds['unexpected']==0 and all(checks.values()),'claimsNotMade':['full closed soil solid','crop merged with global terrain','body/renderer/browser/visual acceptance']}
save('actual-report.json',report);save('actual-failures.json',{'unmatched':unmatched,'nonmanifold':nonmanifold,'winding':winding,'material':materialmismatch,'uvMapping':uvfails,'uvZeroArea':uvnegative,'openEdges':opens});save('actual-face-map.json',faceinfo);np.savez_compressed(OUT/'actual-world-enu.npz',all=faces,top=actualtops,walls=actualwalls);save('input-bindings.json',bindings);print(json.dumps(report,ensure_ascii=False,indent=2))
