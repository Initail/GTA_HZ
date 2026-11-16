"""Freeze an estimated Bai causeway datum against one playable city snapshot.

The original OSM line/land outlines and bridge shapes remain authoritative in
plan. DSM is not a survey of the embankment. A 1 m real bank freeboard is an
explicit game adaptation, joined to the existing public-road ground at ends.
No shared city or previous candidate is overwritten.
"""
import argparse, hashlib, json, math
from pathlib import Path
from city_config import load_city, project
from hangzhou_surface import Surface

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())

def prepare(source, output):
    if output.exists() or ROOT / 'artifacts' not in output.parents:
        raise ValueError('Fresh artifact directory required')
    surface = Surface(source)
    city = load_city('hangzhou')
    spec_path = ROOT / 'docs/hangzhou/research/core/west-lake-causeways-round2/spec.json'
    bridge_path = ROOT / 'docs/hangzhou/research/core/broken-bridge-round2/spec.json'
    spec, bridge = read(spec_path), read(bridge_path)
    paths = [p for p in spec['paths'] if p['causeway'] == 'bai']
    # Insert the externally owned Broken Bridge between the two source nodes.
    paths.insert(-1, {'sourceId': 'way/28538289', 'nodes': bridge['sourceRoadNodeIds'],
                     'coordinatesWGS84': bridge['endpointsWGS84'], 'flatTravelWidthM': bridge['bridgeWidthM']})
    previous = None
    for p in paths:
        if previous and previous != str(p['nodes'][0]): raise ValueError('Source chain disconnected')
        previous = str(p['nodes'][-1])
    water = [w for w in read(source/'city.json')['water'] if w['id'] == 'relation/2308774' and w.get('renderSurface', True)]
    water_y = {w['height'] for w in water}
    if len(water_y) != 1: raise ValueError('One consistent West Lake water datum required')
    water_y = water_y.pop()
    records, stations, distance = [], [], 0.0
    for p in paths:
        points = [project(*ll, city) for ll in p['coordinatesWGS84']]
        records.append({'sourceId': p['sourceId'], 'sourceNodeIds': p['nodes'], 'points': points,
                        'widthGame': p['flatTravelWidthM'] * city['geography']['scale']})
        for a, b in zip(points, points[1:]):
            length = math.dist(a, b); count = max(1, math.ceil(length/1.0))
            for i in range(count):
                t = i/count; x,z = [a[k]+(b[k]-a[k])*t for k in range(2)]
                stations.append([distance+length*t, x,z, max(water_y+.6, surface.ground(x,z)+.105)])
            distance += length
    x,z = records[-1]['points'][-1]
    stations.append([distance,x,z,max(water_y+.6,surface.ground(x,z)+.105)])
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in [spec_path, bridge_path, source/'city.json',
        source/'geography/manifest.json', source/'geography/road-levels.json', source/'geography/terrain-game.bin',
        ROOT/'scripts/landmarks/west_lake_causeways.py', ROOT/'scripts/landmarks/broken_bridge.py',
        ROOT/'scripts/prepare_hangzhou_bai_route.py', ROOT/'config/cities/hangzhou.json']}
    result = {'cityId':'hangzhou','kind':'source-bound Bai route datum candidate','units':'game east/north/up; scale applied once',
        'sourceRoot':str(source.relative_to(ROOT)),'inputs':inputs,'paths':records,'stations':stations,
        'waterYGame':water_y,'minimumBankDatumGame':water_y+.6,'bankFreeboardBasis':{'basis':'estimated',
        'method':'one real metre above existing provisional lake water, blended by max with source DSM earthworks plus original pavement offset',
        'uncertaintyRealMetres':1.0,'notSurveyed':True},
        'bankSourceIds':['way/28538305','relation/20083745'],
        'unchanged':['OSM path coordinates and source node identities','lake source outline and water shader','original actor step, radius and speed'],
        'pending':['actual GLB support extraction','full-body walks in both directions','bank/road visual ownership','browser visual and performance review']}
    output.mkdir(parents=True)
    (output/'route-input.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'stations':len(stations),'lengthGame':distance,'waterYGame':water_y}))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    prepare((ROOT/a.source).resolve(),(ROOT/a.output).resolve())
