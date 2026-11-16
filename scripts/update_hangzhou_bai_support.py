"""Serial support refinement in a fresh, unbuilt demo clone."""
import argparse,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,separators=(',',':'))+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--support',required=True);a=p.parse_args()
    stage=ROOT/a.stage;source=ROOT/a.support;root=stage/'public/cities/hangzhou';marker=stage/'bai-support-refinement.json'
    if marker.exists() or (stage/'dist').exists() or ROOT/'artifacts' not in stage.parents:raise ValueError('Fresh unbuilt stage required')
    site=root/'geography/site-surfaces.json';before=sha(site);data=read(site);new=read(source/'site-surfaces.json')
    for k in ['walkFloors','terrainCuts']:data[k]=[g for g in data[k] if not g['id'].startswith('bai-route:')]+new[k]
    write(site,data);gp=root/'geography/manifest.json';g=read(gp);g['siteSurfacesSha256']=sha(site);write(gp,g)
    dp=root/'landmark-detail.json';d=read(dp);d['terrain']['manifestSha256']=sha(gp);write(dp,d)
    write(marker,{'sourceSupport':str(source.relative_to(ROOT)),'sourceSupportSha256':sha(source/'site-surfaces.json'),
      'previousSiteSha256':before,'siteSha256':sha(site),'geographySha256':sha(gp),'detailSha256':sha(dp)})
