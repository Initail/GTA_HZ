"""Read fixed source only; extract local water/structure context for one ambiguity."""
from pathlib import Path
import json,hashlib,osmium
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
PBF=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
assert hashlib.sha256(PBF.read_bytes()).hexdigest()=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
class Read(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.rows=[]
 def way(self,w):
  tags=dict(w.tags)
  wanted=w.id in [552611348,968854721,25341148]
  if not wanted and not ('waterway' in tags or 'bridge' in tags or 'tunnel' in tags):return
  if not all(n.location.valid() for n in w.nodes):return
  coords=[[n.lon,n.lat] for n in w.nodes]
  if not wanted and not any(119.997<x<120.003 and 30.291<y<30.298 for x,y in coords):return
  self.rows.append({'id':str(w.id),'version':w.version,'timestamp':str(w.timestamp),'tags':tags,'nodeIds':[str(n.ref) for n in w.nodes],'coordinates':coords})
r=Read();r.apply_file(str(PBF),locations=True)
rows={x['id']:x for x in r.rows};channel=rows['552611348'];connections=[]
for k,v in rows.items():
 if k=='552611348' or 'waterway' not in v['tags']:continue
 shared=set(channel['nodeIds'])&set(v['nodeIds'])
 if shared:connections.append({'other':k,'otherTags':v['tags'],'sharedNodes':sorted(shared)})
report={'sourcePbfSha256':hashlib.sha256(PBF.read_bytes()).hexdigest(),'features':r.rows,'lowerLayerChannelConnections':connections,'status':'fixed source topology, not hydraulic survey'}
(OUT/'layer-context.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'features':len(r.rows),'channel':channel,'connections':connections},ensure_ascii=False,indent=2))
