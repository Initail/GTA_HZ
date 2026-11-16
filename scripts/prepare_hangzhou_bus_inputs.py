"""Bind route 7's locked OSM records to the unchanged prepared city graph.

This creates an audited input, not a usable bus route or a live timetable.
The node shards are complete and checked against the source way-node set.
"""
import hashlib,json,math
from pathlib import Path
from city_config import ROOT,load_city,project

BASE=ROOT/'artifacts/cities/hangzhou/bus-route-7-v1'
def read(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def main():
    target=BASE/'prepared-inputs-v1.json'
    if target.exists():raise SystemExit('Existing prepared bus inputs are protected')
    provenance={};ways=read(BASE/'ways.json')['records'];relations=read(BASE/'relations.json')['records'];platforms=read(BASE/'nodes.json')['records']
    wanted_nodes={str(n) for w in ways for n in w['properties']['nodeIds']};nodes={}
    for i in range(6):
        path=BASE/f'way-nodes-bounded-v1-part-{i}.json';d=read(path);assert d['shard']['index']==i and not d['missing']
        assert {str(n) for n in d['shard']['requestedIds']}=={r['id'].split('/')[1] for r in d['records']}
        for r in d['records']:
            assert r['id'] not in nodes;nodes[r['id']]=r
        provenance[str(path.relative_to(ROOT))]=sha(path)
    assert {n.split('/')[1] for n in nodes}==wanted_nodes
    for name in ['relations','nodes','ways']:provenance[str((BASE/(name+'.json')).relative_to(ROOT))]=sha(BASE/(name+'.json'))
    road_ids={w['id'] for w in ways};roads=[];levels=[]
    for folder,key in [('city','roads'),('road-levels','roads')]:
        base=ROOT/'artifacts/cities/hangzhou/stream-data-v1'/folder;manifest=read(base/'manifest.json')
        for array in manifest['arrays']:
            if array['key']!=key:continue
            for c in array['chunks']:
                path=base/c['file'];assert sha(path)==c['sha256']
                selected=[r for r in read(path)['values'] if (r.get('sourceId') or r['id'].split('#')[0]) in road_ids]
                if selected:
                    (roads if folder=='city' else levels).extend(selected);provenance[str(path.relative_to(ROOT))]=c['sha256']
    nav_path=ROOT/'artifacts/cities/hangzhou/demo-v10/public/cities/hangzhou/navigation.json';navigation=read(nav_path);provenance[str(nav_path.relative_to(ROOT))]=sha(nav_path)
    old_indices=sorted({i for r in roads for i in navigation['roadNodes'][r['id']]});index={old:new for new,old in enumerate(old_indices)}
    graph={'nodes':[navigation['nodes'][i] for i in old_indices],'nodeHeights':[navigation['nodeHeights'][i] for i in old_indices],'sourceNodeIds':[navigation['sourceNodeIds'][i] for i in old_indices], 'edges':[], 'roadNodes':{r['id']:[index[i] for i in navigation['roadNodes'][r['id']]] for r in roads}}
    edges={tuple(sorted((a,b))) for chain in graph['roadNodes'].values() for a,b in zip(chain,chain[1:]) if a!=b}
    global_edges={tuple(sorted(e)) for e in navigation['edges']}
    assert all(tuple(sorted((old_indices[a],old_indices[b]))) in global_edges for a,b in edges)
    graph['edges']=[list(e) for e in sorted(edges)];del navigation,global_edges
    city=load_city('hangzhou');anchors=[]
    for p in platforms:
        pp=project(*p['wgs84'],city);matches=[]
        for n in nodes.values():
            if n['tags'].get('public_transport')!='stop_position' or n['tags'].get('name')!=p['tags'].get('name'):continue
            if n['id'].split('/')[1] not in graph['sourceNodeIds']:continue
            idx=graph['sourceNodeIds'].index(n['id'].split('/')[1]);distance=math.dist(pp,graph['nodes'][idx])
            matches.append({'sourceStopId':n['id'],'node':idx,'horizontalDistanceGame':distance,'roadHeightGame':graph['nodeHeights'][idx]})
        matches.sort(key=lambda m:m['horizontalDistanceGame'])
        anchors.append({'sourcePlatformId':p['id'],'name':p['tags'].get('name'),'platformGame':list(pp),'sourcePositionCandidates':matches,'status':'unverified; needs directed route, door-side, dry full-body platform and walking-access checks'})
    result={'schemaVersion':1,'cityId':'hangzhou','source':read(BASE/'relations.json')['source'],'roads':roads,'roadLevels':levels,'graph':graph,'relations':relations,'platforms':platforms,'wayNodes':list(nodes.values()),'anchorCandidates':anchors,'missingSourceWays':sorted(road_ids-{r['sourceId'] for r in roads}),'inputs':provenance,'acceptance':{'sourceNodesComplete':True,'sourceGraphPreserved':True,'stopBinding':False,'platformClearance':False,'routeGeometry':False,'browser':False,'timetable':'simulation only'}}
    target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'output':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'roads':len(roads),'nodes':len(graph['nodes']),'edges':len(edges),'platforms':len(platforms),'withoutSourcePosition':sum(not a['sourcePositionCandidates'] for a in anchors),'missingSourceWays':result['missingSourceWays']},ensure_ascii=False))
if __name__=='__main__':main()
