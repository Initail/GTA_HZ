"""Explicit estimated game-unit floors, kept separate from frozen source models."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from city_config import ROOT,load_city,project
from hangzhou_surface import Surface,digest
def prepare(source,inventory,output):
    source,inventory,output=map(lambda p:Path(p).resolve(),[source,inventory,output])
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
    city=json.loads((source/'city.json').read_text());objects=json.loads(inventory.read_text());profile=load_city('hangzhou');field=Surface(source);water={w['id']:w['height'] for w in city['water']};output.mkdir(parents=True);records=[]
    lake=water['relation/2308774'];leifeng=ROOT/'docs/hangzhou/research/core/leifeng-site-round2/spec.json';lf=json.loads(leifeng.read_text())
    for item in objects['objects']:
        d=json.loads((ROOT/item['deliveryFile']).read_text());spec=json.loads((ROOT/d['spec']).read_text());x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],profile);identifier=item['id'];y=field.ground(x,z);basis='estimated same-source DSM/road earthworks at source anchor; not surveyed finished floor';error=8
        if identifier in ['west-lake-causeways','broken-bridge']:y=lake;basis='same-source provisional West Lake EGM2008 water reference as parent walk datum; bank/floor survey unknown';error=3
        elif identifier=='qiantang-bridges':y=d['baseYGame'];basis='existing source-consistent provisional water plane; rigid structures/decks require separate review';error=6
        elif identifier=='leifeng-pagoda':y=lf['towerPlacement']['recommendedYOffsetGameForEgmZero0'];basis=lf['towerPlacement']['heightBasis'];error=12
        lm={'id':identifier,'x':x,'z':z,'y':y};extra=[]
        if identifier=='lingyin-temple':
            new_spec=ROOT/'docs/hangzhou/research/core/lingyin-round3/spec.json';s=json.loads(new_spec.read_text());lm['hallBaseYGame']={h['id']:field.ground(*project(*h['centroidWGS84'],profile)) for h in s['baseHallSpec']['halls']};basis='five explicit same-source filtered DSM estimated bases; absolute floors/steps remain unknown';error=12;extra.append({'path':str(new_spec.relative_to(ROOT)),'sha256':digest(new_spec)})
        if not all(math.isfinite(v) for v in [x,z,y,*lm.get('hallBaseYGame',{}).values()]):raise ValueError('Nonfinite floor proposal')
        r={'schemaVersion':1,'cityId':'hangzhou','id':identifier,'landmark':lm,'units':'absolute game metres; never multiply input y by .60','heightBasis':basis,'sourceStatus':'estimated, not measured or physical accepted','errorRealMetres':error,'errorMeaning':'engineering investigation allowance, not survey confidence interval','sourceInputs':[{'path':str((source/'geography/manifest.json').relative_to(ROOT)),'sha256':digest(source/'geography/manifest.json')},{'path':str(inventory.relative_to(ROOT)),'sha256':digest(inventory)},*extra],'oldModelBaseYGame':d.get('baseYGame',0),'pending':['terrain/platform joins','real entrances and reachable source arrivals','current visual/collision/browser acceptance']}
        p=output/(identifier+'.json');p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');records.append({'id':identifier,'file':str(p.relative_to(ROOT)),'sha256':digest(p),'baseYGame':y,'hallBaseYGame':lm.get('hallBaseYGame'),'sourceStatus':r['sourceStatus']})
    result={'schemaVersion':1,'cityId':'hangzhou','objects':records,'sourceCitySha256':digest(source/'city.json'),'profileSha256':digest(ROOT/'config/cities/hangzhou.json'),'status':'explicit estimated placement proposals, not verified ground'};(output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--inventory',required=True);p.add_argument('--output',required=True);a=p.parse_args();prepare(a.city_root,a.inventory,a.output)
