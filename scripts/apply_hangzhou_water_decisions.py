"""Apply individually evidenced water semantics without deleting source shapes."""
import argparse,json,copy
from pathlib import Path
import shapely
from shapely.geometry import Polygon
from city_config import ROOT
from prepare_hangzhou_water_topology import digest,parts,rings,overlaps

def geometry(body):return Polygon(body['rings'][0],body['rings'][1:])
def rendered(city):
    return [{**b,'rings':r} for b in city['water'] if b.get('renderSurface',True) for r in b.get('renderRings',[b['rings']])]
def apply(contract_path,output):
    contract_path,output=Path(contract_path).resolve(),Path(output).resolve();contract=json.loads(contract_path.read_text())
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh candidate required')
    for b in contract['bindings']:
        if digest(ROOT/b['path'])!=b['sha256']:raise ValueError('Changed research binding '+b['path'])
    source=ROOT/contract['bindings'][0]['path'];original=json.loads(source.read_text());city=copy.deepcopy(original);records=[]
    def select(key):
        b=city['water'][key['inputIndex']]
        if b['id']!=key['id'] or b['sourcePartIndex']!=key['sourcePartIndex'] or abs(b['height']-key['inputHeightGame'])>1e-10:raise ValueError('Changed decision subject')
        return b
    for d in contract['decisions']:
        subject=select(d['subject']);op=d['operation'];changed=[subject]
        subject['waterDecisionId']=d['decisionId'];subject['sourceHeightGame']=subject['height']
        if op=='retain-source-polygon-as-semantic-region-disable-separate-water-surface':
            parent=select(d['parent'])
            if geometry(subject).difference(geometry(parent)).area>1e-7:raise ValueError('Semantic region not covered by parent')
            subject.update(renderSurface=False,surfaceParentId=parent['id'],height=d['surfaceHeightGame'],heightStatus=d['heightStatus'],semanticKind='lotus-water-region')
        elif op=='subtract-lock-source-polygon-from-broad-river-render-footprint':
            river=select(d['broadRiver']);changed.append(river);cut=geometry(river).difference(geometry(subject))
            river.update(renderRings=[rings(p) for p in parts(cut)],waterDecisionId=d['decisionId']);subject['gateSourceIds']=d['gateSourceIds']
        elif op=='alias-whole-subject-part-height-to-reference-and-subtract-reference-from-subject-render-footprint':
            parent=select(d['referenceRiver']);cut=geometry(subject).difference(geometry(parent))
            subject.update(renderRings=[rings(p) for p in parts(cut)],height=d['surfaceHeightGame'],heightStatus=d['heightStatus'],sourceLayer=d['rawLayer'],surfaceHeightReference=parent['id'])
        else:raise ValueError('Unsupported water decision '+op)
        for b in changed:b['waterDecisionContract']=str(contract_path.relative_to(ROOT))
        records.append({'decisionId':d['decisionId'],'operation':op,'changedSourceIds':[b['id'] for b in changed],'status':'candidate-only','pending':d['pending']})
    before=shapely.union_all([geometry(b) for b in original['water']]);display=rendered(city);after=shapely.union_all([geometry(b) for b in display]);wet_error=before.symmetric_difference(after).area
    if wet_error>1e-6 or len(city['water'])!=len(original['water']):raise ValueError('Water union or source object lost')
    for a,b in zip(original['water'],city['water']):
        if (a['id'],a['sourcePartIndex'],a['rings'])!=(b['id'],b['sourcePartIndex'],b['rings']):raise ValueError('Raw footprint changed')
    remaining=overlaps(display,1e-6)
    expected={tuple(sorted([r['a'],r['b']])) for r in contract['remaining24']}
    if {tuple(sorted([r['a'],r['b']])) for r in remaining}!=expected:raise ValueError('Unexpected remaining surface overlaps')
    city['meta']['status']='water-semantic-candidate-not-integrated';output.mkdir(parents=True);target=output/'city.json';target.write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
    report={'kind':'object-specific-water-semantics-candidate','cityId':'hangzhou','inputs':{str(p.relative_to(ROOT)):digest(p) for p in [source,contract_path,Path(__file__),ROOT/'scripts/prepare_hangzhou_water_topology.py']},'outputCitySha256':digest(target),
        'sourceBodies':len(city['water']),'renderParts':len(display),'semanticRegions':sum(not b.get('renderSurface',True) for b in city['water']),'sourceFootprintsRetained':True,'wetUnionDifferenceGameSquared':wet_error,
        'decisions':records,'remainingSourceOverlaps':remaining,'remainingOverlapCount':len(remaining),'pass':False,'finiteSemanticApplicationPassed':True,'pending':['remaining24 source overlaps','hydraulic levels and north-end connection','lock gates and shoreline geometry','rebuild base-water meshes','browser/visual/collision/performance']}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','decisions','remainingSourceOverlaps']},ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--contract',required=True);p.add_argument('--output',required=True);a=p.parse_args();apply(a.contract,a.output)
