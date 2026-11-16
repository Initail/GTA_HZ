"""Start or reuse the isolated leisure study. Open only its manual entry."""
import argparse,json,socket,subprocess,sys,urllib.request
from pathlib import Path
from open_hangzhou_bicycle_preview import lan_ip
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--no-open',action='store_true');a=p.parse_args()
    for port in range(5206,5212):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=.5) as r:page=r.read(12000).decode('utf-8')
            if '划一程船，等一尾鱼。' in page:
                url=f'http://127.0.0.1:{port}/';print('已有湖畔休闲样片：'+url)
                if not a.no_open:subprocess.run(['open',url],check=True)
                return
        except (OSError,ValueError):pass
    for port in range(5206,5212):
        with socket.socket() as s:
            try:s.bind(('0.0.0.0',port));break
            except OSError:pass
    else:raise SystemExit('5206–5211 已占用，未关闭任何现有服务。')
    child=subprocess.Popen([sys.executable,str(ROOT/'scripts/serve_hangzhou_leisure_preview.py'),'--host','0.0.0.0','--advertise',lan_ip(),'--port',str(port)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    try:
        line=child.stdout.readline();print(line.strip(),flush=True)
        try:info=json.loads(line)
        except ValueError:raise SystemExit('本次没有启动场景，请查看上方原因。')
        print('本机：'+info['localUrl']+'\n同一局域网：'+info['url']+'\n有效至：'+info['expiresAt']+'\n保留此窗口。',flush=True)
        if not a.no_open:subprocess.run(['open',info['localUrl']],check=True)
        for line in child.stdout:print(line,end='',flush=True)
        child.wait()
    except KeyboardInterrupt:pass
    finally:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();child.wait()
if __name__=='__main__':main()
