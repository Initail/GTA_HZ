"""Source semantics and candidate ordering only; never alters shared water."""
from pathlib import Path
from collections import Counter
import hashlib,html,json,math
import shapely
from shapely.geometry import shape,Point,LineString,Polygon,box,mapping
from shapely.ops import transform
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[3]
def read(n):return json.loads((ROOT/n).read_text())
def dump(n,v):(ROOT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
m=read('pair-measurements.json');b={z['index']:z for z in read('body-measurements.json')['bodies']};raw=read('raw-osm-evidence.json');partmap=read('all-parts-crosswalk.json');source=json.loads((PROJECT/'data/processed/hangzhou-261011-extended/water.geojson').read_text());src={f['id']:f for f in source['features']};objects={'way/'+str(w['id']):w for w in raw['ways']};objects.update({'relation/'+str(r['id']):r for r in raw['relations']});ways={w['id']:w for w in raw['ways']};pr=m['projection'];o=pr['originWGS84'];east=pr['eastMetresPerDegree'];north=pr['northMetresPerDegree'];scale=pr['horizontalScale'];bounds=box(*pr['extent'])
def proj(x,y,z=None):return ((x-o[0])*east*scale,(y-o[1])*north*scale)
def members(fid):
 obj=objects[fid]
 return [dict(type='w',ref=obj['id'],role='self-closed-way')] if obj['type']=='way' else obj['members']
def nodes(fid):return {n for mm in members(fid) if mm['type']=='w' for n in ways[mm['ref']]['nodeIds']}
catalog=[]
for fid in raw['requestedFeatureIds']:
 obj=objects[fid];pt=src[fid]['properties']['tags'];missing={k:v for k,v in pt.items() if obj['tags'].get(k)!=v}
 catalog.append(dict(id=fid,version=obj['version'],timestamp=obj['timestamp'],rawTags=obj['tags'],processedTags=pt,processedTagMismatches=missing,areaHandlerOmittedKeys={k:v for k,v in obj['tags'].items() if k not in pt},members=members(fid),allWayMembersAvailable=all(mm['ref'] in ways for mm in members(fid) if mm['type']=='w'),nonWayMembers=[mm for mm in members(fid) if mm['type']!='w'],explicitWaterHeightTags={k:v for k,v in obj['tags'].items() if k in ['ele','height','water:level','water_level','level','depth','min_height']}))
linear=[f for f in source['features'] if f['geometry']['type']=='LineString'];lp=[transform(proj,shape(f['geometry'])) for f in linear];lt=STRtree(lp)
hydro=[]
for f in raw['hydraulicNodes']+raw['hydraulicWays']:
 t=f['tags']
 if t.get('lock') in ['no','false','0'] and t.get('waterway') not in ['weir','dam','lock_gate','sluice_gate','waterfall','rapids']:continue
 geo=Point(f['coordinates']) if f['type']=='node' else LineString(f['coordinates']);hydro.append((f,transform(proj,geo)))
rows=[]
for p in m['pairs']:
 a,bb=p['a'],p['b'];ma,mb=members(a),members(bb);am={z['ref'] for z in ma if z['type']=='w'};bm={z['ref'] for z in mb if z['type']=='w'};ip=shape(p['runtimeIntersectionGeometryGame']);near=[]
 for j in lt.query(ip.buffer(60),predicate='intersects'):
  dist=lp[int(j)].distance(ip)/scale
  if dist<=100:near.append(dict(id=linear[int(j)]['id'],tags=linear[int(j)]['properties']['tags'],distanceRealMetres=round(dist,3)))
 near.sort(key=lambda r:r['distanceRealMetres'])
 hg=[dict(id=f['type']+'/'+str(f['id']),tags=f['tags'],distanceRealMetres=round(g.distance(ip)/scale,3)) for f,g in hydro if g.distance(ip)/scale<=100];hg.sort(key=lambda r:r['distanceRealMetres'])
 cl=p['classification'];zero=cl.startswith('independent-simplification')
 if zero:priority='P0-restore-source-boundary';action='使用对应未简化源part，保持所有原始边界/孔洞/节点；不作相互裁切，不改高度。';future='水位连贯性需另按真实水系/闸坝分段复核，不能以本次边界修复证明同一水位。'
 elif p['hasExplicitLockTag']:priority='P1-protect-lock-chamber-hold';action='当前不自动裁切。先锁定闸室及闸门边界；未来若确认，只在泛河水面扣除闸室的水平占有区，保留独立闸室状态和上下游水位。';future='闸室实际水位/闸门状态/上下游基准未知，不保留当前0.7883game差作为实测，也不平均。'
 elif p['declaredLayerDifference']:priority='P1-protect-explicit-layer-hold';action='保留原始layer差异并hold；不能按面积/feature类型决定谁裁谁，也不能按当前DSM高度倒推层级。';future='layer=-1不等于实高或必在地下；本way无tunnel/bridge配套标签，真实跨层还是历史标注问题待核。'
 elif p['pair']==1:priority='P1-lake-lotus-semantic-identity-hold';action='固定源中荷塘完整嵌在西湖面内，保留荷区身份；未来确认同一连通水面后，西湖作规范水面、荷区作为植被/材质语义区，不创建第二个不同DSM水面。当前不自动裁切。';future='政府/管理处资料支持断桥荷区属于西湖荷区并有围网，但不提供该OSM足印的测绘级位置或独立水位/闸门条件。'
 else:priority='P2-source-overlap-identity-hold';action='当前不自动裁切。保留双方源版本/原节点；先核对岸线、共同河道中心线、护岸及闸坝后决定规范边界与片段归属。';future='相同缺省layer、相邻/共节点、river/canal分类或同一流域关系，均不足以证明可直接共用或平均水位。'
 rows.append(dict(pair=p['pair'],a=a,b=bb,aIndex=p['aIndex'],bIndex=p['bIndex'],aVersion=objects[a]['version'],bVersion=objects[bb]['version'],aTimestamp=objects[a]['timestamp'],bTimestamp=objects[bb]['timestamp'],aRawTags=objects[a]['tags'],bRawTags=objects[bb]['tags'],aMemberWayIds=sorted(am),bMemberWayIds=sorted(bm),sharedMemberWayIds=sorted(am&bm),sharedNodeIds=sorted(nodes(a)&nodes(bb)),aIsDirectMemberOfB=[q for q in mb if q['type']=='w' and a=='way/'+str(q['ref'])],bIsDirectMemberOfA=[q for q in ma if q['type']=='w' and bb=='way/'+str(q['ref'])],sourceOverlapAreaGameSquared=p['sourceOverlapAreaGameSquared'],runtimeOverlapAreaGameSquared=p['runtimeOverlapAreaRecomputedGameSquared'],heightDifferenceGame=p['heightDifferenceGame'],heightDifferenceStatus='estimated DSM plane delta, no measured hydraulic meaning',classification=cl,priority=priority,action=action,blockingUnknown=future,restoreUnsimplifiedGeometryEligible=zero,automaticClipApproved=False,automaticAverageHeightApproved=False,nearbySourceCenterlines=near[:12],nearbyRawHydraulicFeatures=hg,proximityMeaning='Measured map distance only, does not prove same water reach or operational state'))
dump('source-catalog.json',dict(sourcePbfSha256=raw['source']['sha256'],sourceObjects=catalog,tagScope='Raw PBF metadata/tags are reported-volunteer mapping, not field measurements. Libosmium area callback omits type=multipolygon; remaining key/value mismatches listed explicitly.'))
dump('pair-review.json',dict(asOfDate='2026-10-16',pairCount=len(rows),counts=Counter(r['priority'] for r in rows),pairs=rows,policy='No automatic clipping approved for17 source-overlap pairs; first restore38 independently-simplified overlaps. No averaging of estimated water planes.',rawDataChanged=False))
# Check all restored source parts globally, since restoring source can reveal overlaps absent from55 current pairs.
def parts(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [p for q in getattr(g,'geoms',[]) for p in parts(q)]
pp={fid:parts(transform(proj,shape(f['geometry'])).intersection(bounds)) for fid,f in src.items() if f['geometry']['type'] in ['Polygon','MultiPolygon']};geoms=[pp[z['id']][z['sourcePartIndex']] for z in partmap['parts']];tree=STRtree(geoms);previous={tuple(sorted([z['aIndex'],z['bIndex']])) for z in m['pairs']};glob=[]
for i,g in enumerate(geoms):
 for j in tree.query(g,predicate='intersects'):
  j=int(j)
  if j<=i:continue
  area=g.intersection(geoms[j]).area
  if area<=1e-6:continue
  ai=partmap['parts'][i];bj=partmap['parts'][j];glob.append(dict(aIndex=ai['runtimeIndex'],bIndex=bj['runtimeIndex'],a=ai['id'],b=bj['id'],sourceOverlapAreaGameSquared=area,heightDifferenceGame=abs(ai['heightGame']-bj['heightGame']),wasInParent55=tuple(sorted([ai['runtimeIndex'],bj['runtimeIndex']])) in previous))
glob.sort(key=lambda z:z['sourceOverlapAreaGameSquared'],reverse=True)
dump('restored-source-global-overlaps.json',dict(kind='read-only-hypothetical-unsimplified-source-overlap-check',thresholdGameSquared=1e-6,allRuntimePartsMatchedOneToOne=partmap['oneToOne'],partsChecked=len(geoms),positiveAreaPairs=len(glob),previous55StillPositive=sum(z['wasInParent55'] for z in glob),newlyVisibleSourceOverlapPairs=[z for z in glob if not z['wasInParent55']],pairs=glob,note='No shared geometry modified; independent heights retained for this measurement, and source overlaps remain blockers.'))
print(json.dumps(dict(priorities=Counter(r['priority'] for r in rows),rawTagMismatchObjects=sum(bool(r['processedTagMismatches']) for r in catalog),rawHeightTaggedObjects=sum(bool(r['explicitWaterHeightTags']) for r in catalog),globalRestoredPairs=len(glob),newlyVisiblePairs=sum(not z['wasInParent55'] for z in glob)),ensure_ascii=False))
# Human full55 table.
text=['# 全55对源身份和处理优先级','', '数值面积均为game²；Δh为当前估计DSM水面差，不是实测水位。17组源重叠全部保留hold，不自动裁切。','', '|对|A|B|源交叠面积|当前交叠面积|Δh game|源共同节点|优先级|','|---:|---|---|---:|---:|---:|---:|---|']
for r in rows:text.append('|%d|%s|%s|%.9f|%.9f|%.6f|%d|%s|'%(r['pair'],r['a'],r['b'],r['sourceOverlapAreaGameSquared'],r['runtimeOverlapAreaGameSquared'],r['heightDifferenceGame'],len(r['sharedNodeIds']),r['priority']))
text += ['', '每对原始版本、时间、标签、关系成员、共享节点、附近水道/闸坝和具体blocker见 `pair-review.json`。']
(ROOT/'all-55-pairs.md').write_text('\n'.join(text)+'\n')
