"""Bind an actually exported candidate to its job; never record visual verification."""
from __future__ import annotations
import argparse,hashlib,json,shlex
from pathlib import Path
from city_config import ROOT
from landmark_tasks import assess

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def record(job_path,delivery_path,log_path):
 job_path=Path(job_path).resolve();delivery_path=Path(delivery_path).resolve();log_path=Path(log_path).resolve()
 job=json.loads(job_path.read_text());d=json.loads(delivery_path.read_text())
 if d['cityId']!='hangzhou' or d['id']!=job['place']['id']:raise ValueError('Wrong object/city')
 for path,sha in [('artifact','artifactSha256'),('sourceModule','sourceModuleSha256'),('spec','specSha256')]:
  if digest(ROOT/d[path])!=d[sha]:raise ValueError('Changed exported source: '+path)
 log=log_path.read_text()
 if 'Blender quit' not in log or 'Traceback' in log or d['artifactSha256'] not in log:raise ValueError('Successful matching Blender export log required')
 config=ROOT/'config/cities/hangzhou.json'
 if digest(config)!=d['coordinateConfigSha256']:
  config=ROOT/f"docs/hangzhou/audit/city-config-hangzhou-{d['coordinateConfigSha256']}.json"
 if not config.is_file() or digest(config)!=d['coordinateConfigSha256']:raise ValueError('Original coordinate configuration snapshot missing')
 path=job_path.parent/job['files']['model'];model=json.loads(path.read_text())
 command=['/Applications/Blender.app/Contents/MacOS/Blender','--background','--factory-startup','--python-exit-code','1','--python','scripts/build_hangzhou_landmark_candidate.py','--',
  '--job',str(job_path.relative_to(ROOT)),'--spec',d['spec'],'--module',d['sourceModule'],'--output',str(delivery_path.parent.relative_to(ROOT))]
 placement=False
 for item in d.get('sourceInputs',[]):
  if item.get('role')=='placement':command+=['--placement',item['path']];placement=True
  elif item.get('role')=='material-palette' or 'basis' in item:command+=['--palette',item['path']]
 if d.get('baseYGame') and not placement:command+=['--base-y',str(d['baseYGame'])]
 model.update(artifactPath=d['artifact'],sha256=d['artifactSha256'],sourceModule=d['sourceModule'],sourceModuleSha256=d['sourceModuleSha256'],
  sourceSpec=d['spec'],sourceSpecSha256=d['specSha256'],artifactMeshPrefix='detail_'+d['id']+'_',buildCommand=shlex.join(command),status='model-exported-not-verified',
  sourceInputs=[{'path':str(config.relative_to(ROOT)),'sha256':digest(config)},*d.get('sourceInputs',[])],
  exportLog={'path':str(log_path.relative_to(ROOT)),'sha256':digest(log_path)},modelDeliverySha256=digest(delivery_path),glbStats=d['glbStats'])
 model['notes']='Actual Blender export bound to hashes. Ground, collision, in-game appearance, day/night and performance remain unknown.'
 path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')
 _,status=assess(job_path)
 if status['currentStage'] not in ('modelled','verified'):raise ValueError(json.dumps(status['errors'],ensure_ascii=False))
 return status

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--delivery',required=True);p.add_argument('--log',required=True)
 a=p.parse_args();print(json.dumps(record(a.job,a.delivery,a.log),ensure_ascii=False,indent=2))
