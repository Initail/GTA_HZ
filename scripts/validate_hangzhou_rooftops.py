"""Validate actual prototype support against Hangzhou roofs with GEOS.

No browser/visual acceptance. Writes only a fresh isolated final candidate.
The original prototypes and runtime instance budgets are unchanged.
"""
from __future__ import annotations
import argparse,hashlib,json,math,shutil,time
from collections import Counter,defaultdict
from pathlib import Path
from shapely.geometry import Polygon,MultiPoint
from shapely import STRtree,affinity
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--city',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=ROOT/a.input;out=(ROOT/a.output).resolve();city_path=ROOT/a.city
    if ROOT/'artifacts' not in out.parents or out.exists():raise ValueError('Fresh candidate required')
    data=json.loads((source/'unverified-plan.json').read_text());started=time.monotonic()
    if data['cityId']!='hangzhou':raise ValueError('Wrong city')
    for name,digest in data['inputs'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Changed input '+name)
    buildings=json.loads((ROOT/data['source']).read_text());city=json.loads(city_path.read_text())
    roofs=[Polygon(b['rings'][0],b['rings'][1:]) for b in buildings]
    if not all(p.is_valid for p in roofs):raise ValueError('Invalid roof polygon')
    # Independently check Python's exact ring digest against authored GLB floors.
    floor_file=next(k for k in data['inputs'] if k.endswith('/building-floors.json'))
    floors={(b['id'],b['ringsSha256']):b for b in json.loads((ROOT/floor_file).read_text())}
    for b in buildings:
        digest=hashlib.sha256(json.dumps(b['rings'],separators=(',',':')).encode()).hexdigest()
        f=floors[(b['id'],digest)]
        if f['mainRoofYGame']!=b['maxY'] or f['baseYGame']!=b['baseYGame']:raise ValueError('Wrong authored roof')
    obstacles=[Polygon(b['rings'][0],b['rings'][1:]) for b in city['buildings']];tree=STRtree(obstacles)
    prototypes={}
    for kind,p in data['prototypes'].items():
        v=p['vertices'];prototypes[kind]=(MultiPoint([(q[0],q[1]) for q in v]).convex_hull,min(q[2] for q in v),max(q[2] for q in v))
    groups=defaultdict(list);accepted=[];rejected=[];counts=Counter();max_ordinate_error=0
    for index,p in enumerate(data['proposals']):
        b=buildings[p['buildingIndex']];x,z,y,sx,sy,sz,yaw=p['instance'];kind=p['kind'];support,lo,hi=prototypes[kind]
        if not all(math.isfinite(v) for v in p['instance']) or min(sx,sy,sz)<=0:raise ValueError('Invalid transform')
        # Babylon Quaternion about +Y sends (x,z) to (x cos+z sin,-x sin+z cos).
        poly=affinity.translate(affinity.rotate(affinity.scale(support,sx,sz,origin=(0,0)),-yaw,origin=(0,0),use_radians=True),x,z)
        bottom,top=y+lo*sy,y+hi*sy;reason=None
        error=abs(y-b['maxY']);max_ordinate_error=max(max_ordinate_error,error)
        if error>.0050001:raise ValueError('Floating roof placement')
        if not roofs[p['buildingIndex']].buffer(-.04).covers(poly):reason='prototype-support-outside-roof-or-in-courtyard'
        if not reason:
            for oi in tree.query(poly,predicate='intersects'):
                other=city['buildings'][int(oi)];other_top=other.get('maxY',other['height']);other_bottom=other.get('minY',0)
                if other_top>b['maxY']+.02 and other_bottom<top and other_top>bottom and obstacles[int(oi)].intersection(poly).area>1e-7:
                    reason='overlaps-higher-building';break
        if reason:counts[reason]+=1;rejected.append({'proposal':index,'buildingId':b['id'],'kind':kind,'reason':reason});continue
        group_index=len(groups[kind]);groups[kind].append(p['instance']);accepted.append({'proposal':index,'buildingIndex':p['buildingIndex'],'kind':kind,'groupIndex':group_index,'minYGame':bottom,'maxYGame':top,'supportHull':list(poly.exterior.coords)})
    out.mkdir(parents=True)
    for name in ['props.glb','props-manifest.json']:shutil.copy2(ROOT/'public/city/rooftops'/name,out/name)
    shutil.copy2(source/'building-lookup.png',out/'building-lookup.png')
    plan={'version':1,'cityId':'hangzhou','source':'OSM-derived Hangzhou roofs and original artistic equipment typology; not surveyed','groups':[{'kind':k,'count':len(groups[k]),'instances':groups[k]} for k in prototypes],'lookup':data['lookup'],'placement':data['placement']}
    (out/'plan.json').write_text(json.dumps(plan,separators=(',',':')))
    (out/'support-audit.json').write_text(json.dumps({'accepted':accepted,'rejected':rejected},separators=(',',':')))
    report={'cityId':'hangzhou','kind':'exact-prototype-roof-support-candidate','inputs':{**data['inputs'],str((source/'unverified-plan.json').relative_to(ROOT)):sha(source/'unverified-plan.json'),a.city:sha(city_path)},'validatorSha256':sha(__file__),'buildings':len(buildings),'courtyardBuildings':sum(len(b['rings'])>1 for b in buildings),'proposed':len(data['proposals']),'accepted':len(accepted),'rejected':dict(counts),'perKind':{k:len(groups[k]) for k in prototypes},'maxPlacementRoundingErrorGame':max_ordinate_error,'supportMarginGame':.04,'seconds':time.monotonic()-started,'supportChecksPassed':True,'browserAccepted':False,'pending':['roof equipment collision bodies and parapet collision heights','current render/day/night/flight inspection','runtime performance and loading budgets'],'files':{f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir()}}
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
