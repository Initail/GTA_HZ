"""Bind the first leisure site to frozen main-city water, OSM paths and terrain.

The marina point is source evidence, not a surveyed gangway. New platform and
path widths are explicitly game adaptations. Outputs remain in one candidate.
"""
import argparse,hashlib,heapq,json,math,struct
from pathlib import Path
from city_config import load_city,project,ROOT
from hangzhou_feature_window import features
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def closest(p,a,b):
    dx=b[0]-a[0];dz=b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz or 1)));q=[a[0]+dx*t,a[1]+dz*t];return math.dist(p,q),q,t
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--candidate',type=Path,required=True);a=ap.parse_args();candidate=a.candidate.resolve()
    if ROOT/'artifacts' not in candidate.parents:raise SystemExit('Use an isolated artifact candidate.')
    output=candidate/'public/cities/hangzhou/leisure.json'
    if output.exists():raise SystemExit('Existing leisure configuration is protected.')
    city=load_city('hangzhou');geo=city['geography'];chunks=ROOT/'artifacts/cities/hangzhou/stream-data-v1/city';manifest=json.loads((chunks/'manifest.json').read_text())
    poi_source=ROOT/'data/processed/hangzhou-261011-extended/pois.geojson';poi=next(f for f in features(poi_source) if f['id']=='node/1254131927');poi_xy=project(*poi['geometry']['coordinates'],city)
    water_file=chunks/'array-5-8.json';water=[w for w in json.loads(water_file.read_text())['values'] if w.get('id')=='relation/2308774'];water_height=water[0]['height'];assert all(w['height']==water_height for w in water)
    distance,shore,_=min(closest(poi_xy,p,q) for w in water for ring in w['rings'] for p,q in zip(ring,ring[1:]+ring[:1]));normal=[(poi_xy[i]-shore[i])/distance for i in range(2)];side=[normal[1],-normal[0]];yaw=math.atan2(normal[0],normal[1])
    base=ROOT/'artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou/geography';g=json.loads((base/'manifest.json').read_text())['grid'];heights=struct.unpack('<'+'f'*(g['columns']*g['rows']),(base/'terrain-game.bin').read_bytes())
    def terrain(x,z):
        u=(x-g['x0'])/g['step'];v=(z-g['z0'])/g['step'];i=int(math.floor(u));j=int(math.floor(v));u-=i;v-=j;k=j*g['columns']+i;A,B,D,C=heights[k],heights[k+1],heights[k+g['columns']],heights[k+g['columns']+1]
        return A+(B-A)*u+(D-A)*v if u+v<=1 else C+(D-C)*(1-u)+(B-C)*(1-v)
    def offset(along,across=0):return [shore[i]+normal[i]*along+side[i]*across for i in range(2)]
    land_start=offset(-3);deck_height=terrain(*land_start)+.02;land=offset(3.9);berth=offset(3.9,1.9)
    def pose(p,height,heading=yaw):return {'x':p[0],'z':p[1],'height':height,'yaw':heading}
    foot=json.loads((candidate/'footpath-source.json').read_text());paths=[f for f in foot['features'] if f['properties']['tags'].get('highway') in ['footway','pedestrian','path'] and f['properties']['tags'].get('foot')!='no' and f['properties']['tags'].get('access') not in ['private','no']]
    # Find the public road arrival from actual frozen road segments, then follow
    # source shared foot nodes. No 2D intersection is promoted into a junction.
    arrival=None
    for array in manifest['arrays']:
        if array['key']!='roads':continue
        for chunk in array['chunks']:
            for road in json.loads((chunks/chunk['file']).read_text())['values']:
                if road.get('tunnel') not in (None,'no') or road.get('grade','0')!='0':continue
                for p,q in zip(road['points'],road['points'][1:]):
                    d,xy,t=closest(land_start,p,q)
                    if arrival is None or d<arrival['distance']:arrival={'distance':d,'point':xy,'roadId':road['id'],'yaw':math.atan2(q[0]-p[0],q[1]-p[1]),'roadName':road['name']}
    nodes={};edges={};path_meta={}
    for f in paths:
        ids=f['properties']['nodeIds'];ps=[project(*p,city) for p in f['geometry']['coordinates']];path_meta[f['id']]=f['properties']['tags']
        for ident,p in zip(ids,ps):nodes[ident]=p
        for i in range(len(ids)-1):
            d=math.dist(ps[i],ps[i+1]);edges.setdefault(ids[i],[]).append((ids[i+1],d,f['id']));edges.setdefault(ids[i+1],[]).append((ids[i],d,f['id']))
    start=min(nodes,key=lambda n:math.dist(nodes[n],arrival['point']));end=min(nodes,key=lambda n:math.dist(nodes[n],land_start));queue=[(0,start)];dist={start:0};parent={}
    while queue:
        cost,n=heapq.heappop(queue)
        if cost!=dist[n]:continue
        if n==end:break
        for nxt,d,way in edges.get(n,[]):
            if cost+d<dist.get(nxt,math.inf):dist[nxt]=cost+d;parent[nxt]=(n,way);heapq.heappush(queue,(cost+d,nxt))
    if end not in dist:raise ValueError('No source-node walking path to marina bank')
    chain=[];n=end
    while n!=start:
        prev,way=parent[n];chain.append((nodes[prev],nodes[n],way));n=prev
    chain.reverse();chain.append((nodes[end],land_start,'game-approach'))
    floors=[];slabs=[];access=[]
    def strip(ident,p,q,width,hp,hq,slab=False):
        dx=q[0]-p[0];dz=q[1]-p[1];length=math.hypot(dx,dz)
        if length<.01:return
        sx=-dz/length*width/2;sz=dx/length*width/2;vs=[[p[0]+sx,p[1]+sz,hp],[p[0]-sx,p[1]-sz,hp],[q[0]-sx,q[1]-sz,hq],[q[0]+sx,q[1]+sz,hq]]
        triangles=[[vs[0],vs[1],vs[2]],[vs[0],vs[2],vs[3]]]
        for tri in triangles:
            a,b,c=tri
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:tri[1],tri[2]=tri[2],tri[1]
        group={'id':ident,'triangles':triangles};floors.append(group)
        if slab:slabs.append({**group,'thicknessGame':.22})
    for index,(p,q,way) in enumerate(chain):
        # Public motor roads keep priority at crossings in the existing world
        # adapter. Away from those crossings these source footpaths remain foot-only.
        tags=path_meta.get(way,{'highway':'footway','foot':'yes','motor_vehicle':'no','bicycle':'no'})
        access.append({'sourceId':'leisure:'+way+':'+str(index),'points':[p,q],'widthGame':1.8,'kind':tags.get('highway','footway'),'sourceAccessTags':tags})
        bridge=path_meta.get(way,{}).get('bridge') not in (None,'no');count=max(1,math.ceil(math.dist(p,q)/2))
        for i in range(count):
            u=[p[j]+(q[j]-p[j])*i/count for j in range(2)];v=[p[j]+(q[j]-p[j])*(i+1)/count for j in range(2)]
            hu=terrain(*p)+(terrain(*q)-terrain(*p))*i/count+.025 if bridge else terrain(*u)+.025;hv=terrain(*p)+(terrain(*q)-terrain(*p))*(i+1)/count+.025 if bridge else terrain(*v)+.025
            strip('leisure:approach:'+str(index)+':'+str(i),u,v,1.8,hu,hv,bridge)
    strip('leisure:marina-deck',land_start,offset(5),2,deck_height,deck_height,True)
    access.append({'sourceId':'leisure:marina-deck','points':[land_start,offset(5)],'widthGame':2,'kind':'footway','sourceAccessTags':{'highway':'footway','foot':'yes','motor_vehicle':'no','bicycle':'no'}})
    site={'id':'westlake-handboat','name':'手划船体验（游戏操控改编）','waterIds':['relation/2308774'],'sourceIds':['node/1254131927','relation/2308774'],
          'dock':{'id':'westlake-handboat','land':pose(land,deck_height),'berth':pose(berth,water_height)},
          'fishing':pose(offset(-3.5,-3),terrain(*offset(-3.5,-3)),yaw),
          'keeper':pose(offset(-2,1.9),terrain(*offset(-2,1.9)),yaw+math.pi),
          'volunteer':pose(offset(-4,-5),terrain(*offset(-4,-5)),yaw),
          'arrival':arrival,'sourceCenterWGS84':poi['geometry']['coordinates'],'shoreGame':shore,'marinaCenterToShoreGame':distance,'floors':floors,'solidSlabs':slabs,'accessCorridors':access,'walkingRouteGame':[arrival['point']]+[p for p,q,way in chain]+[land_start,land],
          'basis':'OSM marina and footway anchors; rendered platform, path width and dock landing are estimated game adaptation, not a surveyed real entrance',
          'blockers':['Real marina operator and exact gangway identity unknown','Not identified as Broken Bridge self-drive dock','Real-world fishing access not established; interaction explicitly game fiction']}
    result={'schemaVersion':1,'cityId':'hangzhou','originWGS84':geo['originWGS84'],'horizontalScale':geo['scale'],'eastMetresPerDegree':geo['eastMetresPerDegree'],'northMetresPerDegree':geo['northMetresPerDegree'],'units':'game metres; scale applied once','sites':[site],
            'sourceFiles':{str(p.relative_to(ROOT)):sha(p) for p in [poi_source,water_file,candidate/'footpath-source.json',base/'terrain-game.bin']},'license':'OSM source ODbL-1.0; generated game geometry project MIT','physicalAcceptance':'pending'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    surfaces=candidate/'public/cities/hangzhou/geography/site-surfaces.json';data=json.loads(surfaces.read_text());data['walkFloors'].extend(floors);data.setdefault('solidSlabs',[]).extend(slabs);data.setdefault('accessCorridors',[]).extend(access);surfaces.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    gm=surfaces.with_name('manifest.json');m=json.loads(gm.read_text());m['siteSurfacesSha256']=sha(surfaces);gm.write_text(json.dumps(m,separators=(',',':'))+'\n')
    detail=candidate/'public/cities/hangzhou/landmark-detail.json';dm=json.loads(detail.read_text());dm['terrain']['manifestSha256']=sha(gm);detail.write_text(json.dumps(dm,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'site':site['id'],'waterId':site['waterIds'],'arrival':arrival,'walkPathGameMetres':dist[end],'walkingStartGapGame':math.dist(nodes[start],arrival['point']),'floors':len(floors),'slabs':len(slabs),'deckHeight':deck_height,'waterHeight':water_height,'output':str(output)},ensure_ascii=False))
if __name__=='__main__':main()
