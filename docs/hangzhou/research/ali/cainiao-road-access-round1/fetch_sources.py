"""Archive public official search results and public OSM histories; shared data is read only."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,re,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent
REF=ROOT/'references'
API='https://www.yuhang.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info'
APIJS=ROOT.parent/'cainiao-annex-round2/references/gov-searchresults-api.js'
text=APIJS.read_text()
match=re.search(r'"6N89tbnrVTYIQK5jt7q3T": "([^"]+)"',text)
content=match.group(1) if match else 'content'
queries=[('yunlian-title','云联路','title'),('cainiao-north-title','菜鸟北路','title'),('yunlian-full','云联路','title,'+content),('cainiao-north-full','菜鸟北路','title,'+content)]
requests=[]
for slug,q,pos in queries:
 params=dict(q=q+'#',serviceId='YcTOd1ftgC5dxzJ8RhCBN',websiteid='330110000000',cateid='6N89tbnrVTYIQK5jt7q3T',p='1',pg='50',pos=pos)
 requests.append((slug,API+'?'+urllib.parse.urlencode(params),'json'))
requests += [('gov-2023-opening','https://www.yuhang.gov.cn/art/2023/5/11/art_1229175530_4164198.html','html')]
for way in [779247995,779247992,1350297693,1466397036,1466397037,1466397038,1466397039,1228913715]:
 requests.append(('osm-way-'+str(way)+'-history','https://api.openstreetmap.org/api/0.6/way/'+str(way)+'/history','xml'))
def fetch(item):
 slug,url,ext=item; filename=slug+'.'+ext
 out=dict(id=slug,url=url,retrievedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),filename='references/'+filename)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'GTA-HZ-evidence/1.0 (public road source archive)'})
  with urllib.request.urlopen(req,timeout=45) as r:
   data=r.read();out.update(status=r.status,finalUrl=r.url,contentType=r.headers.get('Content-Type'))
  (REF/filename).write_bytes(data);out.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
  if ext=='json':
   obj=json.loads(data); links=[]
   def walk(o):
    if isinstance(o,dict):
     if 'url' in o and ('title' in o or 'title_str' in o): links.append({k:v for k,v in o.items() if k in ['url','title','title_str','createdate','pubdate']})
     for v in o.values():walk(v)
    elif isinstance(o,list):
     for v in o:walk(v)
   walk(obj);(REF/(slug+'-links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2)+'\n');out['links']=len(links)
 except Exception as e:out['error']=repr(e)
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,requests))
(ROOT/'source-fetches.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
for r in results:print(r['id'],r.get('status'),r.get('bytes'),r.get('links'),r.get('error',''))
