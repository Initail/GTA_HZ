"""Read-only coastal input/source audit. Outputs research JSON only in this directory."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,math,osmium
from shapely.geometry import Polygon,LineString,Point
from shapely.strtree import STRtree
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
cp='artifacts/cities/hangzhou/render-input-v5/city.json';lp='artifacts/cities/hangzhou/render-input-v5/lamps.json';rp='artifacts/cities/hangzhou/render-input-v5/geography/road-levels.json';pbf='data/raw/hangzhou/zhejiang-261011.osm.pbf'
assert sha(cp)=='b8d04810aa8f26f9020794a53def59e35e2aeaba0061d30284d59833d1f2ff47'
assert sha(pbf)=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
c=read(cp);lamps=read(lp);waters=[Polygon(w['rings'][0],w['rings'][1:]) for w in c['water']];wt=STRtree(waters);water=unary_union(waters);roads=c['roads'];lines=[LineString(r['points']) for r in roads];rt=STRtree(lines)
node_roads=defaultdict(list)
for i,r in enumerate(roads):
 for n in r['nodeIds']:node_roads[n].append(i)
rows=[];qrows=[]
for i,(r,line) in enumerate(zip(roads,lines)):
 matches=[]
 for j in map(int,wt.query(line,predicate='intersects')):
  length=line.intersection(waters[j]).length
  if length>0.1:matches.append({'waterId':c['water'][j]['id'],'waterSourcePartIndex':c['water'][j].get('sourcePartIndex'),'lengthGame':length,'heightGame':c['water'][j]['height']})
 if not matches:continue
 tunnel=r.get('tunnel','no') not in ['no','false','0',''];bridge=r.get('bridge','no') not in ['no','false','0','']
 category='source-tunnel-not-surface-bridge' if tunnel else 'source-tagged-bridge' if bridge else 'unmarked-water-intersection-review'
 row={k:r.get(k) for k in ['id','sourceId','name','kind','bridge','tunnel','grade','width']};row.update({'category':category,'crossedWaters':matches,'sourceNodeCount':len(r['nodeIds']),'heightRangeGame':[min(r['heights']),max(r['heights'])]})
 rows.append(row)
 if any(m['waterId']=='relation/8227206' for m in matches):
  row=dict(row);row['nodeIds']=r['nodeIds'];row['endpointAdjacencies']={n:[{'id':roads[j]['id'],'sourceId':roads[j].get('sourceId'),'grade':roads[j]['grade'],'bridge':roads[j]['bridge'],'tunnel':roads[j]['tunnel'],'atEndpoint':n in [roads[j]['nodeIds'][0],roads[j]['nodeIds'][-1]]} for j in node_roads[n] if j!=i] for n in [r['nodeIds'][0],r['nodeIds'][-1]]};qrows.append(row)
qindices=[i for i,r in enumerate(roads) if r['id'] in {r['id'] for r in qrows}];crossings=[]
for a,i in enumerate(qindices):
 for j in qindices[a+1:]:
  if not lines[i].intersects(lines[j]):continue
  shared=sorted(set(roads[i]['nodeIds'])&set(roads[j]['nodeIds']))
  if roads[i]['sourceId']==roads[j]['sourceId']:continue
  crossings.append({'a':roads[i]['id'],'b':roads[j]['id'],'gradeA':roads[i]['grade'],'gradeB':roads[j]['grade'],'sharedSourceNodes':shared,'classification':'source-node-connection-needs-mode-level-check' if shared else 'geometric-intersection-not-junction','intersectionType':lines[i].intersection(lines[j]).geom_type})
selected={int(r['sourceId'].split('/')[1]) for r in qrows};selected.update([154142001,826790145,5041735,28596734,28596757,331859982])
class Raw(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.ways=[];self.relations=[]
 def way(self,w):
  if w.id in selected:self.ways.append({'id':'way/'+str(w.id),'version':w.version,'timestamp':str(w.timestamp),'tags':dict(w.tags),'nodeIds':[str(n.ref) for n in w.nodes]})
 def relation(self,r):
  if r.id==8227206:self.relations.append({'id':'relation/'+str(r.id),'version':r.version,'timestamp':str(r.timestamp),'tags':dict(r.tags),'members':[{'type':m.type,'ref':m.ref,'role':m.role} for m in r.members]})
raw=Raw();raw.apply_file(str(ROOT/pbf));rawmap={w['id']:w for w in raw.ways}
for r in qrows:
 r['sourceAudit']={'found':r['sourceId'] in rawmap,'allNodeIdsInRawWay':set(r['nodeIds'])<=set(rawmap[r['sourceId']]['nodeIds']),'rawTags':rawmap[r['sourceId']]['tags']}
cfg=read('config/cities/hangzhou.json');regions=cfg['localLighting'];lighting=[]
for reg in regions:
 inside=[i for i,p in enumerate(lamps) if math.hypot(p[0]-reg['x'],p[1]-reg['z'])<=reg['outer']]
 lighting.append({'id':reg['id'],'lampsWithinOuterRadius':len(inside),'withinInnerRadius':sum(math.hypot(lamps[i][0]-reg['x'],lamps[i][1]-reg['z'])<=reg['inner'] for i in inside)})
greens=[]
for g in c['green']:
 if not g.get('name'):continue
 poly=Polygon(g['rings'][0],g['rings'][1:]);distance=poly.distance(water)
 if distance<=40 and poly.area>=1800:greens.append({'id':g['id'],'name':g['name'],'areaGameSquared':poly.area,'waterDistanceGame':distance,'status':'semantic site candidate only, no fixture positions frozen'})
extent=c['meta']['extent'];width=extent[2]-extent[0];height=extent[3]-extent[1];sizes=[]
for w in [4096,8192]:
 h=math.ceil(height/width*w);sizes.append({'width':w,'height':h,'texelGame':[width/w,height/h],'rgba8MipChainMiB':w*h*4*4/3/1024/1024,'redQuantizationGame':120/255})
write('source-bridge-context.json',{'fixedPbfSha256':sha(pbf),'ways':raw.ways,'relations':raw.relations,'status':'source topology only; no live road-state verification'})
def lineparts(g):
 if g.geom_type=='LineString':return [g] if g.length>.1 else []
 return sum((lineparts(x) for x in getattr(g,'geoms',[])),[])
bridge_ids={r['id'] for r in rows if r['category']=='source-tagged-bridge'}
fragments=sum(len(lineparts(lines[i].intersection(water))) for i,r in enumerate(roads) if r['id'] in bridge_ids)
write('crosswater-audit.json',{'citySha256':sha(cp),'counts':dict(Counter(r['category'] for r in rows)),'taggedBridgeWetFragments':fragments,'crossWaterRoads':rows,'qiantangRoads':qrows,'qiantangGeometricIntersections':crossings,'shoreExtentGame':extent,'shoreTextureResolutionOptions':sizes,'sourceNodeNavigationRule':'Use shared source nodes plus actor mode and level compatibility; never create junction at arbitrary line intersection.'})
write('lighting-shore-audit.json',{'citySha256':sha(cp),'lampsSha256':sha(lp),'streetLamps':len(lamps),'regions':lighting,'namedWaterfrontGreenAreas':sorted(greens,key=lambda r:-r['areaGameSquared']),'parkLampPositionsFrozen':False,'sourceCoastLineCount':len(c['coast']),'existingLandmarkBridgeOverlapPolicy':'source IDs identify named bridge landmark ownership; generic parapets/supports must not duplicate them'})
files=[cp,lp,rp,pbf,'config/cities/hangzhou.json','src/city-coastal-infrastructure.ts','src/city-bay-water.ts','src/city-baypark-look.ts','src/city-public-lighting.ts','src/city-local-lighting.ts','src/city-roadside-planting.ts','scripts/prepare_coastal_infrastructure.py','scripts/build_coastal_infrastructure.py']
write('input-bindings.json',{'files':[{'path':p,'sha256':sha(p)} for p in files]})
print(json.dumps({'crossWaterRoads':len(rows),'categories':dict(Counter(r['category'] for r in rows)),'qiantangRoads':len(qrows),'qiantangPairs':len(crossings),'rawWays':len(raw.ways),'regions':lighting,'namedWaterfrontGreens':len(greens),'textureOptions':sizes},ensure_ascii=False,indent=2))
