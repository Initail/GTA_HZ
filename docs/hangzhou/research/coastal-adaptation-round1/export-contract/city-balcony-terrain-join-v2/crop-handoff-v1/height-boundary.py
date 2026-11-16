"""Full actual shore-top boundary ENU and outside-crop F1 audit."""
from pathlib import Path
import json,sys,hashlib,math
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,shape,box
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import Surface
from hangzhou_site_partition import plane,polygon_parts
read=lambda p:json.loads(p.read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
contract=read(OUT/'contract.json');owner=shape(read(OUT/'shore-top-owner-full.geojson')['features'][0]['geometry']);crop=box(*contract['bboxGame']);rows=read(OUT/'shore-top-actual-triangles.json')['triangles'];field=Surface(ROOT/'artifacts/cities/hangzhou/render-input-v7');bound=[];samples=[];fail=[]
def lines(g):
 if g.geom_type=='LineString':yield g
 elif hasattr(g,'geoms'):
  for a in g.geoms:yield from lines(a)
for row in rows:
 t=np.array(row['enu']);p=Polygon(t[:,:2]);height=plane(t)
 # Source-triangle split preserves genuine upper/lower breakpoints as separate segments.
 for line in lines(p.intersection(owner.boundary)):
  if line.length<1e-10:continue
  coords=[[float(x),float(y),float(height(x,y))] for x,y in line.coords]
  bound.append({'sourceTriangle':row['actualTriangleIndex'],'enu':coords})
 for fragment in polygon_parts(p.intersection(owner).difference(crop)):
  qs=[fragment.representative_point(),fragment.centroid]
  for ring in [fragment.exterior]+list(fragment.interiors):
   for a,b in zip(ring.coords,list(ring.coords)[1:]):
    line=LineString([a,b]);qs.extend(line.interpolate(f,normalized=True) for f in np.linspace(0,1,max(2,math.ceil(line.length/.5)+1)))
  for q in qs:
   delta=float(height(q.x,q.y)-field.uncut_ground(q.x,q.y));r={'sourceTriangle':row['actualTriangleIndex'],'enu':[q.x,q.y,float(height(q.x,q.y))],'F1':float(field.uncut_ground(q.x,q.y)),'shoreMinusF1':delta};samples.append(r)
   if abs(delta)>.01:fail.append(r)
bound=[];source_polys=[Polygon(np.array(r['enu'])[:,:2]) for r in rows];tree=STRtree(source_polys);maximum_source_distance=0.
for component,poly in enumerate(polygon_parts(owner)):
 for ring_index,ring in enumerate([poly.exterior]+list(poly.interiors)):
  for a,b in zip(ring.coords,list(ring.coords)[1:]):
   line=LineString([a,b]);mid=line.interpolate(.5,normalized=True);candidates=list(tree.query(mid,predicate='dwithin',distance=1e-8))
   if not candidates:candidates=[tree.nearest(mid)]
   i=min(candidates,key=lambda i:source_polys[int(i)].distance(mid));i=int(i);row=rows[i];height=plane(np.array(row['enu']));distance=source_polys[i].distance(mid);maximum_source_distance=max(maximum_source_distance,distance)
   bound.append({'component':component,'ring':ring_index,'sourceTriangle':row['actualTriangleIndex'],'sourceMidpointDistanceGame':distance,'enu':[[float(x),float(y),float(height(x,y))] for x,y in [a,b]]})
boundary=shapely.union_all([LineString([v[:2] for v in r['enu']]) for r in bound]);missing=owner.boundary.difference(boundary.buffer(1e-8));save('shore-top-boundary-enu.json',{'schema':1,'units':'game ENU','sourceAssetSha256':contract['shoreAssetSha256'],'boundaryRule':'Ordered actual mask ring edges, preserve source triangle vertex and source water clipping breaks; midpoint source ownership with <=1e-8g numeric distance. Interpolate both edge endpoint heights in that actual top triangle. Do not collapse two heights sharing an XY vertical step.','maximumSourceMidpointDistanceGame':maximum_source_distance,'segments':bound,'totalBoundaryLength':owner.boundary.length,'serializedSegmentUnionLength':boundary.length,'missingLengthBeyond1e-8':missing.length,'rawBoundarySymmetricDifferenceLength':owner.boundary.symmetric_difference(boundary).length,'rawBoundaryHausdorffGame':owner.boundary.hausdorff_distance(boundary),'bufferMetricNote':'Near-coincident line buffer numeric artifact retained; exact line equality and Hausdorff are authoritative'})
save('outside-crop-height-check.json',{'scope':'finite <=.5g edge/vertex/representative probes, no new measured elevation','sourceAssetSha256':contract['shoreAssetSha256'],'outsideArea':owner.difference(crop).area,'samples':len(samples),'minimumShoreMinusF1':min(r['shoreMinusF1'] for r in samples),'maximumShoreMinusF1':max(r['shoreMinusF1'] for r in samples),'heightBudgetGame':.01,'failures':len(fail),'failureExamples':fail[:30],'boundarySegments':len(bound),'boundaryMissingLengthBeyond1e-8':missing.length})
save('outside-crop-height-samples.json',samples);print(json.dumps(read(OUT/'outside-crop-height-check.json'),indent=2))

save('outside-crop-adopted-render-budget.json',{'legacyPoint01Screen':read(OUT/'outside-crop-height-check.json'),'adoptedGlobalRenderBudgetGame':.04,'reason':'Parent applies existing global terrain four-probe render approximation budget; physical F1 and collision untouched','passedFiniteSamples':all(abs(r['shoreMinusF1'])<=.04 for r in samples),'boundarySegmentRawSymmetricDifferenceLength':owner.boundary.symmetric_difference(boundary).length})
