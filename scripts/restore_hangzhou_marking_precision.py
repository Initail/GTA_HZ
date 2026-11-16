"""Reconstruct the original marking domain before the old round(4) step.
Leave lamp/path/bench placements unchanged and explicitly un-revalidated.
"""
import argparse,json,math,hashlib,shutil
from collections import Counter
from pathlib import Path
import shapely
from shapely.geometry import LineString
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]
def key(tri):return tuple(sorted((round(x,4),round(z,4)) for x,z in tri))
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-city',required=True);p.add_argument('--source-street',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    cp=ROOT/a.source_city;source=ROOT/a.source_street;out=(ROOT/a.output).resolve();report=json.loads((source/'report.json').read_text())
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    if sha(cp)!=report['inputs']['citySha256']:raise ValueError('Original marking city required')
    for name,digest in report['files'].items():
        if sha(source/name)!=digest:raise ValueError('Changed original street '+name)
    city=json.loads(cp.read_text());roads=[r for r in city['roads'] if r['grade']=='0' and r['bridge']=='no' and r['tunnel']=='no'];stripes=[]
    asphalt=shapely.union_all([LineString(r['points']).buffer(r['width']/2,cap_style=2,join_style=2) for r in roads])
    for r in roads:
        if r['kind'] not in ('trunk','primary','secondary','tertiary'):continue
        width=r['width']
        for aa,bb in zip(r['points'],r['points'][1:]):
            dx,dz=bb[0]-aa[0],bb[1]-aa[1];length=math.hypot(dx,dz)
            if length<=6:continue
            nx,nz=-dz/length,dx/length
            for off in (-width/2+.35,width/2-.35):stripes.append(LineString([(aa[0]+nx*off,aa[1]+nz*off),(bb[0]+nx*off,bb[1]+nz*off)]).buffer(.055,cap_style=2))
            for j in range(1,max(2,round(width/3))):
                off=-width/2+j*width/max(2,round(width/3))
                for t in range(4,int(length)-4,10):
                    t1=min(length-4,t+3.5);stripes.append(LineString([(aa[0]+dx*t/length+nx*off,aa[1]+dz*t/length+nz*off),(aa[0]+dx*t1/length+nx*off,aa[1]+dz*t1/length+nz*off)]).buffer(.055,cap_style=2))
    markings=shapely.union_all(stripes).intersection(asphalt);triangles=[[[x,z] for x,z in list(p.exterior.coords)[:3]] for p in parts(shapely.constrained_delaunay_triangles(markings)) if p.area>1e-8]
    old=json.loads((source/'roadline-triangles.json').read_text());before=Counter(map(key,old));after=Counter(map(key,triangles))
    if before!=after:raise ValueError('Source reconstruction differs from original rounded triangle multiset: '+str((sum((before-after).values()),sum((after-before).values()))))
    out.mkdir(parents=True)
    for name in report['files']:
        if name!='roadline-triangles.json':shutil.copy2(source/name,out/name)
    (out/'roadline-triangles.json').write_text(json.dumps(triangles,separators=(',',':')))
    result={**report,'kind':'original-marking-domain-full-precision-restoration','restorationInputs':{a.source_city:sha(cp),a.source_street+'/report.json':sha(source/'report.json'),'scripts/restore_hangzhou_marking_precision.py':sha(Path(__file__))},'originalRoundedTriangleMultisetMatches':True,'restoredTriangles':len(triangles),'files':{p.name:sha(p) for p in out.iterdir()},'status':'precision restored; old placements retained for separate clearance review','pending':report['pending']+['full-precision markings mesh and export checks','old lamp/path/bench clearance against current restored water and new model floors']}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
