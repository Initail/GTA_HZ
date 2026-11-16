from pathlib import Path
import concurrent.futures,datetime,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
reqs=[('government-duanqiao-lotus','http://www.hangzhou.gov.cn/art/2022/2/15/art_812268_59049995.html'),('government-lotus-net','http://www.hzzx.gov.cn/cshz/content/2024-04/16/content_8716273.htm'),('operator-lock-drainage-report','http://hznews.hangzhou.com.cn/chengshi/content/2024-06/25/content_8749247_2.htm')]
def fetch(item):
 slug,url=item;r=dict(id=slug,url=url,retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as x:d=x.read();r.update(status=x.status,finalUrl=x.url)
  p=ROOT/'references'/(slug+'.html');p.write_bytes(d);r.update(filename=str(p.relative_to(ROOT)),bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
 except Exception as e:r['error']=repr(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:res=list(p.map(fetch,reqs))
(ROOT/'reference-fetches.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
for r in res:print(r['id'],r.get('status'),r.get('bytes'),r.get('error',''))
