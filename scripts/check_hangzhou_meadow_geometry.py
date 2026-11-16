"""Independent sampled whole-disc audit of serialized near-camera grass masks.

Uses circumscribed polygons around decoded byte positions, not the generator's
point-distance eligibility helper. This is offline geometry evidence only.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.strtree import STRtree
from hangzhou_surface import digest
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    for key in ['candidate','source','detail','life','output']:p.add_argument('--'+key,required=True)
    a=p.parse_args();out=ROOT/a.output
    if out.exists():raise ValueError('Fresh report required')
    candidate=ROOT/a.candidate;source=ROOT/a.source
    def read(p):return json.loads(Path(p).read_text())
    m=read(candidate/'meadow.json');r=read(candidate/'report.json')
    if digest(candidate/'meadow.json')!=r['manifestSha256']:raise ValueError('Changed mask manifest')
    for name,h in r['inputs'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed source '+name)
    c=read(source/'city.json');d=read(ROOT/a.detail);life=read(ROOT/a.life);geo=read(source/'geography/manifest.json');sites=read(source/'geography'/geo['siteSurfacesFile'])
    def poly(rings):return Polygon(rings[0],rings[1:])
    green=shapely.union_all([poly(g['rings']) for g in c['green']]);land=shapely.union_all([poly(g) for g in c['land']]);shapely.prepare(green);shapely.prepare(land)
    groups={
        'road-and-pavement':[LineString(q['points']).buffer(q['width']/2+2.8,cap_style=2,join_style=2) for q in c['roads']],
        'building-and-detail':[poly(q['rings']).buffer(3,quad_segs=32) for q in c['buildings']+d['collisionFootprints']],
        'water':[poly(q['rings']).buffer(6,quad_segs=32) for q in c['water']],
        'coast':[LineString(q).buffer(9,quad_segs=32) for q in c['coast'] if len(q)>1],
        'life':[Polygon(q['footprint']).buffer(3,quad_segs=32) for q in life['sites']],
        'site-surfaces':[Polygon([p[:2] for p in t]) for kind in ['terrainCuts','walkFloors','solidSlabs','terrainPatches'] for q in sites.get(kind,[]) for t in q['triangles']],
        'authored-bases':[Point(q['x'],q['z']).buffer(q['excludeRadius']+3,quad_segs=256) for q in c['landmarks'] if q.get('excludeRadius',0)>0],
    }
    trees={name:STRtree(items) for name,items in groups.items()};points=[];checked_tiles=0;safe_count=0
    for tile in m['tiles']:
        file=candidate/tile['url']
        if digest(file)!=tile['sha256']:raise ValueError('Changed tile')
        data=np.fromfile(file,dtype='u1').reshape(32,32,3);rows,cols=np.where(data[:,:,0]==255)
        if len(rows)!=tile['count']:raise ValueError('Wrong safe count')
        safe_count+=len(rows);checked_tiles+=1
        # Three deterministic distinct positions from every nonempty tile.
        for n in sorted(set([0,len(rows)//2,len(rows)-1])):
            points.append((tile['ix']*128+(int(cols[n])+.5)*4,tile['iz']*128+(int(rows[n])+.5)*4))
    radius=m['safeRadius']/math.cos(math.pi/128)
    failures=[];counts={k:0 for k in ['outside-green','outside-land',*trees]}
    for start in range(0,len(points),512):
        sample=points[start:start+512];discs=shapely.buffer(shapely.points(sample),radius,quad_segs=32)
        for key,mask in [('outside-green',~shapely.covers(green,discs)),('outside-land',~shapely.covers(land,discs))]:
            indices=np.flatnonzero(mask);counts[key]+=len(indices)
            failures.extend({'point':sample[int(i)],'reason':key} for i in indices[:10])
        for key,tree in trees.items():
            pairs=tree.query(discs,predicate='intersects');indices=np.unique(pairs[0]);counts[key]+=len(indices)
            failures.extend({'point':sample[int(i)],'reason':key} for i in indices[:10])
    report={'kind':'serialized mask independent sampled whole-disc geometry audit','candidate':a.candidate,'manifestSha256':digest(candidate/'meadow.json'),'checkerSha256':digest(Path(__file__)),'allTileHashesAndCounts':checked_tiles,'safeCells':safe_count,'sampledDiscs':len(points),'sampling':'first, middle, last safe byte cell in every nonempty tile','discRadiusGame':m['safeRadius'],'circumscribedPolygonRadiusGame':radius,'violations':counts,'examples':failures[:30],'pass':not any(counts.values()),'pending':['not exhaustive full-circle verification of every encoded cell','GPU/night/rendering and complete integrated world']}
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['pass']:raise SystemExit(1)

if __name__=='__main__':main()
