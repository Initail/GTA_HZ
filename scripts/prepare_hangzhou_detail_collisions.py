"""Integrate source-bound exclusions and object collision shapes in candidates only.

No Blender imports, rendered building export or public writes. Conservative
footprints remain candidate collisions until real passages/terrain are tested.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
import shapely
from shapely.geometry import Polygon,Point,box,shape
from shapely.ops import transform
from shapely.strtree import STRtree
from city_config import ROOT,load_city,project
from hangzhou_exclusions import normalized_exclusion_ids
from hangzhou_navigation import nearest_connected_arrival
from hangzhou_surface import Surface
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(source,inventory_path,output):
 source,inventory_path,output=map(lambda p:Path(p).resolve(),[source,inventory_path,output])
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 city=json.loads((source/'city.json').read_text());nav=json.loads((source/'navigation.json').read_text());inventory=json.loads(inventory_path.read_text())
 if city['meta']['cityId']!='hangzhou' or inventory['cityId']!='hangzhou':raise ValueError('Hangzhou only')
 profile=load_city('hangzhou');scale=profile['geography']['scale']
 source_buildings=ROOT/profile['assets']['processedRoot']/'buildings.geojson'
 features={f['id']:f for f in json.loads(source_buildings.read_text())['features']}
 exclusions=set();colliders=[];objects=[];adapters={}
 field=Surface(source) if (source/'geography/manifest.json').exists() else None
 for item in inventory['objects']:
  delivery=ROOT/item['deliveryFile'];d=json.loads(delivery.read_text());spec=json.loads((ROOT/d['spec']).read_text())
  if digest(delivery)!=item['deliverySha256'] or digest(ROOT/d['artifact'])!=d['artifactSha256'] or digest(ROOT/d['sourceModule'])!=d['sourceModuleSha256'] or digest(ROOT/d['spec'])!=d['specSha256']:raise ValueError('Changed candidate '+item['id'])
  ids=normalized_exclusion_ids(d['baseBuildingIdsToExclude'],spec);bounds=item['boundsGameEastUpNorth'];envelope=box(bounds['min'][0],bounds['min'][2],bounds['max'][0],bounds['max'][2]).buffer(2)
  for identifier in ids:
   if identifier not in features:raise ValueError('Excluded building absent from source '+identifier)
   g=transform(lambda x,y,z=None:project(x,y,profile),shape(features[identifier]['geometry']))
   if not g.intersects(envelope):raise ValueError('Exclusion outside current model context '+identifier)
  exclusions.update(ids)
  x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],profile);lm={'id':item['id'],'x':x,'z':z,'y':d.get('baseYGame',0)}
  if d.get('hallBaseYGame') is not None:lm['hallBaseYGame']=d['hallBaseYGame']
  for dep in d.get('sourceInputs',[]):
   if digest(ROOT/dep['path'])!=dep['sha256']:raise ValueError('Changed exported dependency '+dep['path'])
  # The adapter is bound to the exact frozen render source/spec; it replays
  # actual solids and does not turn bridge decks into blocked buildings.
  module_path=ROOT/('scripts/landmarks/qiantang_bridge_collision.py' if item['id']=='qiantang-bridges' else d['sourceModule'])
  if str(module_path.relative_to(ROOT))!=d['sourceModule']:adapters[str(module_path.relative_to(ROOT))]=digest(module_path)
  module_spec=importlib.util.spec_from_file_location('candidate_'+item['id'].replace('-','_'),module_path);module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
  shape_sets=[];vertical_bounds=[];method='object ground_footprints; unverified entrances'
  if hasattr(module,'ground_footprints'):
   for footprint in module.ground_footprints(lm,spec,scale):
    if isinstance(footprint,dict):
     low,high=footprint['minYGame'],footprint['maxYGame']
     if not math.isfinite(low+high) or high<=low:raise ValueError('Invalid vertical detail footprint '+item['id'])
     shape_sets.append([footprint['polygonGame']]);vertical_bounds.append({'minY':low,'maxY':high,'kind':footprint['kind']})
    else:shape_sets.append([footprint]);vertical_bounds.append({})
  elif item['id']=='lingyin-temple':
   shape_sets=[[[list(project(*point,profile)) for point in hall['footprintWGS84']]] for hall in spec['halls']];method='conservative source five-hall envelopes; doors unknown'
  elif item['id']=='big-lotus':
   shape_sets=[[[list(project(*point,profile)) for point in spec[key]] for key in ['outerFootprintWGS84','innerRoofOpeningWGS84']]];method='conservative source annulus; ground portals and bowl level unknown'
  elif item['id'] in ('broken-bridge','west-lake-causeways'):method='walkable surface only; rail/deck height integration pending'
  else:raise ValueError('Collision method not declared '+item['id'])
  for i,rings in enumerate(shape_sets):
   geometry=Polygon(rings[0],rings[1:])
   if not geometry.is_valid or geometry.area<=1e-10:raise ValueError('Invalid detail footprint '+item['id'])
   if any(len(p)!=2 or any(not math.isfinite(v) for v in p) for ring in rings for p in ring):raise ValueError('Invalid projected detail coordinates')
   vertical=(vertical_bounds[i] if vertical_bounds else {}) or {'minY':bounds['min'][1],'maxY':bounds['max'][1],'kind':'conservative-model-envelope'}
   colliders.append({'id':item['id']+':'+str(i),'rings':rings,'height':vertical.get('maxY',1)-vertical.get('minY',0),'style':'landmark-detail',**vertical})
  objects.append({'id':item['id'],'x':x,'z':z,'height':item['heightGame'],'detailCollision':True,
   'baseYGame':lm['y'],'hallBaseYGame':lm.get('hallBaseYGame'),'collisionMethod':method,'artifactSha256':d['artifactSha256'],'sourceModuleSha256':d['sourceModuleSha256'],'specSha256':d['specSha256'],'collisionStatus':'candidate-not-verified'})
 if 'bpy' in sys.modules or 'city_mesh' in sys.modules:raise ValueError('Host collision preparation initialized Blender')
 buildings=[b for b in city['buildings'] if b['id'] not in exclusions and b.get('style')!='landmark-detail'];base_count=len(buildings);buildings+=colliders;city['buildings']=buildings
 # One OSM MultiPolygon legitimately produces several parts with the same
 # source ID. Preserve them, while rejecting repeated geometry or colliders.
 if len({(b['id'],json.dumps(b['rings'],separators=(',',':'))) for b in buildings})!=len(buildings):raise ValueError('Duplicate integrated building geometry')
 if len({b['id'] for b in colliders})!=len(colliders):raise ValueError('Duplicate integrated collider')
 city['meta']['counts']['buildings']=len(buildings);city['meta']['status']='detail-collision-intermediate-not-runtime-accepted'
 land=shapely.union_all([Polygon(r[0],r[1:]) for r in city['land']]);geometries=[Polygon(b['rings'][0],b['rings'][1:]) for b in buildings];tree=STRtree(geometries)
 def blocked(x,z):
  p=Point(x,z);height=field.ground(x,z) if field else 0
  def overlaps(i):
   b=buildings[int(i)];return b.get('maxY',math.inf)>height+.05 and b.get('minY',-math.inf)<height+1.6 and geometries[int(i)].distance(p)<1.15
  return not land.covers(p) or any(overlaps(i) for i in tree.query(p.buffer(1.15)))
 ground_roads=[r for r in city['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no']
 arrivals=[];by_id={o['id']:o for o in objects}
 for landmark in city['landmarks']:
  if landmark['id'] in by_id:
   o=by_id[landmark['id']];landmark.update({k:o[k] for k in ['x','z','height','detailCollision']})
  if blocked(*landmark['arrival']):
   arrival=nearest_connected_arrival([landmark['x'],landmark['z']],ground_roads,nav,blocked,900)
   if not arrival:raise ValueError('No connected clear detail arrival '+landmark['id'])
   landmark.update(arrival)
  if blocked(*landmark['arrival']):raise ValueError('Blocked arrival '+landmark['id'])
  arrivals.append({'id':landmark['id'],'arrival':landmark['arrival'],'blocked':False,'physicalDriving':'unknown'})
 output.mkdir(parents=True,exist_ok=True)
 (output/'city-runtime-collision.json').write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
 collision_manifest={'schemaVersion':1,'cityId':'hangzhou','baseBuildingIds':sorted(exclusions),'collisionFootprints':colliders,'landmarks':objects,
  'status':'collision-only-candidate-not-complete-runtime-manifest','pending':['terrain and source-deck levels','height-aware collision queries for stacked floors','exact portals/passages','visual/context/night/performance/browser']}
 (output/'detail-collision-manifest.json').write_text(json.dumps(collision_manifest,ensure_ascii=False,indent=2)+'\n')
 report={'kind':'source-bound-detail-collision-candidate','inputSha256':{'city':digest(source/'city.json'),'navigation':digest(source/'navigation.json'),'inventory':digest(inventory_path),'sourceBuildings':digest(source_buildings),'preparator':digest(Path(__file__))},'adapterSha256':adapters,
  'baseBuildingsAfterExclusion':base_count,'excludedIds':len(exclusions),'collisionShapes':len(colliders),'landmarkCount':len(objects),
  'arrivals':arrivals,'sourceExclusionPresenceAndContext':True,'cityRuntimeCollisionSha256':digest(output/'city-runtime-collision.json'),
  'pending':collision_manifest['pending']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['baseBuildingsAfterExclusion','excludedIds','collisionShapes','landmarkCount']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--inventory',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();prepare(a.input,a.inventory,a.output)
