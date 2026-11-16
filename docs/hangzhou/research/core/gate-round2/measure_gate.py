"""Measure public OSM data; these are data measurements, not a field survey."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent


def main():
    raw = ROOT / 'osm-local-map.json'
    snapshot = json.loads(raw.read_text())
    nodes = {e['id']: e for e in snapshot['elements'] if e['type'] == 'node'}
    chosen = [e for e in snapshot['elements'] if e['type'] == 'way'
              and e['id'] in (1015040645, 1015040646, 1015040647)]
    lon0, lat0 = 120.23258, 30.22973
    phi = math.radians(lat0)
    a, e2 = 6378137.0, 6.6943799901413165e-3
    den = 1 - e2 * math.sin(phi)**2
    east = math.pi / 180 * a / math.sqrt(den) * math.cos(phi)
    north = math.pi / 180 * a * (1 - e2) / den**1.5
    rings = {}
    for way in chosen:
        geo = [[nodes[n]['lon'], nodes[n]['lat']] for n in way['nodes']]
        xy = [[(x-lon0)*east, (y-lat0)*north] for x, y in geo]
        area2 = cx = cy = 0.0
        for (x, y), (u, v) in zip(xy, xy[1:]):
            cross = x*v-u*y
            area2 += cross
            cx += (x+u)*cross
            cy += (y+v)*cross
        center = [cx/(3*area2), cy/(3*area2)]
        rings[way['id']] = {
            'id': way['id'], 'version': way['version'],
            'wayTimestamp': way['timestamp'],
            'nodeTimestamps': sorted({nodes[n]['timestamp'] for n in way['nodes']}),
            'tags': way['tags'], 'wgs84': geo, 'localMeters': xy,
            'centroidLocalMeters': center,
            'centroidWgs84': [lon0+center[0]/east, lat0+center[1]/north],
            'areaSquareMetres': abs(area2)/2,
        }
    west, east_tower = rings[1015040645], rings[1015040647]
    dx = east_tower['centroidLocalMeters'][0]-west['centroidLocalMeters'][0]
    dy = east_tower['centroidLocalMeters'][1]-west['centroidLocalMeters'][1]
    distance = math.hypot(dx, dy)
    u, v = [dx/distance, dy/distance], [-dy/distance, dx/distance]
    anchor = [(west['centroidWgs84'][i]+east_tower['centroidWgs84'][i])/2 for i in (0, 1)]
    for ring in rings.values():
        cx, cy = ring['centroidLocalMeters']
        local = [(x-cx, y-cy) for x, y in ring['localMeters'][:-1]]
        pu = [x*u[0]+y*u[1] for x, y in local]
        pv = [x*v[0]+y*v[1] for x, y in local]
        ring['towerAxisBoundsMeters'] = [min(pu), max(pu)]
        ring['frontAxisBoundsMeters'] = [min(pv), max(pv)]
        ring['towerAxisWidthMeters'] = max(pu)-min(pu)
        ring['frontAxisDepthMeters'] = max(pv)-min(pv)
        ring['localMetersFromAnchor'] = [[(x-anchor[0])*east, (y-anchor[1])*north]
                                       for x, y in ring['wgs84']]
    result = {
        'schemaVersion': 1, 'retrievedDate': '2026-10-12', 'crs': 'EPSG:4326',
        'sourceUrl': 'https://api.openstreetmap.org/api/0.6/map.json?bbox=120.230,30.227,120.234,30.231',
        'localMetricMethod': 'WGS84 ellipsoid radii at latitude 30.22973 deg; local east/north; polygon shoelace area centroid.',
        'projection': {'east_metres_per_degree': east, 'north_metres_per_degree': north},
        'anchorWgs84': anchor,
        'axis': {
            'westToEastUnitEN': u, 'frontNorthwestUnitEN': v,
            'bearingDegreesFromNorthClockwise': math.degrees(math.atan2(dx, dy)),
            'angleRadiansFromEastCounterclockwise': math.atan2(dy, dx),
            'centerSeparationMetres': distance,
            'innerEdgeGapMetres': distance-west['towerAxisBoundsMeters'][1]+east_tower['towerAxisBoundsMeters'][0],
        },
        'objects': list(rings.values()),
        'uncertainty': 'Measured on OSM data, not in the field. Source positional accuracy unknown. Provisional modelling allowances ±5m footprint/center and ±3deg orientation are planning tolerances, not observed confidence intervals. Output rounding and local projection approximation are much smaller than source uncertainty.',
        'snapshotSha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
    }
    parent = ROOT.parents[4] / 'data/processed/hangzhou/buildings.geojson'
    if parent.exists():
        features = [f for f in json.loads(parent.read_text())['features']
                    if f['properties']['osm_id'] in rings]
        assert len(features) == 3, 'Missing gate component in Geofabrik extraction'
        for feature in features:
            ring = feature['geometry']['coordinates'][0][0]
            assert set(map(tuple, ring)) == set(map(tuple, rings[feature['properties']['osm_id']]['wgs84']))
        subset = {'type': 'FeatureCollection', 'features': features}
        (ROOT/'geofabrik-gate-features.geojson').write_text(json.dumps(subset, ensure_ascii=False, indent=2)+'\n')
        result['geofabrikComparison'] = {
            'status': 'same vertex coordinates; cyclic ordering may differ',
            'parentPath': str(parent),
            'parentSha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
            'pbfPath': 'data/raw/hangzhou/zhejiang-261011.osm.pbf',
            'pbfSha256FromMainIntegration': '4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9',
            'osmSnapshotTimestamp': '2026-10-11T20:21:06Z',
        }
    (ROOT/'osm-footprints-and-measurements.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'anchor': anchor, 'axis': result['axis'],
                      'geofabrikCompared': 'geofabrikComparison' in result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
