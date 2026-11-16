"""Offline evidence/geometry audit. No Blender/runtime/OSM modifications."""
from pathlib import Path
import collections,datetime,hashlib,json,math,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((ROOT/n).read_text())
c=read('crosswalk.json');r=read('fixed-osm-roads.json');e=read('evidence.json');s=read('sources.json');t=read('task.json');ways={w['id']:w for w in r['ways']};checks=[]
def check(name,value,detail=None):checks.append(dict(name=name,passed=bool(value),detail=detail))
check('PBF unchanged and fixed hash matches',sha(PROJECT/'data/raw/hangzhou/zhejiang-261011.osm.pbf')==c['sourcePbfSha256']==r['sourceSha256Verified'])
check('Processed roads unchanged since crosswalk freeze',sha(PROJECT/'data/processed/hangzhou/roads.geojson')==c['processedRoadsSha256'])
check('Raw road archive bound to crosswalk',sha(ROOT/'fixed-osm-roads.json')==c['rawEvidenceSha256'])
exact=True;bounds=True
for seg in c['segments']:
 w=ways[seg['osmWay']];ns=w['nodeIds'];a=ns.index(seg['sourceNodeIds'][0]);b=ns.index(seg['sourceNodeIds'][-1])+1
 exact &= ns[a:b]==seg['sourceNodeIds'] and w['coordinates'][a:b]==seg['coordinatesWGS84'] and w['tags']==seg['sourceTags'] and w['version']==seg['sourceVersion']
 bounds &= len(seg['coordinatesWGS84'])>=2 and all(119.93<p[0]<120.30 and 30.16<p[1]<30.34 for p in seg['coordinatesWGS84'])
check('Every source slice and raw tags retained exactly',exact)
check('All source coordinates are finite regional WGS84',bounds)
check('2023 override eligible exact seven source slices',len([z for z in c['segments'] if z['recommendation']=='eligible-scoped-derived-access'])==7 and all(z['claimSourceIds']==['gov-2023-opening'] for z in c['segments'] if z['role'].startswith('official-2023')))
check('Long southern ways never blanket eligible',all(not z['wholeWay'] for z in c['segments'] if z['osmWay'] in [1350297693,779247992]) and {z['osmWay'] for z in c['excludedSouthSlices']}=={1350297693,779247992})
check('2026 construction way is held with geometry blocker',next(z for z in c['segments'] if z['osmWay']==1228913715)['recommendation'].startswith('hold-') and ways[1228913715]['tags']['highway']=='construction')
internal={1537965096,1537965097,1537965098,1537965099,1537965100,1537965101,1537965102,1537965103,1537965105}
check('Campus services and unrelated access=no not opened',internal.isdisjoint({z['osmWay'] for z in c['segments']}) and internal.issubset({z['osmWay'] for z in c['excludedWays']}) and {779247993,477207222,1464066099,1039904654}.issubset({z['osmWay'] for z in c['excludedWays']}))
processed=json.loads((PROJECT/'data/processed/hangzhou/roads.geojson').read_text());pw={int(f['properties']['osm_id']):f for f in processed['features']}
check('Relevant raw and processed road features agree exactly',all(pw[z['osmWay']]['properties']['tags']==ways[z['osmWay']]['tags'] and pw[z['osmWay']]['geometry']['coordinates']==ways[z['osmWay']]['coordinates'] and list(map(int,pw[z['osmWay']]['properties']['nodeIds']))==ways[z['osmWay']]['nodeIds'] for z in c['segments']))
sourceids={z['id'] for z in s['sources']}
check('Every fact source ID resolves',all(set(z.get('sourceIds',[]))<=sourceids for z in e['facts']))
check('Archived reference files match recorded hashes',all(sha(ROOT/z['filename'])==z['sha256'] for z in s['archiveFiles']))
# OSM history is queried independently; require frozen version exists with same nodes/tags.
history_ok=True
for z in c['segments']:
 w=ways[z['osmWay']];h=read('osm-way-'+str(w['id'])+'-history.json');v=[a for a in h['versions'] if a['version']==w['version']]
 history_ok &= len(v)==1 and v[0]['nodeIds']==w['nodeIds'] and v[0]['tags']==w['tags']
check('Public history contains exact frozen version of each candidate way',history_ok)
# Connectivity proof is only graph-theoretic and uses exact same-node adjacency.
g=collections.defaultdict(set)
def add(ns,oneway):
 for a,b in zip(ns,ns[1:]):
  if oneway!='-1':g[a].add(b)
  if oneway not in ['yes','1','true']:g[b].add(a)
for z in c['segments']:
 if z['role'].startswith('official-2023'):add(z['sourceNodeIds'],z['sourceTags'].get('oneway'))
for i in [1418668534,1418668548,1464066109,456702517]:add(ways[i]['nodeIds'],ways[i]['tags'].get('oneway'))
def reachable(a,b):
 seen={a};q=collections.deque([a])
 while q:
  n=q.popleft()
  if n==b:return True
  for nn in g[n]-seen:seen.add(nn);q.append(nn)
 return False
route_checks={'FengxinToNorthPublicRoadNode':reachable(13037359845,14008463188),'NorthPublicRoadNodeToFengxin':reachable(14008463188,13037359845)}
check('Source-node public-road loop reaches and returns from north frontage',all(route_checks.values()),dict(**route_checks,note='Topology only; no physical driving/turn legality/parking or campus-entry validation. No edge invented from geometric crossing.'))
check('No false final traffic or browser verification status',e['sharedDataModified'] is False and e['visualGameValidation'] is False and e['fullCurrentTrafficCertification'] is False and t['candidateModelCreated'] is False)
# Search coverage must be explicit: result pages can contain false positives and partial ranked pages.
searches=[]
for name in ['http-search-fetches.json','exact-search-fetches.json','more-search-fetches.json','restriction-search-fetches.json']:
 for f in read(name):
  if f.get('status')==200 and f.get('filename','').endswith('.json'):
   try:o=json.loads((ROOT/f['filename']).read_text())
   except Exception:continue
   beans=o.get('data',{}).get('appSearchResultBeanList',[]) if isinstance(o.get('data'),dict) else []
   total=sum(b.get('mapSearchResult',{}).get('totalHits',0) for b in beans);items=[i['data'] for b in beans for i in b.get('mapSearchResult',{}).get('items',[])]
   literal=[];future=[]
   for d in items:
    st=json.dumps(d,ensure_ascii=False)
    if any(q in st for q in ['云联路','菜鸟北路']):literal.append(dict(title=d.get('title_str'),url=d.get('url')))
    if d.get('createdate'):
     date=datetime.datetime.fromtimestamp(int(d['createdate'])/1000,datetime.timezone.utc).date()
     if date>datetime.date(2026,10,16):future.append(dict(title=d.get('title_str'),url=d.get('url'),date=str(date)))
   searches.append(dict(id=f['id'],totalHits=total,returned=len(items),literalRoadNameMatches=literal,postCutoffExcluded=future,completeCurrentRestrictionInventory=False))
(ROOT/'search-audit.json').write_text(json.dumps(dict(asOfDate='2026-10-16',queries=searches,interpretation='Government search forces tokenization; results can match only parts/addresses. No claim that all later restrictions were retrieved. A zero-result or partial ranked page is not a no-restriction certificate.'),ensure_ascii=False,indent=2)+'\n')
out=dict(checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,passed=sum(z['passed'] for z in checks),total=len(checks),allPassed=all(z['passed'] for z in checks),claim='CPU source/provenance/finite-scope checks only',finalRoadAccessAcceptance='pending',browserDriving='not-run',sharedWrites=False,hashes={n:sha(ROOT/n) for n in ['crosswalk.json','evidence.json','sources.json','task.json','fixed-osm-roads.json','road-scope.geojson','road-scope.svg']})
(ROOT/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['allPassed'] else 1)
