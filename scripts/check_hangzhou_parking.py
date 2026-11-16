"""Independent serialized parking clearance check using exact GEOS distances.

Does not call the producer's clear() or fill missing results with passes. Checks
horizontal full-body envelopes only; terrain, appearance and game QA are separate.
"""
from __future__ import annotations
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString
from shapely.strtree import STRtree
from city_config import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(file,output,collision_file=None):
    began=time.monotonic();file,output=Path(file).resolve(),Path(output).resolve();data=json.loads(file.read_text())
    if data.get('cityId')!='hangzhou' or output.exists():raise ValueError('Hangzhou input and fresh report required')
    for name,value in data['sourceInputsSha256'].items():
        if sha(ROOT/name)!=value:raise ValueError('Changed source '+name)
    def source(suffix):return next(ROOT/name for name in data['sourceInputsSha256'] if name.endswith(suffix))
    city=json.loads(source('/city.json').read_text());bikes=np.array(data['bikes']);points=shapely.points(bikes[:,:2]);policy=data['clearanceEnvelopeGame'];radius=policy['fullBodyRadius'];violations={}
    def report(name,indices):violations[name]=sorted(set(map(int,indices)))
    def polygons(items):return [Polygon(rings[0],rings[1:]) for rings in items]
    land=shapely.union_all(polygons(city['land']));water=shapely.union_all(polygons([w['rings'] for w in city['water']]))
    report('land',np.flatnonzero(~shapely.covers(land,points)|(shapely.distance(points,land.boundary)<radius-1e-8)))
    report('water',np.flatnonzero(shapely.distance(points,water)<radius+policy['waterMargin']-1e-8))
    def distances(name,geometry,limits):
        tree=STRtree(geometry);pairs=tree.query(points,predicate='dwithin',distance=float(np.max(limits)))
        if not pairs.size:report(name,[]);return
        d=shapely.distance(points[pairs[0]],np.array(geometry,dtype=object)[pairs[1]])
        threshold=np.asarray(limits);threshold=threshold[pairs[1]] if threshold.ndim else threshold
        report(name,pairs[0][d<threshold-1e-8])
    distances('road',[LineString(r['points']) for r in city['roads']],np.array([r['width']/2+radius+policy['roadMargin'] for r in city['roads']]))
    distances('building',polygons([b['rings'] for b in city['buildings']]),radius+policy['buildingMargin'])
    fixtures=[('lamp','/lamps.json',lambda d:[p[:2] for p in d],radius+.7),
      ('bench','/street/manifest.json',lambda d:[[p['x'],p['z']] for p in d['placements']],radius+1.2),
      ('canopy','/landscape/canopy-trees.json',lambda d:[p[:2] for p in d['trees']],policy['trunkCentreClearance']),
      ('lowTree','/landscape/planting.json',lambda d:[p[:2] for p in d['trees']],policy['trunkCentreClearance']),
      ('signal','/signals/traffic-signals.json',lambda d:[[p['x'],p['z']] for j in d['junctions'] for p in j['arms']],policy['signalPoleCentreClearance'])]
    for name,suffix,positions,limit in fixtures:distances(name,list(shapely.points(positions(json.loads(source(suffix).read_text())))),limit)
    marks=[m for m in city['landmarks'] if m.get('height',0)>0]
    distances('landmarkReservation',list(shapely.points([[m['x'],m['z']] for m in marks])),np.array([max(m['excludeRadius'],12)+radius for m in marks]))
    pairs=STRtree(points).query(points,predicate='dwithin',distance=policy['minimumBikeCentreSpacing']);pairs=pairs[:,pairs[0]<pairs[1]]
    d=shapely.distance(points[pairs[0]],points[pairs[1]]);bad=pairs[:,d<policy['minimumBikeCentreSpacing']-1e-8]
    report('otherBike',bad.ravel());new_detail=None
    if collision_file:
        cp=Path(collision_file).resolve();details=json.loads(cp.read_text())['collisionFootprints'];distances('newDetailHorizontalEnvelope',polygons([b['rings'] for b in details]),radius+policy['buildingMargin'])
        new_detail={'path':str(cp.relative_to(ROOT)),'sha256':sha(cp),'note':'conservative horizontal envelope including overhead objects; conflicts need height/context review'}
    result={'kind':'independent-serialized-full-body-parking-clearance','cityId':'hangzhou','bikes':len(bikes),'source':str(file.relative_to(ROOT)),'sha256':sha(file),
      'sourceInputsSha256':data['sourceInputsSha256'],'checkerSha256':sha(Path(__file__)),'newDetail':new_detail,
      'violations':{k:{'count':len(v),'bikeIndices':v} for k,v in violations.items()},'pass':not any(violations.values()),'cpuSeconds':time.monotonic()-began,
      'pending':['ground slopes and kickstand contact','parked runtime meshes/collision','browser views and performance']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['sourceInputsSha256','violations']},indent=2));print({k:len(v) for k,v in violations.items()})
    if not result['pass']:raise SystemExit(2)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--collision');a=p.parse_args();audit(a.input,a.output,a.collision)
