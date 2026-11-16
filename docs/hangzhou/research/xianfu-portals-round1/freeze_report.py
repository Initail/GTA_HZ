"""Research-package consistency only; does not claim physical/visual acceptance."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((P/'fixed-osm-context.json').read_text());m=json.loads((P/'measurements.json').read_text());sources=json.loads((P/'sources.json').read_text());checks=[]
def check(name,ok):
 assert ok,name
 checks.append({'name':name,'passed':True})
check('snapshot identity preserved',d['source']['sha256']==sources['accepted'][0]['sha256'] and d['source']['snapshot']=='261011')
check('extractor matches frozen source extraction',d['extractorSha256']==sha(P/'extract_context.py'))
check('measurement input matches frozen extraction',m['inputs']['fixedContextSha256']==sha(P/'fixed-osm-context.json'))
w={v['id']:v for v in d['ways']};n={v['id']:v for v in d['nodes']};low=w[697096305]
check('source endpoint identities and coordinates',all(n[i]['coordinates']==c for i,c in zip(low['nodeIds'],low['coordinates'])))
check('source endpoint connections',set(m['portals'][0]['connectedWayIds'])=={697096305,1418959639} and set(m['portals'][1]['connectedWayIds'])=={697096305,697096306})
check('two crossings do not share source nodes',len(m['planarCrossings'])==2 and all(not p['sharedSourceNodeIds'] for p in m['planarCrossings']))
check('bus relation local membership',len(m['busRelations'])==2 and all(r['orderedWayRefs']==[1418959639,697096305,697096306] and r['memberIndicesZeroBased'][-1]-r['memberIndicesZeroBased'][0]==2 for r in m['busRelations']))
check('unverified physical and visual gates remain blocked',m['physicalMeasurementVerified'] is False and m['photosVerified']==0 and not m['browserOrDrivingTestPerformed'])
ET.parse(P/'source-plan.svg');check('source SVG parses',True)
out={'researchDate':'2026-11-11','scope':'research package consistency only','checks':checks,'status':'source-topology-confirmed-dimensions-and-appearance-blocked','sourcePbfHashRecomputedBy':'extract_context.py','physicalGeometryPassed':False,'visualPassed':False,'drivingPassed':False,'files':{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='validation.json'}}
(P/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(f'{len(checks)} research consistency checks passed; physical/visual/driving not tested')
