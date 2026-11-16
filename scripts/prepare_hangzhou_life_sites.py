"""Place original game-unit service prefabs and five explicit mission points.

Uses ground roads in the main OSM component and actual source polygon holes.
No clone of Shenzhen positions, no monetary/mechanic/vehicle changes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.strtree import STRtree
from city_config import ROOT,load_city,project,unproject
from hangzhou_navigation import nearest_connected_arrival

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def prepare(source,output,locations):
 source=Path(source).resolve();output=Path(output).resolve();locations=Path(locations).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh artifacts candidate required')
 city=json.loads((source/'city.json').read_text());graph=json.loads((source/'navigation.json').read_text())
 settings=json.loads(locations.read_text());profile=load_city('hangzhou')
 if city['meta']['cityId']!='hangzhou' or settings['cityId']!='hangzhou':raise ValueError('Hangzhou sources required')
 land=shapely.union_all([Polygon(r[0],r[1:]) for r in city['land']])
 shapes=[Polygon(b['rings'][0],b['rings'][1:]).buffer(2) for b in city['buildings']]
 shapes += [Polygon(w['rings'][0],w['rings'][1:]).buffer(2) for w in city['water']]
 shapes += [LineString(r['points']).buffer(r['width']/2+1) for r in city['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no']
 obstacles=STRtree(shapes)
 marks={m['id']:m for m in city['landmarks']}
 main=graph['meta']['mainComponent']
 roads=[r for r in city['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no'
   and r['kind'] in ('primary','secondary','tertiary','residential','unclassified','service','living_street')
   and graph['componentIds'][graph['roadNodes'][r['id']][0]]==main]
 def target(record):
  if record.get('landmark'):
   mark=marks[record['landmark']];point=[mark['x'],mark['z']];identity=mark['sourceFeatureIds']
  else:
   path=ROOT/profile['assets']['processedRoot']/(record['sourceLayer']+'.geojson')
   found=next(f for f in json.loads(path.read_text())['features'] if f['id']==record['sourceFeatureId'])
   center=shape(found['geometry']).centroid;point=list(project(center.x,center.y,profile));identity=[found['id']]
  offset=record.get('offsetGame',[0,0]);return [point[0]+offset[0],point[1]+offset[1]],identity
 sites=[]
 for seed in settings['sites']:
  point,identity=target(seed);candidates=[]
  for road in roads:
   for a,b in zip(road['points'],road['points'][1:]):
    length=math.dist(a,b)
    if length<.5:continue
    if LineString([a,b]).distance(Point(point))>settings['searchRadiusGame']:continue
    yaw=math.atan2(b[0]-a[0],b[1]-a[1]);steps=max(2,math.ceil(length/12))
    for i in range(steps+1):
     t=i/steps;px=a[0]+(b[0]-a[0])*t;pz=a[1]+(b[1]-a[1])*t
     if math.dist([px,pz],point)>settings['searchRadiusGame']:continue
     for side in (-1,1):
      nx=math.cos(yaw)*side;nz=-math.sin(yaw)*side
      clearance=seed.get('clearanceGame',settings['prefabClearanceGame']);offset=road['width']/2+max(8,clearance['depth']/2+2)
      x,z=px+nx*offset,pz+nz*offset;heading=math.atan2(nx,nz);co,si=math.cos(heading),math.sin(heading)
      w,d=clearance['width']/2,clearance['depth']/2
      corners=[(x+lx*co+lz*si,z-lx*si+lz*co) for lx,lz in [(-w,-d),(w,-d),(w,d),(-w,d)]]
      footprint=Polygon(corners)
      if not land.covers(footprint) or len(obstacles.query(footprint,predicate='intersects')):continue
      if any(footprint.distance(Polygon(s['footprint']))<10 for s in sites):continue
      candidates.append((math.dist([px,pz],point),{'id':seed['id'],'name':seed['name'],'x':x,'z':z,'heading':heading,
        'arrival':[px,pz],'yaw':yaw,'road':road['name'],'roadId':road['id'],'roadWidth':road['width'],
        'footprint':corners,'sourceFeatureIds':identity,'sourceWGS84':list(unproject(x,z,profile)),
        'arrivalWGS84':list(unproject(px,pz,profile)),'prefabUnits':'existing game units; no additional geographic scaling'}) )
  if not candidates:raise ValueError('No clear connected site: '+seed['id'])
  site=min(candidates,key=lambda c:c[0])[1];sites.append(site);print('site',site['id'],site['road'],flush=True)
 mission={s['id']:s['arrival'] for s in sites};details={}
 wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']])
 buildings=STRtree([Polygon(b['rings'][0],b['rings'][1:]).buffer(2) for b in city['buildings']])
 def blocked(x,z):
  p=Point(x,z);return not land.covers(p) or wet.covers(p) or len(buildings.query(p,predicate='intersects'))>0
 for key,record in settings['missionPoints'].items():
  point,identity=target(record);arrival=nearest_connected_arrival(point,roads,graph,blocked,settings['searchRadiusGame'])
  if not arrival:raise ValueError('No clear mission point: '+key)
  mission[key]=arrival['arrival'];details[key]={**record,**arrival,'sourceFeatureIds':identity}
 result={'schemaVersion':1,'version':1,'cityId':'hangzhou','originWGS84':profile['geography']['originWGS84'],
  'horizontalScale':profile['geography']['scale'],'sites':sites,'missionPlaces':mission,'missionPointDetails':details,
  'inputs':{'citySha256':digest(source/'city.json'),'navigationSha256':digest(source/'navigation.json'),
   'locationsSha256':digest(locations)},'source':'Original fictional community services on mapped clear roadside plots',
  'status':'geographic-candidate-not-physical-gameplay-accepted',
  'pending':['DEM/site platform','landmark detail collision','terrain approach','all six contracts and upgrades',
   'story branches','cafe and street placements','actual driving and E/F interactions']}
 output.mkdir(parents=True,exist_ok=True)
 (output/'life-sites.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'output':str(output),'missionPlaces':mission,'pending':result['pending']},ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
 p.add_argument('--locations',default='config/hangzhou/locations.json');a=p.parse_args();prepare(a.input,a.output,a.locations)
