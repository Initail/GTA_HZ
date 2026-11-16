"""Source-bound ground street placements in an isolated Hangzhou candidate.

Road marking dimensions/spacing follow the original builder. Elevated roads
retain separate identities and surfaces. Never mutates city/spawn/planting.
"""
from __future__ import annotations
import argparse,hashlib,json,math,time
from pathlib import Path
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.ops import transform
from shapely.strtree import STRtree
from city_config import ROOT,load_city,project

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(rings):
 p=Polygon(rings[0],rings[1:])
 if not p.is_valid:raise ValueError('Invalid source polygon; repair at source stage')
 return p
def parts(g,kind):
 if g.is_empty:return []
 if g.geom_type==kind:return [g]
 return [p for child in getattr(g,'geoms',[]) for p in parts(child,kind)]

def prepare(city_file,output,reserved_files=()):
 city_file=Path(city_file).resolve();output=Path(output).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
 c=json.loads(city_file.read_text());profile=load_city('hangzhou')
 started=time.monotonic()
 if c['meta']['cityId']!='hangzhou':raise ValueError('Hangzhou required')
 land=shapely.union_all([poly(r) for r in c['land']]);water=shapely.union_all([poly(w['rings']) for w in c['water']]);water_clearance=water.buffer(.5)
 solids=[poly(b['rings']).buffer(1.2) for b in c['buildings']]
 inputs={'citySha256':digest(city_file)}
 for filename in reserved_files:
  path=Path(filename).resolve();v=json.loads(path.read_text());inputs[str(path.relative_to(ROOT))]=digest(path)
  sites=v.get('sites',[]) or [v['site']]
  for site in sites:
   if not site.get('footprint'):raise ValueError('Explicit reserved footprint required')
   solids.append(Polygon(site['footprint']).buffer(2))
 obstacle=STRtree(solids)
 roads=[r for r in c['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no']
 carriageways=[LineString(r['points']).buffer(r['width']/2,cap_style=2,join_style=2) for r in roads]
 lanes=STRtree(carriageways);asphalt=shapely.union_all(carriageways);shapely.prepare(land);shapely.prepare(water)
 def clear(x,z,margin):
  point=Point(x,z);area=point.buffer(margin)
  return land.covers(area) and not water.intersects(area) and not len(obstacle.query(area,predicate='intersects')) and not len(lanes.query(area,predicate='intersects'))
 lamps=[];paths=[];stripes=[];lamp_index={};checks={'lampRejected':0,'pathRejected':0}
 print('Prepared immutable land/water/road clearance indexes',len(roads),flush=True)
 for index,r in enumerate(roads):
  if index%1000==0:print('Ground street roads',index,'/',len(roads),'seconds',round(time.monotonic()-started,2),flush=True)
  width=r['width'];main=r['kind'] in ('trunk','primary','secondary','tertiary')
  for a,b in zip(r['points'],r['points'][1:]):
   dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
   if length<.01:continue
   nx,nz=-dz/length,dx/length
   if main and length>6:
    for off in (-width/2+.35,width/2-.35):stripes.append(LineString([(a[0]+nx*off,a[1]+nz*off),(b[0]+nx*off,b[1]+nz*off)]).buffer(.055,cap_style=2))
    for j in range(1,max(2,round(width/3))):
     off=-width/2+j*width/max(2,round(width/3))
     for t in range(4,int(length)-4,10):
      t1=min(length-4,t+3.5)
      stripes.append(LineString([(a[0]+dx*t/length+nx*off,a[1]+dz*t/length+nz*off),(a[0]+dx*t1/length+nx*off,a[1]+dz*t1/length+nz*off)]).buffer(.055,cap_style=2))
   if main:
    for t in range(12,int(length)-5,42):
     for side in (-1,1):
      x,z=a[0]+dx*t/length+nx*(width/2+1.2)*side,a[1]+dz*t/length+nz*(width/2+1.2)*side
      key=(math.floor(x/5),math.floor(z/5))
      if not clear(x,z,.45) or any(math.dist([x,z],p)<5 for u in range(key[0]-1,key[0]+2) for v in range(key[1]-1,key[1]+2) for p in lamp_index.get((u,v),[])):
       checks['lampRejected']+=1;continue
      lamps.append([round(x,2),round(z,2),round(nx*side,5),round(nz*side,5)])
      lamp_index.setdefault(key,[]).append([x,z])
   if r['kind']=='trunk' or length<=15:continue
   for side in (-1,1):
    off=(width/2+1.15)*side
    path=LineString([(a[0]+nx*off,a[1]+nz*off),(b[0]+nx*off,b[1]+nz*off)])
    cut=[carriageways[int(i)].buffer(.45) for i in lanes.query(path.buffer(.5))]
    cut += [solids[int(i)] for i in obstacle.query(path.buffer(.5))]
    free=path.intersection(land).difference(water_clearance)
    if cut:free=free.difference(shapely.union_all(cut))
    for line in parts(free,'LineString'):
     if line.length<=8:checks['pathRejected']+=1;continue
     # Store each straight interval, matching the original pedestrian API.
     for aa,bb in zip(line.coords,list(line.coords)[1:]):
      if math.dist(aa,bb)>8:paths.append([*[round(v,2) for v in aa],*[round(v,2) for v in bb]])
 print('Ground placements prepared; consolidate markings',len(stripes),flush=True)
 markings=shapely.union_all(stripes).intersection(asphalt)
 triangles=[[[round(x,4),round(z,4)] for x,z in list(p.exterior.coords)[:3]] for p in parts(shapely.constrained_delaunay_triangles(markings),'Polygon') if p.area>1e-8]
 # Bench identity comes from this extraction, not Shenzhen point lists.
 poi_file=ROOT/profile['assets']['processedRoot']/'pois.geojson';inputs['poisSha256']=digest(poi_file)
 road_lines=[LineString(r['points']) for r in roads];road_index=STRtree(road_lines);benches=[]
 for f in json.loads(poi_file.read_text())['features']:
  if f['properties']['tags'].get('amenity')!='bench' or f['geometry']['type']!='Point':continue
  x,z=project(*f['geometry']['coordinates'],profile)
  if not clear(x,z,1.2):continue
  near=int(road_index.nearest(Point(x,z)));r=roads[near]
  if road_lines[near].distance(Point(x,z))>80:continue
  segment=min(zip(r['points'],r['points'][1:]),key=lambda q:LineString(q).distance(Point(x,z)))
  aa,bb=segment;yaw=math.atan2(bb[0]-aa[0],bb[1]-aa[1])+math.pi/2
  if any(math.dist([x,z],l[:2])<1.5 for l in lamps):continue
  benches.append({'id':f['id'],'x':x,'z':z,'yaw':yaw,'orientation':'parallel to nearest ground source road; estimated game adaptation'})
 output.mkdir(parents=True,exist_ok=True)
 for name,value in [('lamps',lamps),('pedestrian-paths',paths),('roadline-triangles',triangles),('bench-placements',benches)]:
  (output/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')))
 report={'cityId':'hangzhou','kind':'source-bound-ground-street-candidate','inputs':inputs,'groundRoads':len(roads),'lamps':len(lamps),'pedestrianPaths':len(paths),'markingTriangles':len(triangles),'benches':len(benches),'checks':checks,'preparationCpuWallSeconds':time.monotonic()-started,
  'files':{p.name:digest(p) for p in output.iterdir()},'spawnAndSourceCityUnchanged':digest(city_file)==inputs['citySha256'],
  'placementStatus':'CPU geometry clearance only; placements are estimated game adaptation',
  'pending':['terrain elevations','elevated markings/lamps/paths','walk surface slopes','runtime visuals and performance','browser walking/driving']}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--city-file',required=True);p.add_argument('--output',required=True);p.add_argument('--reserved',action='append',default=[])
 a=p.parse_args();prepare(a.city_file,a.output,a.reserved)
