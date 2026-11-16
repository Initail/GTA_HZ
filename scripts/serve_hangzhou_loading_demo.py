# -*- coding: utf-8 -*-
"""Serve the optimized v11 overlay only after a manual form submission."""
import argparse
import hashlib
import ipaddress
import json
import mimetypes
import secrets
import shutil
import time
import threading
from socketserver import ThreadingMixIn
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

PROJECT = Path(__file__).resolve().parent.parent
CANDIDATE = PROJECT / 'artifacts/cities/hangzhou/demo-v11-loading'
FALLBACK = PROJECT / 'artifacts/cities/hangzhou/demo-v10/dist'
CHUNKS = PROJECT / 'artifacts/cities/hangzhou/stream-data-v1'
VENDOR = PROJECT / 'node_modules/@babylonjs'


class PreviewServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(4)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        self.slots.acquire()
        request.settimeout(30)
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    def authenticated(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            return cookie.get('hz-preview') is not None and secrets.compare_digest(cookie['hz-preview'].value, self.server.token)
        except Exception:
            return False

    def page(self, head=False):
        data = ('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>杭城之行 · v11体验入口</title><style>body{font:17px system-ui;background:#102c2a;color:#ecf4e9;margin:0}main{max-width:680px;margin:8vh auto;padding:28px}h1{font-size:34px}p,li{line-height:1.7}.notice{padding:16px;background:#523b29;border-radius:8px}button{font:inherit;padding:14px 22px;background:#d4e6b2;border:0;border-radius:8px;cursor:pointer}small{display:block;margin-top:20px;color:#b4c7c4}</style><main><p>GTA_HZ / 杭城之行</p><h1>v11 · 加载优化体验版</h1><ul><li>地图与桥面数据改为小块依次读取。</li><li>遮蔽贴图与屋顶索引串行处理，大图分段读回并释放临时资源。</li><li>首次进入使用低画质，可在游戏设置里调整。</li><li>沿用白堤通行修复、昼夜及晴/阴/雨/雪和原玩法。</li></ul><p class="notice">这是尚未完成稳定性验收的候选版本。此前版本曾在加载时导致整机卡死重启；本次优化尚未证明消除该问题，整城模型还未改为按需加载。请先保存其他工作。打开本页不会启动游戏。</p><form method="post" action="/enter"><input type="hidden" name="ticket" value="''' + self.server.token + '''"><button type="submit">我已了解，进入优化体验版</button></form><small>操作：WASD / 方向键驾驶，F上下车，Shift跑步；地图、职业、天气和画质入口保留。可供同一局域网的同学测试，服务启动后1小时自动停止。</small></main></html>''').encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if self.path != '/enter' or origin not in self.server.origins or origin != 'http://' + self.headers.get('Host', ''):
            self.send_error(403)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 256:
            self.send_error(400)
            return
        ticket = parse_qs(self.rfile.read(length).decode()).get('ticket', [''])[0]
        if not secrets.compare_digest(ticket, self.server.token):
            self.send_error(403)
            return
        self.send_response(303)
        self.send_header('Set-Cookie', 'hz-preview=' + self.server.token + '; HttpOnly; SameSite=Strict; Path=/')
        self.send_header('Location', '/play/?quality=low')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def respond(self, head):
        name = unquote(urlsplit(self.path).path)
        if name in ('/', '/index.html'):
            self.page(head)
            return
        if not self.authenticated():
            self.send_error(403, 'Open the manual entry page first')
            return
        if name in ('/play', '/play/'):
            paths = [CANDIDATE / 'dist/index.html']
        elif name.startswith('/stream-data/'):
            paths = [CHUNKS / name[len('/stream-data/'):]]
        elif name.startswith('/vendor/@babylonjs/'):
            relative = name[len('/vendor/@babylonjs/'):]
            if relative.split('/')[0] not in ('core', 'loaders') or not relative.endswith('.js'):
                self.send_error(404)
                return
            paths = [VENDOR / relative]
        else:
            paths = [CANDIDATE / 'dist' / name.lstrip('/'), FALLBACK / name.lstrip('/')]
        file = next((p for p in paths if any(root.resolve() in p.resolve().parents for root in [CANDIDATE / 'dist', FALLBACK, CHUNKS, VENDOR / 'core', VENDOR / 'loaders']) and p.is_file()), None)
        if file is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(file.stat().st_size))
        self.send_header('Cache-Control', 'private, max-age=3600' if VENDOR in file.parents else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if not head:
            try:
                with file.open('rb') as source:
                    shutil.copyfileobj(source, self.wfile, 64 * 1024)
            except (BrokenPipeError, ConnectionResetError):
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=5203)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--advertise', default='127.0.0.1')
    args = parser.parse_args()
    ipaddress.IPv4Address(args.host)
    ipaddress.IPv4Address(args.advertise)
    report_path = CANDIDATE / 'delivery-check-lan-v1.json'
    if not report_path.is_file() or json.loads(report_path.read_text()).get('offlineReady') is not True:
        raise SystemExit('Candidate has not passed its offline delivery check.')
    report = json.loads(report_path.read_text())
    for name, record in report['artifacts'].items():
        data = (CANDIDATE / name).read_bytes()
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise SystemExit('Checked preview artifact changed: ' + name)
    with PreviewServer((args.host, args.port), Handler) as server:
        server.token = secrets.token_urlsafe(24)
        server.origins = {f'http://{host}:{args.port}' for host in ['127.0.0.1', 'localhost', args.advertise]}
        server.timeout = .5
        deadline = time.monotonic() + 3600
        print(json.dumps({'url': f'http://{args.advertise}:{args.port}/', 'bind': args.host, 'version': 'demo-v11-loading', 'manualEntryRequired': True, 'expiresInSeconds': 3600}), flush=True)
        while time.monotonic() < deadline:
            server.handle_request()


if __name__ == '__main__':
    main()
