"""Fixed PBF centerline connectivity near all 27 remaining overlaps; no asset writes."""
from pathlib import Path
import json,hashlib,osmium
import shapely
from shapely.geometry import Polygon,LineString,box
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
PBF=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf';CITY=ROOT/'artifacts/cities/hangzhou/water-data-v2/city.json';REPORT=ROOT/'artifacts/cities/hangzhou/water-data-v2/report.json'
c=json.loads(CITY.read_text());pairs=json.loads(REPORT.read_text())['remainingSourceOverlaps'];m=c['meta'];o=m['originWGS84'];e=m['eastMetresPerDegree']*m['horizontalScale'];n=m['northMetresPerDegree']*m['horizontalScale']
def project(lon,lat):return [(lon-o[0])*e,(lat-o[1])*n]
polygons=[Polygon(b['rings'][0],b['rings'][1:]) for b in c['water']]
regions=[polygons[p['aIndex']].intersection(polygons[p['bIndex']]).buffer(30) for p in pairs];region=shapely.union_all(regions)
class Read(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.rows=[];self.shapes=[]
 def way(self,w):
  tags=dict(w.tags)
  if 'waterway' not in tags or not all(n.location.valid() for n in w.nodes) or len(w.nodes)<2:return
  pts=[project(p.lon,p.lat) for p in w.nodes];line=LineString(pts)
  if not line.intersects(region):return
  self.rows.append({'id':'way/'+str(w.id),'version':w.version,'timestamp':str(w.timestamp),'tags':tags,'nodeIds':[str(n.ref) for n in w.nodes],'pointsGame':pts});self.shapes.append(line)
r=Read();r.apply_file(str(PBF),locations=True);tree=STRtree(r.shapes);rows=[]
for number,p in enumerate(pairs):
 a,b=polygons[p['aIndex']],polygons[p['bIndex']];overlap=a.intersection(b);near=list(map(int,tree.query(regions[number],predicate='intersects')))
 bodylines=[[],[]]
 for idx,g in enumerate([a,b]):
  for j in near:
   if r.rows[j]['tags']['waterway'] not in ['river','canal','stream','drain','ditch']:continue
   if r.shapes[j].intersection(g.difference(overlap)).length>.1:bodylines[idx].append(j)
 connections=[]
 for ia in bodylines[0]:
  for ib in bodylines[1]:
   wa,wb=r.rows[ia],r.rows[ib]
   if ia==ib:connections.append({'kind':'same-source-centerline','a':wa['id'],'b':wb['id'],'tagsA':wa['tags'],'tagsB':wb['tags']});continue
   common=set(wa['nodeIds'])&set(wb['nodeIds']);local=[]
   for node in common:
    q=wa['pointsGame'][wa['nodeIds'].index(node)]
    if regions[number].covers(shapely.Point(q)):local.append({'node':node,'pointGame':q})
   if local:connections.append({'kind':'local-shared-source-node','a':wa['id'],'b':wb['id'],'tagsA':wa['tags'],'tagsB':wb['tags'],'shared':local})
 controls=[r.rows[j] for j in near if r.rows[j]['tags']['waterway'] in ['weir','dam','lock_gate'] or r.rows[j]['tags'].get('lock')=='yes']
 rows.append({'pair':number+1,'a':p['a'],'b':p['b'],'candidateConnections':connections,'mappedControlsWithin30Game':[{k:v for k,v in q.items() if k!='pointsGame'} for q in controls],'bodyCenterlineCandidates':[[r.rows[j]['id'] for j in group] for group in bodylines], 'boundary':'Source graph supports mapped connectivity only; no-control-in-subset does not prove physical absence or equal water level.'})
result={'fixedSourceSha256':hashlib.sha256(PBF.read_bytes()).hexdigest(),'citySha256':hashlib.sha256(CITY.read_bytes()).hexdigest(),'nearbyWaterwayCount':len(r.rows),'pairResults':rows,'sourceWaterways':r.rows}
(OUT/'all-pair-waterway-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for x in rows:print(x['pair'],len(x['candidateConnections']),len(x['mappedControlsWithin30Game']),[(q['kind'],q['a'],q['b']) for q in x['candidateConnections']])
