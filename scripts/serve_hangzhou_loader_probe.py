"""Serve a hash-bound single-tile GPU diagnostic, never a whole-city endpoint."""
import argparse,hashlib,json,mimetypes,subprocess,time,re
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from hangzhou_probe_guard import probe_guard_status
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=5208);p.add_argument('--name',default='loader-probe-v1');p.add_argument('--resource-log');a=p.parse_args()
assert re.fullmatch(r'loader-probe-v[1-9][0-9]*',a.name)
C=ROOT/'artifacts/cities/hangzhou/city-leisure-v15'/a.name
resource_log=(C/a.resource_log).resolve() if a.resource_log else None
if resource_log:resource_log.relative_to(C.resolve())
if subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip()!='1':raise SystemExit('Memory pressure is not normal')
manifest=json.loads((C/'server-files.json').read_text());files={}
for url,record in manifest.items():
 path=(ROOT/record['path']).resolve();path.relative_to(ROOT)
 data=path.read_bytes()
 if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:raise SystemExit('Changed diagnostic input: '+url)
 files[url]=path
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/guard.json' and resource_log:
   status=probe_guard_status(resource_log)
   if status['stop']:self.server.guard_stopped=True
   if self.server.guard_stopped:status=dict(status,ready=False,stop=True)
   data=json.dumps(status).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
  if self.path not in files:self.send_error(404);return
  path=files[self.path];data=path.read_bytes();self.send_response(200)
  # Pinned meshoptimizer ships a browser-compatible .cjs decoder. Keep nosniff
  # and the hash allowlist; explicitly identify JavaScript rather than relying
  # on the host's incomplete MIME database for .cjs/.mjs files.
  mime='text/javascript' if path.suffix in ('.js','.mjs','.cjs') else mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
  self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
with HTTPServer(('127.0.0.1',a.port),Handler) as server:
 server.guard_stopped=False
 server.timeout=.25;deadline=time.monotonic()+180
 print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_address[1])+'/','expiresSeconds':180,'allowlistedFiles':len(files),'scope':'one base tile only','resourceGuard':bool(resource_log)}),flush=True)
 while time.monotonic()<deadline and not server.guard_stopped:server.handle_request()
