"""Fixed-source search catalog with conservative directed road arrivals."""
import argparse,json,math,time
from pathlib import Path
from collections import deque,Counter
import numpy as np
import shapely
from shapely.geometry import Point,Polygon,LineString,shape
from city_config import ROOT,load_city,project
from hangzhou_surface import Surface,digest

def prepare(root,city_path,output):
    root,city_path,output=map(lambda p:Path(p).resolve(),[root,city_path,output]);began=time.monotonic()
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh candidate output required')
    city=json.loads(city_path.read_text());nav_path=root/'navigation.json';nav=json.loads(nav_path.read_text());field=Surface(root);profile=load_city('hangzhou');source=ROOT/profile['assets']['processedRoot'];extraction=json.loads((source/'extraction-manifest.json').read_text());features={};inputs=[city_path,nav_path,root/'geography/manifest.json',source/'extraction-manifest.json',ROOT/'config/cities/hangzhou.json',ROOT/'scripts/hangzhou_surface.py',Path(__file__)]
    if city['meta']['cityId']!='hangzhou':raise ValueError('Wrong city')
    for layer in ['places','pois']:
        p=source/(layer+'.geojson')
        if digest(p)!=extraction['sha256'][layer]:raise ValueError('Changed fixed source '+layer)
        inputs.append(p)
        for f in json.loads(p.read_text())['features']:
            if f['properties'].get('name'):features[f['id']]=f
    levels={r['id']:r for r in field.levels['roads']};count=len(nav['nodes']);forward=[[] for _ in range(count)];reverse=[[] for _ in range(count)]
    for r in city['roads']:
        chain=nav['roadNodes'][r['id']]
        for a,b in zip(chain,chain[1:]):
            forward[a].append(b);reverse[b].append(a)
            if not r['oneway']:forward[b].append(a);reverse[a].append(b)
    spawn=min(range(count),key=lambda i:math.hypot(nav['nodes'][i][0]-city['spawn']['x'],nav['nodes'][i][1]-city['spawn']['z']))
    def reachable(graph):
        visited={spawn};queue=deque([spawn])
        while queue:
            for other in graph[queue.popleft()]:
                if other not in visited:visited.add(other);queue.append(other)
        return visited
    connected=reachable(forward)&reachable(reverse);segments=[];owners=[];node_pairs=[]
    for r in city['roads']:
        if levels[r['id']]['tier']!=0:continue
        chain=nav['roadNodes'][r['id']]
        for a,b,i,j in zip(r['points'],r['points'][1:],chain,chain[1:]):
            if i in connected and j in connected and math.dist(a,b)>.01:segments.append(LineString([a,b]));owners.append(r);node_pairs.append([i,j])
    lines=np.asarray(segments,dtype=object);roads=shapely.STRtree(lines)
    buildings=[Polygon(b['rings'][0],b['rings'][1:]) for b in city['buildings']];solids=shapely.STRtree(buildings)
    wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']]);land=shapely.union_all([Polygon(r[0],r[1:]) for r in city['land']]);shapely.prepare(land);shapely.prepare(wet)
    places=[];omitted=[];categories=Counter()
    for num,(identifier,f) in enumerate(sorted(features.items())):
        tags=f['properties']['tags'];point=shape(f['geometry']).representative_point();lon,lat=point.x,point.y;x,z=project(lon,lat,profile);pt=Point(x,z)
        if not (city['meta']['extent'][0]<=x<=city['meta']['extent'][2] and city['meta']['extent'][1]<=z<=city['meta']['extent'][3]):continue
        candidates=roads.query(pt,predicate='dwithin',distance=600);arrival=None
        if len(candidates):
            distances=shapely.distance(lines[candidates],pt)
            for k in candidates[np.argsort(distances)]:
                k=int(k);line=segments[k];q=line.interpolate(line.project(pt));a,b=list(line.coords);dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);tx,tz=dx/length,dz/length;nx,nz=-tz,tx
                envelope=Polygon([(q.x+tx*u+nx*v,q.y+tz*u+nz*v) for u,v in [(-2.65,-1.1),(2.65,-1.1),(2.65,1.1),(-2.65,1.1)]])
                if not land.covers(envelope) or wet.intersects(envelope):continue
                y=field.ground(q.x,q.y)
                if any(city['buildings'][int(i)].get('minY',0)<y+1.9 and city['buildings'][int(i)].get('maxY',math.inf)>y for i in solids.query(envelope,predicate='intersects')):continue
                arrival={'arrival':[q.x,q.y],'yaw':math.atan2(dx,dz),'arrivalRoadId':owners[k]['id'],'arrivalNodes':node_pairs[k],'arrivalDistanceGame':q.distance(pt),'arrivalHeightGame':y};break
        if arrival is None:omitted.append({'id':identifier,'name':f['properties']['name'],'reason':'no bidirectionally reachable ground road within600game with conservative clear vehicle envelope'});continue
        kind=tags.get('place',tags.get('leisure',tags.get('amenity',tags.get('railway',tags.get('tourism','source-place')))))
        category='district' if tags.get('place') in ['city','town','suburb','neighbourhood','quarter','village','hamlet'] else 'park' if tags.get('leisure') in ['park','garden','nature_reserve'] else 'transport' if 'public_transport' in tags or tags.get('railway') in ['station','halt','subway_entrance'] or tags.get('highway')=='bus_stop' else 'landmark' if 'historic' in tags or tags.get('tourism') in ['attraction','museum','viewpoint'] else 'place'
        places.append({'id':'osm:'+identifier,'name':f['properties']['name'],'nameEn':tags.get('name:en',''),'category':category,'kind':kind,'lon':lon,'lat':lat,'x':x,'z':z,**arrival,'address':tags.get('addr:full',''),
            'source':{'provider':'OpenStreetMap','id':identifier,'url':'https://www.openstreetmap.org/'+identifier,'file':str(source.relative_to(ROOT)),'coordinateMethod':'fixed WGS84 source representative point; same authoritative city projection, scale applied once'}});categories[category]+=1
        if num%1000==0:print('map place',num,'/',len(features),'accepted',len(places),flush=True)
    output.mkdir(parents=True);target=output/'map-places.json'
    document={'schemaVersion':1,'cityId':'hangzhou','license':'ODbL-1.0; © OpenStreetMap contributors','sourceSnapshotUtc':extraction['source']['osmReplicationTimestamp'],'coordinateSystem':'WGS84; projected once using config/cities/hangzhou.json','scope':'Source representative labels are not entrances. Prepared arrivals use actual connected ground roads and conservative static clearances. Physical mesh and gameplay acceptance pending.','places':places}
    target.write_text(json.dumps(document,ensure_ascii=False,separators=(',',':')))
    report={'kind':'source-bound-map-search-candidate','cityId':'hangzhou','sourceInputs':{str(p.relative_to(ROOT)):digest(p) for p in inputs},'candidateSha256':digest(target),'placeCount':len(places),'categories':dict(categories),'omitted':omitted,'directedRoundTripReachableNodes':len(connected),'arrivalEnvelopeGame':{'length':5.3,'width':2.2,'height':1.9},'elapsedSeconds':time.monotonic()-began,'status':'offline candidate; not map/browser accepted','pending':['actual runtime map/catalog/route verification','props/facade clearance','physical road meshes and entrance access']}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sourceInputs','omitted']},ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--city',required=True);p.add_argument('--output',required=True);a=p.parse_args();prepare(a.root,a.city,a.output)
