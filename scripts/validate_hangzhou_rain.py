"""Exact candidate containment and source-asphalt plane proof; no public writes."""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.strtree import STRtree
from hangzhou_surface import digest
ROOT=Path(__file__).resolve().parents[1]
def poly(r):return shapely.make_valid(Polygon(r[0],r[1:]))
def main():
    ap=argparse.ArgumentParser()
    for k in ['input','meshes','output']:ap.add_argument('--'+k,required=True)
    a=ap.parse_args();src=ROOT/a.input;meshroot=ROOT/a.meshes;out=ROOT/a.output
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    start=time.monotonic();generation=json.loads((src/'generation.json').read_text())
    for p,h in generation['sources'].items():
        if digest(ROOT/p)!=h:raise ValueError('Changed generated input '+p)
    city=json.loads((ROOT/generation['cityRoot']/'city.json').read_text());detail=json.loads((ROOT/generation['collisionFile']).read_text());source=json.loads((src/'unverified-layout.json').read_text())
    manifest=json.loads((meshroot/'manifest.json').read_text());triangles=[]
    for row in manifest['meshRecords']:
        if 'asphalt' not in row['triangles']:continue
        p=meshroot/row['file']
        if digest(p)!=row['sha256']:raise ValueError('Changed mesh source')
        with np.load(p) as f:triangles.append(f['asphalt'])
    ts=np.concatenate(triangles);del triangles
    tops=shapely.polygons(ts[:,:,:2]);tree=STRtree(tops)
    # z=ax+by+c for every nondegenerate prepared asphalt triangle.
    d=ts[:,1:,:2]-ts[:,None,0,:2];h=ts[:,1:,2]-ts[:,None,0,2]
    det=d[:,0,0]*d[:,1,1]-d[:,0,1]*d[:,1,0]
    if np.any(det<=0):raise ValueError('Invalid source asphalt orientation')
    ax=(h[:,0]*d[:,1,1]-h[:,1]*d[:,0,1])/det;by=(d[:,0,0]*h[:,1]-d[:,1,0]*h[:,0])/det
    c=ts[:,0,2]-ax*ts[:,0,0]-by*ts[:,0,1]
    del d,h
    land=shapely.union_all([poly(r) for r in city['land']]);shapely.prepare(land)
    waters=[poly(r) for w in city['water'] if w.get('renderSurface',True) for r in w.get('renderRings',[w['rings']])]
    blocked=waters+[poly(b['rings']) for b in city['green']+city['buildings']+detail['collisionFootprints']]
    blocked_tree=STRtree(blocked)
    roads={r['id']:r for r in city['roads']};road_domains={}
    fields=['x','z','dx','dz','length','width','lateral','roadWidth','seed','alpha']
    values=[];bases=[];accepted=[];envelopes=[];water_polys=[];occupied={};rejected={k:0 for k in ['sourceRoad','landUse','overlap','renderCoverage','ceiling','renderRelief']};height_rows=[]
    out.mkdir(parents=True)
    for i,p in enumerate(source['pools']):
        r=roads[p['roadId']]
        if r['grade']!='0' or r['kind'].endswith('_link') or r['width']<3.2:raise ValueError('Unexpected source road')
        domain=road_domains.get(r['id'])
        if domain is None:domain=road_domains.setdefault(r['id'],LineString(r['points']).buffer(r['width']/2,cap_style=2))
        envelope=shapely.union_all([Polygon(p['outlines']['apron'][str(n)]) for n in [12,6,4]]);margin=envelope.buffer(.03,quad_segs=2)
        if not domain.covers(margin):rejected['sourceRoad']+=1;continue
        if not land.covers(margin) or len(blocked_tree.query(margin,predicate='intersects')):rejected['landUse']+=1;continue
        x0,z0,x1,z1=envelope.bounds;cells=[(x,z) for x in range(math.floor(x0/160),math.floor(x1/160)+1) for z in range(math.floor(z0/160),math.floor(z1/160)+1)]
        others={j for cell in cells for j in occupied.get(cell,[])}
        if any(envelope.intersection(envelopes[j]).area>1e-7 for j in others):rejected['overlap']+=1;continue
        ids=tree.query(envelope,predicate='intersects');pieces=[];lo=math.inf;hi=-math.inf;ceiling=False
        for j in ids:
            clip=tops[j].intersection(envelope)
            if clip.area<=1e-12:continue
            xy=shapely.get_coordinates(clip);zs=ax[j]*xy[:,0]+by[j]*xy[:,1]+c[j];low=float(zs.min());high=float(zs.max())
            if high>p['baseHeightGame']+.10+.15:ceiling=True;break
            if low<p['groundProbeMinGame']+.10-.15:continue
            pieces.append(clip);lo=min(lo,low);hi=max(hi,high)
        if ceiling:rejected['ceiling']+=1;continue
        if not pieces or envelope.difference(shapely.union_all(pieces)).area>1e-7:rejected['renderCoverage']+=1;continue
        if hi-lo>.028:rejected['renderRelief']+=1;continue
        # v5 exported asphalt maximum world error is <.000044g; world float32
        # X/Z adds <.001g horizontal drift. A .0003g vertical allowance keeps
        # this shallow plane above the independently verified actual surface.
        base=hi-.10+.0003
        for cell in cells:occupied.setdefault(cell,[]).append(len(accepted))
        accepted.append(p);envelopes.append(envelope);values.extend(p[k] for k in fields);bases.append(base);water_polys.append(Polygon(p['outlines']['water']['12']))
        height_rows.append({'id':p['id'],'roadId':p['roadId'],'minRenderedAsphaltYGame':lo,'maxRenderedAsphaltYGame':hi,'baseHeightGame':base,'maxWaterAboveAsphaltGame':hi-lo+.0083})
        if i%2000==0:print(json.dumps({'stage':'source-mesh-containment','checked':i,'accepted':len(accepted)}),flush=True)
    wet=shapely.union_all(water_polys);apron=shapely.union_all(envelopes)
    road_polys=[LineString(r['points']).buffer(r['width']/2,cap_style=2) for r in city['roads'] if r['grade']=='0' and not r['kind'].endswith('_link') and r['width']>=3.2]
    eligible=shapely.union_all(road_polys).intersection(land).difference(shapely.union_all(blocked))
    spawn=city['spawn'];center=Point(spawn['x'],spawn['z']);local=[]
    for radius in [80,120,180,250,440,900]:
        region=center.buffer(radius,quad_segs=64);denom=eligible.intersection(region).area;num=wet.intersection(region).area
        local.append({'radiusGame':radius,'eligibleRoadUnionGame2':denom,'waterUnionGame2':num,'fraction':num/denom if denom else None,'pools':sum(math.hypot(p['x']-spawn['x'],p['z']-spawn['z'])<radius for p in accepted)})
    coverage={'method':'all-LOD exact source-road/land/blocker margin and prepared asphalt triangle plane intersection; current GLB v5 independently bounded; no browser claim','target':[.25,1/3],'fraction':wet.area/eligible.area,'outsideEligibleGame2':wet.difference(eligible).area,'overlapGame2':sum(p.area for p in water_polys)-wet.area,'eligibleRoadUnionGame2':eligible.area,'waterUnionGame2':wet.area,'spawn':local,'safeMarginGame':.03,'maxReliefGame':.028,'maxWaterAboveAsphaltGame':max((p['maxWaterAboveAsphaltGame'] for p in height_rows),default=0)}
    stats=source['stats']|{'accepted':len(accepted),'estimatedWetArea':apron.area,'estimatedPuddleArea':wet.area}
    packed={'cityId':'hangzhou','version':2,'profileVariants':5,'stride':10,'values':values,'baseHeightsGame':bases,'stats':stats,'coverage':coverage}
    (out/'puddles-layout.json').write_text(json.dumps(packed,separators=(',',':')))
    order=sorted(range(len(accepted)),key=lambda i:math.hypot(accepted[i]['x']-spawn['x'],accepted[i]['z']-spawn['z']))[:180]
    fallback={'values':[v for i in order for v in values[i*10:(i+1)*10]],'baseHeightsGame':[bases[i] for i in order]}
    (out/'fallback.json').write_text(json.dumps(fallback,separators=(',',':')))
    (out/'source-plane-checks.json').write_text(json.dumps(height_rows,separators=(',',':')))
    report={'cityId':'hangzhou','kind':'exact source-and-prepared-mesh CPU validation','sourceGenerationSha256':digest(src/'generation.json'),'sourceLayoutSha256':digest(src/'unverified-layout.json'),'renderMeshManifestSha256':digest(meshroot/'manifest.json'),'validatorSha256':digest(Path(__file__)),'pools':len(accepted),'rejected':rejected,'coverage':coverage,'geometryPass':len(accepted)>0 and coverage['outsideEligibleGame2']<1e-5 and coverage['overlapGame2']<1,'coverageTargetPass':.25<=coverage['fraction']<=1/3,'seconds':time.monotonic()-start,'pending':['full current actual mesh and ground screenshot','rain/day/night visual review','GPU frame time and reflection appearance','final revised landmark collisions and road profiles'],'files':{p.name:digest(p) for p in out.iterdir() if p.is_file()}}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['geometryPass']:raise ValueError('Geometry gate failed')
if __name__=='__main__':main()
