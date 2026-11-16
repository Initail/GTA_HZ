"""Bind one immutable road tile to a bounded browser diagnostic allowlist."""
import json,hashlib,argparse,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--name',default='loader-probe-v1');m=p.add_mutually_exclusive_group();m.add_argument('--far',action='store_true');m.add_argument('--pack',action='store_true');a=p.parse_args()
assert re.fullmatch(r'loader-probe-v[1-9][0-9]*',a.name)
C=ROOT/'artifacts/cities/hangzhou/city-leisure-v15'/a.name
SOURCE=ROOT/('artifacts/cities/hangzhou/city-leisure-v15/pack-pilot-v1/output' if a.pack else 'artifacts/cities/hangzhou/city-leisure-v15/public/base-far-pilot/roads' if a.far else 'artifacts/cities/hangzhou/stream-mesh-v1/roads')
def sha(data):return hashlib.sha256(data).hexdigest()
if (C/'server-files.json').exists():raise SystemExit('Existing diagnostic inputs are protected')
source_manifest=SOURCE/('descriptor.json' if a.far or a.pack else 'manifest.json')
manifest=json.loads(source_manifest.read_text())
tile={k:manifest[k] for k in ['id','file','bytes','sha256','bounds','logicalBytes','triangles']} if a.pack else manifest['tile'] if a.far else next(t for t in manifest['tiles'] if t['id']=='roads:-1,-2')
if a.pack:
 proof=json.loads((SOURCE.parent/'pack-verification-v1.json').read_text())
 assert proof['exactPacking'] and proof['packSha256']==tile['sha256'] and proof['descriptorSha256']==sha(source_manifest.read_bytes())
descriptor={'tile':dict(tile,role='pack' if a.pack else 'roads'),'textures':manifest['textures'],'sourceManifestSha256':sha(source_manifest.read_bytes()),'farPilot':a.far,'physicalPack':a.pack}
(C/'descriptor.json').write_text(json.dumps(descriptor,ensure_ascii=False,indent=2)+'\n')
paths={'/':C/'index.html','/main.js':C/'main.js','/descriptor.json':C/'descriptor.json','/meshopt_decoder.js':ROOT/'public/city/meshopt_decoder.js','/assets/'+tile['file']:SOURCE/tile['file']}
for record in [tile,*manifest['textures']]:
 data=(SOURCE/record['file']).read_bytes()
 assert len(data)==record['bytes'] and sha(data)==record['sha256']
for texture in manifest['textures']:paths['/assets/'+texture['file']]=SOURCE/texture['file']
files={url:{'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for url,path in paths.items()}
(C/'server-files.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(files),'allowlistedBytes':sum(r['bytes'] for r in files.values()),'tile':tile['id'],'maxContextSeconds':25,'wholeCityAllowed':False}))
