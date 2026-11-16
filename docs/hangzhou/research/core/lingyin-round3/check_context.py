"""Read-only fixed OSM and terrain-v3 context; never chooses actual hall bases."""
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from shapely.geometry import box,shape

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


def main():
    city=load_city('hangzhou')
    spec=json.loads((OUT/'spec.json').read_text())
    source=ROOT/'data/processed/hangzhou/buildings.geojson'
    buildings={f['id']:f for f in json.loads(source.read_text())['features']}
    for hall in spec['baseHallSpec']['halls']:
        f=buildings[hall['sourceFeatureIds'][0]]
        assert shape(f['geometry']).is_valid
        # Exact fixed source vertex sets, not newly guessed plans.
        geometry=f['geometry']
        if geometry['type']=='MultiPolygon':
            assert len(geometry['coordinates'])==1 and len(geometry['coordinates'][0])==1
            ring=geometry['coordinates'][0][0]
        else:
            assert geometry['type']=='Polygon' and len(geometry['coordinates'])==1
            ring=geometry['coordinates'][0]
        mapped={tuple(p) for p in ring[:-1]}
        assert mapped=={tuple(p) for p in hall['footprintWGS84']}
    path=ROOT/'artifacts/cities/hangzhou/terrain-glo30-v3'
    manifest=json.loads((path/'manifest.json').read_text())
    grid=manifest['grid']
    arrays={}
    for name,row in manifest['files'].items():
        p=path/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
        a=np.fromfile(p,dtype='<f4').reshape(grid['rows'],grid['columns'])
        assert np.isfinite(a).all()
        arrays[name]=a
    rows=[]
    for hall in spec['baseHallSpec']['halls']:
        x,z=project(*hall['centroidWGS84'],city)
        i=round((x-grid['x0'])/grid['step'])
        j=round((z-grid['z0'])/grid['step'])
        rows.append({'id':hall['id'],'pointWGS84':hall['centroidWGS84'],
          'nearestGridGame':[grid['x0']+i*grid['step'],grid['z0']+j*grid['step']],
          'nearestHorizontalOffsetRealM':math.hypot(grid['x0']+i*grid['step']-x,grid['z0']+j*grid['step']-z)/city['geography']['scale'],
          'sampleMetresEGM2008':{name:float(a[j,i]) for name,a in arrays.items()},
          'sample3x3RangeMetresEGM2008':{name:[float(a[j-1:j+2,i-1:i+2].min()),float(a[j-1:j+2,i-1:i+2].max())] for name,a in arrays.items()},
          'actualHallThresholdYGame':None,'actualStepCount':None,
          'use':'broad canopy/roof/mountain context only; not site platform input'})
    roads_file=ROOT/'data/processed/hangzhou/roads.geojson'
    roads=json.loads(roads_file.read_text())['features']
    extent=box(120.0954,30.2417,120.0977,30.245)
    near=[f for f in roads if extent.intersects(shape(f['geometry']))]
    (OUT/'source-context.geojson').write_text(json.dumps({'type':'FeatureCollection','features':near,
      'sourceCRS':'EPSG:4326','sourceSnapshotSha256':spec['sourceSnapshotSha256'],'license':'ODbL-1.0',
      'interpretation':'Nearby ways only. No mapped way automatically equates to the central five-hall stair system.'},ensure_ascii=False,indent=2)+'\n')
    result={'schemaVersion':1,'status':'passed-read-only-context-contract','at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'inputHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [source,roads_file,path/'manifest.json',ROOT/'config/cities/hangzhou.json']},
      'fiveFixedOsmHallVertexSets':'matched','terrainArrays':manifest['files'],'halls':rows,
      'nearbyWays':[{'id':f['id'],'tags':f['properties']['tags'],'nodeIds':f['properties'].get('nodeIds'),
        'actualAxialHallStairsConfirmed':False} for f in near],
      'terrainInterpretation':{'verticalDatum':'EGM2008 EPSG:3855','sourceType':'30m DSM, not surveyed DTM',
        'sampleGridRealM':grid['step']/city['geography']['scale'],
        'effectiveFilterDependency':'3x3 min -> max -> mean; radius3 samples,7x7 support,300m center-to-center at50m real grid',
        'actualFloorInference':None,'verticalDatumConversionApplied':None,
        'warning':'The effective support extent is not a hall terrace. Interpolation/filtering does not establish ground accuracy.'},
      'boundary':'unknown WGS84 cadastral/monastery outer ring; Fig5/official overview are uncalibrated diagrams',
      'runtimeAcceptance':'unknown; no terrain cuts, path/entry collision or accessible-route tests performed'}
    (OUT/'context-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'matchedHalls':len(rows),'nearbyWays':len(near),'v3Samples':[{**{'id':r['id']},**r['sampleMetresEGM2008']} for r in rows]},ensure_ascii=False))


if __name__=='__main__':main()
