"""Relocate the original fictional interior without scaling/rebuilding its assets."""
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
from city_config import ROOT,load_city
from prepare_hangzhou_life_sites import prepare
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(source,output):
 output=Path(output).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 seed=ROOT/'config/hangzhou/cafe-seed.json'
 prepare(source,output/'placement',seed)
 placement=json.loads((output/'placement/life-sites.json').read_text());site=placement['sites'][0]
 original=ROOT/'public/city/bamboo-cafe';destination=output/'bamboo-cafe'
 # Source files already hydrated/verified. Reuse is byte-exact except for the
 # city-bound manifest; public assets and character contract are untouched.
 shutil.copytree(original,destination)
 manifest=json.loads((original/'manifest.json').read_text());spec=manifest['spec']
 spec['site']={k:site[k] for k in ['x','z','heading','arrival']};spec['site']['roadYaw']=site['yaw'];spec['area']='上城 · 钱江新城'
 spec['scale']['geography']='Hangzhou WGS84 origin [120.155,30.274]; city .60; fictional interior stays scale1'
 spec['review']={'notSurveyed':True,'source':'Original fictional gameplay cafe, relocated beside mapped Hangzhou roads',
  'placementInputs':placement['inputs'],'siteClearance':'28x48 game-unit rotated envelope clear of source buildings/water/roads; actual ground/detail/camera pending'}
 spec['staff'][0]['line']='欢迎来到月白。窗边是钱江街景，先坐下来，慢慢喝一杯吧。'
 manifest['cityId']='hangzhou';manifest['originWGS84']=load_city('hangzhou')['geography']['originWGS84'];manifest['horizontalScale']=.60
 (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 assets=[]
 for p in destination.rglob('*'):
  if not p.is_file():continue
  relative=p.relative_to(destination);source_file=original/relative;identical=digest(p)==digest(source_file)
  if str(relative)!='manifest.json' and not identical:raise ValueError('Unexpected interior/character mutation: '+str(relative))
  assets.append({'path':str(relative),'bytes':p.stat().st_size,'sha256':digest(p),'sourceSha256':digest(source_file),'byteExactReuse':identical})
 result={'cityId':'hangzhou','kind':'original-fictional-cafe-geographic-candidate','site':site,
  'originalManifestSha256':digest(original/'manifest.json'),'manifestSha256':digest(destination/'manifest.json'),
  'assetCount':len(assets),'assets':assets,'localScale':1,'geographicScaleAppliedToInterior':False,
  'pending':['terrain datum and platform','detailed landmark avoidance','entrance/door/floor/wall/camera in browser','characters in browser','vegetation clearance','day/night and performance']}
 (output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'assetCount':len(assets),'site':site,'pending':result['pending']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.input,a.output)
