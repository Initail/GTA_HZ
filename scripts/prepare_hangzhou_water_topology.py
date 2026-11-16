"""Restore fixed-source water boundaries, retaining unresolved source overlaps.

No per-body simplification, water-level averaging or arbitrary priority cuts.
This is an isolated replacement packet; props/meshes must be regenerated or
rechecked against its exact geometry before the packet can be integrated.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
from collections import defaultdict
import shapely
from shapely.geometry import Polygon,shape,box
from shapely.ops import transform
from shapely.strtree import STRtree
from city_config import ROOT

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for member in getattr(g,'geoms',[]) for p in parts(member)]
def rings(p):return [list(map(list,r.coords)) for r in [p.exterior,*p.interiors]]
def overlaps(bodies,threshold=.01):
    polygons=[Polygon(b['rings'][0],b['rings'][1:]) for b in bodies];tree=STRtree(polygons);found=[]
    for i,p in enumerate(polygons):
        for j in tree.query(p,predicate='intersects'):
            j=int(j)
            if j<=i:continue
            area=p.intersection(polygons[j]).area
            if area>threshold:found.append({'aIndex':i,'bIndex':j,'a':bodies[i]['id'],'b':bodies[j]['id'],'areaGameSquared':area,'heightDifferenceGame':abs(bodies[i]['height']-bodies[j]['height'])})
    return sorted(found,key=lambda r:r['areaGameSquared'],reverse=True)
def prepare(source,raw_path,crosswalk_path,output):
    source,raw_path,crosswalk_path,output=map(lambda p:Path(p).resolve(),[source,raw_path,crosswalk_path,output])
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh candidate required')
    city_path=source/'city.json';city=json.loads(city_path.read_text());raw=json.loads(raw_path.read_text());crosswalk=json.loads(crosswalk_path.read_text());m=city['meta']
    if m['cityId']!='hangzhou' or not crosswalk['oneToOne']:raise ValueError('Verified one-to-one Hangzhou water crosswalk required')
    if digest(city_path)!=crosswalk['inputs']['citySha256'] or digest(raw_path)!=crosswalk['inputs']['waterSha256']:raise ValueError('Changed crosswalk source')
    o=m['originWGS84'];e=m['eastMetresPerDegree'];n=m['northMetresPerDegree'];scale=m['horizontalScale'];domain=box(*m['extent'])
    def project(x,y,z=None):return (x-o[0])*e*scale,(y-o[1])*n*scale
    originals={};tags={}
    for f in raw['features']:
        tags[f['id']]=f['properties'].get('tags',{})
        for i,p in enumerate(parts(transform(project,shape(f['geometry'])).intersection(domain))):
            if p.area>=20:originals[f['id'],i]=p
    before=overlaps(city['water']);old_union=shapely.union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in city['water']]);used=set()
    for row in crosswalk['parts']:
        b=city['water'][row['runtimeIndex']];key=(row['id'],row['sourcePartIndex']);p=originals[key]
        if key in used or b['id']!=row['id'] or not p.is_valid:raise ValueError('Invalid part mapping')
        used.add(key);b['rings']=rings(p);b['sourcePartIndex']=row['sourcePartIndex'];b['boundaryStatus']='fixed-source unsimplified WGS84 polygon; projected once; absolute mapping accuracy unknown'
    if used!=set(originals):raise ValueError('Unmapped source part')
    after=overlaps(city['water'],1e-6);wet=shapely.union_all([Polygon(b['rings'][0],b['rings'][1:]) for b in city['water']]);land=domain.difference(wet)
    if not land.is_valid:raise ValueError('Invalid restored land topology')
    city['land']=[rings(p) for p in parts(land)];city['meta']['status']='water-topology-candidate-not-integrated'
    for row in after:
        row['tagsA']=tags[row['a']];row['tagsB']=tags[row['b']];row['status']='unresolved source overlap; no invented water level or cut priority'
    output.mkdir(parents=True);target=output/'city.json';target.write_text(json.dumps(city,ensure_ascii=False,separators=(',',':')))
    restored=json.loads(target.read_text())
    assert all(Polygon(b['rings'][0],b['rings'][1:]).is_valid for b in restored['water'])
    report={'kind':'fixed-source-water-topology-candidate','cityId':'hangzhou','sourceInputs':{str(p.relative_to(ROOT)):digest(p) for p in [city_path,raw_path,crosswalk_path,Path(__file__)]},
        'outputCitySha256':digest(target),'waterBodies':len(city['water']),'sourcePartsAllRetained':len(used)==len(originals),'heightValuesUnchanged':True,
        'beforeOverlapPairs':len(before),'remainingSourceOverlapPairs':len(after),'remainingAbovePoint01':sum(r['areaGameSquared']>.01 for r in after),'sourceOverlapAreaThresholdGameSquared':1e-6,'remainingSourceOverlaps':after,
        'changedWetAreaGameSquared':old_union.symmetric_difference(wet).area,'landWaterOverlapGameSquared':land.intersection(wet).area,
        'pass':False,'topologyRestorationPassed':True,'pending':['unresolved source overlaps including lock and layer uncertainty','connected water levels/datum and shoreline geometry','all prop/arrival clearances against restored boundaries','regenerated terrain/water meshes','browser visual and physical acceptance']}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sourceInputs','remainingSourceOverlaps']},ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['source','raw','crosswalk','output']:p.add_argument('--'+key,required=True)
    a=p.parse_args();prepare(a.source,a.raw,a.crosswalk,a.output)
