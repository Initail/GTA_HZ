"""Three bounded, read-only passes over the locked OSM snapshot for route 7.

This does not install a route or turn OSM schedules into live transit claims.
Each pass writes one fresh isolated artifact; no location index is allocated.
"""
import argparse,hashlib,json,resource,sys
from pathlib import Path
from city_config import ROOT
from hangzhou_feature_window import features
SOURCE=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'
OUT=ROOT/'artifacts/cities/hangzhou/bus-route-7-v1'
ROUTES={18906871,18906857,18906869,18906856}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('phase',choices=['relations','nodes','ways','way-nodes']);ap.add_argument('--revision',default='');ap.add_argument('--shard',type=int);a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);target=OUT/(a.phase+('-'+a.revision if a.revision else '')+(f'-part-{a.shard}' if a.shard is not None else '')+'.json')
    if target.exists():raise SystemExit('Existing source evidence is protected.')
    manifest=json.loads((ROOT/'data/hangzhou/source-manifest.json').read_text())
    if SOURCE.stat().st_size!=manifest['bytes'] or sha(SOURCE)!=manifest['sha256']:raise SystemExit('Locked source snapshot differs from manifest.')
    def checkpoint(label):print(json.dumps({'phase':label,'peakRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024 if sys.platform=='darwin' else 1)}),flush=True)
    checkpoint('before-osmium')
    import osmium
    checkpoint('after-osmium')
    records=[];missing=[]
    if a.phase=='relations':
        class Handler(osmium.SimpleHandler):
            def relation(self,r):
                if r.id not in ROUTES:return
                tags=dict(r.tags)
                if tags.get('ref')!='7' or tags.get('route')!='bus':raise ValueError('Bus relation identity changed')
                records.append({'id':f'relation/{r.id}','version':r.version,'timestamp':r.timestamp.isoformat(),'tags':tags,'members':[{'type':m.type,'id':str(m.ref),'role':m.role} for m in r.members]})
        Handler().apply_file(str(SOURCE),locations=False)
        missing=sorted(ROUTES-{int(r['id'].split('/')[1]) for r in records})
    else:
        relations=json.loads((OUT/'relations.json').read_text())['records'];wanted={int(m['id']) for r in relations for m in r['members'] if m['type']==('n' if a.phase=='nodes' else 'w')}
        if a.phase=='way-nodes':wanted={int(n) for w in json.loads((OUT/'ways.json').read_text())['records'] for n in w['properties']['nodeIds']}
        if a.shard is not None:
            if a.phase!='way-nodes' or not 0<=a.shard<6:raise ValueError('Expected way-node shard 0..5')
            wanted=set(sorted(wanted)[a.shard*64:(a.shard+1)*64])
        if a.phase in ('nodes','way-nodes'):
            # Native IdFilter rejects millions of unrelated nodes before Python.
            # This preserves all requested IDs without a locations index.
            class Handler(osmium.SimpleHandler):
                def node(self,n):
                    if not n.location.valid():raise ValueError('Bus source node lacks WGS84')
                    records.append({'id':f'node/{n.id}','version':n.version,'timestamp':n.timestamp.isoformat(),'tags':dict(n.tags),'wgs84':[n.location.lon,n.location.lat]})
            checkpoint('before-idfilter')
            id_filter=osmium.filter.IdFilter(wanted)
            checkpoint('after-idfilter')
            with osmium.io.Reader(str(SOURCE),osmium.osm.NODE,thread_pool=osmium.io.ThreadPool(1,2)) as reader:
                checkpoint('after-reader')
                osmium.apply(reader,id_filter,Handler())
            missing=sorted(wanted-{int(r['id'].split('/')[1]) for r in records})
        else:
            path=ROOT/'data/processed/hangzhou-261011-extended/roads.geojson'
            for f in features(path):
                if int(f['id'].split('/')[1]) in wanted:records.append(f)
            missing=sorted(wanted-{int(r['id'].split('/')[1]) for r in records})
    result={'schemaVersion':1,'cityId':'hangzhou','phase':a.phase,'source':{'path':str(SOURCE.relative_to(ROOT)),'sha256':manifest['sha256'],'snapshotUTC':manifest['osmReplicationTimestamp'],'crs':manifest['crs'],'license':manifest['license'],'attribution':manifest['attribution']},'records':records,'missing':missing,'currentScheduleStatus':'unknown; any game headway must be labelled simulated','physicalAcceptance':'pending; no road graph, platform clearance or browser checks yet'}
    if a.shard is not None:result['shard']={'index':a.shard,'count':6,'requestedIds':sorted(wanted)}
    if a.phase!='relations':result['relationEvidenceSha256']=sha(OUT/'relations.json')
    if a.phase=='ways':result['processedRoadSha256']=sha(ROOT/'data/processed/hangzhou-261011-extended/roads.geojson')
    target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'phase':a.phase,'records':len(records),'missing':missing,'bytes':target.stat().st_size,'sha256':sha(target)},ensure_ascii=False))
if __name__=='__main__':main()
