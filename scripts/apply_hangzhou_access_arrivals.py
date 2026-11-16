"""Apply a source-checked public arrival proposal in a fresh demo clone."""
import json,sys,hashlib
from pathlib import Path
stage,proposal=map(Path,sys.argv[1:]);root=stage/'public/cities/hangzhou';marker=stage/'access-arrivals-integration.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if marker.exists() or (stage/'dist').exists():raise ValueError('Unbuilt fresh candidate required')
report=json.loads(proposal.read_text());objects={}
for file,expected in report['inputs'].items():
    if sha(root/file)!=expected:raise ValueError('Changed arrival input '+file)
for c in report['changes']:
    data=objects.setdefault(c['file'],json.loads((root/c['file']).read_text()))
    lm=next(lm for lm in data[c['key']] if lm['id']==c['id'])
    lm['previousRestrictedArrival']=c['previous'];lm.update(c['next'])
    if 'arrivalData' in lm:lm['arrivalData'].update(arrival=c['next']['arrival'],yaw=c['next']['yaw'],roadId=c['next']['arrivalRoadId'],basis='source access and full-car-footprint public candidate')
for file,data in objects.items():(root/file).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
marker.write_text(json.dumps({'proposal':str(proposal),'proposalSha256':sha(proposal),'changed':len(report['changes']),
    'files':{file:sha(root/file) for file in objects},'blocked':report['blocked'],'pending':'furniture, final walking leg and browser'},indent=2)+'\n')
