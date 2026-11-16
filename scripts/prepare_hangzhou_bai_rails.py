"""Finite rail solids bound to vertices checked in the actual GLB export."""
import argparse,json,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from shapely.geometry import MultiPoint
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--support',required=True);a=p.parse_args()
    model=ROOT/a.model;support=ROOT/a.support;report=json.loads((support/'support-report.json').read_text())
    if sha(model/'source-faces.json')!=report['inputs']['sourceFaces']:raise ValueError('Rail source drift')
    groups=defaultdict(list)
    for f in json.loads((model/'source-faces.json').read_text()):
        if f['changed'] and f['rail']:groups[f['rail']].extend(f['points'])
    solids=[]
    for identifier,pts in groups.items():
        pts=np.asarray(pts,dtype=np.float32).astype(float).tolist();hull=MultiPoint([p[:2] for p in pts]).convex_hull
        if hull.geom_type!='Polygon' or hull.area<=0:raise ValueError('Non-solid rail')
        solids.append({'id':'bai-route:'+identifier,'rings':[list(map(list,hull.exterior.coords))],
            'minY':min(p[2] for p in pts),'maxY':max(p[2] for p in pts),'blocksRoad':True})
    out=support/'rail-collisions.json'
    with out.open('x') as f:json.dump({'cityId':'hangzhou','sourceFacesSha256':report['inputs']['sourceFaces'],'actualSupportReportSha256':sha(support/'support-report.json'),'collisionFootprints':solids},f)
    print(json.dumps({'solids':len(solids),'sha256':sha(out)}))
