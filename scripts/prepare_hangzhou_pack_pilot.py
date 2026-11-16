"""Write a hash-bound three-role near-block task; no GLB parsing or scene load."""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/cities/hangzhou/city-leisure-v15/pack-pilot-v1'
assert not OUT.exists(), 'Fresh candidate required'
members=[]
for role,version in [('terrain','v1'),('roads','v1'),('buildings','v2')]:
    directory=ROOT/('artifacts/cities/hangzhou/stream-mesh-'+version)/role
    manifest=directory/'manifest.json'
    raw=manifest.read_bytes(); data=json.loads(raw)
    tile=next(t for t in data['tiles'] if t['id']==role+':-1,-2')
    members.append({'role':role,'quality':'near','manifest':str(manifest.relative_to(ROOT)),
      'manifestSha256':hashlib.sha256(raw).hexdigest(),'id':tile['id'],'sha256':tile['sha256']})
OUT.mkdir()
(OUT/'task.json').write_text(json.dumps({'schemaVersion':1,'id':'near--1--2','scope':'one actual physical pack, not whole-city release','members':members},indent=2)+'\n')
print(str((OUT/'task.json').relative_to(ROOT)))
