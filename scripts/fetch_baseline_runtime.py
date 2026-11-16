"""Fetch missing immutable runtime Git blobs; verify SHA1 before object storage.

Public raw.githubusercontent.com at the adopted commit, no working-tree writes.
LFS bodies have a separate SHA256 pipeline and are never fetched as text here.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from restore_upstream_baseline import ROOT, COMMIT, GIT


def fetch(entry):
    url=f"https://raw.githubusercontent.com/linranff/GTA_SZ/{COMMIT}/"+quote(entry['path'],safe='/')
    with urlopen(Request(url,headers={'User-Agent':'GTA_HZ-baseline-recovery/0.1'}),timeout=120) as response:
        data=response.read(100*1024*1024+1)
    if len(data)>100*1024*1024: raise ValueError('Runtime JSON exceeds expected budget')
    actual=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    if actual!=entry['oid']: raise ValueError('Immutable baseline blob mismatch: '+entry['path'])
    stored=subprocess.check_output([GIT,'hash-object','-w','--stdin'],input=data,cwd=ROOT,env={**os.environ,'GIT_NO_LAZY_FETCH':'1'}).decode().strip()
    if stored!=actual: raise ValueError('Git object storage mismatch')
    print(f"Verified {entry['path']} ({len(data)} bytes)",flush=True)
    return {'path':entry['path'],'gitBlobSha1':actual,'bytes':len(data),'sourceUrl':url}


if __name__=='__main__':
    report=json.loads((ROOT/'docs/hangzhou/audit/baseline-object-inventory.json').read_text())
    needed=[e for e in report['missingObjects'] if e['path'].startswith('public/') or (e['path'].startswith('ue5/') and e['path'].endswith('.json'))]
    with ThreadPoolExecutor(max_workers=4) as pool: verified=list(pool.map(fetch,needed))
    (ROOT/'docs/hangzhou/audit/baseline-runtime-recovery.json').write_text(json.dumps({'commit':COMMIT,'verified':verified},ensure_ascii=False,indent=2)+'\n')
