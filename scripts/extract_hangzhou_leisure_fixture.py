"""Select real, unchanged city records for bounded local collision regression."""
import hashlib,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
chunks=ROOT/'artifacts/cities/hangzhou/stream-data-v1/city'
ap=argparse.ArgumentParser();ap.add_argument('--version',choices=['v1','v2'],default='v1');args=ap.parse_args()
out=ROOT/('artifacts/cities/hangzhou/city-leisure-v14/tests/main-city-fixture'+('-v2' if args.version=='v2' else '')+'.json')
if out.exists():raise SystemExit('Existing fixture is protected')
m=json.loads((chunks/'manifest.json').read_text());result={'meta':{'cityId':'hangzhou'}};sources={}
def coords(value):
    if isinstance(value,list):
        if len(value)>=2 and isinstance(value[0],(int,float)):yield value
        else:
            for child in value:yield from coords(child)
def intersects(points):
    ps=list(coords(points))
    return bool(ps) and min(p[0] for p in ps)<100 and max(p[0] for p in ps)>-450 and min(p[1] for p in ps)<-600 and max(p[1] for p in ps)>-1150
for array in m['arrays']:
    key=array['key']
    if key not in ['roads','buildings','water','land','landmarks']:continue
    result[key]=[]
    for c in array['chunks']:
        path=chunks/c['file'];raw=path.read_bytes();values=json.loads(raw)['values'];selected=[]
        for v in values:
            keep=key=='land' or key=='water' and v.get('id')=='relation/2308774'
            if key in ['roads','buildings']:keep=intersects(v.get('points',v.get('rings',[])))
            if key=='landmarks':keep=-450<v['x']<100 and -1150<v['z']<-600
            if keep:selected.append(v)
        if selected:sources[c['file']]=hashlib.sha256(raw).hexdigest();result[key].extend(selected)
if args.version=='v2':
    folder=chunks.parent/'road-levels';road_manifest=json.loads((folder/'manifest.json').read_text());ids={r['id'] for r in result['roads']};result['roadLevels']=[]
    for array in road_manifest['arrays']:
        if array['key']!='roads':continue
        for c in array['chunks']:
            path=folder/c['file'];raw=path.read_bytes();selected=[r for r in json.loads(raw)['values'] if r['id'] in ids]
            if selected:result['roadLevels'].extend(selected);sources['road-levels/'+c['file']]=hashlib.sha256(raw).hexdigest()
    if len(result['roadLevels'])!=len(ids):raise ValueError('Missing source road levels')
result['_evidence']={'boundsGame':[-450,-1150,100,-600],'sourceChunks':sources,'purpose':'Unmodified real records within a regression window, not whole-city acceptance'}
out.write_text(json.dumps(result,separators=(',',':'))+'\n')
print(json.dumps({'output':str(out),'counts':{k:len(v) for k,v in result.items() if isinstance(v,list)},'bytes':out.stat().st_size}))
