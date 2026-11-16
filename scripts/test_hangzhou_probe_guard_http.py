"""Actual HTTP guard lifecycle with a named synthetic monitor, no browser/GPU."""
import json,subprocess,select,time,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/cities/hangzhou/city-leisure-v15/loader-probe-v6'
fixture=OUT/'guard-http-fixture.jsonl';report=OUT/'guard-http-verification-v1.json'
assert not fixture.exists() and not report.exists()
row={'atUTC':datetime.now(timezone.utc).isoformat(),'sample':0,'memoryPressure':'1','rssGrowthKiB':0,'alarms':[],'scope':'synthetic guard lifecycle fixture; not observed host metrics'}
fixture.write_text(json.dumps(row)+'\n')
process=subprocess.Popen([sys.executable,'scripts/serve_hangzhou_loader_probe.py','--port','0','--name','loader-probe-v6','--resource-log',fixture.name],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 assert select.select([process.stdout],[],[],3)[0],'Server did not start'
 startup=json.loads(process.stdout.readline());assert startup['resourceGuard'];url=startup['url']
 def get():
  with urlopen(url+'guard.json',timeout=2) as response:return json.loads(response.read(2049))
 healthy=get();assert healthy['ready'] and not healthy['stop']
 try:urlopen(url+'unlisted-city.glb',timeout=2);raise AssertionError('Unlisted resource admitted')
 except HTTPError as error:assert error.code==404
 row.update(sample=1,atUTC=datetime.now(timezone.utc).isoformat(),alarms=['synthetic-test-alarm']);fixture.write_text(json.dumps(row)+'\n')
 began=time.monotonic();stopped=get();assert stopped['stop'] and not stopped['ready'];process.wait(timeout=2);elapsed=time.monotonic()-began;assert process.returncode==0
 report.write_text(json.dumps({'scope':'HTTP lifecycle with synthetic alarm; no GPU and not resource acceptance','healthy':healthy,'stopped':stopped,'serverExitCode':process.returncode,'secondsFromAlarmRequestToServerExit':elapsed,'unlistedResourceDenied':True,'browserRun':False},indent=2)+'\n')
 print(json.dumps({'httpGuardLifecycle':True,'serverExited':True,'seconds':elapsed,'browserRun':False}))
finally:
 if process.poll() is None:process.terminate();process.wait(timeout=2)
