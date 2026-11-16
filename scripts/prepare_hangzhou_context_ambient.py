"""Replace exact context roof owners in the frozen ambient-light raster.

Reproduce the entire old height/owner raster first, then replace selected IDs
with canonical footprints and actual exported model maximum heights. This keeps
the original 4-game-metre flat-envelope lighting approximation; it is neither
surveyed roof geometry nor a terrain/physics update.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import time
import numpy as np
from affine import Affine
from rasterio.features import rasterize
from city_config import load_city, project

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def model_bounds(file, identify):
    """Strict reader for these uncompressed, identity-node candidate exports."""
    raw = Path(file).read_bytes()
    assert raw[:4] == b'glTF' and struct.unpack_from('<II', raw, 4) == (2, len(raw))
    length, kind = struct.unpack_from('<II', raw, 12)
    assert kind == 0x4e4f534a
    doc = json.loads(raw[20:20 + length])
    off = 20 + length
    size, kind = struct.unpack_from('<II', raw, off)
    assert kind == 0x004e4942 and off + 8 + size == len(raw)
    binary = memoryview(raw)[off + 8:]
    assert not doc.get('extensionsRequired')
    assert len(doc['scenes']) == 1 and set(doc['scenes'][0]['nodes']) == set(range(len(doc['nodes'])))
    bounds = {}
    for node in doc['nodes']:
        assert not any(k in node for k in ('matrix', 'translation', 'rotation', 'scale', 'children', 'skin'))
        mesh = doc['meshes'][node['mesh']]
        identifier = identify(node, mesh)
        for primitive in mesh['primitives']:
            assert primitive.get('mode', 4) == 4
            a = doc['accessors'][primitive['attributes']['POSITION']]
            assert a['type'] == 'VEC3' and a['componentType'] == 5126 and not a.get('sparse')
            v = doc['bufferViews'][a['bufferView']]
            assert v.get('buffer', 0) == 0 and not v.get('extensions')
            values = np.ndarray((a['count'], 3), dtype='<f4', buffer=binary,
                                offset=v.get('byteOffset', 0) + a.get('byteOffset', 0),
                                strides=(v.get('byteStride', 12), 4))
            assert np.isfinite(values).all()
            enu = values[:, [0, 2, 1]].astype(np.float64)
            enu[:, 1] *= -1
            low, high = enu.min(axis=0), enu.max(axis=0)
            if identifier in bounds:
                low = np.minimum(low, bounds[identifier][0])
                high = np.maximum(high, bounds[identifier][1])
            bounds[identifier] = [low, high]
    return bounds


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--request', required=True)
    p.add_argument('--lingyin', required=True)
    p.add_argument('--west-lake', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    source, request, lingyin, west, out = [(ROOT / s).resolve() for s in
                                         (a.input, a.request, a.lingyin, a.west_lake, a.output)]
    if ROOT / 'artifacts/cities/hangzhou' not in out.parents or out.exists():
        raise ValueError('Fresh Hangzhou artifact directory required')
    began = time.monotonic()
    inputs = {}

    def bind(p):
        inputs[str(p.relative_to(ROOT))] = sha(p)
        return p

    original = read(bind(source / 'manifest.json'))
    assert original['cityId'] == 'hangzhou' and original['heightReference'] == 'terrain'
    for file, digest in original['files'].items():
        assert sha(bind(source / file)) == digest
    city_file = next(ROOT / f for f in original['inputs'] if f.endswith('/city.json'))
    floor_file = next(ROOT / f for f in original['inputs'] if f.endswith('/building-floors.json'))
    for file in (city_file, floor_file):
        assert sha(bind(file)) == original['inputs'][str(file.relative_to(ROOT))]
    city = read(city_file)
    floors = read(floor_file)
    floor_by_id = {}
    for floor in floors:
        floor_by_id.setdefault(floor['id'], []).append(floor)
    old = []
    for index, b in enumerate(city['buildings']):
        top = b.get('maxY', b['height'])
        matches = [f for f in floor_by_id.get(b['id'], []) if abs(f['mainRoofYGame'] - top) < 1e-7]
        if matches:
            top = max(f['visualMaximumYGame'] for f in matches)
        old.append(({'type': 'Polygon', 'coordinates': b['rings']}, top, index + 1, b['id']))
    grid = original['grid']
    width, height, cell, x0, z0 = [grid[k] for k in ('width', 'height', 'cell', 'minX', 'minZ')]
    shape = (height, width)
    transform = Affine(cell, 0, x0, 0, cell, z0)

    def raster(objects):
        ordered = sorted(objects, key=lambda o: o[1])
        heights = rasterize([(o[0], o[1]) for o in ordered], out_shape=shape,
                            transform=transform, dtype='float32', fill=0)
        owners = rasterize([(o[0], o[2]) for o in ordered], out_shape=shape,
                           transform=transform, dtype='int32', fill=0)
        return heights, owners

    old_heights = np.fromfile(source / 'heights.f32', dtype='<f4').reshape(shape)
    old_ids = np.fromfile(source / 'ids.i32', dtype='<i4').reshape(shape)
    replay_heights, replay_ids = raster(old)
    assert np.array_equal(replay_heights, old_heights) and np.array_equal(replay_ids, old_ids), 'Old raster provenance mismatch'
    del replay_heights, replay_ids
    requested = read(bind(request))
    excluded = set(requested['baseBuildingIdsToExclude'])
    assert excluded <= {o[3] for o in old}
    for file, digest in requested['contracts'].items():
        assert sha(bind(ROOT / file)) == digest, 'Context contract changed'

    contract = read(lingyin / 'integration-contract.json')
    lingyin_glb = bind(lingyin / contract['artifact'])
    assert sha(lingyin_glb) == contract['artifactSha256']
    spec = read(bind(lingyin / 'spec.json'))
    assert sha(lingyin / 'spec.json') == contract['specSha256']
    lb = model_bounds(lingyin_glb, lambda node, mesh: node['extras']['sourceEntityId'])
    mapping = {row['entityId']: row['sourceIds'] for row in contract['sourceEntityMapping']}
    assert set(lb) == set(mapping) and len(lb) == 30
    bind(ROOT / 'config/cities/hangzhou.json')
    bind(ROOT / 'scripts/city_config.py')
    configuration = load_city('hangzhou')
    source_features = read(bind(lingyin / 'source-footprints.geojson'))
    features = {f['id']: f for f in source_features['features']}
    replacements = []
    for identifier, bounds in lb.items():
        geo = features[identifier]['geometry']
        assert geo['type'] == 'MultiPolygon'
        polygons = [[[[*project(lon, lat, configuration)] for lon, lat in ring] for ring in polygon]
                    for polygon in geo['coordinates']]
        replacements.append({'id': identifier, 'sourceIds': mapping[identifier],
                             'geometry': {'type': 'MultiPolygon', 'coordinates': polygons},
                             'maxYGame': float(bounds[1][2]), 'model': str(lingyin_glb.relative_to(ROOT))})
    wc = read(west / 'integration-candidates.json')
    west_glb = bind(ROOT / wc['artifactPath'])
    assert sha(west_glb) == wc['artifactSha256']
    candidates = {row['sourceId']: row for row in wc['objects']}

    def west_id(node, mesh):
        matches = [identifier for identifier in candidates
                   if mesh['name'].startswith(candidates[identifier]['actualMeshPrefix'])]
        assert len(matches) == 1, mesh['name']
        return matches[0]

    wb = model_bounds(west_glb, west_id)
    assert set(wb) == set(candidates) and len(wb) == 7
    for identifier, bounds in wb.items():
        row = candidates[identifier]
        assert np.max(np.abs(np.array(row['actualModelBoundsENUGame']) - bounds)) < 1e-7
        replacements.append({'id': identifier, 'sourceIds': [identifier],
                             'geometry': {'type': 'Polygon', 'coordinates': row['footprintGame']},
                             'maxYGame': float(bounds[1][2]), 'model': str(west_glb.relative_to(ROOT))})
    replaced_sources = {identifier for r in replacements for identifier in r['sourceIds']}
    assert replaced_sources == excluded | set(wc['proposedRestoredSourceIds'])
    new = [o for o in old if o[3] not in excluded]
    for i, r in enumerate(replacements):
        r['rasterOwner'] = len(old) + i + 1
        new.append((r['geometry'], r['maxYGame'], r['rasterOwner'], r['id']))
    new_heights, new_ids = raster(new)
    selected_old_ids = [o[2] for o in old if o[3] in excluded]
    selected_new_ids = [r['rasterOwner'] for r in replacements]
    domain = np.isin(old_ids, selected_old_ids) | np.isin(new_ids, selected_new_ids)
    assert np.array_equal(old_ids[~domain], new_ids[~domain])
    assert np.array_equal(old_heights[~domain], new_heights[~domain])
    changed = (new_ids != old_ids) | (new_heights != old_heights)
    out.mkdir(parents=True)
    new_heights.astype('<f4').tofile(out / 'heights.f32')
    new_ids.astype('<i4').tofile(out / 'ids.i32')
    changed.astype('u1').tofile(out / 'changed.u8')
    for name in ('ground.f32', 'ground.u8'):
        shutil.copy2(source / name, out / name)
        assert sha(out / name) == original['files'][name]
    report = {
        'cityId': 'hangzhou', 'kind': 'context-height ambient candidate input',
        'grid': grid, 'heightReference': original['heightReference'],
        'groundRange': original['groundRange'],
        'groundAlphaQuantizationErrorGame': original['groundAlphaQuantizationErrorGame'],
        'groundPolicy': 'inherited frozen receiver raster, byte-identical; not a terrain update',
        'inputs': inputs, 'scriptSha256': sha(__file__),
        'sourceRasterReplayExact': True, 'unrelatedRasterCellsExact': True,
        'changedCells': int(changed.sum()), 'sourceIdsRemoved': sorted(excluded),
        'replacementEnvelopes': replacements, 'files': {f.name: sha(f) for f in out.iterdir()},
        'seconds': time.monotonic() - began,
        'approximation': 'same 4-game-metre canonical-footprint / flat maximum-roof envelope as original AO',
        'status': 'offline input only; horizon bake and runtime visual acceptance pending',
    }
    (out / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('sourceRasterReplayExact', 'unrelatedRasterCellsExact', 'changedCells', 'seconds')}, indent=2))


if __name__ == '__main__':
    main()
