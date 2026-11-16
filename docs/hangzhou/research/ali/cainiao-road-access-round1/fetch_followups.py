from pathlib import Path
import datetime,hashlib,json,re,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent
API='http://www.yuhang.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info'
js=(ROOT.parent/'cainiao-annex-round2/references/gov-searchresults-api.js').read_text();content=re.search(r'"6N89tbnrVTYIQK5jt7q3T": "([^"]+)"',js).group(1)
requests=[]
for slug,q,pos in [('yunlian-title','云联路','title'),('cainiao-north-title','菜鸟北路','title'),('yunlian-full','云联路','title,'+content),('cainiao-north-full','菜鸟北路','title,'+content)]:
 params=dict(q=q+'#',serviceId='YcTOd1ftgC5dxzJ8RhCBN',websiteid='330110000000',cateid='6N89tbnrVTYIQK5jt7q3T',p='1',pg='50',pos=pos)
 requests.append((slug,API+'?'+urllib.parse.urlencode(params)))
results=[]
for slug,url in requests:
 r={'id':slug,'url':url,'retrievedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'http://www.yuhang.gov.cn/'}),timeout=30) as x:d=x.read();r.update(status=x.status,finalUrl=x.url)
  f=ROOT/'references'/(slug+'.json');f.write_bytes(d);r.update(filename=str(f.relative_to(ROOT)),sha256=hashlib.sha256(d).hexdigest(),bytes=len(d))
  o=json.loads(d);links=[]
  def walk(v):
   if isinstance(v,dict):
    if 'url' in v and ('title' in v or 'title_str' in v):links.append({k:x for k,x in v.items() if k in ['url','title','title_str','createdate','pubdate']})
    for x in v.values():walk(x)
   elif isinstance(v,list):
    for x in v:walk(x)
  walk(o);(ROOT/'references'/(slug+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2)+'\n');r['links']=len(links)
 except Exception as e:r['error']=repr(e)
 results.append(r);print(slug,r.get('status'),r.get('bytes'),r.get('links'),r.get('error',''))
(ROOT/'http-search-fetches.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
