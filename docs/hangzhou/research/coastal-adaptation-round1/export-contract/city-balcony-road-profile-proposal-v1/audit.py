"""Source-node graph and real slab clearance. No world or source-road edits."""
from pathlib import Path
import json,hashlib,collections,math,ast,struct,sys
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,mapping
from shapely.strtree import STRtree
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_site_partition import plane,polygon_parts
bindings={}
def bind(p):
 p=Path(p);p=p if p.is_absolute() else ROOT/p;bindings[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
base=OUT.parent;helper=bind(base/'shore-model-v2-review/check.py');exec(compile(ast.Module(body=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='glb'],type_ignores=[]),str(helper),'exec'),globals())
city=read('artifacts/cities/hangzhou/render-input-v7/city.json');roads={r['id']:r for r in city['roads']};by=collections.defaultdict(list)
for r in roads.values():
 for i,n in enumerate(r['nodeIds']):by[n].append((r['id'],i))
ids=['way/557050557#0','way/157967583#0','way/157967584#0','way/605330157#0','way/157967585#0','way/157967586#0','way/336828925#0']
floor,_=glb('artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb');meshes={m['name']:m for m in floor};links=read(base/'city-balcony-walk-envelope-v2/slab-glb-correspondence.json');slabs=[]
for r in links:
 for ref in r['actualFaceLinks']:
  link=ref['actualBottomFaces'][0];t=np.array(meshes[link['mesh']]['triangles'][link['triangleIndex']]);poly=Polygon(t[:,:2]);slabs.append({'id':r['id'],'actualBottomFace':link,'poly':poly,'height':plane(t if poly.exterior.is_ccw else t[::-1])})
tree=STRtree([r['poly'] for r in slabs]);reports=[];geo=[]
for id in ids:
 r=roads[id];line=LineString(r['points']);cum=[0.]
 for a,b in zip(r['points'],r['points'][1:]):cum.append(cum[-1]+math.dist(a,b))
 samples=[]
 for s in sorted(set(cum+list(np.arange(0,line.length,.5))+[line.length])):
  j=min(np.searchsorted(cum,s,side='right')-1,len(cum)-2);j=max(0,j);u=(s-cum[j])/(cum[j+1]-cum[j]);p=line.interpolate(s);h=r['heights'][j]*(1-u)+r['heights'][j+1]*u
  # Include full road width; this is cross-section clearance, not only centerline.
  tangent=np.array(r['points'][j+1])-r['points'][j];tangent=tangent/np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]]);cross=LineString([np.array(p.coords[0])-normal*r['width']/2,np.array(p.coords[0])+normal*r['width']/2]);ceiling=[]
  for k in tree.query(cross,predicate='intersects'):
   row=slabs[int(k)];over=cross.intersection(row['poly']);points=[]
   if over.geom_type=='Point':points=[over]
   elif over.geom_type=='LineString':points=[Point(q) for q in over.coords]
   elif hasattr(over,'geoms'):
    for g in over.geoms:
     if g.geom_type=='Point':points.append(g)
     elif g.geom_type=='LineString':points.extend(Point(q) for q in g.coords)
   if points:ceiling.append({'slab':row['id'],'minimumY':min(float(row['height'](q.x,q.y)) for q in points)})
  if ceiling:
   minimum=min(c['minimumY'] for c in ceiling);samples.append({'station':float(s),'point':[p.x,p.y],'rawEstimatedRoadY':h,'minimumActualSlabBottomY':minimum,'rawVerticalClearance':minimum-h,'conservativeTargetYAt3point6Clearance':minimum-3.6,'slabs':sorted(set(c['slab'] for c in ceiling))})
 reports.append({'id':id,'sourceRoad':r,'lengthGame':line.length,'nodeStations':cum,'sharedNodeConnections':[{'nodeId':n,'station':cum[i],'connections':[{'roadId':a,'nodeIndex':j,'rawEstimatedY':roads[a]['heights'][j]} for a,j in by[n]]} for i,n in enumerate(r['nodeIds'])],'occupiedCrossSections':samples,'minRawClearance':min((a['rawVerticalClearance'] for a in samples),default=None),'minConservativeTargetY':min((a['conservativeTargetYAt3point6Clearance'] for a in samples),default=None)})
 geo.append({'type':'Feature','properties':{'id':id,'tunnel':r['tunnel'],'grade':r['grade'],'nodeIds':r['nodeIds']},'geometry':mapping(line)})
save('source-graph-and-clearance.json',reports);save('source-road-geometry.geojson',{'type':'FeatureCollection','features':geo});save('input-bindings.json',bindings)
print(json.dumps([{k:v for k,v in r.items() if k in ['id','lengthGame','minRawClearance','minConservativeTargetY']} for r in reports],indent=2))
