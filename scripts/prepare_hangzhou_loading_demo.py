"""Prepare a new demo source snapshot without changing the frozen v10 assets."""
import hashlib
import json
import shutil
from pathlib import Path

project = Path(__file__).resolve().parent.parent
base = project / 'artifacts/cities/hangzhou/demo-v10'
target = project / 'artifacts/cities/hangzhou/demo-v11-loading'
if target.exists():
    raise SystemExit('Candidate exists; choose a fresh version, do not overwrite.')
target.mkdir()
shutil.copytree(base / 'src', target / 'src')
changed = ['main.ts', 'city-world.ts', 'city-geography.ts', 'city-json-chunks.ts',
           'city-raster-decode.ts', 'city-ambient-occlusion.ts', 'city-roof-surface.ts', 'city-startup-trace.ts',
           'city-content-hash.ts', 'city-landscape.ts']
for name in changed:
    shutil.copyfile(project / 'src' / name, target / 'src' / name)
# The frozen snapshot's generated Hangzhou/demo profile stays untouched.
main = target / 'src/main.ts'
text = main.read_text()
needle = 'await world.init(s=>{trace(s);loading.update(s);});'
if text.count(needle) != 1:
    raise ValueError('Startup call differs; do not patch heuristically.')
release = json.loads((project / 'artifacts/cities/hangzhou/stream-release-v1/descriptor.json').read_text())
sources = {}
for key, directory in [('city', 'city'), ('roadLevels', 'road-levels')]:
    record = release['data'][key]
    sources[key] = {k: record[k] for k in ['manifestBytes', 'manifestSha256', 'sourceSha256']}
    sources[key]['manifestUrl'] = '/stream-data/' + directory + '/manifest.json'
source_expression = json.dumps(sources, separators=(',', ':'))
for source in sources.values():
    literal = json.dumps(source['manifestUrl'])
    source_expression = source_expression.replace(literal, 'new URL(' + literal + ',location.href).href')
main.write_text(text.replace(needle, 'await world.init(s=>{trace(s);loading.update(s);},' + source_expression + ');'))
# Low is the default only; explicit user choices and the original three presets stay available.
quality = target / 'src/city-graphics-quality.ts'
q = quality.read_text()
needle = "export const CITY_GRAPHICS_DEFAULT:CityGraphicsQuality='medium';"
if q.count(needle) != 1:
    raise ValueError('Graphics default differs.')
quality.write_text(q.replace(needle, "export const CITY_GRAPHICS_DEFAULT:CityGraphicsQuality='low';"))
changed.append('city-graphics-quality.ts')
(target / 'dist/assets').mkdir(parents=True)
html = (base / 'dist/index.html').read_text()
import re
html, scripts = re.subn(r'src="/assets/index-[^"/]+\.js"', 'src="/assets/main.js"', html)
html, styles = re.subn(r'href="/assets/index-[^"/]+\.css"', 'href="/assets/main.css"', html)
if (scripts, styles) != (1, 1):
    raise ValueError('Frozen HTML entry differs.')
html = html.replace('杭州体验版</span>', '杭州体验版 v11 · 加载优化候选</span>')
imports = {'@babylonjs/core': '/vendor/@babylonjs/core/index.js', '@babylonjs/core/': '/vendor/@babylonjs/core/',
           '@babylonjs/loaders/glTF': '/vendor/@babylonjs/loaders/glTF/index.js', '@babylonjs/loaders/': '/vendor/@babylonjs/loaders/'}
html = html.replace('    <script type="module"', '    <script type="importmap">' + json.dumps({'imports': imports}, separators=(',', ':')) + '</script>\n    <script type="module"', 1)
(target / 'dist/index.html').write_text(html)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'version': 'demo-v11-loading', 'base': str(base.relative_to(project)),
          'runtimeAssetsFallback': str((base / 'dist').relative_to(project)),
          'dataChunks': str((project / 'artifacts/cities/hangzhou/stream-data-v1').relative_to(project)),
          'changes': changed, 'sourceFiles': {str(p.relative_to(target)): sha(p) for p in sorted((target / 'src').rglob('*')) if p.is_file()},
          'dataSources': sources, 'gameplayParametersChanged': False, 'glbStreamingInstalled': False,
          'fullTypecheckPassed': False, 'browserValidated': False, 'watchdogResolved': False,
          'note': 'User-requested manually entered preview. Existing v10 binary assets and gameplay are retained; no stability claim.'}
(target / 'candidate.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'target': str(target), 'changed': changed, 'sourceCount': len(report['sourceFiles']), 'browserValidated': False}))
