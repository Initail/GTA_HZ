"""Independent recomputation of local mesh heights, boundaries and solid ownership."""
from pathlib import Path
import sys,json,math,hashlib
from collections import defaultdict,Counter
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,shape,LineString
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface,digest
from hangzhou_site_partition import plane
SRC=ROOT/'artifacts/cities/hangzhou/render-input-v7';read=lambda p:json.loads(p.read_text());write=lambda n,d:(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
mesh=np.load(OUT/'local-terrain.npz');top=mesh['top'];walls=mesh['walls'];meta=read(OUT/'top-provenance.json');bound=read(OUT/'vertical-boundaries.json');sites=read(OUT/'site-surfaces-repair.json');field=Surface(SRC)
from hangzhou_site_surfaces import SiteSurfaces
field.sites=SiteSurfaces(sites)
planes={g['id']+':'+str(i):plane(t) for g in sites['terrainCuts'] for i,t in enumerate(g['triangles'])};domains={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']}
shapes=[Polygon(t[:,:2]) for t in top];union=shapely.union_all(shapes);tree=STRtree(shapes)
def ownerheight(i,x,z):return min([field.uncut_ground(x,z)]+[planes[o](x,z) for o in meta[i]['owners']])
# Every vertex and four interior/edge probes. Own boundary closures intentionally differ from global min at step edges.
maxvertex=0;maxprobe=0;maxoutside=0;count=0;errors=[];sourcequeryfails=[];outside=0
weights=[[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3]*3]
for i,t in enumerate(top):
 for j,w in enumerate(weights):
  p=np.asarray(w)@t;expected=ownerheight(i,*p[:2]);err=abs(p[2]-expected);count+=1
  if j<3:maxvertex=max(maxvertex,err)
  else:maxprobe=max(maxprobe,err)
  if not meta[i]['owners']:
   outside+=1;maxoutside=max(maxoutside,abs(p[2]-field.uncut_ground(*p[:2])))
  if err>.01:errors.append({'face':i,'weights':w,'error':err,'point':p.tolist()})
 # Only strict interior witness compares global min; this catches selecting the wrong side of a cell.
 p=t.mean(axis=0);pt=Point(p[:2]);distance=domains['cut-union'].boundary.distance(pt)
 if distance>1e-8:
  actual=field.ground(*p[:2]);err=abs(actual-p[2])
  if err>.01:sourcequeryfails.append({'face':i,'point':p.tolist(),'runtime':actual,'error':err,'owners':meta[i]['owners']})
# Mesh top and sidewalls share exact XY: vertical sides never span different XZ banks.
verticalbad=[];walltopbad=[]
for i,t in enumerate(walls):
 xy={tuple(p[:2]) for p in t}
 if len(xy)!=2:verticalbad.append(i)
# Record oriented edge incidence; separate numerical residuals from true openings.
allts=np.concatenate([top,walls]);cross=np.linalg.norm(np.cross(allts[:,1]-allts[:,0],allts[:,2]-allts[:,0]),axis=1)
exact=defaultdict(list);rounded=defaultdict(list)
for i,t in enumerate(allts):
 for a,b in zip(t,np.roll(t,-1,axis=0)):
  a,b=tuple(a),tuple(b);key=tuple(sorted([a,b]));exact[key].append((i,a<b))
  a,b=tuple(round(v,9) for v in a),tuple(round(v,9) for v in b)
  if a!=b:rounded[tuple(sorted([a,b]))].append((i,a<b))
# Expected openings only at the crop and the shoreline (owned by separate shore-v3).
unexpected=[];nonmanifold=[];winding=[];openkind=Counter()
for key,uses in rounded.items():
 if len(uses)==1:
  a,b=map(np.asarray,key);mid=Point((a[:2]+b[:2])/2)
  kind='shore-v3-owned' if domains['water'].boundary.distance(mid)<1e-7 else 'local-crop' if domains['local-crop'].boundary.distance(mid)<1e-7 else 'unexpected'
  openkind[kind]+=1
  if kind=='unexpected':unexpected.append({'edge':key,'uses':uses})
 elif len(uses)!=2:nonmanifold.append({'edge':key,'uses':uses})
 elif uses[0][1]==uses[1][1]:winding.append({'edge':key,'uses':uses})
# Planar overlap audit independent from producer area sum.
overlaps=[]
for i,p in enumerate(shapes):
 for j in tree.query(p,predicate='intersects'):
  if j>i:
   area=p.intersection(shapes[int(j)]).area
   if area>1e-10:overlaps.append({'a':i,'b':int(j),'area':area})
# Source-floor support: dry floor area sits over cut/domain or retained base, never manufactures water land.
slabdomains={g['id']:shapely.union_all([Polygon([p[:2] for p in t]) for t in g['triangles']]) for g in sites['solidSlabs']}
sourcefloor={k:{'area':p.area,'dryArea':p.intersection(domains['dry']).area,'waterArea':p.intersection(domains['water']).area,'dryOutsideCutArea':p.intersection(domains['dry']).difference(domains['cut-union']).area} for k,p in slabdomains.items()}
report={'meshSha256':digest(OUT/'local-terrain.npz'),'sourceSamplerSha256':digest(ROOT/'scripts/hangzhou_surface.py'),'partitionSha256':digest(ROOT/'scripts/hangzhou_site_partition.py'),'topTriangles':len(top),'wallTriangles':len(walls),'heightProbeCount':count,'maxVertexSourceErrorGame':maxvertex,'maxInteriorEdgeProbeErrorGame':maxprobe,'heightProbeErrorsAbovePoint01Game':len(errors),'strictInteriorRuntimeMinFailuresAbovePoint01Game':len(sourcequeryfails),'outsideCutF1ProbeCount':outside,'outsideCutMaxF1MeshApproximationGame':maxoutside,'domainSymmetricDifferenceArea':union.symmetric_difference(domains['dry']).area,'positiveAreaOverlapsAbove1eMinus10':len(overlaps),'topWaterOverlapArea':union.intersection(domains['water']).area,'verticalWallPlanFailures':len(verticalbad),'zeroArea3dTriangles':int(np.sum(cross==0)),'minimum3dDoubleArea':float(cross.min()),'exactUnpairedEdges':sum(len(v)==1 for v in exact.values()),'exactNonmanifoldEdges':sum(len(v)>2 for v in exact.values()),'exactSameDirectionSharedEdges':sum(len(v)==2 and v[0][1]==v[1][1] for v in exact.values()),'topologyWeldToleranceGame':1e-9,'weldedUnpairedByKind':dict(openkind),'unexpectedOpenEdges':len(unexpected),'nonmanifoldEdges':len(nonmanifold),'sameDirectionSharedEdges':len(winding),'sourceFloorCoverage':sourcefloor,'passed':not(errors or sourcequeryfails or overlaps or verticalbad or unexpected or nonmanifold or winding or np.any(cross==0)) and union.symmetric_difference(domains['dry']).area<1e-9,'limitations':['CPU projected terrain partition only; GLB intersections, actual renderer, actors and browser unverified','Welded topology uses explicit 1e-9g numerical tolerance; 1e-8g derived noding and boundary duplicate normalization are reported separately','Finite 1g mesh probe error is not a continuous error bound','crop and water boundaries remain open by ownership, not claimed closed full solid']}
write('validation.json',report);write('validation-failures.json',{'height':errors,'runtime':sourcequeryfails,'overlaps':overlaps,'vertical':verticalbad,'unexpected':unexpected,'nonmanifold':nonmanifold,'winding':winding})
print((OUT/'validation.json').read_text(),flush=True)
