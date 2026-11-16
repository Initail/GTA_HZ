from pathlib import Path
import datetime,hashlib,json,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent
API='http://www.yuhang.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info'
queries=[('yunlian-phrase','云联路'),('cainiao-north-phrase','菜鸟北路'),('yunlian-quoted','"云联路"'),('cainiao-north-quoted','"菜鸟北路"')]
res=[]
for slug,q in queries:
 params=dict(q=q,serviceId='YcTOd1ftgC5dxzJ8RhCBN',websiteid='330110000000',cateid='6N89tbnrVTYIQK5jt7q3T',p='1',pg='50',pos='title')
 url=API+'?'+urllib.parse.urlencode(params);r=dict(id=slug,url=url,retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as x:d=x.read();r.update(status=x.status,finalUrl=x.url)
  f=ROOT/'references'/(slug+'.json');f.write_bytes(d);r.update(filename=str(f.relative_to(ROOT)),bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
  o=json.loads(d);a=o['data']['appSearchResultBeanList'][0]['mapSearchResult'];r['totalHits']=a['totalHits'];links=[{k:v for k,v in i['data'].items() if k in ['url','title','title_str','createdate']} for i in a['items']]
  (ROOT/'references'/(slug+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2)+'\n');print(slug,a['totalHits'],len(links));print(json.dumps(links,ensure_ascii=False))
 except Exception as e:r['error']=repr(e);print(r)
 res.append(r)
(ROOT/'exact-search-fetches.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
