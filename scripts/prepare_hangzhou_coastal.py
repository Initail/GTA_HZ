"""Prepare source-bound cross-water identity, safe public park lights and shore distance.
No invented sea, geometric turn connections, radial deck raising or model export.
"""
from __future__ import annotations
import argparse,json,math,time
from collections import defaultdict,deque,Counter
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.strtree import STRtree
from rasterio.features import rasterize
from affine import Affine
from hangzhou_surface import Surface,digest
from pack_hangzhou_ambient import png
ROOT=Path(__file__).resolve().parents[1]
def parts(g,kind):
    if g.is_empty:return []
    if g.geom_type==kind:return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child,kind)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--city-root',required=True);ap.add_argument('--placements-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=ROOT/a.city_root;placed=ROOT/a.placements_root;out=(ROOT/a.output).resolve();inputs={};began=time.monotonic()
    if ROOT/'artifacts' not in out.parents or out.exists():raise ValueError('Fresh candidate required')
    def read(p):inputs[str(p.relative_to(ROOT))]=digest(p);return json.loads(p.read_text())
    city=read(root/'city.json');config=read(ROOT/'config/hangzhou/waterfront.json');raw=read(ROOT/'data/processed/hangzhou-261011-extended/roads.geojson');field=Surface(root)
    if city['meta']['cityId']!='hangzhou':raise ValueError('Wrong city')
    for p in [Path(__file__),ROOT/'scripts/pack_hangzhou_ambient.py',ROOT/'scripts/hangzhou_surface.py',root/'geography/manifest.json',root/'geography'/field.manifest['terrainFile'],root/'geography'/field.manifest['roadLevelsFile']]:inputs[str(p.relative_to(ROOT))]=digest(p)
    waters=[Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']];wet=shapely.union_all(waters);domain=box(*city['meta']['extent']);dry=domain.difference(wet)
    crossings=[]
    for r in city['roads']:
        if r.get('bridge','no') in ('no','false','0','') or r.get('tunnel','no') not in ('no','false','0',''):continue
        line=LineString(r['points']);chain=np.r_[0,np.cumsum([math.dist(p,q) for p,q in zip(r['points'],r['points'][1:])])]
        for i,part in enumerate(parts(line.intersection(wet),'LineString')):
            if part.length<=.1:continue
            points=list(part.coords);stations=[line.project(Point(p)) for p in points]
            if stations[0]>stations[-1]:points.reverse();stations.reverse()
            ys=np.interp(stations,chain,r['heights']).tolist()
            crossings.append({'id':r['id']+'@wet-'+str(i),'name':r['name'],'width':r['width'],'points':points,'pointHeightsGame':ys,'pointStationsGame':stations,'length':part.length,'height':float(np.interp((stations[0]+stations[-1])/2,chain,r['heights'])),'ramp':0,'sourceRoadId':r['id'],'sourceId':r.get('sourceId'),'nodeIds':r['nodeIds'],'status':'source identity and estimated profile, not measured bridge elevations'})
    if not 0<len(crossings)<=4096:raise ValueError('Invalid crossing scope')
    # Public paths use only shared OSM nodes to reach the existing ground graph.
    geo=city['meta'];origin=geo['originWGS84'];scale=geo['horizontalScale']
    def project(p):return [(p[0]-origin[0])*geo['eastMetresPerDegree']*scale,(p[1]-origin[1])*geo['northMetresPerDegree']*scale]
    graph=defaultdict(list);paths=[];seeds={str(n) for r in city['roads'] if r['grade']=='0' for n in r['nodeIds'] if not str(n).startswith('clip:')}
    for f in raw['features']:
        tags=f['properties']['tags'];kind=tags.get('highway')
        if kind not in ('footway','path','pedestrian','cycleway') or tags.get('access') in ('private','no') or tags.get('foot')=='no' or tags.get('bridge','no') not in ('no','false','0','') or tags.get('tunnel','no') not in ('no','false','0',''):continue
        refs=list(map(str,f['properties']['nodeIds']));coords=list(map(project,f['geometry']['coordinates']))
        if len(refs)!=len(coords):raise ValueError('Path node identity mismatch')
        for n,m in zip(refs,refs[1:]):graph[n].append(m);graph[m].append(n)
        paths.append((f['id'],refs,LineString(coords)))
    reachable=set(seeds);queue=deque(seeds&graph.keys())
    while queue:
        for n in graph[queue.popleft()]:
            if n not in reachable:reachable.add(n);queue.append(n)
    paths=[p for p in paths if all(n in reachable for n in p[1])];path_lines=[p[2] for p in paths];path_tree=STRtree(path_lines)
    obstacles=[Polygon(b['rings'][0],b['rings'][1:]).buffer(2) for b in city['buildings']]
    obstacles.extend(LineString(r['points']).buffer(r['width']/2+1.5) for r in city['roads'])
    obstacles.extend(Point(m['arrival']).buffer(7) for m in city['landmarks'])
    fixture_sources=[('landscape/canopy-trees.json',lambda d:[p[:2] for p in d['trees']],4),('landscape/planting.json',lambda d:[p[:2] for p in d['trees']],3),('street/manifest.json',lambda d:[[p['x'],p['z']] for p in d['placements']],2.5),('signals/traffic-signals.json',lambda d:[[p['x'],p['z']] for j in d['junctions'] for p in j['arms']],2.5)]
    for name,positions,radius in fixture_sources:obstacles.extend(Point(p).buffer(radius) for p in positions(read(placed/name)))
    obstacles.extend(Point(p[:2]).buffer(2) for p in read(root/'lamps.json'))
    obstacles.extend(Point(p[:2]).buffer(2.5) for p in read(ROOT/'artifacts/cities/hangzhou/ebikes-v4/parked.json')['bikes'])
    for file in ['artifacts/cities/hangzhou/life-sites-v3/life-sites.json','artifacts/cities/hangzhou/cafe-v3/report.json']:
        d=read(ROOT/file)
        for site in d.get('sites',[]) or [d['site']]:obstacles.append(Polygon(site['footprint']).buffer(3))
    obstacle_tree=STRtree(obstacles);lights=[];counts=Counter();policy=config['parkLight'];wet_margin=wet.buffer(4)
    for park in city['green']:
        if park['id'] not in config['publicParkSourceIds']:continue
        area=Polygon(park['rings'][0],park['rings'][1:]);safe=area.intersection(dry).difference(wet_margin)
        for pi in path_tree.query(area,predicate='intersects'):
            path_id,refs,line=paths[int(pi)]
            for segment in parts(line.intersection(area),'LineString'):
                for station in np.arange(12,segment.length-5,policy['spacingGame']):
                    q=segment.interpolate(station);prev=segment.interpolate(max(0,station-.5));nxt=segment.interpolate(min(segment.length,station+.5));dx,dz=nxt.x-prev.x,nxt.y-prev.y;length=math.hypot(dx,dz)
                    if length<1e-7:continue
                    for side in (-1,1):
                        point=Point(q.x-side*dz/length*policy['pathOffsetGame'],q.y+side*dx/length*policy['pathOffsetGame']);support=point.buffer(policy['supportRadiusGame']);reason=None
                        if not safe.covers(support):reason='water-or-park-edge'
                        elif len(obstacle_tree.query(support,predicate='intersects')):reason='fixture-building-road-or-entry'
                        elif path_tree.query(point,predicate='dwithin',distance=2).size:reason='mapped-walking-path'
                        elif any(math.hypot(point.x-p['x'],point.y-p['z'])<policy['spacingGame'] for p in lights):reason='spacing'
                        if reason:counts[reason]+=1;continue
                        y=field.ground(point.x,point.y);ys=[field.ground(point.x+dx,point.y+dz) for dx,dz in [(1,0),(-1,0),(0,1),(0,-1)]]
                        if max(abs(v-y) for v in ys)>.12:counts['sloping-support']+=1;continue
                        lights.append({'id':'hz-park-'+str(len(lights)),'name':park['name'],'x':point.x,'z':point.y,**{k:policy[k] for k in ['height','radius','color','power']},'sourceAreaId':park['id'],'sourcePathId':path_id,'groundYGame':y,'placementStatus':'estimated game fixture; not a surveyed lamp','pathConnectivity':'shared source-node path to existing ground road'})
                        if len(lights)>=policy['maximum']:break
                    if len(lights)>=policy['maximum']:break
                if len(lights)>=policy['maximum']:break
            if len(lights)>=policy['maximum']:break
        if len(lights)>=policy['maximum']:break
    if not lights:raise ValueError('No valid public park lights; never emit an empty placeholder')
    out.mkdir(parents=True)
    reference=next(w for w in city['water'] if w['id']==config['reflectionReferenceWaterId'])
    manifest={'schemaVersion':1,'cityId':'hangzhou','citySha256':inputs[str((root/'city.json').relative_to(ROOT))],'waterHeight':reference['height'],'referenceWaterId':reference['id'],'crossings':crossings,'parkLights':lights,'shoreDistance':{'url':'/cities/hangzhou/coastal/shore-distance.png','extent':city['meta']['extent'],'maxDistance':config['shoreDistance']['maximumGame']},'artDirection':'Source-bound estimated game bridge/lighting reconstruction, not surveyed elevations or existing lamps'}
    (out/'infrastructure.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
    # Remove only the explicitly artificial crop boundary from the physical
    # shore set. Dissolve source overlaps and lock/lotus semantic partitions.
    boundary=wet.boundary.difference(domain.boundary.buffer(1e-7));segments=[]
    for line in parts(boundary,'LineString'):segments.extend(LineString([p,q]) for p,q in zip(line.coords,line.coords[1:]) if math.dist(p,q)>1e-9)
    shore_tree=STRtree(segments);extent=city['meta']['extent'];w=config['shoreDistance']['width'];h=math.ceil(w*(extent[3]-extent[1])/(extent[2]-extent[0]));sx=(extent[2]-extent[0])/w;sz=(extent[3]-extent[1])/h
    mask=rasterize([(wet,1)],out_shape=(h,w),transform=Affine(sx,0,extent[0],0,sz,extent[1]),dtype='uint8');image=np.zeros((h,w,3),dtype='uint8');image[:,:,0]=mask*255;image[:,:,1]=mask*255;maximum=config['shoreDistance']['maximumGame'];near=0
    for r0 in range(0,h,96):
        row,col=np.nonzero(mask[r0:r0+96]);points=shapely.points(extent[0]+(col+.5)*sx,extent[1]+(row+r0+.5)*sz)
        pairs,distances=shore_tree.query_nearest(points,max_distance=maximum,return_distance=True,all_matches=False)
        image[row[pairs[0]]+r0,col[pairs[0]],0]=np.rint(np.clip(distances/maximum,0,1)*255).astype('u1');near+=len(distances)
        if r0%480==0:print('shore rows',r0,'/',h,'seconds',round(time.monotonic()-began,2),flush=True)
    (out/'shore-distance.png').write_bytes(png(image))
    report={'cityId':'hangzhou','kind':'source-bound-waterfront-runtime-data-candidate','inputs':inputs,'crossings':len(crossings),'sourceBridges':len({c['sourceRoadId'] for c in crossings}),'parkLights':len(lights),'parkLightRejects':dict(counts),'mappedReachablePaths':len(paths),'shoreRaster':{'width':w,'height':h,'pixelGame':[sx,sz],'wetPixels':int(mask.sum()),'nearShorePixels':near,'distanceMaximumGame':maximum,'physicalBoundaryLengthGame':boundary.length,'omittedCropEdgeLengthGame':wet.boundary.length-boundary.length,'rgbaMipBudgetBytes':math.ceil(w*h*4*4/3)},'seconds':time.monotonic()-began,'files':{p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in out.iterdir()},'pending':['independent serialized clearance/distance/axis verification','waterfront bank and bridge-rail models and collisions','remaining water overlap decisions and bridge/portal profile repair','current shader/visual/GPU texture limit/memory/frame checks'],'browserAccepted':False}
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
