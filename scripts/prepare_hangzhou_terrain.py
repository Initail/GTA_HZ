"""Sample source-bound Hangzhou DSM into an isolated terrain investigation.

Raw and filtered grids share WGS84 coordinates. Filtering is a ground estimate;
neither it nor interpolation claims new measured resolution. Roads/building
platforms/water levels are intentionally separate integration gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject,Resampling
from city_config import ROOT,load_city,project

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def neighborhood(grid,kind):
 padded=np.pad(grid,1,mode='edge')
 samples=[padded[j:j+grid.shape[0],i:i+grid.shape[1]] for j in range(3) for i in range(3)]
 if kind=='min':return np.minimum.reduce(samples)
 if kind=='max':return np.maximum.reduce(samples)
 return sum(samples)/9

def prepare(output,step=30,city_source='artifacts/cities/hangzhou/skeleton-261011-v3/city.json'):
 output=Path(output).resolve()
 if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate under artifacts required')
 source_path=ROOT/'data/hangzhou/dsm-source-manifest.json';source=json.loads(source_path.read_text())
 city=load_city('hangzhou');g=city['geography'];bbox=g['bboxWGS84']
 x0,z0=project(bbox[0],bbox[1],city);x1,z1=project(bbox[2],bbox[3],city)
 columns=int(np.ceil((x1-x0)/step))+1;rows=int(np.ceil((z1-z0)/step))+1
 z1=z0+(rows-1)*step
 affine=from_origin(g['originWGS84'][0]+(x0-step/2)/(g['eastMetresPerDegree']*g['scale']),
   g['originWGS84'][1]+(z1+step/2)/(g['northMetresPerDegree']*g['scale']),
   step/(g['eastMetresPerDegree']*g['scale']),step/(g['northMetresPerDegree']*g['scale']))
 dsm=np.full((rows,columns),np.nan,dtype=np.float32)
 for record in source['tiles']:
  path=ROOT/record['localPath']
  if digest(path)!=record['sha256']:raise ValueError('Changed DSM source')
  sample=np.full_like(dsm,np.nan)
  with rasterio.open(path) as ds:
   reproject(rasterio.band(ds,1),sample,src_transform=ds.transform,src_crs=ds.crs,
     dst_transform=affine,dst_crs='EPSG:4326',resampling=Resampling.bilinear,dst_nodata=np.nan)
  mask=np.isfinite(sample);dsm[mask]=sample[mask]
 if not np.all(np.isfinite(dsm)):raise ValueError('DSM does not cover the continuous study area')
 dsm=dsm[::-1].copy()
 # Morphological opening suppresses compact canopy/roof peaks. Broad wooded
 # slopes retain bias; this is an estimate, never a surveyed DTM or road deck.
 opened=neighborhood(neighborhood(dsm,'min'),'max')
 ground=neighborhood(opened,'mean')
 output.mkdir(parents=True,exist_ok=True)
 arrays={'dsm-egm2008-metres.bin':dsm.astype('<f4'),'ground-estimate-egm2008-metres.bin':ground.astype('<f4')}
 for name,array in arrays.items():(output/name).write_bytes(array.tobytes())
 def sample_point(lon,lat):
  x,z=project(lon,lat,city);i=round((x-x0)/step);j=round((z-z0)/step)
  return {'pointWGS84':[lon,lat],'nearestGridGame':[x0+i*step,z0+j*step],
    'dsmMetres':float(dsm[j,i]),'groundEstimateMetres':float(ground[j,i])}
 city_path=ROOT/city_source;city_data=json.loads(city_path.read_text())
 marks={m['id']:m for m in city_data['landmarks']}
 if city_data['meta']['cityId']!='hangzhou':raise ValueError('Hangzhou source places required')
 manifest={'schemaVersion':1,'cityId':'hangzhou','sourceManifestSha256':digest(source_path),
  'sourcePlacesSha256':digest(city_path),
  'coordinateConfigSha256':digest(ROOT/'config/cities/hangzhou.json'),'sources':source['tiles'],
  'grid':{'x0':x0,'z0':z0,'step':step,'columns':columns,'rows':rows,'rowOrder':'south-to-north'},
  'units':'real metres above EGM2008; not yet game-scaled','verticalScaleToApplyOnce':g['scale'],
  'files':{name:{'sha256':digest(output/name),'bytes':array.nbytes,'dtype':'little-endian-float32'} for name,array in arrays.items()},
  'method':{'nativeResolutionMetres':30,'sampleSpacingGameMetres':step,'sampleSpacingRealMetres':step/g['scale'],
   'sourceResampling':'bilinear','groundEstimate':'3x3 min then max then mean; removes compact surface spikes'},
  'samples':{'lingyin-main-hall':sample_point(marks['lingyin-temple']['lon'],marks['lingyin-temple']['lat']),
   'westLake-water-reference-point':sample_point(120.145,30.25),
   'wulin-square-centroid':sample_point(marks['wulin-square']['lon'],marks['wulin-square']['lat']),
   'qiantang-water-reference-point':sample_point(120.213,30.233)},
  'heightRangeMetres':[float(dsm.min()),float(dsm.max())],
  'status':'source-sampled-not-ground-or-driving-accepted',
  'pending':['ground datum and water levels','road decks and ramp profiles','tunnels and stacked surfaces',
   'building platforms','temple steps','runtime terrain mesh','collision','current visual and performance review']}
 (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'output':str(output),'grid':manifest['grid'],'samples':manifest['samples'],'range':manifest['heightRangeMetres']},ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--step',type=float,default=30)
 p.add_argument('--city-source',default='artifacts/cities/hangzhou/skeleton-261011-v3/city.json')
 a=p.parse_args();prepare(a.output,a.step,a.city_source)
