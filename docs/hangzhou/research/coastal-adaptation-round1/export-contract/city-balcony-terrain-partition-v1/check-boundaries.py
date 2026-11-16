"""Keep discontinuity geometry and height comparisons separate from smooth-field error."""
from pathlib import Path
import sys,json,math
from collections import defaultdict,Counter
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,shape
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface,digest
read=lambda p:json.loads(p.read_text());write=lambda n,d:(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v))+'\n')
SRC=ROOT/'artifacts/cities/hangzhou/render-input-v7';field=Surface(SRC);mesh=np.load(OUT/'local-terrain.npz');top=mesh['top'];walls=mesh['walls'];meta=read(OUT/'top-provenance.json');bound=read(OUT/'vertical-boundaries.json');domains={f['properties']['id']:shape(f['geometry']) for f in read(OUT/'local-domains.geojson')['features']}
main=domains['city-balcony:dry-main'];west=domains['city-balcony:west-finger'];east=domains['city-balcony:east-finger'];dry=domains['dry'];original={'main':main,'west':west.difference(main),'east':east.difference(main),'F1':dry.difference(main.union(west).union(east))}
def label(owners):
 if any(o.startswith('city-balcony:dry-main:') for o in owners):return 'main'
 if any(o.startswith('city-balcony:west-finger:') for o in owners):return 'west'
 if any(o.startswith('city-balcony:east-finger:') for o in owners):return 'east'
 return 'F1'
triangles=[Polygon(t[:,:2]) for t in top];bylabel=defaultdict(list);bymat=defaultdict(list)
for p,m in zip(triangles,meta):bylabel[label(m['owners'])].append(p);bymat[m['material']].append(p)
actual={k:shapely.union_all(v) for k,v in bylabel.items()};diffs=[]
for k,p in original.items():
 q=actual[k];pn,qn=shapely.set_precision(p,1e-10),shapely.set_precision(q,1e-10);diffs.append({'id':k,'sourceArea':p.area,'derivedArea':q.area,'symmetricDifferenceArea':p.symmetric_difference(q).area,'addedArea':q.difference(p).area,'removedArea':p.difference(q).area,'rawBoundaryHausdorffGame':p.boundary.hausdorff_distance(q.boundary),'metricNormalizedBoundaryHausdorffGame':pn.boundary.hausdorff_distance(qn.boundary),'metricNormalizedSymmetricDifferenceArea':pn.symmetric_difference(qn).area,'status':'derived ownership line only; original physics boundary unchanged'})
material=[]
for k,source in [('park',domains['green']),('land',dry.difference(domains['green']))]:
 actualmat=shapely.union_all(bymat[k]);pn,qn=shapely.set_precision(source,1e-10),shapely.set_precision(actualmat,1e-10);material.append({'id':k,'sourceArea':source.area,'derivedArea':actualmat.area,'symmetricDifferenceArea':source.symmetric_difference(actualmat).area,'rawBoundaryHausdorffGame':source.boundary.hausdorff_distance(actualmat.boundary),'metricNormalizedBoundaryHausdorffGame':pn.boundary.hausdorff_distance(qn.boundary),'metricNormalizedSymmetricDifferenceArea':pn.symmetric_difference(qn).area})
# Each seam is explicitly vertical and lies on both adjacent original ownership boundaries within the noding budget.
seams=[];maxdistance=0;maxstep=0;maxcapheightdifference=0
for seam in bound['seams']:
 high=label(seam['highOwners']);low=label(seam['lowOwners']);a,b=map(np.asarray,seam['edge']);dist=0
 for t in [0,.25,.5,.75,1]:
  p=Point((1-t)*a+t*b)
  dist=max(dist,p.distance(original[high].boundary),p.distance(original[low].boundary))
 maxdistance=max(maxdistance,dist);step=max(h-l for h,l in zip(seam['highY'],seam['lowY']));maxstep=max(maxstep,step)
 seams.append({'high':high,'low':low,'edge':seam['edge'],'distanceToBothSourceBoundariesGame':dist,'maximumHeightStepGame':step,'wallTriangles':seam['wallTriangles']})
# Actual point queries split by a 2e-8g boundary envelope. No averaging away multi-metre jumps.
source_edges=shapely.union_all([p.boundary for p in original.values()]);narrow=[];smooth_max=0;smooth_count=0;smooth_fail=[]
for i,t in enumerate(top):
 for w in [[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3]*3]:
  p=np.asarray(w)@t;distance=source_edges.distance(Point(p[:2]));actual_height=field.ground(*p[:2]);error=abs(actual_height-p[2])
  if distance<=2e-8:
   narrow.append({'face':i,'point':p.tolist(),'distanceToSourceBoundaryGame':distance,'meshY':p[2],'physicsY':actual_height,'heightDifferenceGame':error,'owners':meta[i]['owners']})
  else:
   smooth_max=max(smooth_max,error);smooth_count+=1
   if error>.01:smooth_fail.append({'face':i,'point':p.tolist(),'error':error})
# Float32 feasibility simulation is explicitly not an actual GLB result.
allts=np.concatenate([top,walls]);origin=(allts.min(axis=(0,1))+allts.max(axis=(0,1)))/2;rounded=(allts-origin).astype('<f4').astype('<f8')+origin;cross=np.linalg.norm(np.cross(rounded[:,1]-rounded[:,0],rounded[:,2]-rounded[:,0]),axis=1);bad=np.flatnonzero(cross==0)
float_record={'status':'simulated one local origin, not actual GLB','originENU':origin.tolist(),'maximumVertexErrorGame':float(np.max(np.linalg.norm(rounded-allts,axis=2))),'zeroAreaTriangleCount':len(bad),'zeroAreaTriangles':[{'index':int(i),'kind':'top' if i<len(top) else 'wall','verticesENU':allts[i].tolist()} for i in bad]}
write('ownership-boundary-differences.json',diffs);write('discontinuity-segments.json',seams);write('narrow-boundary-height-queries.json',narrow);write('float32-preflight.json',float_record)
report={'meshSha256':digest(OUT/'local-terrain.npz'),'sourceSitesSha256':digest(SRC/'geography/site-surfaces.json'),'nodingGridGame':1e-8,'restoredOriginalDryWaterBoundary':True,'geometryBudgetGame':2e-8,'ownershipBoundaries':diffs,'materialChanges':material,'maximumActualSeamToBothSourceBoundariesGame':maxdistance,'maximumDiscontinuityGame':maxstep,'smoothQueryCountOutsideBoundaryBand':smooth_count,'smoothMaximumHeightErrorGame':smooth_max,'smoothHeightFailuresAbovePoint01':len(smooth_fail),'boundaryBandHalfWidthGame':2e-8,'boundaryBandQueryCount':len(narrow),'boundaryBandMaximumHeightDifferenceGame':max((p['heightDifferenceGame'] for p in narrow),default=0),'boundaryBandDifferencesAbovePoint01':sum(p['heightDifferenceGame']>.01 for p in narrow),'float32Preflight':float_record,'rawBoundaryMetricPassed':all(d['rawBoundaryHausdorffGame']<=2e-8 for d in diffs+material),'metricOnlyNormalizationGame':1e-10,'metricNormalizationScope':'collapse Boolean zero-width returns in temporary measurement geometry only, not source nor candidate mesh; raw metric failures retained','passedBoundedGeometryAndHeight':maxdistance<=2e-8 and all(d['metricNormalizedBoundaryHausdorffGame']<=2e-8 for d in diffs+material) and not smooth_fail and len(bad)==0,'pending':['Actual GLB local-frame export, float32 topology, foundation/shore seam and world/body/browser acceptance','Bounded noding does not make original physical masks move; runtime keeps original cut discontinuities']}
write('boundary-validation.json',report);print(json.dumps(report,indent=2,ensure_ascii=False,default=lambda v:v.item() if hasattr(v,'item') else str(v)))
