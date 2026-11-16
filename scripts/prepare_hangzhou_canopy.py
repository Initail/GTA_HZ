"""Regional canopy points with whole-crown clearance and fixed source hashes.

Estimated species mixes/positions, not surveyed individual trees. No Blender
imports, no changes to original Shenzhen planting or prototype bytes.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,shutil
from pathlib import Path
from collections import Counter
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
from city_config import ROOT,load_city
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(rings):
 p=Polygon(rings[0],rings[1:])
 if not p.is_valid:raise ValueError('Invalid source polygon')
 return p
def prepare(city_root,family,output,reserved=()):
 city_root,family,output=map(lambda p:Path(p).resolve(),[city_root,family,output]);profile=load_city('hangzhou');policy=profile['vegetation'];scale=profile['geography']['scale']
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 city=json.loads((city_root/'city.json').read_text());manifest_path=family/'landscape/canopy/manifest.json';manifest=json.loads(manifest_path.read_text());delivery=json.loads((family/'delivery.json').read_text())
 if city['meta']['cityId']!='hangzhou' or manifest['cityId']!='hangzhou' or digest(manifest_path)!=delivery['manifestSha256']:raise ValueError('Wrong/changed candidate')
 for source in manifest['sourceInputs']:
  p=ROOT/source['path']
  if digest(p)!=source['sha256']:
   snapshot=ROOT/'docs/hangzhou/audit'/('city-config-hangzhou-'+source['sha256']+'.json')
   if source['path']!='config/cities/hangzhou.json' or not snapshot.exists() or digest(snapshot)!=source['sha256']:
    raise ValueError('Changed vegetation source '+source['path'])
   old=json.loads(snapshot.read_text())
   if old['geography']!=profile['geography']:raise ValueError('Changed vegetation geographic scale/frame')
 for model in manifest['models']:
  if digest(family/'landscape'/model['file'])!=model['sha256']:raise ValueError('Changed canopy model')
 land=shapely.union_all([poly(r) for r in city['land']]);water=shapely.union_all([poly(w['rings']) for w in city['water']]);shapely.prepare(land);shapely.prepare(water)
 solids=[poly(b['rings']) for b in city['buildings']];inputs={str(manifest_path.relative_to(ROOT)):digest(manifest_path),str((city_root/'city.json').relative_to(ROOT)):digest(city_root/'city.json')}
 for filename in reserved:
  p=Path(filename).resolve();v=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=digest(p)
  for site in v.get('sites',[]) or [v['site']]:solids.append(Polygon(site['footprint']).buffer(2))
 solid_tree=STRtree(solids);carriageways=[LineString(r['points']).buffer(r['width']/2) for r in city['roads']];road_tree=STRtree(carriageways)
 primary=[LineString(r['points']) for r in city['roads'] if r['kind'] in ['trunk','primary'] and r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no'];primary_tree=STRtree(primary)
 lamps_path=city_root/'lamps.json';signals_path=city_root/'signals/traffic-signals.json';bench_path=city_root/'street/manifest.json'
 lights=[Point(p[0],p[1]) for p in json.loads(lamps_path.read_text())]
 lights += [Point(a['x'],a['z']) for j in json.loads(signals_path.read_text())['junctions'] for a in j['arms']]
 lights += [Point(b['x'],b['z']) for b in json.loads(bench_path.read_text())['placements']]
 light_tree=STRtree(lights)
 for p in [lamps_path,signals_path,bench_path]:inputs[str(p.relative_to(ROOT))]=digest(p)
 lake=shapely.union_all([poly(w['rings']) for w in city['water'] if w['id']=='relation/2308774']);rng=random.Random(20261014);species=manifest['species'];index={s['id']:i for i,s in enumerate(species)}
 trees=[];cells={};counts=Counter();rejected=Counter();band=policy['streetBandRealMetres']*scale
 # Allocate density across every parcel. Never exhaust the budget in source
 # extraction order: a large western forest must not remove eastern parks.
 green_polygons=[poly(g['rings']) for g in city['green']]
 expected=sum(p.area/(policy['spacingGame']*(4 if p.area>40000 else 1))**2 for p in green_polygons)
 density_factor=max(1,math.sqrt(expected/(policy['maxTrees']*.9)))
 def add(x,z,sid,variation,basis):
  x,z,variation=round(x,3),round(z,3),round(variation,4)
  i=index[sid];s=species[i];radius=s['crown']/2*variation;height=s['height']*variation;point=Point(x,z);crown=point.buffer(radius)
  if not land.covers(crown) or water.intersects(point.buffer(policy['waterClearanceGame'])):rejected['land-water']+=1;return False
  if len(solid_tree.query(crown.buffer(policy['buildingClearanceGame']),predicate='intersects')):rejected['building-reserved']+=1;return False
  if len(road_tree.query(crown.buffer(policy['roadClearanceGame']),predicate='intersects')):rejected['all-carriageways']+=1;return False
  if len(light_tree.query(point.buffer(policy['lightClearanceGame']),predicate='intersects')):rejected['lights-benches']+=1;return False
  cell=(math.floor(x/12),math.floor(z/12))
  if any(math.hypot(x-t[0],z-t[1])<max(3,(radius+t[2])*.9) for u in range(cell[0]-1,cell[0]+2) for v in range(cell[1]-1,cell[1]+2) for t in cells.get((u,v),[])):rejected['tree-spacing']+=1;return False
  trees.append([round(x,3),round(z,3),i,round(variation,4),round(rng.uniform(-math.pi,math.pi),4)]);cells.setdefault(cell,[]).append([x,z,radius]);counts[basis+':'+sid]+=1;return True
 for number,(green,p) in enumerate(zip(city['green'],green_polygons)):
  shapely.prepare(p);x0,z0,x1,z1=p.bounds;seed=random.Random(int(hashlib.sha256((green['id']+str(number)).encode()).hexdigest()[:12],16));step=policy['spacingGame']*density_factor*(4 if p.area>40000 else 1)
  for x in range(math.ceil(x0/step),math.floor(x1/step)+1):
   for z in range(math.ceil(z0/step),math.floor(z1/step)+1):
    px,pz=x*step+seed.uniform(-step*.28,step*.28),z*step+seed.uniform(-step*.28,step*.28);point=Point(px,pz)
    if not p.covers(point):continue
    near_primary=bool(primary) and primary[int(primary_tree.nearest(point))].distance(point)<band
    if near_primary:
     if seed.random()<.28:continue # clustered gaps/window, not a continuous crown wall
     sid=seed.choice(['camphor','plane','ginkgo','sweetgum']);target=seed.uniform(*policy['streetHeightRangeRealMetres'])*scale;variation=target/species[index[sid]]['height'];basis='estimated-primary-edge-tier'
    elif lake.distance(point)<90:
     sid=seed.choice(['willow','peach','camphor','osmanthus']);variation=seed.uniform(.85,1.12);basis='source-informed-west-lake'
    elif '山' in green['name']:
     sid=seed.choice(['masson-pine','camphor','sweetgum']);variation=seed.uniform(.85,1.15);basis='source-informed-hillside'
    else:sid=seed.choice(['camphor','ginkgo','osmanthus','sweetgum','plane']);variation=seed.uniform(.85,1.12);basis='estimated-mixed-green'
    add(px,pz,sid,variation,basis)
  if number%500==0:print('green',number,'trees',len(trees),flush=True)
 if len(trees)>policy['maxTrees']:raise ValueError('Regional density budget exceeded; do not truncate districts')
 output.mkdir(parents=True,exist_ok=True);dest=output/'landscape';shutil.copytree(family/'landscape',dest)
 planting={'version':1,'cityId':'hangzhou','species':species,'trees':trees,'units':'game coordinates; prototype scale once, variation only','sourceStatus':'source green polygons and estimated regional mixtures; not a tree census'}
 (dest/'canopy-trees.json').write_text(json.dumps(planting,ensure_ascii=False,separators=(',',':')))
 # Keep legacy layer interface, using region-specific trees for its three slots.
 original=ROOT/'public/city/landscape';old_manifest=json.loads((original/'manifest.json').read_text());models=[]
 for model in old_manifest['models']:
  if model['id'] in ['banyan','banyan-lod','palm','palm-lod','orchid-tree','orchid-tree-lod']:continue
  models.append(model);shutil.copyfile(original/model['file'],dest/model['file'])
 for asset in ['foliage-atlas-padded.png']:shutil.copyfile(original/asset,dest/asset)
 by_model={m['id']:m for m in manifest['models']}
 for sid in policy['baseTreeNames']:
  for suffix,source_suffix in [('', ''),('-lod','-far')]:
   m=by_model[sid+source_suffix];models.append({'id':sid+suffix,'file':m['file'],'triangles':m['triangles'],'meshes':m['meshes'],'bytes':m['bytes']})
 base_planting={'trees':[],'details':[],'roadDetails':[]}
 (dest/'planting.json').write_text(json.dumps(base_planting,separators=(',',':')))
 (dest/'manifest.json').write_text(json.dumps({**old_manifest,'cityId':'hangzhou','models':models},ensure_ascii=False,indent=2)+'\n')
 report={'kind':'whole-crown-CPU-placement-candidate','cityId':'hangzhou','trees':len(trees),'speciesMix':dict(counts),'rejected':dict(rejected),'inputs':inputs,'canopyPlantingSha256':digest(dest/'canopy-trees.json'),
  'originalPlantingUntouchedSha256':digest(original/'planting.json'),'prototypeUnits':'game, no second .60',
  'allGreenParcelsVisited':len(green_polygons),'densityFactor':density_factor,'largeParcelSpacingGame':policy['spacingGame']*density_factor*4,
  'pending':['regional low-layer details and street source tree points','terrain/bridge/platform ground attachment','willow/road/camera canopy shape','LOD/night/rain/browser/performance']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--family',required=True);p.add_argument('--output',required=True);p.add_argument('--reserved',action='append',default=[])
 a=p.parse_args();prepare(a.city_root,a.family,a.output,a.reserved)
