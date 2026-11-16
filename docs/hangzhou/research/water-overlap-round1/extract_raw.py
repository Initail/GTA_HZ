"""Read fixed PBF twice for finite water identity/member/infrastructure evidence."""
from pathlib import Path
import datetime,hashlib,json,time
import osmium
from shapely.geometry import LineString,box
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[3];PBF=PROJECT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
a=json.loads((PROJECT/'docs/hangzhou/audit/water-overlap-v4.json').read_text());ids={p[k] for p in a['worst'] for k in ['a','b']};targetWays={int(i.split('/')[1]) for i in ids if i.startswith('way/')};targetRels={int(i.split('/')[1]) for i in ids if i.startswith('relation/')}
def info(o,kind):return dict(type=kind,id=o.id,version=o.version,timestamp=str(o.timestamp),tags=dict(o.tags))
class Relations(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.rows=[];self.related=[]
 def relation(self,r):
  members=[dict(type=m.type,ref=m.ref,role=m.role) for m in r.members];v=dict(**info(r,'relation'),members=members)
  if r.id in targetRels:self.rows.append(v)
  elif any((m['type']=='w' and m['ref'] in targetWays) or (m['type']=='r' and m['ref'] in targetRels) for m in members):self.related.append(v)
t0=time.monotonic();rel=Relations();rel.apply_file(str(PBF));memberways={m['ref'] for r in rel.rows for m in r['members'] if m['type']=='w'};wanted=targetWays|memberways
region=box(119.93,30.15,120.3,30.34);infrastructure={'weir','dam','lock_gate','sluice_gate','waterfall','rapids'}
class Features(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.ways=[];self.infrastructure=[];self.nodes=[]
 def node(self,n):
  if not n.location.valid() or not (119.93<=n.location.lon<=120.3 and 30.15<=n.location.lat<=30.34):return
  t=dict(n.tags)
  if t.get('waterway') in infrastructure or t.get('lock') or t.get('man_made') in ['sluice_gate','dam','water_works']:self.nodes.append(dict(**info(n,'node'),coordinates=[n.location.lon,n.location.lat]))
 def way(self,w):
  t=dict(w.tags);hydro=t.get('waterway') in infrastructure or t.get('lock') or t.get('man_made') in ['sluice_gate','dam','water_works']
  if w.id not in wanted and not hydro:return
  cs=[[n.lon,n.lat] for n in w.nodes if n.location.valid()]
  v=dict(**info(w,'way'),nodeIds=[n.ref for n in w.nodes],coordinates=cs)
  if w.id in wanted:self.ways.append(v)
  if hydro and len(cs)>=2 and LineString(cs).intersects(region):self.infrastructure.append(v)
f=Features();f.apply_file(str(PBF),locations=True)
manifest=json.loads((PROJECT/'data/raw/hangzhou/source-manifest.json').read_text());assert hashlib.sha256(PBF.read_bytes()).hexdigest()==manifest['sha256']
out=dict(asOfDate='2026-10-16',source=manifest,requestedFeatureIds=sorted(ids),requestedWays=len(targetWays),requestedRelations=len(targetRels),selection='Raw selected water ways and all way members of selected area relations, plus directly containing relations. Hydraulic feature nodes/ways in extended city bbox. No inferred heights, edits or geometry repair.',relations=rel.rows,relatedRelations=rel.related,ways=f.ways,hydraulicWays=f.infrastructure,hydraulicNodes=f.nodes,unresolvedRequestedRelations=sorted(targetRels-{r['id'] for r in rel.rows}),unresolvedRequestedWays=sorted(wanted-{w['id'] for w in f.ways}),elapsedSeconds=round(time.monotonic()-t0,3),retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
(ROOT/'raw-osm-evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:len(out[k]) for k in ['ways','relations','relatedRelations','hydraulicWays','hydraulicNodes','unresolvedRequestedRelations','unresolvedRequestedWays']}),out['elapsedSeconds'])
