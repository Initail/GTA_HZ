"""Read-only fixed PBF road, barrier-node and restriction extraction."""
from pathlib import Path
import hashlib,json,time,datetime
import osmium
from shapely.geometry import LineString,box
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[4]
PBF=PROJECT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
BBOX=(119.9570,30.2625,119.9655,30.2714)
REGION=box(*BBOX)
source=json.loads((PROJECT/'data/raw/hangzhou/source-manifest.json').read_text())
class Extract(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.ways=[];self.nodes=[];self.relations=[]
 def node(self,n):
  if n.location.valid() and BBOX[0]<=n.location.lon<=BBOX[2] and BBOX[1]<=n.location.lat<=BBOX[3]:
   tags=dict(n.tags)
   if any(k in tags for k in ['barrier','access','vehicle','motor_vehicle','entrance','highway']):self.nodes.append(dict(type='node',id=n.id,version=n.version,timestamp=str(n.timestamp),tags=tags,coordinates=[n.location.lon,n.location.lat]))
 def way(self,w):
  tags=dict(w.tags)
  if 'highway' not in tags:return
  coords=[[n.lon,n.lat] for n in w.nodes if n.location.valid()]
  if len(coords)<2 or not LineString(coords).intersects(REGION):return
  self.ways.append(dict(type='way',id=w.id,version=w.version,timestamp=str(w.timestamp),tags=tags,nodeIds=[n.ref for n in w.nodes],coordinates=coords))
 def relation(self,r):
  if r.tags.get('type')=='restriction':self.relations.append(dict(type='relation',id=r.id,version=r.version,timestamp=str(r.timestamp),tags=dict(r.tags),members=[dict(type=m.type,ref=m.ref,role=m.role) for m in r.members]))
t0=time.monotonic();h=Extract();h.apply_file(str(PBF),locations=True)
wayids={w['id'] for w in h.ways};nodeids={n for w in h.ways for n in w['nodeIds']}
rels=[r for r in h.relations if any((m['type']=='w' and m['ref'] in wayids) or (m['type']=='n' and m['ref'] in nodeids) for m in r['members'])]
actual=hashlib.sha256(PBF.read_bytes()).hexdigest();assert actual==source['sha256']
out=dict(source=source,sourceSha256Verified=actual,bboxWGS84=BBOX,selection='Raw highway ways with line intersecting bbox; whole selected ways retained, not clipped. Tagged barrier/access/entrance/highway nodes in bbox; all restriction relations touching selected ways/nodes. No mutations/geometry repair.',retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsedSeconds=round(time.monotonic()-t0,3),ways=h.ways,nodes=h.nodes,restrictions=rels)
(ROOT/'fixed-osm-roads.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(ways=len(h.ways),nodes=len(h.nodes),restrictions=len(rels),elapsedSeconds=out['elapsedSeconds'],sourceSha256=actual)))
