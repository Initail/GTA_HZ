# -*- coding: utf-8 -*-
"""Frozen v13 bicycle preview. The entry page never loads the game automatically."""
import argparse,hashlib,ipaddress,json,secrets,subprocess,time
from datetime import datetime,timedelta
import serve_hangzhou_loading_demo as base
base.CANDIDATE=base.PROJECT/'artifacts/cities/hangzhou/westlake-bicycle-v1'

class Handler(base.Handler):
    def page(self,head=False):
        page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>杭城之行 · v13 骑行试玩</title><style>body{font:17px system-ui;background:#102c2a;color:#edf4ea;margin:0}main{max-width:680px;margin:5vh auto;padding:24px}h1{font-size:34px}p,li{line-height:1.7}.notice{padding:14px;background:#4a3c2c;border-radius:8px}button{font:inherit;padding:14px 22px;background:#d4e6b2;border:0;border-radius:8px;cursor:pointer}small{display:block;margin-top:20px;color:#b4c7c4}kbd{border:1px solid #8da59a;border-radius:4px;padding:1px 5px}a{color:#d4e6b2}</style><main><p>GTA_HZ / 杭城之行 · 阶段一</p><h1>v13 · 走一走，也骑一程</h1><p>本阶段新增玩家单车。保留 v12 的车辆碰撞、昼夜天气、地图、任务和驾驶操作，景区精修与其他休闲玩法继续分阶段处理。</p><ol><li>汽车停稳后按 <kbd>F</kbd> 下车，找平整开阔的位置，按 <kbd>N</kbd> 或点击“取出单车”。</li><li><kbd>W</kbd> 踩踏，<kbd>A D</kbd> 转向，<kbd>S</kbd> / <kbd>空格</kbd> 刹车，<kbd>C</kbd> 切换跟随镜头远近。</li><li>停稳后按 <kbd>F</kbd> 下车；在车旁按 <kbd>N</kbd> 再骑，或点“收起单车”后步行。汽车留在原处。</li><li>白堤明确禁骑的路段会提示下车；请走过后在允许骑行处重新取车。地图仍可搜索“白堤”“断桥”。</li></ol><p>试骑不收费，单车里程不计汽车里程。当前使用既有单车和坐姿人物，踏频动画待完善；单车停放和里程仅在本次会话保留。这个独立端口的浏览器存档与 v12 分开，旧试玩存档保留。</p><p class="notice">新增骑行已通过离线控制、路权和回归检查，完整场景实机、手感和性能仍待确认。此前整机卡顿重启问题未确认彻底消除，请先保存其他工作。打开本页不会启动游戏。</p><form method="post" action="/enter"><input type="hidden" name="ticket" value="TOKEN"><button type="submit">进入 v13 骑行试玩</button></form><small>同学可使用同一局域网链接。服务启动后 1 小时自动停止；之后双击项目里的“启动骑行试玩.command”可重新启动。游船、钓鱼、实景景区、NPC、公交和门禁标识尚未全部完成。</small></main></html>'''
        data=page.replace('TOKEN',self.server.token).encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");self.end_headers()
        if not head:self.wfile.write(data)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=5205);parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--advertise',default='127.0.0.1');args=parser.parse_args()
    ipaddress.IPv4Address(args.host);ipaddress.IPv4Address(args.advertise)
    if subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip()!='1':raise SystemExit('当前系统内存压力不是正常状态。请关闭暂不用的游戏页，再启动试玩。')
    report=json.loads((base.CANDIDATE/'delivery-check-lan-v1.json').read_text())
    if report.get('offlineReady') is not True or report.get('version')!='demo-v13-bicycle':raise SystemExit('This candidate has not passed its offline delivery checks.')
    for name,record in report['artifacts'].items():
        data=(base.CANDIDATE/name).read_bytes()
        if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:raise SystemExit('Frozen candidate changed: '+name)
    with base.PreviewServer((args.host,args.port),Handler) as server:
        server.token=secrets.token_urlsafe(24);server.origins={f'http://{h}:{args.port}' for h in ['127.0.0.1','localhost',args.advertise]};server.timeout=.5
        now=datetime.now().astimezone();deadline=time.monotonic()+3600
        print(json.dumps({'url':f'http://{args.advertise}:{args.port}/','localUrl':f'http://127.0.0.1:{args.port}/','bind':args.host,'version':'demo-v13-bicycle','startedAt':now.isoformat(),'expiresAt':(now+timedelta(hours=1)).isoformat(),'manualEntryRequired':True}),flush=True)
        while time.monotonic()<deadline:server.handle_request()
if __name__=='__main__':main()
