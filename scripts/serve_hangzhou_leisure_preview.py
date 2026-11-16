"""Serve only the isolated leisure mechanics preview; no full-city fallback."""
import argparse,hashlib,ipaddress,json,subprocess,time
from datetime import datetime,timedelta
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from serve_hangzhou_loading_demo import PreviewServer
ROOT=Path(__file__).resolve().parents[1]
PREVIEW=ROOT/'artifacts/cities/hangzhou/westlake-leisure-v1/preview'
def verify_artifacts():
    manifest=json.loads((PREVIEW.parent/'delivery.json').read_text())
    for name in ['preview/index.html','preview/leisure.js']:
        data=(PREVIEW.parent/name).read_bytes();expected=manifest['files'][name]
        if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:raise SystemExit('休闲样片与已验收文件不一致：'+name)
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):self.respond(True)
    def do_GET(self):self.respond(False)
    def respond(self,head):
        route=self.path.split('?',1)[0]
        if route=='/':
            data='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>杭城之行 · 湖畔休闲操作样片</title><style>body{font:17px system-ui;background:#244c45;color:#eff0df;max-width:650px;margin:8vh auto;padding:24px;line-height:1.8}a{display:inline-block;padding:12px 24px;background:#d6dec0;color:#244c45;border-radius:8px;text-decoration:none}small{display:block;margin-top:24px}</style><p>GTA_HZ · 前五项推进 / 休闲玩法</p><h1>划一程船，等一尾鱼。</h1><p>本阶段为独立的低负载操作样片：登船、划行、避岸、停泊下船、码头人物交谈，以及抛竿、控线、放流与手账保存。</p><p>这是虚构测试场地，尚未接入杭州主城，不代表西湖的真实地理或实际垂钓许可。已认可的主城试玩及原玩法保留。</p><p>WASD 行走 / 划船，E 交谈 / 上下船，Q 抛竿，空格提竿 / 收线；按 Esc 暂停。垂钓区在码头右侧。</p><a href="/play/">进入湖畔休闲样片</a><small>不加载完整杭州模型。服务启动后 1 小时结束。</small></html>'''.encode();kind='text/html; charset=utf-8'
        elif route in ('/play/','/play/leisure.js'):
            name='index.html' if route=='/play/' else 'leisure.js';data=(PREVIEW/name).read_bytes();kind='text/html; charset=utf-8' if name.endswith('.html') else 'text/javascript; charset=utf-8'
        elif route=='/favicon.ico':self.send_response(204);self.end_headers();return
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");self.end_headers()
        if not head:
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,*args):pass
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='127.0.0.1');p.add_argument('--advertise',default='127.0.0.1');p.add_argument('--port',type=int,default=5206);a=p.parse_args();ipaddress.IPv4Address(a.host);ipaddress.IPv4Address(a.advertise)
    if subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip()!='1':raise SystemExit('系统内存压力非正常，本次未启动场景。')
    if not (PREVIEW/'leisure.js').is_file():raise SystemExit('请先构建独立休闲样片。')
    verify_artifacts()
    with PreviewServer((a.host,a.port),Handler) as server:
        server.timeout=.5;start=datetime.now().astimezone();deadline=time.monotonic()+3600
        print(json.dumps({'localUrl':f'http://127.0.0.1:{a.port}/','url':f'http://{a.advertise}:{a.port}/','version':'leisure-mechanics-v1','startedAt':start.isoformat(),'expiresAt':(start+timedelta(hours=1)).isoformat()}),flush=True)
        while time.monotonic()<deadline:server.handle_request()
if __name__=='__main__':main()
