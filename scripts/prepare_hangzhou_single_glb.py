"""Prepare one existing, byte-exact terrain tile; never decode or launch a GPU."""
import argparse
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
TILE_ID = 'terrain:-21,-13'
TILE_SHA = '57fc2aa45c190ee55c5601c5d76737a26c02f341057c6236eefcd09fd51db87e'


def checked(path, record, limit):
    if not 0 < record['bytes'] <= limit or path.stat().st_size != record['bytes']:
        raise ValueError('Unexpected asset size: ' + str(path))
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('Asset hash differs: ' + str(path))
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    if args.root.exists():
        raise SystemExit('Use a fresh candidate directory.')
    release = json.loads((PROJECT / 'artifacts/cities/hangzhou/stream-release-v1/descriptor.json').read_text())
    source = release['models']['terrain']
    manifest_path = PROJECT / source['manifestPath']
    manifest = json.loads(checked(manifest_path, {'bytes': source['manifestBytes'], 'sha256': source['manifestSha256']}, 256 * 1024))
    if manifest['source']['sha256'] != source['sourceSha256']:
        raise ValueError('Source identity differs.')
    tiles = [t for t in manifest['tiles'] if t['id'] == TILE_ID]
    if len(tiles) != 1 or tiles[0]['sha256'] != TILE_SHA:
        raise ValueError('The fixed P2 tile is missing or changed.')
    tile = tiles[0]
    if tile['triangles'] != 228 or tile['logicalBytes'] != 5848 or tile['nodes'] != 1:
        raise ValueError('Unexpected P2 geometry cost.')
    textures = manifest['textures']
    if len(textures) != 1 or textures[0]['file'] != 'textures/terrain-0.jpg':
        raise ValueError('Unexpected texture set.')
    files = {tile['file']: checked(manifest_path.parent / tile['file'], tile, 8192)}
    files[textures[0]['file']] = checked(manifest_path.parent / textures[0]['file'], textures[0], 128 * 1024)
    decoder = PROJECT / 'public/city/meshopt_decoder.js'
    if not 0 < decoder.stat().st_size <= 128 * 1024:
        raise ValueError('Unexpected local decoder size.')
    files['meshopt_decoder.js'] = decoder.read_bytes()
    fixture = {'tile': {**tile, 'role': 'terrain'}, 'textures': textures,
               'sourceSha256': source['sourceSha256'], 'manifestSha256': source['manifestSha256'],
               'limits': {'canvasWidth': 320, 'canvasHeight': 200, 'renderFrames': 3, 'deadlineMs': 25000}}
    args.root.mkdir(parents=True)
    for name, data in files.items():
        target = args.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (args.root / 'fixture.json').write_text(json.dumps(fixture, indent=2) + '\n')
    (args.root / 'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>杭城之行 · 单块地形验证</title><link rel="stylesheet" href="/single-glb.css"><main><p>GTA_HZ · 受控诊断 P2</p><h1>单块地形加载与释放</h1><p>仅一块228面地形及配套贴图。不会载入城市、车辆或任务。手动开始后最多25秒自动释放；这不是可玩体验版。</p><button id="run">开始一次单块验证</button><button id="stop" disabled>停止并释放</button><canvas id="view" width="320" height="200" aria-label="单块地形预览"></canvas><pre id="result" role="status">等待手动开始。页面不会自动创建三维上下文。</pre></main><script type="module" src="/single-glb.js"></script></html>''', encoding='utf-8')
    (args.root / 'single-glb.css').write_text('body{font:16px system-ui;background:#122128;color:#edf4f5;margin:0}main{max-width:700px;margin:32px auto;padding:24px}button{padding:10px 18px;margin:8px 8px 16px 0;font:inherit}canvas{display:block;width:320px;height:200px;background:#20343e;max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#20343e;padding:16px;line-height:1.5}h1{font-size:28px}', encoding='utf-8')
    report = {'preparedOnly': True, 'browserValidated': False, 'sourceSha256': source['sourceSha256'],
              'tile': tile, 'textures': textures, 'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files.items()},
              'requiresManualStart': True, 'limits': fixture['limits']}
    (args.root / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
