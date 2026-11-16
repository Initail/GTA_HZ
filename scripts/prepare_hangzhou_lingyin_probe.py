"""Bind a small Lingyin precinct to frozen source geometry; no city writes."""
from pathlib import Path
import json, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]).resolve();assert not out.exists();out.relative_to(ROOT/'artifacts/cities/hangzhou/city-leisure-v15')
out.mkdir()
files={};sources=[]
def bind(url,p):
 p=Path(p);b=p.read_bytes();r={'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};files[url]=r;return dict(file=url,bytes=r['bytes'],sha256=r['sha256'])
def read(p):
 p=ROOT/p;b=p.read_bytes();sources.append({'file':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return json.loads(b)
prefix='artifacts/cities/hangzhou/lingyin-entry-v1/'
entry=prefix+'entry-ground-v1/';local=entry+'path-surface-v1/'
geo=read(entry+'local-geography.json');surfaces=read(sys.argv[2] if len(sys.argv)>2 else local+'site-surfaces-candidate.json');masks=read(local+'local-city-masks.json');solids=read(local+'local-closed-structures.json')['solids'];route=read(local+'runtime-audit-v2.json')['route']
exclusions=set(read(prefix+'atomic-integration-contract.json')['sourceIds'])
def polygons(g):
 if g['type']=='Polygon':return [g['coordinates']]
 if g['type']=='MultiPolygon':return g['coordinates']
 if g['type']=='GeometryCollection':return [p for x in g['geometries'] for p in polygons(x)]
 raise ValueError(g['type'])
roads=read(local+'local-collision-roads.json')['roads'];level_roads=read(entry+'local-road-levels.json')['roads']
assert len(level_roads)==len(roads)
for road in level_roads:
 match=next(r for r in roads if r['id']==road['id']);assert road['points']==match['points'] and road['heights']==match['heights']
city={'meta':{'cityId':'hangzhou'},'roads':roads,'buildings':[x for x in masks['selected']['buildings'] if x['id'] not in exclusions]+solids,'landmarks':[],
 'land':[p for x in masks['selected']['land'] for g in x['clippedGeometries'] for p in polygons(g)],'water':[{'rings':p} for x in masks['selected']['water'] for g in x['clippedGeometries'] for p in polygons(g)]}
streams=[];textures={}
for role in ['terrain','roads']:
 base=ROOT/'artifacts/cities/hangzhou/stream-mesh-v1'/role;manifest=read(str((base/'manifest.json').relative_to(ROOT)))
 textures[role]=manifest['textures']
 for f in textures[role]:
  r=bind('/'+role+'/'+f['file'],base/f['file']);assert r['sha256']==f['sha256'] and r['bytes']==f['bytes']
 for tile in manifest['tiles']:
  if tile['tile'] not in [[-6,-4],[-5,-4]]:continue
  r=bind('/'+role+'/'+tile['file'],base/tile['file']);assert r['sha256']==tile['sha256'] and r['bytes']==tile['bytes'];streams.append(dict(tile,role=role,baseUrl='/'+role+'/'))
models=[]
for name,file in [('halls','artifacts/cities/hangzhou/landmarks/lingyin-site-v2/lingyin-temple.glb'),('annex','artifacts/cities/hangzhou/lingyin-context-batched-v1/context.glb')]:
 models.append(dict(bind('/'+name+'.glb',ROOT/file),id=name))
placements=read('artifacts/cities/hangzhou/city-leisure-v15/site-path-integration-v1/placement-audit.json')
cm=read('artifacts/cities/hangzhou/city-leisure-v15/public/cities/hangzhou/landscape/canopy/manifest.json');lm=read('artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou/landscape/manifest.json');trees=[]
for row in placements['canopyCandidates']+placements['baseTreeCandidates']:
 t=row['placement'];name=cm['species'][t[2]]['id'] if row['kind']=='canopy' else ['camphor','ginkgo','osmanthus'][t[2]]
 model=next(m for m in (cm if row['kind']=='canopy' else lm)['models'] if m['id']==name)
 file=ROOT/'artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou/landscape'/model['file'];record=bind('/tree-'+name+'.glb',file)
 if 'sha256' in model:assert record['sha256']==model['sha256']
 trees.append(dict(record,id='tree-'+str(row['index']),placement=t))
terrain=bind('/terrain.bin',ROOT/geo['terrain']['file']);assert terrain['sha256']==geo['terrain']['sha256']
bind('/meshopt_decoder.js',ROOT/'node_modules/meshoptimizer/meshopt_decoder.cjs')
payload={'scope':'fixed Lingyin approach only; actual terrain/road tiles and candidate halls/annex; not full city', 'surfaces':surfaces,'geo':geo['manifest'],'city':city,'levelRoads':level_roads,
 'terrain':terrain,'streams':streams,'textures':textures,'models':models,'trees':trees,'starts':[route[1500],route[1690]],'sources':sources,
 'limits':{'seconds':25,'canvasPixels':900*480,'triangleEstimate':sum(x['triangles'] for x in streams)+29784+30423+2047+5*2000,'maxAssetContainers':len(streams)+len(models)+len(trees)},
 'omissions':['outside the two source terrain/road tiles','distant buildings and facade patches','all but five fixed trees; low plants and supplemental plants','moving actors','full-world lights and effects','real gate operations and exact annex colliders']}
assert len(streams)==4 and payload['limits']['triangleEstimate']<150000 and payload['limits']['maxAssetContainers']<=32
(out/'scene-data.json').write_text(json.dumps(payload)+'\n');bind('/scene-data.json',out/'scene-data.json')
(out/'asset-files.json').write_text(json.dumps(files,indent=2)+'\n')
(out/'preflight.json').write_text(json.dumps({'scope':payload['scope'],'limits':payload['limits'],'assetBytes':sum(v['bytes'] for v in files.values()),'browserAccepted':False,'wholeCityAccepted':False},indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':sum(v['bytes'] for v in files.values()),'limits':payload['limits']}))
