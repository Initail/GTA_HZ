"""Build evidence crosswalk only. Never edits OSM, runtime, roads or derived city files."""
from pathlib import Path
import hashlib,html,importlib.util,json,math,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[4]
def read(p):return json.loads(p.read_text())
def write(name,data):(ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ms=importlib.util.spec_from_file_location('research_enu',ROOT.parent/'measure_osm.py');m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m)
x=read(ROOT/'fixed-osm-roads.json');ways={w['id']:w for w in x['ways']};source=read(PROJECT/'data/raw/hangzhou/source-manifest.json')
segments=[]
def segment(key,way,start=None,end=None,role='official-2023-road-scope',adopt='eligible-scoped-derived-access'):
 w=ways[way];ns=w['nodeIds'];a=ns.index(start) if start is not None else 0;b=ns.index(end)+1 if end is not None else len(ns)
 assert a<b
 coords=w['coordinates'][a:b];p=[m.enu(c,(119.960,30.266)) for c in coords]
 s=dict(id=key,osmWay=way,sourceVersion=w['version'],sourceTimestamp=w['timestamp'],sourceNodeIds=ns[a:b],coordinatesWGS84=coords,sourceTags=w['tags'],sourceSliceInclusive=[ns[a],ns[b-1]],wholeWay=(a==0 and b==len(ns)),lengthMetresMeasured=round(sum(math.dist(u,v) for u,v in zip(p,p[1:])),3),measurement='WGS84 ECEF to local ENU at [119.960,30.266], sum of source centerline segments; OSM mapping not survey; no game scale applied',role=role,recommendation=adopt,claimSourceIds=['gov-2023-opening'] if role.startswith('official-2023') else ['official-weibo-index-2026','zjol-2026-opening'],preserveTags=['oneway','bridge','layer','tunnel'],runtimeModified=False)
 segments.append(s);return s
segment('yunlian-northbound-fengxin-junction-inclusive',1350297693,13037359845,13449607094)
segment('yunlian-northbound-bridge',1466397037)
segment('yunlian-northbound-north',1466397036)
segment('yunlian-southbound-north',1466397038)
segment('yunlian-southbound-bridge',1466397039)
segment('yunlian-southbound-fengxin-junction-inclusive',779247992,13449607096,7276172380)
segment('cainiao-north-yunlian-to-shuyun-junction-inclusive',779247995)
segment('yunlian-2026-north-extension-mapped-centerline-only',1228913715,role='reported-2026-opening-unresolved-current-geometry',adopt='hold-physical-reconstruction-and-current-primary-notice')
exclude=[dict(osmWay=i,reason=reason) for i,reason in [(779247993,'数云路南行：2023公告以其为端点，未开放其全线。'),(477207222,'文二西路东行：2023公告仅以其为端点，不能凭相交推出整条东行开放。'),(1464066099,'文二西路以西/延伸施工 way，无该公告开放证据。'),(1039904654,'附近跨线桥 access=no，不属于公告命名范围。')]]
for i in [1537965096,1537965097,1537965098,1537965099,1537965100,1537965101,1537965102,1537965103,1537965105]:exclude.append(dict(osmWay=i,reason='总部园区服务环路/支路/服务桥，2023公共道路公告不证明其向社会车辆开放。固定OSM无access标签也不证明开放。'))
excluded_slices=[]
for i,a,b in [(1350297693,9575340391,13037359845),(779247992,7276172380,8973495747)]:
 w=ways[i];ns=w['nodeIds'];l=ns.index(a);r=ns.index(b)+1
 excluded_slices.append(dict(osmWay=i,sourceNodeIds=ns[l:r],coordinatesWGS84=w['coordinates'][l:r],reason='凤新路南侧，超出2023公告；共享边界节点保留，不沿经纬度或路名整way开放。'))
metrics=[]
# Inner carriageway junctions, explicitly a different endpoint convention from the inclusive scope above.
def length_nodes(wid,a,b):
 w=ways[wid];ns=w['nodeIds'];cs=w['coordinates'][ns.index(a):ns.index(b)+1];p=[m.enu(c,(119.960,30.266)) for c in cs];return sum(math.dist(u,v) for u,v in zip(p,p[1:]))
nb_inner=length_nodes(1350297693,13037359823,13449607094)+segments[1]['lengthMetresMeasured']+length_nodes(1466397036,13449607093,13037359843)
sb_inner=segments[3]['lengthMetresMeasured']+segments[4]['lengthMetresMeasured']+length_nodes(779247992,13449607096,13037359824)
ca_inner=length_nodes(779247995,13037359844,7276175685)
for key,reported,measured,note in [('yunlian-2023-northbound-inner-junctions',504,nb_inner,'凤新路北侧 carriageway node13037359823→文二西路南侧13037359843；公告未给测量起讫断面。'),('yunlian-2023-southbound-inner-junctions',504,sb_inner,'文二西路公共路口7276172378→凤新路北侧13037359824。'),('cainiao-north-inner-road-junction',473,ca_inner,'云联路东侧 node13037359844→数云路西侧7276175685；含跨交叉口至东侧时更长。'),('yunlian-2026-mapped-straight-centerline',350,segments[-1]['lengthMetresMeasured'],'OSM仅两个节点；350m来自官方账号搜索索引，2024设计进展报道为352m。')]:
 metrics.append(dict(id=key,reportedMetres=reported,measuredMetres=round(measured,3),differenceMetres=round(measured-reported,3),differencePercent=round((measured/reported-1)*100,3),note=note,doNotRescaleSourceToMatchReport=True))
# Record only shared source nodes. Different layer crossings are not invented turns.
bindings=[]
for s in segments:
 for node in [s['sourceNodeIds'][0],s['sourceNodeIds'][-1]]:
  others=[dict(osmWay=w['id'],name=w['tags'].get('name'),highway=w['tags'].get('highway'),access=w['tags'].get('access'),layer=w['tags'].get('layer','0')) for w in x['ways'] if w['id']!=s['osmWay'] and node in w['nodeIds']]
  bindings.append(dict(segment=s['id'],nodeId=node,sharedWith=others))
obj=dict(schemaVersion=1,asOfDate='2026-10-16',scope='Evidence recommendations only; not permission for actual vehicles and not an OSM edit',sourcePbfSha256=source['sha256'],sourceCrs='EPSG:4326',fixedSnapshot='2026-10-11T20:21:06Z',rawEvidenceSha256=sha(ROOT/'fixed-osm-roads.json'),processedRoadsSha256=sha(PROJECT/'data/processed/hangzhou/roads.geojson'),segments=segments,excludedWays=exclude,excludedSouthSlices=excluded_slices,junctionBindings=bindings,lengthDiscrepancies=metrics,pending=['2026北延段正式完整通告/稳定post permalink及分车道现状几何','2023南段和菜鸟北路公告长度与固定OSM长度差异未解释','2026-10-16现场临时管制及车种/转向限制无完整现状清单','园区内部服务路/服务桥/入口的公众通行条件未知','菜鸟北路西端只有北行云联路共享节点，不能按几何邻近补南行转向连接'],sourceDataModified=False)
write('crosswalk.json',obj)
features=[]
for s in segments:
 features.append(dict(type='Feature',id=s['id'],properties={k:v for k,v in s.items() if k!='coordinatesWGS84'},geometry=dict(type='LineString',coordinates=s['coordinatesWGS84'])))
for i,s in enumerate(excluded_slices):features.append(dict(type='Feature',id='out-of-scope-south-'+str(i),properties={k:v for k,v in s.items() if k!='coordinatesWGS84'},geometry=dict(type='LineString',coordinates=s['coordinatesWGS84'])))
write('road-scope.geojson',dict(type='FeatureCollection',source=source,features=features))
# Diagram is an authored OSM research diagram, not an in-game screenshot or measured carriageway survey.
W,H=1000,1050;B=(119.9573,30.2621,119.9651,30.27165)
def xy(c):return (100+(c[0]-B[0])/(B[2]-B[0])*760,910-(c[1]-B[1])/(B[3]-B[1])*800)
def line(coords,stroke,width=3,dash=''):
 pts=' '.join('%.2f,%.2f'%xy(c) for c in coords);return '<polyline points="'+pts+'" fill="none" stroke="'+stroke+'" stroke-width="'+str(width)+'"'+(' stroke-dasharray="'+dash+'"' if dash else '')+'/>'
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1050" viewBox="0 0 1000 1050">','<rect width="1000" height="1050" fill="#f8fafc"/>','<defs><clipPath id="m"><rect x="80" y="90" width="800" height="840"/></clipPath></defs>','<g font-family="Arial, sans-serif" fill="#172033">','<text x="65" y="40" font-size="24">Cainiao road scope / frozen OSM 2026-10-11</text>','<text x="65" y="70" font-size="14">Research diagram only: node topology retained; no shared data modified.</text>','<g clip-path="url(#m)">']
for w in x['ways']:
 t=w['tags'];colour='#cbd5e1';width=2
 if t.get('highway')=='service':colour='#a78bfa'
 elif t.get('name') in ['数云路','文二西路']:colour='#94a3b8';width=4
 svg.append(line(w['coordinates'],colour,width))
for s in excluded_slices:svg.append(line(s['coordinatesWGS84'],'#b91c1c',5,'6 5'))
for s in segments:svg.append(line(s['coordinatesWGS84'],'#d97706' if s['role'].startswith('reported-2026') else '#047857',5,'9 6' if s['role'].startswith('reported-2026') else ''))
for label,c,dx,dy in [('Wenyi W Rd',[119.9605,30.2711],0,-16),('Wener W Rd',[119.9605,30.2677],0,-18),('Fengxin Rd',[119.9617,30.26287],0,28),('Cainiao N Rd',[119.9601,30.26616],0,-15),('Yunlian Rd',[119.9581,30.2657],-100,0),('Shuyun Rd',[119.9640,30.2671],0,0),('HQ service roads',[119.9595,30.2642],0,0)]:
 xx,yy=xy(c);svg.append('<text x="%.2f" y="%.2f" font-size="14">%s</text>'%(xx+dx,yy+dy,html.escape(label)))
svg += ['</g>','<text x="900" y="125" font-size="21">N</text>','<path d="M908 160L908 135L900 145M908 135L916 145" stroke="#172033" fill="none"/>','<rect x="60" y="940" width="18" height="5" fill="#047857"/>','<text x="90" y="948" font-size="14">2023 notice: scoped public-road opening evidence</text>','<path d="M60 972H80" stroke="#d97706" stroke-width="5" stroke-dasharray="7 3"/>','<text x="90" y="977" font-size="14">2026 north extension: reported opening; geometry / primary notice pending</text>','<path d="M60 999H80" stroke="#b91c1c" stroke-width="5" stroke-dasharray="7 3"/>','<text x="90" y="1004" font-size="14">Beyond 2023 scope; violet = campus service ways, public access unknown</text>','<text x="60" y="1034" font-size="12">© OpenStreetMap contributors / ODbL-1.0. Diagram axes are schematic lon/lat; lengths in crosswalk use real ENU metres.</text>','</g></svg>']
(ROOT/'road-scope.svg').write_text('\n'.join(svg)+'\n')
print(json.dumps(dict(segments=len(segments),eligible2023=7,excludedWays=len(exclude),lengthDiscrepancies=metrics),ensure_ascii=False,indent=2))
