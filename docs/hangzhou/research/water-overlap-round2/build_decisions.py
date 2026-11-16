"""Freeze semantic research decisions and dry-run geometry; never writes city assets."""
from pathlib import Path
import hashlib,json
from shapely.geometry import Polygon
from shapely.ops import unary_union

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
def read(p): return json.loads((ROOT/p).read_text())
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
city_path='artifacts/cities/hangzhou/water-data-v2/city.json'
report_path='artifacts/cities/hangzhou/water-data-v2/report.json'
c=read(city_path); pairs=read(report_path)['remainingSourceOverlaps']
context=json.loads((OUT/'all-pair-waterway-context.json').read_text())
assert sha(city_path)=='15904a2c40f323546262e7ead44bd4794f354dd45f8125cf7c827313c09814fb'
assert len(pairs)==27
files=[city_path,report_path,'data/raw/hangzhou/zhejiang-261011.osm.pbf',
 'docs/hangzhou/research/water-overlap-round1/raw-osm-evidence.json',
 'docs/hangzhou/research/water-overlap-round1/pair-review.json',
 'docs/hangzhou/research/water-overlap-round1/references/government-lotus-net.html',
 'docs/hangzhou/research/water-overlap-round2/layer-context.json',
 'docs/hangzhou/research/water-overlap-round2/all-pair-waterway-context.json']
bindings=[{'path':p,'sha256':sha(p)} for p in files]
def ref(index):
 w=c['water'][index]
 return {'id':w['id'],'sourcePartIndex':w['sourcePartIndex'],'inputIndex':index,'inputHeightGame':w['height']}
decisions=[
 {'decisionId':'HZ-WATER-R2-001','pair':1,'status':'ready-for-isolated-candidate','classification':'reported-semantic-region-with-estimated-parent-height',
  'subject':ref(1699),'parent':ref(2066),
  'operation':'retain-source-polygon-as-semantic-region-disable-separate-water-surface',
  'surfaceOwner':'relation/2308774','surfaceHeightGame':c['water'][2066]['height'],
  'heightStatus':'estimated-not-surveyed','preserve':['source polygon and part identity','name 断桥荷塘','original OSM tags','original estimated height provenance','lotus vegetation/material region'],
  'evidence':['lotus-net-report','fixed-osm-nesting'],
  'scope':'Only the nested part 0 of way/975870009; parent West Lake geometry and height unchanged.',
  'pending':['water and lotus visual review','night reflection and collision review','absolute hydraulic level remains unmeasured']},
 {'decisionId':'HZ-WATER-R2-002','pair':2,'status':'ready-for-isolated-candidate','classification':'source-mapped-lock-partition-with-estimated-heights',
  'subject':ref(581),'broadRiver':ref(260),
  'operation':'subtract-lock-source-polygon-from-broad-river-render-footprint',
  'surfaceOwnerInOverlap':'way/662789923','surfaceHeightGame':c['water'][581]['height'],
  'heightStatus':'estimated-not-surveyed','outsideOverlapHeightPolicy':'retain each existing input height; do not average',
  'preserve':['both original source polygons and part identities','lock chamber render footprint','original estimated height provenance','lock gate source objects'],
  'gateSourceIds':['way/662789912','way/662789916','way/662789921','way/662618623'],
  'lockCenterlineSourceId':'way/662789918','evidence':['fixed-osm-lock','osm-water-lock'],
  'scope':'Only part 0 of way/520199008 minus part 0 of way/662789923; preserve all resulting holes and polygon parts.',
  'pending':['gate physical model and operating state','upstream/downstream/chamber measured levels','dynamic level behavior','collision/navigation and visual acceptance']},
 {'decisionId':'HZ-WATER-R2-003','pair':3,'status':'ready-for-isolated-estimated-candidate','classification':'explicit-bounded-game-adaptation-not-measured-hydraulics',
  'subject':ref(351),'referenceRiver':ref(473),
  'operation':'alias-whole-subject-part-height-to-reference-and-subtract-reference-from-subject-render-footprint',
  'surfaceOwnerInOverlap':'way/642559807','surfaceHeightGame':c['water'][473]['height'],
  'heightStatus':'estimated-game-adaptation-not-surveyed','rawLayer':'-1','layerIsNotMetres':True,
  'preserve':['both original source polygons and part identities','original layer=-1 metadata','original estimated height provenance','mapped centerline node connections'],
  'evidence':['fixed-osm-layer-connection','osm-layer'],
  'scope':'Only all of part 0 of way/552611233 uses the existing height of part 0 of way/642559807. No upstream/downstream recursive height propagation, no other water object height edits, no inferred tunnel.',
  'reasonForWholePart':'A mouth-only flat patch would add an artificial step at its boundary. Whole bounded source part is the explicit candidate modeling choice, not a claim of surveyed longitudinal level.',
  'pending':['north-end junction height and profile','bridge underside clearance','physical water levels and possible unrecorded controls','visual/collision review; source connectivity alone is insufficient']}
]
geometry=[]
for d,p in zip(decisions,pairs[:3]):
 a,b=(Polygon(c['water'][i]['rings'][0],c['water'][i]['rings'][1:]) for i in (p['aIndex'],p['bIndex']))
 before=unary_union([a,b])
 if d['pair']==1: after=[b]
 elif d['pair']==2: after=[a.difference(b),b]
 else: after=[a.difference(b),b]
 geometry.append({'pair':d['pair'],'sourceAValid':a.is_valid,'sourceBValid':b.is_valid,'subjectSourceAreaGameSquared':a.area if d['pair']!=2 else b.area,
  'renderAreasGameSquared':[g.area for g in after],'originalOverlapAreaGameSquared':a.intersection(b).area,
  'remainingPairOverlapGameSquared':0 if len(after)==1 else after[0].intersection(after[1]).area,
  'wetUnionSymmetricDifferenceGameSquared':before.symmetric_difference(unary_union(after)).area,
  'resultGeometryValid':all(g.is_valid for g in after),'resultGeometryTypes':[g.geom_type for g in after],
  'scope':'in-memory Shapely dry-run only; no GLB, runtime, hydraulic or visual pass'})
 assert geometry[-1]['wetUnionSymmetricDifferenceGameSquared']<1e-6
 assert geometry[-1]['remainingPairOverlapGameSquared']<1e-6
 assert geometry[-1]['resultGeometryValid']
pending=[]
for row,p in zip(context['pairResults'][3:],pairs[3:]):
 controls=row['mappedControlsWithin30Game']
 if controls:
  recommendation='Retain separate identities and levels; map control-side domains before any surface merge.'
  blocker='Mapped weir nearby: control geometry and level domains unresolved.'
 elif row['candidateConnections']:
  recommendation='Source supports connected junction; next bounded candidate may partition shared footprint using named channel ownership. Freeze an explicit reference and scope before height changes.'
  blocker='Hydraulic profile and per-object surface ownership not frozen; connectivity is not equal-level measurement.'
 else:
  recommendation='Retain identities; determine duplicate boundary, nested semantic zone, or independent basin before selecting footprint ownership.'
  blocker='No direct centerline graph proof found in local source subset; boundary contact alone does not establish hydraulic continuity.'
 pending.append({'pair':row['pair'],'a':p['a'],'b':p['b'],'areaGameSquared':p['areaGameSquared'],
  'heightDifferenceGame':p['heightDifferenceGame'],'status':'not-passed','recommendation':recommendation,'blocker':blocker,
  'candidateConnections':row['candidateConnections'],'mappedControlsWithin30Game':controls})
save('decisions.json',{'schemaVersion':1,'createdDate':'2026-11-11','kind':'frozen-semantic-research-contract-not-runtime-integration',
 'sourceSnapshot':'2026-10-11','sourceCrs':'WGS84','license':'OSM ODbL 1.0; retain source attribution',
 'bindings':bindings,'decisions':decisions,'remaining24':pending,
 'integrationRequirements':['Keep original source geometries distinct from render partitions, without deleting source objects.',
 'Do not infer measured heights from DSM samples, layer tags, centerline continuity or this contract.',
 'Apply only the three identified source parts; report all other 24 overlaps as not passed.',
 'Validate source identity/footprint retention, wet union, resulting holes, no positive-area overlap and unchanged unrelated heights.',
 'Model and browser visual/collision/performance gates remain pending.']})
save('geometry-dry-run.json',{'citySha256':sha(city_path),'result':'three-pair-horizontal-geometry-check-only','checks':geometry,
 'pairwiseOverlapAreaAll27GameSquared':sum(p['areaGameSquared'] for p in pairs),'pairwiseOverlapAreaFirst3GameSquared':sum(p['areaGameSquared'] for p in pairs[:3]),
 'notClaimed':['global water hydraulic pass','all 27 pairs resolved','runtime mesh validated','visual acceptance']})
print(json.dumps({'decisions':len(decisions),'pending':len(pending),'dryRunChecks':geometry},ensure_ascii=False,indent=2))
