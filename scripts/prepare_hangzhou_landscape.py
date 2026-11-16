"""Preserve the low vegetation and road-detail layers in a fresh city candidate.

Original authored detail prototypes are reused unchanged. New positions are
source-derived art direction, never a surveyed planting/drain inventory.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random, shutil
from pathlib import Path
from collections import Counter
import shapely
from shapely.geometry import Polygon, Point, LineString
from shapely.strtree import STRtree
from city_config import ROOT, load_city, project

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(rings):
    p=Polygon(rings[0],rings[1:])
    if not p.is_valid: raise ValueError('Invalid source polygon')
    return p

def prepare(city_root, canopy, output, reserved=()):
    city_root,canopy,output=map(lambda p:Path(p).resolve(),[city_root,canopy,output])
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())): raise ValueError('Fresh candidate required')
    profile=load_city('hangzhou');scale=profile['geography']['scale']
    c=json.loads((city_root/'city.json').read_text());report=json.loads((canopy/'report.json').read_text())
    cp=canopy/'landscape/canopy-trees.json';tall=json.loads(cp.read_text());family=json.loads((canopy/'landscape/canopy/manifest.json').read_text())
    if c['meta']['cityId']!='hangzhou' or digest(cp)!=report['canopyPlantingSha256'] or report['allGreenParcelsVisited']!=len(c['green']): raise ValueError('Incomplete/changed canopy')
    inputs={str(p.relative_to(ROOT)):digest(p) for p in [city_root/'city.json',cp,canopy/'report.json']}
    land=shapely.union_all([poly(r) for r in c['land']]);water=shapely.union_all([poly(w['rings']) for w in c['water']]);green=shapely.union_all([poly(g['rings']) for g in c['green']])
    for g in [land,water,green]: shapely.prepare(g)
    solids=[poly(b['rings']) for b in c['buildings']]
    for name in reserved:
        p=Path(name).resolve();r=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=digest(p)
        for site in r.get('sites',[]) or [r['site']]: solids.append(Polygon(site['footprint']).buffer(2))
    building_tree=STRtree(solids);road_tree=STRtree([LineString(r['points']).buffer(r['width']/2) for r in c['roads']])
    fixtures=[]
    for name in ['lamps.json','signals/traffic-signals.json','street/manifest.json']:
        p=city_root/name;r=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=digest(p)
        if name=='lamps.json': fixtures.extend(Point(v[0],v[1]) for v in r)
        elif name.startswith('signals'): fixtures.extend(Point(a['x'],a['z']) for j in r['junctions'] for a in j['arms'])
        else: fixtures.extend(Point(v['x'],v['z']) for v in r['placements'])
    fixture_tree=STRtree(fixtures);trunks=STRtree([Point(t[0],t[1]) for t in tall['trees']]);rejected=Counter();cells={}
    trees=[];details=[];road_details=[];detail_cells=set();tree_sources=[]
    by_species={s['id']:s for s in family['species']};base_names=profile['vegetation']['baseTreeNames'];rng=random.Random(20261014)
    def clear(x,z,radius):
        disk=Point(x,z).buffer(radius)
        for key,bad in [('water-land',not land.covers(disk) or water.intersects(disk)),('carriageway',bool(road_tree.query(disk.buffer(.65),predicate='intersects').size)),('building-reserved',bool(building_tree.query(disk.buffer(.6),predicate='intersects').size)),('fixture',bool(fixture_tree.query(Point(x,z).buffer(radius+.5),predicate='intersects').size))]:
            if bad: rejected[key]+=1;return False
        return True
    def tree(x,z,kind,basis,source_id):
        x,z=round(x,3),round(z,3);s=by_species[base_names[kind]]
        variation=round((rng.uniform(6.5,8.0)*scale)/s['height'],4);radius=s['crown']/2*variation
        cell=(math.floor(x/12),math.floor(z/12))
        if trunks.query(Point(x,z).buffer(radius+3.5)).size or any(math.hypot(x-a,z-b)<max(6,radius+r+.5) for u in range(cell[0]-1,cell[0]+2) for v in range(cell[1]-1,cell[1]+2) for a,b,r in cells.get((u,v),[])): rejected['tree-spacing']+=1;return
        if clear(x,z,radius):
            trees.append([x,z,kind,variation,round(rng.uniform(-math.pi,math.pi),4)]);cells.setdefault(cell,[]).append((x,z,radius));tree_sources.append({'index':len(trees)-1,'basis':basis,'sourceId':source_id})
    def detail(x,z,kind):
        x,z=round(x,3),round(z,3);variation=round(rng.uniform(.7,1.1),3);radius=[.85,1.1,.65][kind]*variation;key=(round(x/2),round(z/2),kind)
        if key in detail_cells or not clear(x,z,radius):return
        distance=min((road_tree.geometries[int(i)].distance(Point(x,z)) for i in road_tree.query(Point(x,z).buffer(10))),default=math.inf)
        if not green.covers(Point(x,z)) and not 3.2<distance<9:return
        detail_cells.add(key);details.append([x,z,kind,variation,round(rng.uniform(-math.pi,math.pi),4)])
    pois_path=ROOT/profile['assets']['processedRoot']/'pois.geojson';inputs[str(pois_path.relative_to(ROOT))]=digest(pois_path)
    source_trees=[f for f in json.loads(pois_path.read_text())['features'] if f['properties']['tags'].get('natural')=='tree']
    for f in source_trees:tree(*project(*f['geometry']['coordinates'],profile),0,'source tree position, estimated species/dimensions',f['id'])
    roads=sorted((r for r in c['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no' and r['kind'] in ['trunk','primary','secondary','tertiary','residential']),key=lambda r:hashlib.sha256(r['id'].encode()).hexdigest())
    for n,r in enumerate(roads):
        line=LineString(r['points'])
        for distance in range(8,int(line.length)-2,24):
            p,q=line.interpolate(distance),line.interpolate(distance+1);dx,dz=q.x-p.x,q.y-p.y;length=math.hypot(dx,dz)
            if length<.01:continue
            for side in [-1,1]:
                off=r['width']/2+rng.uniform(4,6);x,z=p.x-dz/length*off*side,p.y+dx/length*off*side
                detail(x,z,0 if distance%72 else rng.choice([1,2]))
                if distance%72==8:tree(x,z,rng.randrange(3),'estimated ground-road verge',r['id'])
        if r['kind'] in ['primary','secondary','tertiary']:
            for distance in range(16,int(line.length)-3,52):
                p,q=line.interpolate(distance),line.interpolate(distance+1);dx,dz=q.x-p.x,q.y-p.y;length=math.hypot(dx,dz)
                if length<.01:continue
                for kind,off in [(0,r['width']/2-.52),(1,-.7)]:
                    if kind==1 and (distance%104!=16 or r['width']<=5):continue
                    x,z=round(p.x-dz/length*off,3),round(p.y+dx/length*off,3);spot=Point(x,z)
                    if land.covers(spot) and not water.intersects(spot.buffer(.25)) and not building_tree.query(spot.buffer(.3),predicate='intersects').size:road_details.append([x,z,kind,1,round(math.atan2(dx,dz),4) if kind==0 else 0])
        if n%3000==0:print('road',n,'trees/details',len(trees),len(details),flush=True)
    # Every district retains a share if the expanded map exceeds the original
    # placement density; the renderer keeps its original visibility budgets.
    if len(trees)>12000:
        selected=sorted(range(len(trees)),key=lambda i:hashlib.sha256(json.dumps(trees[i][:2]).encode()).hexdigest())[:12000];mapping={old:new for new,old in enumerate(selected)}
        trees=[trees[i] for i in selected];tree_sources=[{**s,'index':mapping[s['index']]} for s in tree_sources if s['index'] in mapping]
    for n,t in enumerate(tall['trees']):
        if n%4:continue
        for k in range(3):detail(t[0]+math.sin(t[4]+k*math.tau/3)*2,t[1]+math.cos(t[4]+k*math.tau/3)*2,k)
    output.mkdir(parents=True,exist_ok=True);shutil.copytree(canopy/'landscape',output/'landscape');dest=output/'landscape'
    planting={'trees':trees,'details':details,'roadDetails':road_details}
    (dest/'planting.json').write_text(json.dumps(planting,separators=(',',':')))
    original=ROOT/'public/city/landscape'
    for p in original.iterdir():
        if p.is_file() and not (dest/p.name).exists():shutil.copyfile(p,dest/p.name)
    # Tropical CC0 supplementation has no eligible Hangzhou instances. Keep the
    # loader contract and attribution; native regional trees supply both tiers.
    (output/'open-vegetation').mkdir();(output/'open-vegetation/manifest.json').write_text(json.dumps({'version':1,'cityId':'hangzhou','plantingSHA256':digest(dest/'planting.json'),'eligibleIndices':{'islandTree':[],'palm':[]},'models':[],'source':'Native authored Hangzhou regional trees; no tropical substitutions'},ensure_ascii=False,indent=2)+'\n')
    result={'kind':'source-bound-low-vegetation-and-road-detail-candidate','cityId':'hangzhou','canopyTrees':len(tall['trees']),'baseTrees':len(trees),'details':len(details),'roadDetails':len(road_details),'sourceTreeNodes':len(source_trees),'treeSourceRecords':tree_sources,'rejected':dict(rejected),'inputs':inputs,'plantingSha256':digest(dest/'planting.json'),'prototypeScale':'native game units; low tree dimensions estimated 6.5–8m, instance variation only','runtimeVisibilityBudgets':'original and unchanged','pending':['absolute ground/platform attachment','serialized clearance audit and parked vehicles','real browser LOD/night/rain/visual/performance']}
    (output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['treeSourceRecords','inputs']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--canopy',required=True);p.add_argument('--output',required=True);p.add_argument('--reserved',action='append',default=[])
    a=p.parse_args();prepare(a.city_root,a.canopy,a.output,a.reserved)
