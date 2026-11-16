"""Check actual packed lighting pixels and locality against the served bake."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def pixels(p):
    with rasterio.open(p) as ds:
        return ds.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    reference, candidate, source, output = [(ROOT / p).resolve() for p in
                                          (args.reference, args.candidate, args.input, args.output)]
    assert ROOT / 'docs/hangzhou/audit' in output.parents and not output.exists()
    manifest = read(candidate / 'manifest.json')
    for name, record in manifest['files'].items():
        assert sha(candidate / name) == record['sha256'], name
    meta = read(reference / 'occlusion.json')
    assert meta == read(candidate / 'occlusion.json'), 'Sampler/grid/receiver policy changed'
    assert sha(reference / 'ground-height.png') == sha(candidate / 'ground-height.png'), 'Receiver ground changed'
    original = ROOT / 'artifacts/cities/hangzhou/ambient-runtime-v1'
    old_report = read(original / 'manifest.json')
    for name in ('occlusion.json', 'occlusion.png', 'ground-height.png'):
        assert sha(reference / name) == old_report['files'][name]['sha256'], 'Served reference provenance changed'
    algorithm = 'src/city-ambient-bake.ts'
    assert sha(ROOT / algorithm) == old_report['inputs'][algorithm], 'Original horizon algorithm changed'
    prepared = read(source / 'manifest.json')
    assert sha(source / 'changed.u8') == prepared['files']['changed.u8']
    h, w = meta['height'], meta['width']
    changed = np.fromfile(source / 'changed.u8', dtype='u1').reshape(h, w).astype(bool)
    assert int(changed.sum()) == prepared['changedCells']
    reach = meta['reachMetres'] / meta['cell']
    assert reach == 50
    influence = np.zeros((h, w), dtype=bool)
    for r, c in zip(*np.nonzero(changed)):
        influence[max(0, r - 50):min(h, r + 51), max(0, c - 50):min(w, c + 51)] = True
    before, after = pixels(reference / 'occlusion.png'), pixels(candidate / 'occlusion.png')
    assert before.shape == after.shape == (3, h, w)
    delta = after.astype(np.int16) - before.astype(np.int16)
    altered = np.any(delta != 0, axis=0)
    assert np.array_equal(before[:, ~influence], after[:, ~influence]), 'Distant lighting pixels changed'
    assert altered.any(), 'No change despite removed high-rise shadows'
    record = {
        'pass': True, 'scope': 'actual opaque RGB bake; no browser or measured illumination claim',
        'inputs': {str(p.relative_to(ROOT)): sha(p) for p in
                   (source / 'manifest.json', candidate / 'manifest.json', reference / 'occlusion.png',
                    reference / 'occlusion.json', ROOT / algorithm)},
        'scriptSha256': sha(__file__), 'changedRoofRasterCells': int(changed.sum()),
        'possibleInfluenceCells': int(influence.sum()), 'changedLightingPixels': int(altered.sum()),
        'lighterChannelValues': int((delta > 0).sum()), 'darkerChannelValues': int((delta < 0).sum()),
        'maxChannelDelta': int(np.abs(delta).max()),
        'outsideOriginal200GameMetreReachExact': True, 'receiverGroundBytesExact': True,
        'samplerMetadataExact': True, 'originalAlgorithmExact': True,
        'pending': ['physical terrain/entry integration', 'current-asset daytime/nighttime visual inspection'],
    }
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k not in ('inputs', 'pending')}, indent=2))


if __name__ == '__main__':
    main()
