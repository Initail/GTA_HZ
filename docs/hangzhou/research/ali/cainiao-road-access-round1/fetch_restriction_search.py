from pathlib import Path
import concurrent.futures,datetime,hashlib,json,re,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent
API='http://www.yuhang.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info'
js=(ROOT.parent/'cainiao-annex-round2/references/gov-searchresults-api.js').read_text();content=re.search(r'"6N89tbnrVTYIQK5jt7q3T": "([^"]+)"',js).group(1)
queries=[('yunlian-traffic','云联路 交通'),('yunlian-closure','云联路 封闭'),('yunlian-restriction','云联路 禁止'),('cainiao-north-closure','菜鸟北路 封闭'),('cainiao-north-traffic','菜鸟北路 交通')]
def run(item):
 slug,q=item;params=dict(q=q+'#',serviceId='YcTOd1ftgC5dxzJ8RhCBN',websiteid='330110000000',cateid='6N89tbnrVTYIQK5jt7q3T',p='1',pg='15',pos='title,'+content);url=API+'?'+urllib.parse.urlencode(params);r=dict(id=slug,query=q,url=url,retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),page=1,pageSize=15)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as x:d=x.read();r.update(status=x.status,finalUrl=x.url)
  f=ROOT/'references'/(slug+'.json');f.write_bytes(d);r.update(filename=str(f.relative_to(ROOT)),bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
  o=json.loads(d);links=[];r['totalHits']=0
  for b in o['data']['appSearchResultBeanList']:
   r['totalHits']+=b['mapSearchResult'].get('totalHits',0);links += [{k:v for k,v in i['data'].items() if k in ['url','title','title_str','createdate']} for i in b['mapSearchResult']['items']]
  (ROOT/'references'/(slug+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2)+'\n');r['links']=len(links)
 except Exception as e:r['error']=repr(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:rs=list(p.map(run,queries))
(ROOT/'restriction-search-fetches.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n')
for r in rs:print(r['id'],r.get('status'),r.get('totalHits'),r.get('links'),r.get('error',''))
