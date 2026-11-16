# -*- coding: utf-8 -*-
"""Serve the isolated v12 West Lake candidate; opening the entry does not start the game."""
import argparse,hashlib,ipaddress,json,secrets,subprocess,time
from datetime import datetime,timedelta
import serve_hangzhou_loading_demo as base
base.CANDIDATE=base.PROJECT/'artifacts/cities/hangzhou/westlake-collision-v1'

class Handler(base.Handler):
    def page(self,head=False):
        page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>杭城之行 · v12 西湖碰撞试玩</title><style>body{font:17px system-ui;background:#102c2a;color:#ecf4e9;margin:0}main{max-width:680px;margin:7vh auto;padding:28px}h1{font-size:34px}p,li{line-height:1.7}.notice{padding:16px;background:#523b29;border-radius:8px}button{font:inherit;padding:14px 22px;background:#d4e6b2;border:0;border-radius:8px;cursor:pointer}small{display:block;margin-top:20px;color:#b4c7c4}</style><main><p>GTA_HZ / 杭城之行</p><h1>v12 · 西湖碰撞试玩</h1><ul><li>车辆按实际车身方向和桥面高度接触，加入减速、推挤、短促镜头震动及撞击声。</li><li>NPC 会让停在前方的车辆；步行时也不会穿过同层车辆。</li><li>补齐白堤／断桥步行面的机动车限制；限行和水域停车有不同提示。</li><li>沿用 v11 加载优化、原玩法、昼夜和晴／阴／雨／雪。</li></ul><p>建议测试：白堤西侧公共道路驾驶 → 限行入口停车并按 F 下车；路上低速追尾、并排侧擦、倒车离开；同学请使用同一局域网。</p><p class="notice">这是独立候选，碰撞手感与完整场景尚未经过本轮实机验收。此前加载曾导致整机卡死重启，稳定性问题仍未确认消除；请先保存其他工作。打开本页不会启动游戏。</p><form method="post" action="/enter"><input type="hidden" name="ticket" value="TOKEN"><button type="submit">我已了解，进入西湖碰撞试玩</button></form><small>WASD / 方向键驾驶，F 上下车，Shift 跑步；地图可搜索“白堤”“断桥”。先沿公共道路试车，再步行进入景区。服务启动后 1 小时自动停止。</small></main></html>'''
        data=page.replace('TOKEN',self.server.token).encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");self.end_headers()
        if not head:self.wfile.write(data)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=5204);parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--advertise',default='127.0.0.1');args=parser.parse_args()
    ipaddress.IPv4Address(args.host);ipaddress.IPv4Address(args.advertise)
    if subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip()!='1':raise SystemExit('System memory pressure is not normal; preview not started.')
    report=json.loads((base.CANDIDATE/'delivery-check-lan-v1.json').read_text())
    if report.get('offlineReady') is not True or report.get('version')!='demo-v12-westlake':raise SystemExit('This candidate has not passed its offline delivery checks.')
    for name,record in report['artifacts'].items():
        p=base.CANDIDATE/name;b=p.read_bytes()
        if len(b)!=record['bytes'] or hashlib.sha256(b).hexdigest()!=record['sha256']:raise SystemExit('Frozen candidate changed: '+name)
    with base.PreviewServer((args.host,args.port),Handler) as server:
        server.token=secrets.token_urlsafe(24);server.origins={f'http://{h}:{args.port}' for h in ['127.0.0.1','localhost',args.advertise]};server.timeout=.5
        now=datetime.now().astimezone();deadline=time.monotonic()+3600
        print(json.dumps({'url':f'http://{args.advertise}:{args.port}/','bind':args.host,'version':'demo-v12-westlake','startedAt':now.isoformat(),'expiresAt':(now+timedelta(hours=1)).isoformat(),'manualEntryRequired':True}),flush=True)
        while time.monotonic()<deadline:server.handle_request()
if __name__=='__main__':main()
