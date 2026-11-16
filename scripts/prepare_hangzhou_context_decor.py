"""Remove obsolete context-building decorations using exact source ownership.

The old roof plan has no source IDs. Recover them through the frozen accepted
proposal ledger, verifying every instance before filtering. Re-rasterize roof
finishes in original height order so overlapping neighbours are revealed, not
erased. Outputs stay in a fresh candidate; no runtime city is changed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
import rasterio
from pack_hangzhou_ambient import png

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def fill(rings, value, grid, lookup):
    """Mirror rasterizeRing's scanline/JS Math.round, including all holes."""
    h, w = grid.shape
    x0, z0, cell = (lookup[k] for k in ('minX', 'minZ', 'cell'))
    rows = [(p[1] - z0) / cell for p in rings[0]]
    for row in range(max(0, math.floor(min(rows))), min(h - 1, math.ceil(max(rows))) + 1):
        z = z0 + (row + .5) * cell
        xs = []
        for ring in rings:
            for a, b in zip(ring, ring[1:]):
                if (a[1] <= z < b[1]) or (b[1] <= z < a[1]):
                    xs.append(a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            c0 = max(0, math.floor((xs[i] - x0) / cell + .5))
            c1 = min(w - 1, math.floor((xs[i + 1] - x0) / cell + .5) - 1)
            if c1 >= c0:
                grid[row, c0:c1 + 1] = value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--city-root', required=True)
    p.add_argument('--request', required=True)
    p.add_argument('--proposals', required=True)
    p.add_argument('--validated', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    city, request, proposals, validated, out = [
        (ROOT / value).resolve() for value in
        (a.city_root, a.request, a.proposals, a.validated, a.output)]
    if ROOT / 'artifacts/cities/hangzhou' not in out.parents or out.exists():
        raise ValueError('Fresh Hangzhou artifact output required')
    began = time.monotonic()
    inputs = {}

    def bind(file):
        inputs[str(file.relative_to(ROOT))] = sha(file)
        return file

    requested = read(bind(request))
    ids = set(requested['baseBuildingIdsToExclude'])
    assert ids and len(ids) == len(requested['baseBuildingIdsToExclude'])
    raw = read(bind(proposals / 'unverified-plan.json'))
    manifest = read(bind(validated / 'manifest.json'))
    assert raw['cityId'] == manifest['cityId'] == 'hangzhou'
    for name, record in manifest['files'].items():
        assert sha(bind(validated / name)) == record['sha256'], name
    for name, digest in raw['inputs'].items():
        assert sha(bind(ROOT / name)) == digest, 'Changed proposal input: ' + name
    buildings = read(ROOT / raw['source'])
    assert ids <= {b['id'] for b in buildings}, 'Missing old source ID'
    ledger = read(validated / 'support-audit.json')
    plan_path = bind(city / 'rooftops/plan.json')
    assert sha(plan_path) == manifest['files']['plan.json']['sha256']
    plan = read(plan_path)
    assert plan['lookup'] == raw['lookup']
    groups = {g['kind']: g for g in plan['groups']}
    assert len(groups) == len(plan['groups'])
    seen, removed, kept_ownership = set(), [], []
    remove_at = {kind: set() for kind in groups}
    for entry in ledger['accepted']:
        proposal = raw['proposals'][entry['proposal']]
        assert entry['buildingIndex'] == proposal['buildingIndex']
        assert entry['kind'] == proposal['kind']
        key = (entry['kind'], entry['groupIndex'])
        assert key not in seen
        seen.add(key)
        instance = groups[key[0]]['instances'][key[1]]
        assert instance == proposal['instance'], 'Accepted ledger does not match served instance'
        source_id = buildings[entry['buildingIndex']]['id']
        record = {'buildingId': source_id, 'kind': key[0], 'oldGroupIndex': key[1],
                  'proposal': entry['proposal'], 'instance': instance}
        if source_id in ids:
            remove_at[key[0]].add(key[1])
            removed.append(record)
        else:
            kept_ownership.append(record)
    assert seen == {(g['kind'], i) for g in plan['groups'] for i in range(len(g['instances']))}
    before = sum(len(g['instances']) for g in plan['groups'])
    for group in plan['groups']:
        assert group['count'] == len(group['instances'])
        group['instances'] = [v for i, v in enumerate(group['instances']) if i not in remove_at[group['kind']]]
        group['count'] = len(group['instances'])
    after = sum(g['count'] for g in plan['groups'])
    assert before - after == len(removed)
    for kind, group in groups.items():
        original = [r['instance'] for r in sorted((r for r in kept_ownership if r['kind'] == kind), key=lambda r: r['oldGroupIndex'])]
        assert original == group['instances'], 'Retained transforms/order changed'

    lookup = raw['lookup']
    lookup_path = bind(city / 'rooftops/building-lookup.png')
    assert sha(lookup_path) == manifest['files']['building-lookup.png']['sha256']
    with rasterio.open(lookup_path) as dataset:
        old_png = dataset.read(1)
    shape = (lookup['height'], lookup['width'])
    assert old_png.shape == shape and old_png.dtype == np.uint8
    old_grid, new_grid = np.zeros(shape, np.uint8), np.zeros(shape, np.uint8)
    owners = np.zeros(shape, np.int32)
    finishes = sorted(raw['finishes'], key=lambda f: buildings[f['buildingIndex']]['maxY'])
    for f in finishes:
        index = f['buildingIndex']
        building = buildings[index]
        value = 1 + f['finish'] * 16 + f['tint']
        fill(building['rings'], value, old_grid, lookup)
        fill(building['rings'], index + 1, owners, lookup)
        if building['id'] not in ids:
            fill(building['rings'], value, new_grid, lookup)
    assert np.array_equal(old_grid, old_png), 'Scanline reconstruction differs from frozen PNG'
    selected_indices = [i + 1 for i, b in enumerate(buildings) if b['id'] in ids]
    selected_mask = np.isin(owners, selected_indices)
    assert np.array_equal(new_grid[~selected_mask], old_png[~selected_mask]), 'Unrelated lookup cells changed'

    signs_file = bind(city / 'building-signs.json')
    signs = read(signs_file)
    removed_signs = [s for s in signs['signs'] if s['buildingId'] in ids]
    signs['signs'] = [s for s in signs['signs'] if s['buildingId'] not in ids]
    signs['previousStats'] = signs.pop('stats')
    signs['stats'] = {
        'selectedCount': len(signs['signs']),
        'realNameSigns': sum(s['kind'] == 'osm-building-name' for s in signs['signs']),
        'fictionalBusinessSigns': sum(s['kind'] != 'osm-building-name' for s in signs['signs']),
        'orientations': dict(Counter(s['orientation'] for s in signs['signs'])),
        'fonts': dict(Counter(s['font'] for s in signs['signs'])),
        'contextExcludedSignCount': len(removed_signs),
        'basis': 'current retained signs; source-city coverage statistics preserved in previousStats',
    }
    provenance = {'requestSha256': sha(request), 'excludedBuildingIds': sorted(ids),
                  'basis': 'exact source-ID ownership; replacement signage belongs to authored models'}
    plan['contextExclusion'] = provenance
    signs['contextExclusion'] = provenance
    out.mkdir(parents=True)
    (out / 'rooftops').mkdir()
    (out / 'rooftops/plan.json').write_text(json.dumps(plan, separators=(',', ':')))
    (out / 'rooftops/building-lookup.png').write_bytes(png(new_grid[:, :, None]))
    (out / 'building-signs.json').write_text(json.dumps(signs, ensure_ascii=False, separators=(',', ':')))
    with rasterio.open(out / 'rooftops/building-lookup.png') as dataset:
        assert np.array_equal(dataset.read(1), new_grid), 'PNG encoding changed lookup'
    for name, digest in inputs.items():
        assert sha(ROOT / name) == digest, 'Input changed during candidate preparation'
    report = {
        'kind': 'source-owned context decoration exclusion candidate', 'pass': True,
        'inputs': inputs, 'scriptSha256': sha(__file__), 'sourceIds': sorted(ids),
        'roofProps': {'before': before, 'after': after, 'removed': removed,
                      'retainedExactTransformsAndOrder': True, 'acceptedLedgerComplete': True},
        'roofLookup': {'sourcePixelParity': True, 'selectedOwnerCells': int(selected_mask.sum()),
                       'changedPixels': int(np.count_nonzero(old_png != new_grid)),
                       'revealedUnderlyingBuildingPixels': int(np.count_nonzero(selected_mask & (new_grid != 0))),
                       'unrelatedPixelsUnchanged': True},
        'signs': {'removed': removed_signs, 'retained': len(signs['signs'])},
        'files': {str(f.relative_to(out)): {'bytes': f.stat().st_size, 'sha256': sha(f)}
                  for f in out.rglob('*') if f.is_file()},
        'seconds': time.monotonic() - began,
        'pending': ['AO raster update', 'old collision removal and replacement physics',
                    'replacement GLB and contact geometry', 'browser visual/night/performance'],
        'browserAccepted': False,
    }
    (out / 'decor-exclusion-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pass': True, 'sourceIds': len(ids), 'removedRoofProps': len(removed),
                      'removedSigns': len(removed_signs), 'lookup': report['roofLookup'],
                      'seconds': report['seconds']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
