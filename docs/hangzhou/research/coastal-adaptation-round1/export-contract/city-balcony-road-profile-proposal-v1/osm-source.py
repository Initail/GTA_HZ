"""Extract the immutable 20261011 snapshot for road lineage and entry evidence."""
from pathlib import Path
import json,hashlib,osmium
from shapely.geometry import Point,LineString
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
options=read(OUT/'options-summary.json');ids={int(x.split('/')[1].split('#')[0]) for r in options for x in r['affectedRoadIds']};cfg=read(ROOT/'config/cities/hangzhou.json')['geography'];audit=read(OUT/'source-graph-and-clearance.json');service=next(r['sourceRoad'] for r in audit if r['id']=='way/336828925#0');near=LineString(service['points']).buffer(50);ways=[];nodes=[];pbf=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
class Handler(osmium.SimpleHandler):
 def node(self,n):
  if not n.tags:return
  lon,lat=n.location.lon,n.location.lat;x=(lon-cfg['originWGS84'][0])*cfg['eastMetresPerDegree']*cfg['scale'];y=(lat-cfg['originWGS84'][1])*cfg['northMetresPerDegree']*cfg['scale']
  if near.covers(Point(x,y)):nodes.append({'id':n.id,'version':n.version,'timestamp':str(n.timestamp),'wgs84':[lon,lat],'gameEN':[x,y],'tags':dict(n.tags)})
 def way(self,w):
  if w.id in ids:ways.append({'id':w.id,'version':w.version,'timestamp':str(w.timestamp),'nodeIds':[n.ref for n in w.nodes],'tags':dict(w.tags)})
Handler().apply_file(str(pbf))
(OUT/'fixed-osm-road-and-nearby-tags.json').write_text(json.dumps({'sourcePbf':str(pbf.relative_to(ROOT)),'sha256':hashlib.sha256(pbf.read_bytes()).hexdigest(),'ways':ways,'taggedNodesWithin50GameOfService':nodes,'scope':'No current OSM refresh. Absence of source entrance tags is not proof that no entrance exists.'},ensure_ascii=False,indent=2)+'\n');print('ways',len(ways),'nearby tagged nodes',len(nodes))
