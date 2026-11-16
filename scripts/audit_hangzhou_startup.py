"""Read GLB JSON headers only. Never decode meshes, create a scene, or use a GPU."""
import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path


def inspect_glb(path):
    with path.open('rb') as stream:
        header = stream.read(20)
        magic, version, length, json_length, kind = struct.unpack('<5I', header)
        if magic != 0x46546C67 or version != 2 or kind != 0x4E4F534A:
            raise ValueError(f'Invalid GLB: {path}')
        if length != path.stat().st_size or json_length > 16 * 1024 * 1024:
            raise ValueError(f'GLB size/header limit: {path}')
        raw = stream.read(json_length)
        document = json.loads(raw)
    triangles = 0
    for mesh in document.get('meshes', []):
        for primitive in mesh['primitives']:
            if primitive.get('mode', 4) != 4:
                raise ValueError('Non-triangle primitive requires a separate budget')
            accessor = primitive.get('indices', primitive['attributes']['POSITION'])
            triangles += document['accessors'][accessor]['count'] // 3
    return {'path': path.name, 'bytes': length, 'headerBytes': json_length,
            'headerSha256': hashlib.sha256(raw).hexdigest(),
            'triangles': triangles, 'meshes': len(document.get('meshes', [])),
            'logicalBufferViewBytes': sum(v['byteLength'] for v in document.get('bufferViews', [])),
            'meshoptViews': sum('EXT_meshopt_compression' in v.get('extensions', {}) for v in document.get('bufferViews', []))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit('Preserve existing evidence; choose a new output.')
    names = ['terrain.glb', 'roads.glb', 'buildings.glb', 'landmark-detail.glb', 'landmarks.glb']
    meshes = [inspect_glb(args.city_root / name) for name in names]
    data = {'schemaVersion': 1, 'candidate': args.city_root.parent.parent.name,
            'createdAtUTC': datetime.now(timezone.utc).isoformat(), 'cityRoot': str(args.city_root),
            'inspection': 'JSON headers only; no GLB binary payload read/decode and no browser/GPU',
            'meshes': meshes,
            'totals': {key: sum(m[key] for m in meshes) for key in ['bytes', 'triangles', 'logicalBufferViewBytes', 'meshes']},
            'jsonBytes': {name: (args.city_root / name).stat().st_size for name in [
                'city.json', 'geography/road-levels.json', 'landscape/planting.json',
                'landscape/canopy-trees.json', 'rooftops/plan.json']},
            'limits': {'perAssetBytes': 32 * 1024 * 1024, 'startupMeshBytes': 96 * 1024 * 1024,
                       'logicalBufferViewBytes': 256 * 1024 * 1024, 'triangles': 2_000_000,
                       'perJsonBytes': 16 * 1024 * 1024},
            'limitations': ['Core meshes are a lower bound: excludes facades, props, textures, HDR, JS objects, copies and GPU allocation.',
                           'Logical buffer-view bytes are declared logical data, not measured peak memory.',
                           'Conservative temporary stop thresholds, not a hardware capacity certification.',
                           'The watchdog root cause and full-scene stability are unconfirmed.']}
    limit = data['limits']
    violations = [m['path'] + ': encoded asset exceeds 32 MiB' for m in meshes if m['bytes'] > limit['perAssetBytes']]
    violations += [f'total {key} exceeds startup limit' for key in ['triangles', 'logicalBufferViewBytes'] if data['totals'][key] > limit[key]]
    if data['totals']['bytes'] > limit['startupMeshBytes']:
        violations.append('total encoded mesh bytes exceeds startup limit')
    violations += [name + ': JSON exceeds 16 MiB' for name, size in data['jsonBytes'].items() if size > limit['perJsonBytes']]
    data['budget'] = {'allowed': not violations, 'violations': violations}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'totals': data['totals'], 'budget': data['budget']}))


if __name__ == '__main__':
    main()
