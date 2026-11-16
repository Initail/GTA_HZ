"""Run one named offline job with fixed 10s / 256MiB sampled RSS stop limits."""
import argparse,json,os,resource,signal,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
command=a.command[1:] if a.command[:1]==['--'] else a.command
log_path=a.report.with_suffix('.stdout.log')
if not command or a.report.exists() or log_path.exists():raise SystemExit('Provide a command and a fresh report/log.')
a.report.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic();log=log_path.open('x+')
def pressure():
 if sys.platform!='darwin':return None
 return subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip()
started_at=datetime.now(timezone.utc).isoformat();initial_pressure=pressure()
if initial_pressure not in (None,'1'):
 result={'command':command,'startedAtUTC':started_at,'exitCode':75,'stopped':'system memory pressure before launch','memoryPressure':initial_pressure,'pid':None,'limits':{'rssKiB':256*1024,'seconds':10,'sampleSeconds':.1}}
 a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');log.close();print(json.dumps(result));raise SystemExit(75)
process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True);peak=0;stopped=None;peak_pids=[]
def stop(sig):
 try:os.killpg(process.pid,sig)
 except ProcessLookupError:pass
 except PermissionError:
  # Darwin can refuse a process-group signal after the owned child has already
  # exited. Reap that child, but retain the stop reason in the report. Never
  # suppress failure to stop a still-running job.
  if process.poll() is None:raise
while process.poll() is None:
 # Node's test runner may fork. Bound the owned process tree, not only its parent.
 rows=[list(map(int,line.split())) for line in subprocess.check_output(['ps','-axo','pid=,ppid=,rss='],text=True).splitlines() if line.strip()]
 owned={process.pid}
 while True:
  children={pid for pid,ppid,_ in rows if ppid in owned}
  if children<=owned:break
  owned|=children
 rss=sum(value for pid,_,value in rows if pid in owned)
 if rss>peak:peak=rss;peak_pids=sorted(owned)
 current_pressure=pressure()
 if rss>256*1024 or time.monotonic()-start>10 or log_path.stat().st_size>1024*1024 or current_pressure not in (None,'1'):
  stopped='system memory pressure' if current_pressure not in (None,'1') else 'RSS/time/output limit';stop(signal.SIGTERM);break
 time.sleep(.1)
try:process.wait(timeout=2)
except subprocess.TimeoutExpired:stop(signal.SIGKILL);process.wait()
if stopped:stop(signal.SIGKILL)
log.seek(0);output=log.read(65536);log.close()
# Very short jobs can finish between ps samples. The kernel high-water mark
# supplements sampling; it is one-child maximum, not a simultaneous tree sum.
kernel_peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/(1024 if sys.platform=='darwin' else 1)
if kernel_peak>256*1024 and stopped is None:stopped='kernel child RSS exceeded limit between samples'
result={'command':command,'startedAtUTC':started_at,'pid':process.pid,'exitCode':process.returncode,'elapsedSeconds':time.monotonic()-start,'peakSampledRssKiB':peak,'peakKernelChildRssKiB':kernel_peak,'rssScope':'sampled owned-tree sum plus kernel child high-water mark; shared pages may overlap','peakPids':peak_pids,'stopped':stopped,'memoryPressureAtStart':initial_pressure,'limits':{'rssKiB':256*1024,'seconds':10,'sampleSeconds':.1,'outputBytes':1024*1024},'outputLog':str(log_path),'output':output}
a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));raise SystemExit(process.returncode or (1 if stopped else 0))
