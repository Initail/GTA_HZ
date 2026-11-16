"""Host-side HTTP/byte checks only: no browser, JavaScript execution or GPU."""
import argparse,hashlib,http.client,json,re
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'artifacts/cities/hangzhou/westlake-bicycle-v1'
def main():
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=5205);p.add_argument('--report',required=True);args=p.parse_args()
    output=STAGE/args.report
    if output.exists():raise SystemExit('Use a fresh report')
    connection=http.client.HTTPConnection(args.host,args.port,timeout=3);records=[]
    def request(method,path,body=None,headers=None):
        connection.request(method,path,body,headers or {});r=connection.getresponse();data=r.read();records.append({'method':method,'path':path,'status':r.status,'bytes':len(data)})
        return r,data
    r,data=request('GET','/');assert r.status==200
    page=data.decode();assert 'v13 · 走一走，也骑一程' in page and '<script' not in page and '<canvas' not in page
    token=re.search(r'name="ticket" value="([^"]+)"',page).group(1)
    r,_=request('GET','/assets/main.js');assert r.status==403
    origin='http://%s:%d'%(args.host,args.port)
    r,_=request('POST','/enter',urlencode({'ticket':'incorrect'}),{'Origin':origin,'Content-Type':'application/x-www-form-urlencoded'});assert r.status==403
    r,_=request('POST','/enter',urlencode({'ticket':token}),{'Origin':'http://not-this-preview.invalid','Content-Type':'application/x-www-form-urlencoded'});assert r.status==403
    r,_=request('POST','/enter',urlencode({'ticket':token}),{'Origin':origin,'Content-Type':'application/x-www-form-urlencoded'});assert r.status==303
    cookie=r.getheader('Set-Cookie');assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
    headers={'Cookie':cookie.split(';')[0]}
    report=json.loads((STAGE/'delivery-check-lan-v1.json').read_text())
    for name,expected in report['artifacts'].items():
        url='/play/?quality=low' if name=='dist/index.html' else '/'+name[len('dist/'):]
        r,data=request('GET',url,headers=headers);assert r.status==200,url
        assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],url
    for url,local in [('/vendor/@babylonjs/core/Meshes/mesh.js',ROOT/'node_modules/@babylonjs/core/Meshes/mesh.js'),('/cities/hangzhou/ebikes/ebikes.glb',ROOT/'artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou/ebikes/ebikes.glb')]:
        r,data=request('GET',url,headers=headers);assert r.status==200 and hashlib.sha256(data).digest()==hashlib.sha256(local.read_bytes()).digest(),url
    connection.close()
    result={'version':'demo-v13-bicycle','origin':origin,'hostHttpPassed':True,'peerDeviceVerified':False,'browserStarted':False,'gpuValidated':False,'records':records}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
