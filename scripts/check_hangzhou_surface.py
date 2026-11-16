"""Cross-language physical sampler audit; no browser, renderer, or pass substitution."""
from __future__ import annotations
import argparse,json,subprocess,random,math
from pathlib import Path
from city_config import ROOT
from hangzhou_surface import Surface,digest

def audit(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh artifact directory required')
    field=Surface(source);g=field.grid;randomizer=random.Random(261011);points=[]
    for _ in range(1200):
        points.append((g['x0']+randomizer.random()*(g['columns']-1)*g['step'],g['z0']+randomizer.random()*(g['rows']-1)*g['step'],'region'))
    # Exact tile perimeter and outside are part of the sampler contract.
    for x in [g['x0']-1,g['x0'],g['x0']+(g['columns']-1)*g['step'],g['x0']+g['columns']*g['step']]:
        for z in [g['z0']-1,g['z0'],g['z0']+(g['rows']-1)*g['step'],g['z0']+g['rows']*g['step']]:points.append((x,z,'boundary'))
    ground=[r for r in field.levels['roads'] if r['tier']==0];sampled=randomizer.sample(ground,min(2400,len(ground)))
    road_errors=[];derivatives=[]
    for road in sampled:
        index=randomizer.randrange(len(road['points'])-1);a,b=road['points'][index:index+2];x,z=(a[0]+b[0])/2,(a[1]+b[1])/2
        source_y=sum(road['heights'][index:index+2])/2;earth=field.ground(x,z)
        road_errors.append({'id':road['id'],'x':x,'z':z,'sourceY':source_y,'earthY':earth,'differenceGame':abs(source_y-earth)})
        dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz) or 1
        for distance in [0,road['width']/2,road['width']/2+10,road['width']/2+field.transition]:
            qx,qz=x-dz/length*distance,z+dx/length*distance;points.append((qx,qz,'road-band'))
            epsilon=1e-5
            derivatives.append(abs(field.ground(qx-epsilon,qz)-field.ground(qx+epsilon,qz)))
    samples=[{'x':x,'z':z,'kind':kind,'terrain':field.terrain(x,z),'ground':field.ground(x,z)} for x,z,kind in points]
    output.mkdir(parents=True);fixture=output/'sampler-fixture.json';fixture.write_text(json.dumps(samples,separators=(',',':')))
    report={'cityId':'hangzhou','source':str(source.relative_to(ROOT)),'fixtureSha256':digest(fixture),
        'inputs':{str(p.relative_to(ROOT)):digest(p) for p in [source/'geography/manifest.json',ROOT/'scripts/hangzhou_surface.py',ROOT/'src/city-road-levels.ts',Path(__file__)]},
        'samples':len(samples),'maxOppositeEpsilonDifferenceGame':max(derivatives),'epsilonGame':1e-5,
        'roadCentreComparison':{'sampled':len(road_errors),'over004':sum(r['differenceGame']>.04 for r in road_errors),'maxDifferenceGame':max(r['differenceGame'] for r in road_errors),'worst':sorted(road_errors,key=lambda r:r['differenceGame'],reverse=True)[:30]},
        'physicalAcceptance':'pending; blended earthworks and source road decks must be meshed independently and reconciled at junctions',
        'browserAcceptance':'not run'}
    (output/'python-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    subprocess.run(['node','--experimental-transform-types','scripts/check_hangzhou_surface.mjs',str(source),str(output)],cwd=ROOT,check=True)
    print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','roadCentreComparison']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--output',required=True);a=p.parse_args();audit(a.city_root,a.output)
