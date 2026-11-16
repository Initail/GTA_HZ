"""Serve only the bounded, GPU-free recovery page. Never serve game assets."""
import argparse
import json
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

FILES = {'/': ('index.html', 'text/html; charset=utf-8'),
         '/index.html': ('index.html', 'text/html; charset=utf-8'),
         '/recovery.js': ('recovery.js', 'text/javascript; charset=utf-8'),
         '/recovery.css': ('recovery.css', 'text/css; charset=utf-8'),
         '/startup-inventory.json': ('startup-inventory.json', 'application/json; charset=utf-8')}
SERVICE = 'recovery-only'


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def respond(self, head):
        name = urlsplit(self.path).path
        if name not in FILES:
            self.send_error(404, 'Game assets are quarantined')
            return
        file, content_type = FILES[name]
        data = (self.root / file).read_bytes()
        self.server.requests += 1
        if len(data) > 65536 or self.server.requests > 100 or self.server.sent + len(data) > 1048576:
            self.send_error(429, 'Recovery inspection budget exceeded')
            return
        self.server.sent += len(data)
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-src 'none'; object-src 'none'; form-action 'none'")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def log_message(self, format, *args):
        print(json.dumps({'atMonotonic': time.monotonic(), 'request': args[0], 'status': args[1] if len(args) > 1 else None}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=5202)
    parser.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        raise SystemExit('Run duration must be 1–300 seconds; no unattended service.')
    for filename, _ in FILES.values():
        if not (args.root / filename).is_file() or (args.root / filename).stat().st_size > 65536:
            raise SystemExit('Missing or oversized recovery asset: ' + filename)
    with HTTPServer(('127.0.0.1', args.port), partial(Handler, root=args.root.resolve())) as server:
        server.requests = server.sent = 0
        server.timeout = .5
        deadline = time.monotonic() + args.seconds
        print(json.dumps({'service': SERVICE, 'port': args.port, 'deadlineSeconds': args.seconds}), flush=True)
        while time.monotonic() < deadline:
            server.handle_request()
        print(json.dumps({'stopped': 'time limit', 'requests': server.requests, 'bytes': server.sent}), flush=True)


if __name__ == '__main__':
    main()
