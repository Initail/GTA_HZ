"""Read-only finite fixed-PBF investigation; no source or runtime mutation."""
from pathlib import Path
import hashlib,json,time,datetime
import osmium
from shapely.geometry import LineString,box
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];PBF=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
AREA=box(119.978,30.198,119.991,30.209);wanted={697096305,697096306,1418959639,358503184};nodes={6547053710,6547053711}
def info(o,t):return {'type':t,'id':o.id,'version':o.version,'timestamp':str(o.timestamp),'changeset':o.changeset,'tags':dict(o.tags)}
class Context(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.nodes=[];self.ways=[];self.relations=[]
 def node(self,n):
  if not n.location.valid():return
  x,y=n.location.lon,n.location.lat
  if n.id in nodes or (len(n.tags) and AREA.covers(__import__('shapely').Point(x,y))):self.nodes.append({**info(n,'node'),'coordinates':[x,y]})
 def way(self,w):
  ts=dict(w.tags)
  if w.id not in wanted and not ts:return
  if not all(n.location.valid() for n in w.nodes):return
  cs=[[n.lon,n.lat] for n in w.nodes]
  if len(cs)<2:return
  if w.id not in wanted and not LineString(cs).intersects(AREA):return
  self.ways.append({**info(w,'way'),'nodeIds':[n.ref for n in w.nodes],'coordinates':cs})
 def relation(self,r):
  if any(m.type=='w' and m.ref in wanted for m in r.members):self.relations.append({**info(r,'relation'),'members':[{'type':m.type,'ref':m.ref,'role':m.role} for m in r.members]})
t=time.monotonic();handler=Context();handler.apply_file(str(PBF),locations=True)
source=json.loads((ROOT/'data/raw/hangzhou/source-manifest.json').read_text());sha=hashlib.sha256(PBF.read_bytes()).hexdigest();assert sha==source['sha256']
result={'kind':'fixed-PBF-local-portal-source-evidence','researchDate':'2026-11-11','source':source,'bboxWGS84':list(AREA.bounds),'ways':handler.ways,'nodes':handler.nodes,'directContainingRelations':handler.relations,'elapsedSeconds':time.monotonic()-t,'extractorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'fixed-osm-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('ways',len(handler.ways),'nodes',len(handler.nodes),'direct relations',len(handler.relations))
for w in handler.ways:
 if w['id'] in wanted or w['tags'].get('name') or w['tags'].get('tunnel') or w['tags'].get('bridge'):print(w['id'],w['tags'])
