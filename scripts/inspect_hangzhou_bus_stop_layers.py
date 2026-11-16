"""Small source-layer inventory for three physically ambiguous bus platforms.

Reads one already bounded road-level shard at a time. No Blender import,
geometry mutation, nearest-level selection or acceptance claim.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/cities/hangzhou/bus-route-7-v2'


def main():
    target = BASE / 'station-layer-context-v1.json'
    if target.exists():
        raise SystemExit('Choose a fresh report')
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    probes = []
    for batch in (0, 1):
        for row in read(BASE / ('platform-ground-batch-%d-layers-v1.json' % batch))['results']:
            if not row['ambiguities']:
                continue
            probes.append({'id': row['id'], 'name': row['name'],
                           'sourceStopId': row['sourceStopId'],
                           'sourcePlatformGame': row['sourcePlatformGame'],
                           'ambiguities': row['ambiguities'], 'nearbyRoads': []})
    folder = ROOT / 'artifacts/cities/hangzhou/stream-data-v1/road-levels'
    manifest = read(folder / 'manifest.json')
    for array in manifest['arrays']:
        if array['key'] != 'roads':
            continue
        for chunk in array['chunks']:
            path = folder / chunk['file']
            data = read(path)
            assert hashes[str(path.relative_to(ROOT))] == chunk['sha256']
            for road in data['values']:
                points = road['points']
                for probe in probes:
                    x, z = probe['sourcePlatformGame']
                    nearby = []
                    for i, (a, b) in enumerate(zip(points, points[1:])):
                        dx, dz = b[0] - a[0], b[1] - a[1]
                        length2 = dx * dx + dz * dz
                        if length2 == 0:
                            continue
                        t = max(0, min(1, ((x-a[0])*dx+(z-a[1])*dz) / length2))
                        distance = math.hypot(x-a[0]-dx*t, z-a[1]-dz*t)
                        if distance > road['width']/2 + 8:
                            continue
                        nearby.append({'segment': i, 'fraction': t, 'distance': distance,
                                       'sourceHeight': road['heights'][i]*(1-t)+road['heights'][i+1]*t,
                                       'nodeIds': road['nodeIds'][i:i+2]})
                    if nearby:
                        item = {key: road.get(key) for key in ('id', 'name', 'grade', 'tier', 'bridge', 'tunnel', 'width', 'heightBasis')}
                        item['segments'] = nearby
                        probe['nearbyRoads'].append(item)
    result = {'scope': 'source identity context, not a selected physical surface',
              'inputs': hashes, 'probes': probes, 'installable': False}
    with target.open('x') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(json.dumps({'probes': len(probes), 'output': str(target.relative_to(ROOT)),
                      'roadCounts': [len(p['nearbyRoads']) for p in probes]}))


if __name__ == '__main__':
    main()
