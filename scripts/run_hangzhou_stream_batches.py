"""Resume immutable offline tiles serially. Every Node child gets the same fixed
10 second / 256 MiB stop policy; any failed job ends the run without retry."""
import argparse,json,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('artifacts/cities/hangzhou/stream-mesh-v1'));p.add_argument('--reports',type=Path,default=Path('docs/hangzhou/audit/stability-20261111/stream-batches-v1'));p.add_argument('--roles',nargs='+',choices=['terrain','roads','buildings'],default=['terrain','roads','buildings']);a=p.parse_args()
root=a.root;reports=a.reports;reports.mkdir(parents=True,exist_ok=True)
started=time.monotonic();jobs=0
for role in a.roles:
 directory=root/role;plan=json.loads((directory/'plan.json').read_text());tiles=plan['tiles'];cursor=0
 while cursor<len(tiles):
  file=directory/tiles[cursor]['file']
  if Path(str(file)+'.validation.json').exists():cursor+=1;continue
  exists=file.exists()
  count=1
  while count<8 and cursor+count<len(tiles):
   following=directory/tiles[cursor+count]['file']
   if following.exists()!=exists or Path(str(following)+'.validation.json').exists():break
   count+=1
  operations=['check'] if exists else ['extract','check']
  for operation in operations:
   report=reports/f'{role}-{cursor:04}-{operation}.json'
   if report.exists():raise SystemExit(f'Existing failed/incomplete job needs review: {report}')
   command=['node','--expose-gc','--max-old-space-size=128']
   command+=['scripts/partition_hangzhou_glb.mjs','batch',str(directory),str(cursor),str(count)] if operation=='extract' else ['scripts/check_hangzhou_stream_batch.mjs',str(directory),str(cursor),str(count)]
   run=subprocess.run([sys.executable,'scripts/run_hangzhou_bounded.py','--report',str(report),'--',*command],capture_output=True,text=True)
   jobs+=1
   if run.returncode:
    print(json.dumps({'stopped':True,'report':str(report),'output':run.stdout[-4000:],'stderr':run.stderr[-2000:]},ensure_ascii=False),flush=True);raise SystemExit(run.returncode)
  cursor+=count
  if cursor%32==0 or cursor==len(tiles):print(json.dumps({'role':role,'validated':cursor,'total':len(tiles),'jobs':jobs,'elapsedSeconds':round(time.monotonic()-started,1)}),flush=True)
print(json.dumps({'pass':True,'scope':'offline extraction and decoded equality only','jobs':jobs,'elapsedSeconds':round(time.monotonic()-started,1)}),flush=True)
