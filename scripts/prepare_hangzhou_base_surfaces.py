"""Prepare disjoint Hangzhou base surfaces for an isolated intermediate export.

This stage contains no southern ocean/backdrop, preserves polygon holes, and
does not union elevated and ground carriageways. Decks, ramps and terrain
integration are explicit pending outputs, never a claimed playable delivery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shapely
from shapely.geometry import Polygon,LineString,box
from city_config import ROOT
from hangzhou_exclusions import normalized_exclusion_ids

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def polygon(rings):return shapely.make_valid(Polygon(rings[0],rings[1:]))
def triangles(geometry):
 result=[]
 collection=shapely.constrained_delaunay_triangles(geometry)
 def visit(g):
  if g.geom_type=='Polygon':
   points=list(g.exterior.coords)[:3]
   if g.area>.000001:result.append([[round(x,4),round(z,4)] for x,z in points])
  else:
   for part in getattr(g,'geoms',[]):visit(part)
 visit(collection)
 return result

def prepare(source,output,candidates=()):
 source=Path(source).resolve();output=Path(output).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate directory required')
 manifest=json.loads((source/'skeleton-manifest.json').read_text())
 for name,sha in manifest['sha256'].items():
  if digest(source/name)!=sha:raise ValueError('Changed source skeleton')
 city=json.loads((source/'city.json').read_text())
 if city['meta']['cityId']!='hangzhou':raise ValueError('Hangzhou geographic source required')
 exclusions=set();deliveries=[]
 for item in candidates:
  path=Path(item).resolve();record=json.loads(path.read_text())
  if record['cityId']!='hangzhou' or record['sourceSnapshotSha256']!=manifest['sourceSha256']:raise ValueError('Landmark source mismatch')
  for name,key in [('artifact','artifactSha256'),('sourceModule','sourceModuleSha256'),('spec','specSha256')]:
   if digest(ROOT/record[name])!=record[key]:raise ValueError('Changed landmark '+name)
  spec=json.loads((ROOT/record['spec']).read_text())
  excluded=normalized_exclusion_ids(record['baseBuildingIdsToExclude'],spec)
  record={**record,'baseBuildingIdsToExclude':excluded}
  exclusions.update(excluded);deliveries.append(record)
 buildings=[b for b in city['buildings'] if b['id'] not in exclusions]
 land_polygons=[Polygon(r[0],r[1:]) for r in city['land']]
 if any(not p.is_valid for p in land_polygons):raise ValueError('Invalid land topology; regenerate skeleton with topology-preserving precision')
 land=shapely.union_all(land_polygons)
 water=shapely.union_all([polygon(w['rings']) for w in city['water']])
 green=shapely.union_all([polygon(g['rings']) for g in city['green']]).intersection(land).difference(water)
 layers={'land':land.difference(green).difference(water),'park':green,'water':water}
 def ground_road(r):return r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no'
 ground_roads=[r for r in city['roads'] if ground_road(r)]
 elevated=[r for r in city['roads'] if not ground_road(r)]
 print('Consolidate ground-only road surfaces',len(ground_roads),flush=True)
 asphalt=shapely.union_all([LineString(r['points']).buffer(r['width']/2,cap_style=2,join_style=2) for r in ground_roads])
 paved=shapely.union_all([LineString(r['points']).buffer(r['width']/2+1.8,cap_style=2,join_style=2) for r in ground_roads]).difference(asphalt)
 output.mkdir(parents=True,exist_ok=True)
 counts={}
 for name,geometry in {**layers,'asphalt':asphalt,'pavement':paved}.items():
  tris=triangles(geometry);counts[name]=len(tris)
  (output/(name+'.json')).write_text(json.dumps(tris,separators=(',',':')))
  print(name,len(tris),'triangles',flush=True)
 # Closed walls include every interior ring; roofs triangulate actual holes.
 for b in buildings:b['roofTriangles']=triangles(polygon(b['rings']))
 (output/'buildings.json').write_text(json.dumps(buildings,ensure_ascii=False,separators=(',',':')))
 city['buildings']=buildings;city['meta']['counts']['buildings']=len(buildings)
 city['meta']['status']='base-mesh-intermediate-not-publishable'
 (output/'city.json').write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
 (output/'pending-road-surfaces.json').write_text(json.dumps(elevated,ensure_ascii=False,separators=(',',':')))
 exclusions_record={'cityId':'hangzhou','baseBuildingIds':sorted(exclusions),'inputCitySha256':digest(source/'city.json'),
  'candidateCitySha256':digest(output/'city.json'),'landmarks':deliveries,
  'facadeStatus':'not generated; must use same filtered buildings when generated','collisionStatus':'detail footprints and physical access pending'}
 (output/'building-exclusions.json').write_text(json.dumps(exclusions_record,ensure_ascii=False,indent=2)+'\n')
 files=[p.name for p in output.iterdir() if p.is_file()]
 report={'schemaVersion':1,'cityId':'hangzhou','sourceSkeleton':str(source.relative_to(ROOT)),
  'sourceSha256':manifest['sourceSha256'],'sha256':{name:digest(output/name) for name in files},
  'triangles':counts,'buildings':len(buildings),'excludedBuildingIds':sorted(exclusions),'groundRoads':len(ground_roads),
  'pendingElevatedOrTunnelRoads':len(elevated),'landWaterOverlapArea':float(land.intersection(water).area),
  'renderedLandWaterOverlapArea':float(layers['land'].intersection(water).area),
  'groundGreenOverlapArea':float(layers['land'].intersection(green).area),
  'status':'flat-intermediate-mesh-data-only',
  'pending':['DSM terrain integration','elevated decks ramps and tunnels','lane markings','all street placements',
    'near facade chunks','collision detail geometry','game loading and controls','visual and performance acceptance']}
 (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
 p.add_argument('--landmark-candidate',action='append',default=[])
 a=p.parse_args();prepare(a.input,a.output,a.landmark_candidate)
