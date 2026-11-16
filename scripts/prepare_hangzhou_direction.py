"""Migrate direction semantics without rebuilding unchanged physical positions.

Fresh candidate only. Reverses all dependent road chains/heights together;
graph nodes, edges, components and physical geometry remain byte-equivalent.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
from collections import Counter
from city_config import ROOT,load_city
from hangzhou_road_direction import road_direction
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
    profile=load_city('hangzhou');raw=ROOT/profile['assets']['processedRoot']/'roads.geojson';features={f['id']:f for f in json.loads(raw.read_text())['features']}
    city=json.loads((source/'city.json').read_text());nav=json.loads((source/'navigation.json').read_text());levels=json.loads((source/'geography/road-levels.json').read_text());manifest=json.loads((source/'geography/manifest.json').read_text());by_id={r['id']:r for r in levels['roads']};changed=[];bases=Counter()
    if city['meta']['cityId']!='hangzhou' or digest(source/'geography/road-levels.json')!=manifest['roadLevelsSha256']:raise ValueError('Changed geography input')
    for road in city['roads']:
        tags=features[road['sourceId']]['properties']['tags'];oneway,reverse,basis=road_direction(tags);bases[basis]+=1;level=by_id[road['id']]
        if level['points']!=road['points'] or level['nodeIds']!=road['nodeIds']:raise ValueError('Changed source chain')
        if reverse:
            for key in ['points','nodeIds','heights']:road[key]=list(reversed(road[key]))
            for key in ['points','nodeIds','heights','groundHeights']:
                if key in level:level[key]=list(reversed(level[key]))
            nav['roadNodes'][road['id']]=list(reversed(nav['roadNodes'][road['id']]))
        if reverse or road['oneway']!=oneway:changed.append({'id':road['id'],'sourceId':road['sourceId'],'oldOneway':road['oneway'],'oneway':oneway,'reversed':reverse,'basis':basis})
        road['oneway']=oneway;road['directionBasis']=basis
        for point,node_id,y,idx in zip(road['points'],road['nodeIds'],road['heights'],nav['roadNodes'][road['id']]):
            if point!=nav['nodes'][idx] or str(node_id)!=str(nav['sourceNodeIds'][idx]) or abs(y-nav['nodeHeights'][idx])>1e-5:raise ValueError('Physical/source/node-height mismatch after direction migration')
    city['meta']['directionSemantics']='OSM explicit reverse, explicit two-way and implied motorway/roundabout; same gameplay controls'
    shutil.copytree(source,output)
    for name,value in [('city.json',city),('navigation.json',nav),('geography/road-levels.json',levels)]: (output/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')))
    manifest['roadLevelsSha256']=digest(output/'geography/road-levels.json');(output/'geography/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    result={'kind':'source-direction-semantics-candidate','cityId':'hangzhou','inputCitySha256':digest(source/'city.json'),'inputNavigationSha256':digest(source/'navigation.json'),'inputSourceRoadsSha256':digest(raw),'outputCitySha256':digest(output/'city.json'),'directionBasisCounts':dict(bases),'changes':changed,'unchanged':['source node identities and coordinates','undirected graph nodes/edges/components','per-node physical heights','building/water/green/land geometry','spawn and arrivals'],'references':['https://wiki.openstreetmap.org/wiki/Key:oneway','https://wiki.openstreetmap.org/wiki/Tag:junction=roundabout'],'pending':['directed destination route regression','current browser traffic/autopilot and bridge driving'],'files':{str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()}}
    (output/'direction-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['files','changes']},ensure_ascii=False,indent=2));print('changed',len(changed))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();prepare(a.input,a.output)
