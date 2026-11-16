# -*- coding: utf-8 -*-
"""User-invoked launcher: reuse this version or start one bounded manual-entry server."""
import argparse,json,socket,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def lan_ip():
    route=subprocess.run(['route','-n','get','default'],capture_output=True,text=True)
    interface=next((line.split(':',1)[1].strip() for line in route.stdout.splitlines() if line.strip().startswith('interface:')),None)
    if interface:
        result=subprocess.run(['ipconfig','getifaddr',interface],capture_output=True,text=True)
        try:socket.inet_aton(result.stdout.strip());return result.stdout.strip()
        except OSError:pass
    return '127.0.0.1'

def existing_version(port):
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/'%port,timeout=1) as response:
            return 'v13 · 走一走，也骑一程' in response.read(16384).decode('utf-8')
    except (OSError,ValueError):return False

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-open',action='store_true');args=parser.parse_args()
    for port in range(5205,5211):
        if existing_version(port):
            url='http://127.0.0.1:%d/'%port;print('已有 v13 试玩：'+url)
            if not args.no_open:subprocess.run(['open',url],check=True)
            return
    for port in range(5205,5211):
        with socket.socket() as probe:
            try:probe.bind(('0.0.0.0',port))
            except OSError:continue
        break
    else:raise SystemExit('5205–5210 端口已被使用；没有停止任何现有服务。')
    command=[sys.executable,str(ROOT/'scripts/serve_hangzhou_bicycle_demo.py'),'--host','0.0.0.0','--advertise',lan_ip(),'--port',str(port)]
    process=subprocess.Popen(command,cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    try:
        line=process.stdout.readline();print(line.strip(),flush=True)
        try:info=json.loads(line)
        except ValueError:raise SystemExit('试玩未启动。请检查上方信息；没有打开完整游戏。')
        print('本机：'+info['localUrl']+'\n同学同一局域网：'+info['url']+'\n有效至：'+info['expiresAt']+'\n请保留本终端窗口。游戏需在入口页手动点击。',flush=True)
        if not args.no_open:subprocess.run(['open',info['localUrl']],check=True)
        for line in process.stdout:print(line,end='',flush=True)
        process.wait()
    except KeyboardInterrupt:print('\n正在停止本次试玩服务。')
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
