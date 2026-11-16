"""Bind a built Bai-route preview to its actual files; preserve inherited provenance."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', type=Path)
    parser.add_argument('--browser-report', type=Path)
    args = parser.parse_args()
    stage = args.stage
    manifest = stage / 'public/demo-manifest.json'
    backup = stage / ('demo-manifest.inherited-' + stage.name + '.json')
    if backup.exists():
        raise SystemExit('Already finalized: preserve this release; use a fresh candidate.')
    original = manifest.read_bytes()
    data = json.loads(original)
    if data.get('candidate') == stage.name and data.get('finalizedAtUTC'):
        raise SystemExit('Release manifest is already finalized.')
    if not (stage / 'dist/index.html').exists():
        raise SystemExit('Build the candidate before binding its release manifest.')
    changes = {
        'terrain.glb': 'scripts/clip_hangzhou_bai_base.mjs',
        'roads.glb': 'scripts/clip_hangzhou_bai_base.mjs',
        'map-places.json': 'scripts/apply_hangzhou_access_arrivals.py',
        'landmark-detail.glb': 'scripts/integrate_hangzhou_bai_models.mjs',
    }
    changed = []
    for name, entry in data['files'].items():
        actual = sha(stage / name)
        if actual != entry['sha256']:
            leaf = Path(name).name
            if leaf not in changes:
                raise SystemExit(f'Unexpected inherited asset change: {name}')
            changed.append(name)
            data['files'][name] = {
                'sha256': actual,
                'previousOrigin': entry,
                'derivationScript': changes[leaf],
                'derivationScriptSha256': sha(changes[leaf]),
            }
        # The served build must contain the exact public asset audited above.
        if sha(stage / 'dist' / Path(name).relative_to('public')) != actual:
            raise SystemExit(f'Build/public asset mismatch: {name}')
    old_generated = data['generated']
    data['previousGenerated'] = old_generated
    data['generated'] = {}
    for name in old_generated:
        actual = sha(stage / 'public/cities/hangzhou' / name)
        if sha(stage / 'dist/cities/hangzhou' / name) != actual:
            raise SystemExit(f'Build/public generated mismatch: {name}')
        data['generated'][name] = actual
    data['candidate'] = stage.name
    data['finalizedAtUTC'] = datetime.now(timezone.utc).isoformat()
    data['inheritedManifestSha256'] = hashlib.sha256(original).hexdigest()
    data['base'] = 'render-input-v6 / base-meshopt-v5 + actual Bai route model-v3/support-v3/base-clip-v1 + source access + public arrivals'
    evidence = [
        Path('artifacts/cities/hangzhou/bai-route-input-v1/route-input.json'),
        Path('artifacts/cities/hangzhou/bai-route-model-v3/asset-manifest.json'),
        Path('artifacts/cities/hangzhou/bai-route-support-v3/site-surfaces.json'),
        Path('artifacts/cities/hangzhou/bai-base-clip-v1/actual-context-verification.json'),
        Path('docs/hangzhou/audit/access-arrivals-v7b-20261111.json'),
        Path('docs/hangzhou/audit/bai-walk-final-v7-20261111.json'),
        stage / 'bai-integration.json', stage / 'bai-support-refinement.json',
        stage / 'access-arrivals-integration.json',
    ]
    if args.browser_report:
        evidence.append(args.browser_report)
    data['evidence'] = {str(p): sha(p) for p in evidence}
    data['runtimeSource'] = {str(p.relative_to(stage)): sha(p) for p in sorted((stage / 'src').rglob('*')) if p.is_file()}
    data['build'] = {str(p.relative_to(stage)): sha(p) for p in sorted((stage / 'dist/assets').rglob('*')) if p.is_file()}
    data['browserVerified'] = False
    data['browserScopeReport'] = str(args.browser_report) if args.browser_report else None
    data['limitations'] += [
        'Bai walking geometry/CPU route is checked separately. A browser scope report is not full game acceptance.',
        'Lingyin and West Lake ordinary building heights/roofs remain incorrect. Full scenery acceptance is not passed.',
        'Bus boarding, gate/signage completion, full careers/stories/saves and citywide runtime acceptance remain pending.',
    ]
    backup.write_bytes(original)
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode() + b'\n'
    manifest.write_bytes(payload)
    (stage / 'dist/demo-manifest.json').write_bytes(payload)
    print(json.dumps({'candidate': stage.name, 'changedAssets': changed,
                      'assetCount': len(data['files']), 'manifestSha256': sha(manifest)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
