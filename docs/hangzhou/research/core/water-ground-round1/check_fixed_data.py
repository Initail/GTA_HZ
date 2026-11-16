"""Read-only OSM/DSM/datum audit; all reports stay in this independent scope."""
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
import pyproj
from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.transformer import TransformerGroup
from shapely.geometry import Polygon,Point,box,shape
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,d):(OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    city=load_city('hangzhou');terrain=ROOT/'artifacts/cities/hangzhou/terrain-glo30-v2';mp=terrain/'manifest.json';m=json.loads(mp.read_text());grid=m['grid'];scale=city['geography']['scale'];assert scale==.6
    arrays={}
    for name,r in m['files'].items():
        p=terrain/name;assert digest(p)==r['sha256'];a=np.fromfile(p,dtype='<f4').reshape(grid['rows'],grid['columns']);assert np.isfinite(a).all();arrays[name]=a
    def sample(lon,lat):
        x,z=project(lon,lat,city);i,j=round((x-grid['x0'])/grid['step']),round((z-grid['z0'])/grid['step']);assert 1<=i<grid['columns']-1 and 1<=j<grid['rows']-1
        return {'pointWGS84':[lon,lat],'nearestGridIndices':[i,j],'nearestGridGame':[grid['x0']+i*grid['step'],grid['z0']+j*grid['step']],
          'nearestGridHorizontalOffsetRealM':math.hypot(grid['x0']+i*grid['step']-x,grid['z0']+j*grid['step']-z)/scale,
          'dsmMetresEGM2008':float(arrays['dsm-egm2008-metres.bin'][j,i]),
          'filteredEstimateMetresEGM2008':float(arrays['ground-estimate-egm2008-metres.bin'][j,i]),
          'neighborhood3x3RangesMetresEGM2008':{name:[float(a[j-1:j+2,i-1:i+2].min()),float(a[j-1:j+2,i-1:i+2].max())] for name,a in arrays.items()},
          'basis':'sampled existing edited DSM/derived estimate; not measured public floor, water level or steps'}
    lingpath=ROOT/'docs/hangzhou/research/core/lingyin-round2/spec.json';ls=json.loads(lingpath.read_text())
    halls=[{'id':h['id'],'name':h['name'],'sourceFeatureIds':h['sourceFeatureIds'],'frozenModuleRelativeBaseM':h['baseElevationRelativeM'],
      'sample':sample(*h['centroidWGS84']),'groundFloorAbsoluteMetres':None,'stepCount':None,'stepHeightM':None,
      'blocker':'DSM/filtered canopy-roof/slope sample cannot establish surveyed platform datum or axial stair run'} for h in ls['halls']]
    points={'westLake-reference':[120.145,30.25],'westLake-north':[120.143,30.256],'westLake-east':[120.150,30.254],
      'westLake-south':[120.146,30.239],'qiantang-reference':[120.213,30.233],
      'qiantang-off-balcony':[120.2148,30.2428],'qiantang-east':[120.2215,30.235]}
    water=json.loads((ROOT/'data/processed/hangzhou/water.geojson').read_text())['features'];wd={f['id']:f for f in water}
    water_samples=[]
    for name,pt in points.items():
        ident='relation/2308774' if name.startswith('westLake') else 'relation/8227206';inside=shape(wd[ident]['geometry']).covers(Point(*pt))
        water_samples.append({'id':name,'sourceWaterId':ident,'sourcePolygonCoversReference':inside,
          'sample':sample(*pt) if inside else None,'observedActualWaterLevel':None})
    balcony=json.loads((ROOT/'docs/hangzhou/research/core/city-balcony-round2/spec.json').read_text())
    theatre=json.loads((ROOT/'docs/hangzhou/research/core/grand-theatre-round2/spec.json').read_text())
    platform_samples={'cityBalcony-footprintCentroid':sample(balcony['anchor']['lon'],balcony['anchor']['lat']),
      'grandTheatre-footprintCentroid':sample(theatre['anchor']['lon'],theatre['anchor']['lat']),
      'cityBalcony-sourceShoreMouths':[{'id':p['id'],'sample':sample(*p['wgs84']),'verifiedEntry':False} for p in balcony['shoreApproachEdges']]}
    roads=json.loads((ROOT/'data/processed/hangzhou/roads.geojson').read_text())['features']
    temple_box=box(120.0954,30.2417,120.0977,30.245);near=[f for f in roads if temple_box.intersects(shape(f['geometry']))]
    combined=Polygon([tuple(p) for h in ls['halls'] for p in h['footprintWGS84']]).convex_hull
    metric=lambda p: ((p[0]-ls['anchor']['lon'])*city['geography']['eastMetresPerDegree'],(p[1]-ls['anchor']['lat'])*city['geography']['northMetresPerDegree'])
    from shapely.ops import transform
    bounds=transform(lambda x,y,z=None:metric((x,y)),combined)
    detailed=[]
    for f in near:
        sh=transform(lambda x,y,z=None:metric((x,y)),shape(f['geometry']));tags=f['properties']['tags']
        detailed.append({'id':f['id'],'name':f['properties'].get('name'),'tags':tags,'nodeIds':f['properties'].get('nodeIds'),
          'distanceToFiveHallConvexEnvelopeM':sh.distance(bounds),'hasNumericalEle':bool(tags.get('ele')),
          'hasStepCount':bool(tags.get('step_count')),'interpretation':'nearby source way, not automatically five-hall axial stairs; source=survey is an OSM tag, no original height survey delivered'})
    pool_box=box(120.209,30.2452,120.2118,30.2476)
    pool_hits=[{'id':f['id'],'name':f['properties'].get('name'),'tags':f['properties']['tags'],'geometryType':f['geometry']['type']} for f in water if pool_box.intersects(shape(f['geometry']))]
    snapshots=write('source-context-features.geojson',{'type':'FeatureCollection','crs':'EPSG:4326','license':'ODbL-1.0',
      'sourceSnapshotSha256':'4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9','features':near,
      'templeBBoxWGS84':list(temple_box.bounds),'poolBBoxWGS84':list(pool_box.bounds),'poolWaterLayerHits':pool_hits,
      'searchLimit':'Current processed roads/water layers only, not a statement that no unextracted or newly mapped object can exist in all OSM.'})
    group=TransformerGroup('EPSG:4326+3855','EPSG:4326+5737',always_xy=True,allow_ballpark=False,area_of_interest=AreaOfInterest(119.9,30.1,120.4,30.5))
    write('datum-check.json',{'checkedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'pyprojVersion':pyproj.__version__,'projVersion':pyproj.proj_version_str,
      'verticalCRSs':{str(code):{'name':CRS.from_epsg(code).name,'datum':CRS.from_epsg(code).datum.name} for code in [3855,5736,5737]},
      'sourceCompound':'EPSG:4326+3855','targetCompound':'EPSG:4326+5737','allowBallpark':False,
      'availableNonBallparkOperations':[{'description':t.description,'accuracyM':t.accuracy} for t in group.transformers],
      'unavailableOperationsCount':len(group.unavailable_operations),'empiricalOffsetApplied':None,
      'blockers':['Official West Lake documents label Yellow Sea height but do not identify1956or1985 edition.',
        'No trusted local vertical tie/transformation supplied. Identity/ballpark transformation not accepted.',
        'Difference between DSM7.5 and reported7.18 must not be fitted as a datum correction; edited water and time/level are additional effects.']})
    files=[ROOT/'config/cities/hangzhou.json',ROOT/'data/hangzhou/dsm-source-manifest.json',mp,lingpath,ROOT/'docs/hangzhou/research/core/city-balcony-round2/spec.json',
      ROOT/'docs/hangzhou/research/core/grand-theatre-round2/spec.json',ROOT/'data/processed/hangzhou/roads.geojson',ROOT/'data/processed/hangzhou/water.geojson']
    write('fixed-data-check.json',{'schemaVersion':1,'status':'passed-read-only-source-and-sample-contract','inputSha256':{str(p.relative_to(ROOT)):digest(p) for p in files},
      'coordinateProjection':{key:city['geography'][key] for key in ['originWGS84','eastMetresPerDegree','northMetresPerDegree','scale']},
      'sourceArraySha256':{name:r['sha256'] for name,r in m['files'].items()},'nativeDSMResolutionM':30,
      'sampleGridSpacingGame':grid['step'],'sampleGridSpacingRealM':grid['step']/scale,
      'nearestGridMaximumHorizontalOffsetRealM':grid['step']/scale/math.sqrt(2),
      'filterStages':'3x3min then3x3max then3x3mean','effectiveSupportRadiusGridCells':3,
      'effectiveSupportWidthGridCells':7,'effectiveSupportCenterToCenterSpanRealM':6*grid['step']/scale,
      'filterSupportInterpretation':'Three radius1stages depend on raw samples up to radius3. This is a dependency bound, not increased native resolution or actual feature precision.',
      'halls':halls,'waterSamples':water_samples,'platformSamples':platform_samples,
      'templeNearbyRoads':detailed,'theatreWaterLayerHits':pool_hits,
      'scalePolicy':'array height unscaled EGM2008 metres. Apply .60 once only after selected height/relative reference/datum contract; game-unit lm.y is not rescaled.',
      'formalGroundWaterAcceptance':'unknown; no construction survey, current tide series, base datum conversion or runtime driving test'})
    print(json.dumps({'halls':[(h['name'],round(h['sample']['dsmMetresEGM2008'],3),round(h['sample']['filteredEstimateMetresEGM2008'],3)) for h in halls],
      'nearbyRoads':len(near),'poolSourceHits':[f['id'] for f in pool_hits],'nonBallparkDatumOperations':len(group.transformers),'writesScope':str(OUT.relative_to(ROOT))},ensure_ascii=False))
if __name__=='__main__':main()
