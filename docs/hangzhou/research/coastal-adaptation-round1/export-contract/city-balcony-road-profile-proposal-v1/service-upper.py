"""Compare service source line against whole-width upper support and actual obstacles."""
from pathlib import Path
import json,hashlib,ast,struct,sys,math,importlib.util
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,mapping
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_site_partition import plane,polygon_parts
bindings={}
def bind(p):
 p=Path(p);p=p if p.is_absolute() else ROOT/p;bindings[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
helper=bind(BASE/'shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(helper),'exec'),globals())
r=next(x['sourceRoad'] for x in read(OUT/'source-graph-and-clearance.json') if x['id']=='way/336828925#0');line=LineString(r['points']);corridor=line.buffer(r['width']/2,cap_style=2);site=read(BASE/'city-balcony-terrain-join-v2/site-surfaces-repair.json');floors=[np.array(t) for g in site['walkFloors'] for t in g['triangles']];polys=[Polygon(t[:,:2]) for t in floors];tree=STRtree(polys);upper=shapely.union_all(polys);inside=line.intersection(upper);crossings=[]
spec=read(BASE/'city-balcony-floor-v2/candidate-spec.json');placement=read(BASE/'city-balcony-floor-v2/placement.json');modspec=importlib.util.spec_from_file_location('balcony_floor_v2',bind('scripts/landmarks/city_balcony_floor_v2.py'));module=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(module);lm={'x':placement['anchorGame'][0],'z':placement['anchorGame'][1],'y':placement['baseYGame']};ring=[module._to_game(u,v,lm,spec,.6) for u,v in spec['upperOuterUVMetres']];open_edges={9,13,14,15}
for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
 edge=LineString([a,b]);over=edge.intersection(corridor)
 if not over.is_empty:crossings.append({'sourceOuterEdge':i,'modelHasUpperRail':i not in open_edges,'sourceOpenMouth':i in open_edges,'intersectLengthGame':over.length,'geometry':mapping(over),'endpointStations':[line.project(Point(p)) for p in edge.coords]})
cum=[0.]
for a,b in zip(r['points'],r['points'][1:]):cum.append(cum[-1]+math.dist(a,b))
samples=[];full_width=[]
for s in sorted(set(cum+list(np.arange(0,line.length,.25))+[line.length])):
 j=min(len(cum)-2,max(0,int(np.searchsorted(cum,s,side='right')-1)));u=(s-cum[j])/(cum[j+1]-cum[j]);point=line.interpolate(s);tangent=np.array(r['points'][j+1])-r['points'][j];tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]]);cross=LineString([np.array(point.coords[0])-normal*r['width']/2,np.array(point.coords[0])+normal*r['width']/2]);inside_width=cross.intersection(upper).length;raw=r['heights'][j]*(1-u)+r['heights'][j+1]*u;support=[]
 for k in tree.query(cross,predicate='intersects'):
  over=cross.intersection(polys[int(k)]);h=plane(floors[int(k)])
  if hasattr(over,'coords'):
   support.extend(float(h(x,y)) for x,y in over.coords)
 if support:samples.append({'station':float(s),'rawEstimatedY':raw,'upperMinY':min(support),'upperMaxY':max(support),'rawMinusUpperRange':[raw-max(support),raw-min(support)],'widthGame':r['width'],'supportedWidthGame':inside_width})
 if inside_width>=r['width']-1e-6:full_width.append(float(s))
# Only inspect actual geometry above the intended upper surface, not lower piers as false obstacles.
floor,_=glb('artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb');low=placement['upperYGame']+.02;high=placement['upperYGame']+3.;hits=[]
def clip(poly,y,greater):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=(a[2]>=y) if greater else (a[2]<=y);ib=(b[2]>=y) if greater else (b[2]<=y)
  if ia:out.append(a)
  if ia!=ib:out.append(a+(b-a)*(y-a[2])/(b[2]-a[2]))
 return out
for part in floor:
 for i,t in enumerate(part['triangles']):
  clipped=clip(clip(list(t),low,True),high,False)
  if len(clipped)<2:continue
  coords=[p[:2] for p in clipped];poly=Polygon(coords) if len(coords)>=3 else LineString(coords)
  if not poly.is_valid or poly.area<1e-12:poly=shapely.convex_hull(LineString(coords))
  if not poly.intersects(corridor):continue
  over=poly.intersection(corridor)
  if over.is_empty:continue
  p=over.representative_point();hits.append({'mesh':part['name'],'material':part['material'],'actualTriangle':i,'projectedIntersectionArea':over.area,'projectedIntersectionLength':over.length,'station':line.project(p),'actualHeightRange':[float(t[:,2].min()),float(t[:,2].max())],'geometry':mapping(over)})
save('service-upper-obstacle-hits.json',hits);save('service-upper-width-samples.json',samples)
report={'id':r['id'],'rawSourceRole':'highway=service only; no entrance/access/layer/tunnel tag','sourceNodeCount':len(r['nodeIds']),'sourceLengthGame':line.length,'actualUpperMainYGame':placement['upperYGame'],'partInsideUpperCenterlineLengthGame':inside.length,'corridorInsideUpperAreaGame2':corridor.intersection(upper).area,'corridorAreaGame2':corridor.area,'firstPartialUpperCrossSectionStation':min(x['station'] for x in samples),'firstFullWidthUpperCrossSectionStation':min(full_width),'sourceBoundaryCrossings':crossings,'rawMinusUpperHeightRange':[min(x['rawMinusUpperRange'][0] for x in samples),max(x['rawMinusUpperRange'][1] for x in samples)],'actualObstacleProbeVerticalBand':[low,high],'actualObstacleHitCount':len(hits),'actualObstacleMaterials':dict(__import__('collections').Counter(h['material'] for h in hits)),'actualObstacleStationRange':[min((x['station'] for x in hits),default=None),max((x['station'] for x in hits),default=None)],'upperOption':'An estimated road/supported ramp from unchanged source shared junction to upper height is geometrically plausible in longitudinal slope, but existing boundary railing and actual above-deck obstacles must be resolved explicitly. Do not fill lower floor or label the source service a verified upper entrance.','inputSha256':bindings}
save('service-upper-comparison.json',report);print(json.dumps(report,indent=2))
