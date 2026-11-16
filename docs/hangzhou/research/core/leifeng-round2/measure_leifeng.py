"""Measure fixed OSM vectors through Hangzhou's side-effect-free coordinates."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
from city_config import load_city, project


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    city = load_city('hangzhou')
    geo = city['geography']
    paths = {key: ROOT / f'data/processed/hangzhou/{key}.geojson' for key in ('buildings', 'places', 'roads')}
    features = {}
    for key, path in paths.items():
        data = json.loads(path.read_text())
        ids = {'way/340652169', 'way/1448327494', 'way/1448327495'} if key == 'roads' else {'way/229726934'}
        features[key] = [f for f in data['features'] if f['id'] in ids]
    assert len(features['buildings']) == len(features['places']) == 1
    assert features['buildings'][0]['geometry'] == features['places'][0]['geometry']
    feature = features['buildings'][0]
    ring = feature['geometry']['coordinates'][0][0]
    assert ring[0] == ring[-1] and len(ring) == 9
    origin = ring[0]
    en = [((x-origin[0])*geo['eastMetresPerDegree'], (y-origin[1])*geo['northMetresPerDegree']) for x, y in ring[:-1]]
    edges = list(zip(en, en[1:] + en[:1]))
    area = sum(x*v-u*y for (x,y),(u,v) in edges) / 2
    cx = sum((x+u)*(x*v-u*y) for (x,y),(u,v) in edges) / (6*area)
    cy = sum((y+v)*(x*v-u*y) for (x,y),(u,v) in edges) / (6*area)
    center = [origin[0]+cx/geo['eastMetresPerDegree'], origin[1]+cy/geo['northMetresPerDegree']]
    local = [[x-cx, y-cy] for x, y in en]
    bearings = [(90-math.degrees(math.atan2(v-y,u-x))) % 360 for (x,y),(u,v) in edges]
    approach = next(f for f in features['roads'] if f['id'] == 'way/340652169')['geometry']['coordinates']
    dx = (approach[0][0]-approach[-1][0])*geo['eastMetresPerDegree']
    dy = (approach[0][1]-approach[-1][1])*geo['northMetresPerDegree']
    result = {
        'cityId': 'hangzhou', 'crs': 'EPSG:4326', 'osmFeatureId': feature['id'],
        'sourcePbfSha256': sha(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'),
        'sourceSnapshot': '2026-10-11T20:21:06Z',
        'processedSourceSha256': {key: sha(path) for key,path in paths.items()},
        'centerWGS84': center, 'centerGameEN': project(*center, city),
        'footprintWGS84': ring, 'footprintLocalMetresEN': local,
        'areaM2': abs(area), 'bboxEastM': max(x for x,y in local)-min(x for x,y in local),
        'bboxNorthM': max(y for x,y in local)-min(y for x,y in local),
        'edgeBearingsDegreesClockwiseFromNorth': bearings,
        'southApproachFeatureId': 'way/340652169',
        'southApproachBearingTowardTowerDegrees': math.degrees(math.atan2(dx,dy)) % 360,
        'method': 'area centroid and edge bearings of fixed mapped WGS84 octagon; city_config Hangzhou coefficients; metres before one .60 game scaling',
        'uncertainty': 'Vector computations only. OSM mapping accuracy unverified: use ±5m plan-position/outline allowance and ±2° face direction. Ring likely covers broad protection base/terrace, not upper tower diameter; no survey claim.',
        'ignoredTags': {'height': '71.7: tagged-unverified; do not treat as survey', 'alt_name:en': 'Six Harmonies Pagoda: identity conflict, not adopted'},
    }
    selected = {'type': 'FeatureCollection', 'cityId': 'hangzhou', 'features': features['buildings']+features['roads']}
    (HERE/'geofabrik-leifeng-features.geojson').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
    (HERE/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
