"""Attribute the *measured process totals*, not a page's private memory.
Uses existing P0 samples; does not open a browser or sample new heavy work."""
import json
from pathlib import Path
root=Path('docs/hangzhou/audit/stability-20261111')
rows=[json.loads(line) for line in (root/'recovery-resources.jsonl').read_text().splitlines()]
first=rows[0];peak=max(rows,key=lambda r:r['appFamilyRssKiB']);base={p['pid']:p for p in first['processes']};end={p['pid']:p for p in peak['processes']}
changes=[]
for pid in base.keys()|end.keys():
 before=base.get(pid,{}).get('rssKiB',0);after=end.get(pid,{}).get('rssKiB',0);p=end.get(pid,base.get(pid))
 changes.append({'pid':pid,'name':p['name'],'ppid':p['ppid'],'baselineKiB':before,'peakSampleKiB':after,'deltaKiB':after-before,'presentAtBaseline':pid in base,'presentAtPeak':pid in end})
changes.sort(key=lambda r:r['deltaKiB'],reverse=True)
delta=peak['appFamilyRssKiB']-first['appFamilyRssKiB'];assert sum(p['deltaKiB'] for p in changes)==delta
result={'scope':'Existing P0 samples only; endpoint differences at the same peak sample, not sums of per-process maxima',
 'baselineUTC':first['atUTC'],'peakUTC':peak['atUTC'],'peakSample':peak['sample'],'growthKiB':delta,'newProcessGrowthKiB':sum(r['deltaKiB'] for r in changes if not r['presentAtBaseline']),
 'existingProcessNetGrowthKiB':sum(r['deltaKiB'] for r in changes if r['presentAtBaseline']),'changes':changes,
 'pageAttribution':'unknown: samples contain PID/name/parent only, no browser target-to-renderer mapping or private/proportional-memory counters',
 'gameAttribution':'No game assets or WebGL were requested by the recovery page; app-family RSS cannot be called game memory',
 'gate':'P0 remains stopped under the original 512 MiB app-family growth limit; no threshold increase',
 'nextMeasurement':'Warm tool infrastructure first, then require a quiet baseline and separately record existing/new process deltas plus exact page requests. Do not subtract workers to claim the original gate passed.'}
out=root/'recovery-rss-attribution-v1.json'
with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='changes'},ensure_ascii=False))
