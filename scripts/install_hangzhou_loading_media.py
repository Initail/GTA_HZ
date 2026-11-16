"""Install checked loading media into a new Hangzhou-only asset directory.
Never changes active-city.json or overwrites the Shenzhen loading film.
"""
import argparse,json,shutil
from pathlib import Path
from prepare_hangzhou_loading_media import ROOT,sha
def main():
    p=argparse.ArgumentParser()
    for name in ['source','review','visual']:p.add_argument('--'+name,required=True)
    a=p.parse_args();source=ROOT/a.source;review_path=ROOT/a.review;visual_path=ROOT/a.visual
    manifest=json.loads((source/'asset-manifest.json').read_text());review=json.loads(review_path.read_text());visual=json.loads(visual_path.read_text())
    if manifest['cityId']!='hangzhou' or not review['pass']:raise ValueError('Checked Hangzhou loading media required')
    if visual['sourceReportSha256']!=sha(review_path):raise ValueError('Visual review does not bind decoded movie')
    for name,digest in review['inputs'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Changed decode input '+name)
    for name,record in manifest['files'].items():
        if sha(source/name)!=record['sha256']:raise ValueError('Changed asset '+name)
    out=ROOT/'public/cities/hangzhou/loading'
    if out.exists():raise ValueError('Existing media directory requires a separate reviewed replacement')
    active=sha(ROOT/'config/active-city.json');out.mkdir(parents=True)
    for name in manifest['files']:shutil.copy2(source/name,out/name)
    record={**manifest,'installation':'Hangzhou loading assets only; city remains inactive',
            'decodeReview':str(review_path.relative_to(ROOT)),'decodeReviewSha256':sha(review_path),
            'visualReview':str(visual_path.relative_to(ROOT)),'visualReviewSha256':sha(visual_path),
            'installerSha256':sha(Path(__file__)),
            'pending':['real browser loading UI/autoplay/reduced-motion/error fallback','complete Hangzhou city and gameplay acceptance']}
    (out/'hangzhou-clay-source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    assert sha(ROOT/'config/active-city.json')==active
    for name,info in manifest['files'].items():assert sha(out/name)==info['sha256']
    print(json.dumps({'installed':str(out.relative_to(ROOT)),'files':manifest['files'],'activeCityUnchanged':True},indent=2))
if __name__=='__main__':main()
