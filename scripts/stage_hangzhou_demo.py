"""Prepare an isolated, explicitly interim Hangzhou build for local playtesting."""
import argparse
import json
from pathlib import Path
import re
import shutil

from hangzhou_surface import digest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts/cities/hangzhou'
ASSEMBLY = ROOT / 'docs/hangzhou/audit/xianfu-underpass-repair-20261111/runtime-assembly-readiness-v1/assembly-order.json'
ENTRY = ROOT / 'docs/hangzhou/audit/grand-theatre-entry-20261111'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')


def stage(output):
    if ARTIFACTS not in output.parents or output.exists():
        raise ValueError('Use a fresh Hangzhou demo directory')
    runtime = output / 'public/cities/hangzhou'
    sources = {}

    def copy(source, destination, expected=None):
        with source.open('rb') as f:
            if f.read(64).startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise ValueError(f'Git LFS payload missing: {source}')
        checksum = digest(source)
        if expected and checksum != expected:
            raise ValueError(f'Changed asset: {source}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        sources[str(destination.relative_to(output))] = {'source': str(source.relative_to(ROOT)), 'sha256': checksum}

    base = ARTIFACTS / 'render-input-v6'
    model_manifest = read(ARTIFACTS / 'base-meshopt-v5/asset-manifest.json')
    render_manifest = ROOT / model_manifest['sourceManifest']
    if digest(render_manifest) != model_manifest['sourceManifestSha256']:
        raise ValueError('Base render manifest drift')
    render = read(render_manifest)
    for file in [base / 'city.json', base / 'geography/manifest.json']:
        if render['inputs'][str(file.relative_to(ROOT))] != digest(file):
            raise ValueError(f'Base render and geography disagree: {file}')

    for item in read(ASSEMBLY)['copyPlan']:
        target = item['destinationRelativeToRuntimeRoot']
        if target in {'city.json', 'navigation.json', 'geography/', 'landmark-detail.glb', 'landmark-detail.json'}:
            continue
        pattern = item['source']
        if '*' not in pattern:
            copy(ROOT / pattern, runtime / target, item.get('sha256'))
            continue
        prefix = pattern.split('*', 1)[0].rsplit('/', 1)[0]
        paths = sorted(file for file in ROOT.glob(pattern) if file.is_file())
        if not paths:
            raise ValueError(f'No assets for {pattern}')
        for source in paths:
            destination = target.split('*', 1)[0] if '*' in target else target
            copy(source, runtime / destination / source.relative_to(ROOT / prefix))

    for directory in ['assets', 'licenses', 'characters']:
        for file in sorted((ROOT / 'public' / directory).rglob('*')):
            if file.is_file():
                copy(file, output / 'public' / file.relative_to(ROOT / 'public'))
    copy(ROOT / 'public/favicon.svg', output / 'public/favicon.svg')
    copy(ROOT / 'LICENSE', output / 'public/LICENSE')
    for file in sorted((ROOT / 'public/city/textures').iterdir()):
        if file.is_file() and not file.name.startswith('sign-'):
            copy(file, runtime / 'textures' / file.name)
    for file in sorted((ROOT / 'public/cities/hangzhou/loading').iterdir()):
        if file.is_file():
            copy(file, runtime / 'loading' / file.name)
    for file in sorted((ARTIFACTS / 'meadow-v2').glob('meadow/**/*')):
        if file.is_file():
            copy(file, runtime / 'grassland-v2' / file.relative_to(ARTIFACTS / 'meadow-v2'))
    copy(ARTIFACTS / 'meadow-v2/meadow.json', runtime / 'grassland-v2/meadow.json')

    city = read(base / 'city.json')
    buildings_file = render_manifest.parent / render['buildingsFile']
    if digest(buildings_file) != render['buildingsSha256']:
        raise ValueError('Changed base building floors')
    floors = {(b['id'], json.dumps(b['rings'])): b for b in read(buildings_file)}
    for building in city['buildings']:
        if building['style'] != 'landmark-detail':
            floor = floors[(building['id'], json.dumps(building['rings']))]
            building.update(minY=floor['minY'], maxY=floor['maxY'])
    city['meta']['status'] = 'Hangzhou local preview using prepared v6 base geography'
    write(runtime / 'city.json', city)

    geo = read(base / 'geography/manifest.json')
    for file_key, hash_key in [('terrainFile', 'terrainSha256'), ('roadLevelsFile', 'roadLevelsSha256')]:
        filename = geo[file_key]
        copy(base / 'geography' / filename, runtime / 'geography' / filename, geo[hash_key])
    walk_surfaces = read(ENTRY / 'candidate-walk-site.json')
    if walk_surfaces.get('terrainCuts') or walk_surfaces.get('terrainPatches') or walk_surfaces.get('roadSurfaces'):
        raise ValueError('Theatre append must not modify v6 physical ground or roads')
    write(runtime / 'geography/site-surfaces.json', walk_surfaces)
    geo.update(siteSurfacesFile='site-surfaces.json', siteSurfacesSha256=digest(runtime / 'geography/site-surfaces.json'))
    write(runtime / 'geography/manifest.json', geo)

    navigation = read(ARTIFACTS / 'render-input-v7/navigation.json')
    for road in city['roads']:
        chain = navigation['roadNodes'][road['id']]
        if len(chain) != len(road['heights']):
            raise ValueError(f"Navigation chain length mismatch: {road['id']}")
        if any(navigation['nodes'][i] != point or navigation['nodeHeights'][i] != height or str(navigation['sourceNodeIds'][i]) != str(node)
               for i, point, height, node in zip(chain, road['points'], road['heights'], road['nodeIds'])):
            raise ValueError(f"Navigation and demo source road disagree: {road['id']}")
    navigation['meta']['roadLevelsSha256'] = geo['roadLevelsSha256']
    write(runtime / 'navigation.json', navigation)

    detail_dir = ARTIFACTS / 'landmark-packet-v6'
    detail_report = read(detail_dir / 'report.json')
    for filename, expected in detail_report['files'].items():
        if digest(detail_dir / filename) != expected:
            raise ValueError(f'Changed detail packet: {filename}')
    detail = read(detail_dir / 'landmark-detail.json')
    detail['terrain']['manifestSha256'] = digest(runtime / 'geography/manifest.json')
    detail['collisionFootprints'] = [f for f in detail['collisionFootprints'] if not f['id'].startswith(('xianfu:', 'qiantang-bridges:'))]
    entry = read(ENTRY / 'integration-contract.json')
    copy(ROOT / entry['newAsset'], runtime / 'landmarks.glb', entry['newAssetSha256'])
    detail['requiredStructuralAssets'] = [{'role': 'landmarks', 'sourceFile': entry['newAsset'], 'sha256': entry['newAssetSha256']}]
    detail['status'] = 'demo: v6 base and selected detail; updated bridge and underpass collision reserved for integrated world'
    write(runtime / 'landmark-detail.json', detail)
    copy(detail_dir / 'landmark-detail.glb', runtime / 'landmark-detail.glb', detail_report['files']['landmark-detail.glb'])
    bridge = ARTIFACTS / 'coastal-bridges-v1'
    bridge_asset = read(bridge / 'asset-manifest.json')['assets'][0]
    copy(bridge / bridge_asset['file'], runtime / 'coastal-bridges.glb', bridge_asset['sha256'])

    shutil.copytree(ROOT / 'src', output / 'src')
    profiles = output / 'src/city-profiles.generated.ts'
    value = profiles.read_text()
    value, count = re.subn(r'export const ACTIVE_CITY_ID="shenzhen" as const;', 'export const ACTIVE_CITY_ID="hangzhou" as const;', value)
    if count != 1:
        raise ValueError('Active profile source changed')
    profiles.write_text(value.replace('"gta-hz', '"gta-hz-demo'))
    for name in ['vite.config.ts', 'tsconfig.json']:
        shutil.copy2(ROOT / name, output / name)
    html = (ROOT / 'index.html').read_text().replace('</body>', '<span style="position:fixed;right:12px;bottom:8px;z-index:30;color:#fff;background:#153e36;padding:4px 8px;border-radius:4px;font:12px system-ui;pointer-events:none">杭州体验版</span></body>')
    (output / 'index.html').write_text(html)

    limitations = ['v6 base road and terrain. Latest structural work is visible on named bridges, with known bridge deck differences.',
                   'New Xianfu underpass, balcony cuts and source road profiles still need integrated render layers.',
                   'Some landmark bases and entrances are unfinished. Browser gameplay, visual and performance acceptance pending.',
                   'Grass masks retain v10 exclusions. Bridge-area slope sampling may differ from this v6 terrain.']
    generated = ['city.json', 'navigation.json', 'geography/manifest.json', 'geography/site-surfaces.json', 'landmark-detail.json']
    write(output / 'public/demo-manifest.json', {'city': 'hangzhou', 'kind': 'interim local preview', 'base': 'render-input-v6 / base-meshopt-v5', 'files': sources,
          'generated': {filename: digest(runtime / filename) for filename in generated}, 'limitations': limitations, 'browserVerified': False})
    print(f'Staged {len(sources)} verified files in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    stage((ROOT / parser.parse_args().output).resolve())
