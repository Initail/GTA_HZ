"""Restore each mapped green source part before rendering, without rounding.
The exact fixed-source crosswalk makes this a bounded geometry correction,
not a proximity snap of arbitrary terrain, water or source road nodes.
"""
from __future__ import annotations
import argparse,json,hashlib,shutil
from pathlib import Path
import shapely
from shapely.geometry import shape,box,Polygon
from shapely.ops import transform
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--crosswalk',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    source=ROOT/a.source;crosswalk=ROOT/a.crosswalk;out=(ROOT/a.output).resolve();contract=json.loads(crosswalk.read_text())
    if ROOT/'artifacts' not in out.parents or out.exists():raise ValueError('Fresh artifact output required')
    if not contract['allRuntimePartsMapped'] or contract['unmatched']:raise ValueError('Unique full source crosswalk required')
    for f,h in contract['inputs'].items():
        if sha(ROOT/f)!=h:raise ValueError('Changed source '+f)
    raw_path=next(ROOT/f for f in contract['inputs'] if f.endswith('/green.geojson'));raw=json.loads(raw_path.read_text());city_path=source/'city.json';city=json.loads(city_path.read_text())
    if sha(city_path)!=contract['inputs'][str(city_path.relative_to(ROOT))]:raise ValueError('Wrong source city')
    m=city['meta'];domain=box(*m['extent']);old=shapely.union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in city['green']]);cache={};restored=[]
    def project(x,y,z=None):return (x-m['originWGS84'][0])*m['eastMetresPerDegree']*m['horizontalScale'],(y-m['originWGS84'][1])*m['northMetresPerDegree']*m['horizontalScale']
    for row in contract['rows']:
        i=row['sourceFeatureIndex'];f=raw['features'][i]
        if i not in cache:cache[i]=parts(transform(project,shape(f['geometry'])).intersection(domain))
        p=cache[i][row['sourcePartIndex']];b=city['green'][row['runtimeIndex']]
        if f['id']!=row['id'] or b['id']!=row['id'] or hashlib.sha256(shapely.normalize(p).wkb).hexdigest()!=row['originalWkbSha256']:raise ValueError('Changed mapped source part')
        if not p.is_valid:raise ValueError('Invalid source green')
        b['rings']=[[[x,z] for x,z in ring.coords] for ring in [p.exterior,*p.interiors]];b['sourcePartIndex']=row['sourcePartIndex'];b['boundaryStatus']='fixed-source unsimplified polygon clipped to exact shared domain; no rounding, no second scale'
        restored.append(p)
    if len(restored)!=len(city['green']):raise ValueError('Incomplete crosswalk')
    new=shapely.union_all(restored);out.mkdir(parents=True);(out/'city.json').write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
    shutil.copytree(source/'geography',out/'geography');shutil.copy2(source/'lamps.json',out/'lamps.json')
    source_edge=shapely.union_all([p.boundary.intersection(domain.boundary) for p in restored]);output_edge=shapely.union_all([Polygon(b['rings'][0],b['rings'][1:]).boundary.intersection(domain.boundary) for b in city['green']])
    mismatch=source_edge.symmetric_difference(output_edge).length
    if mismatch:raise ValueError('Lost original domain-edge identity')
    report={'cityId':'hangzhou','kind':'source-green-boundary-precision-restoration','inputs':{**contract['inputs'],a.crosswalk:sha(crosswalk),'scripts/restore_hangzhou_green_precision.py':sha(Path(__file__))},'restoredParts':len(restored),'originalSourceVertices':sum(len(r.coords) for p in restored for r in [p.exterior,*p.interiors]),'sourceDomainEdgeLengthGame':source_edge.length,'domainEdgeMismatchGame':mismatch,'oldToRestoredGreenSymmetricDifferenceGameSquared':old.symmetric_difference(new).area,'citySha256':sha(out/'city.json'),'unchangedSections':['land','water','roads including IDs/nodes/direction/heights','buildings','landmarks','spawn','geographic projection','geography files','lamps'],'passScope':'unique source-part restoration only','pending':['rebuild and inspect actual terrain GLB topology','inner clipped slivers and float32/meshopt precision','green-related placements against restored geometry','current visual/collision/performance']}
    (out/'input-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
