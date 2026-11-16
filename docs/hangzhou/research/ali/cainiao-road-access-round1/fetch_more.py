from pathlib import Path
import concurrent.futures,datetime,hashlib,json,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent
API='http://www.yuhang.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info'
queries=[('yunlian-title-page'+str(p),'云联路#',p) for p in range(2,6)]+[('cainiao-title','菜鸟#',1),('yunlian-notice-title','云联路 通告#',1)]
res=[]
def fetch(slug,url,ext):
 r=dict(id=slug,url=url,retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as x:d=x.read();r.update(status=x.status,finalUrl=x.url)
  f=ROOT/'references'/(slug+'.'+ext);f.write_bytes(d);r.update(filename=str(f.relative_to(ROOT)),bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
  if ext=='json':
   o=json.loads(d);a=o['data']['appSearchResultBeanList'];links=[]
   for b in a:
    r['totalHits']=b['mapSearchResult'].get('totalHits');links += [{k:v for k,v in i['data'].items() if k in ['url','title','title_str','createdate']} for i in b['mapSearchResult']['items']]
   (ROOT/'references'/(slug+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2)+'\n');r['links']=len(links)
 except Exception as e:r['error']=repr(e)
 return r
reqs=[]
for slug,q,p in queries:
 params=dict(q=q,serviceId='YcTOd1ftgC5dxzJ8RhCBN',websiteid='330110000000',cateid='6N89tbnrVTYIQK5jt7q3T',p=str(p),pg='15',pos='title')
 reqs.append((slug,API+'?'+urllib.parse.urlencode(params),'json'))
reqs += [('zjol-2026-opening-http','http://zjnews.zjol.com.cn/zjnews/90zxw/202606/t20260603_31702006.shtml','html'),('hangzhouwang-2024-progress-http','http://hznews.hangzhou.com.cn/chengshi/content/2024-03/29/content_8708606.htm','html')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:res=list(p.map(lambda i:fetch(*i),reqs))
(ROOT/'more-search-fetches.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
for r in res:print(r['id'],r.get('status'),r.get('bytes'),r.get('links'),r.get('error',''))
