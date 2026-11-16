"""Read omitted member geometry for tagged structural relations in fixed PBF."""
from pathlib import Path
import json,hashlib,osmium
from shapely.geometry import LineString,Polygon,box,mapping
ROOT=Path(__file__).resolve().parents[6];OUT=Path(__file__).resolve().parent
relations=json.loads((OUT/'relations-and-nodes.json').read_text())['relations'];wanted={m['ref'] for r in relations for m in r['members'] if m['type']=='w'};c=json.loads((ROOT/'artifacts/cities/hangzhou/water-data-v3/city.json').read_text());meta=c['meta'];water=next(w for w in c['water'] if w['id']=='relation/8227206');river=Polygon(water['rings'][0],water['rings'][1:]);domain=box(*meta['extent']);pbf=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
assert hashlib.sha256(pbf.read_bytes()).hexdigest()=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
class Read(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.rows={}
 def way(self,w):
  if w.id not in wanted:return
  points=[[n.lon,n.lat] for n in w.nodes if n.location.valid()]
  if len(points)!=len(w.nodes) or len(points)<2:raise ValueError('Incomplete member')
  game=[[(x-meta['originWGS84'][0])*meta['eastMetresPerDegree']*.6,(y-meta['originWGS84'][1])*meta['northMetresPerDegree']*.6] for x,y in points];line=LineString(game)
  self.rows[str(w.id)]={'id':'way/'+str(w.id),'version':w.version,'timestamp':str(w.timestamp),'tags':dict(w.tags),'nodeIds':[str(n.ref) for n in w.nodes],'geometry':mapping(LineString(points)),'geometryGame':mapping(line),'intersectsCity':line.intersects(domain),'distanceToQiantangBankGame':line.distance(river.boundary)}
r=Read();r.apply_file(str(pbf),locations=True);result=[]
for relation in relations:
 members=[r.rows[str(m['ref'])] for m in relation['members'] if m['type']=='w' and str(m['ref']) in r.rows]
 result.append({**relation,'memberGeometry':members,'intersectsCity':any(m['intersectsCity'] for m in members),'minDistanceToQiantangBankGame':min((m['distanceToQiantangBankGame'] for m in members),default=None)})
(OUT/'tagged-relation-geometry.json').write_text(json.dumps({'sourcePbfSha256':hashlib.sha256(pbf.read_bytes()).hexdigest(),'relations':result,'expectedMemberWays':len(wanted),'foundMemberWays':len(r.rows)},ensure_ascii=False,indent=2)+'\n');print(json.dumps([{'id':r['id'],'tags':r['tags'],'intersectsCity':r['intersectsCity'],'bankDistanceGame':r['minDistanceToQiantangBankGame']} for r in result],ensure_ascii=False,indent=2))
