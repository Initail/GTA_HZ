"""Pin public Copernicus GLO-30 source tiles; never fetch Shenzhen terrain.

The first HTTPS acquisition records SHA256, size and HTTP object metadata.
Subsequent runs verify the local content and refuse a changed source silently.
"""
from __future__ import annotations
import hashlib
import json
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from city_config import ROOT

DEST=ROOT/'data/raw/hangzhou/dsm'
NOTICE='produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved'
LICENSE='https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def acquire(lon):
 name=f'Copernicus_DSM_COG_10_N30_00_E{lon}_00_DEM'
 url=f'https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif'
 path=DEST/(name+'.tif');manifest=path.with_suffix('.manifest.json')
 if path.exists():
  if not manifest.exists():raise ValueError('Existing source without provenance: '+str(path))
  record=json.loads(manifest.read_text())
  if path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:raise ValueError('Changed cached source: '+str(path))
  return record
 part=path.with_suffix('.tif.part')
 if part.exists():raise ValueError('Incomplete download preserved; review before retry: '+str(part))
 with urllib.request.urlopen(url,timeout=45) as response,part.open('xb') as out:
  headers={key:response.headers.get(key) for key in ['Content-Length','Last-Modified','ETag']}
  while block:=response.read(1024*1024):out.write(block)
 if headers['Content-Length'] and part.stat().st_size!=int(headers['Content-Length']):raise ValueError('Incomplete source tile')
 import rasterio
 with rasterio.open(part) as ds:
  if ds.crs.to_epsg()!=4326 or ds.width!=3600 or ds.height!=3600 or ds.count!=1:raise ValueError('Unexpected source raster grid')
  grid={'width':ds.width,'height':ds.height,'bounds':list(ds.bounds),'transform':list(ds.transform),'nodata':ds.nodata}
 record={'url':url,'localPath':str(path.relative_to(ROOT)),'sha256':digest(part),'bytes':part.stat().st_size,
  'downloadedAtUTC':datetime.now(timezone.utc).isoformat(),'httpObjectMetadata':headers,
  'sourceType':'DSM including vegetation/buildings; not a surveyed DTM','release':'AWS Copernicus DEM 2021',
  'nominalResolutionMetres':30,'nativeGridArcSeconds':1,'horizontalCRS':'EPSG:4326',
  'verticalDatum':'EGM2008 / EPSG:3855','grid':grid,'licenseUrl':LICENSE,'derivativeNotice':NOTICE,
  'liabilityNotice':'The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.',
  'status':'source-raster-verified; terrain-adaptation-pending'}
 part.replace(path);manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 print(name,record['bytes'],record['sha256'],flush=True)
 return record

def main():
 DEST.mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(acquire,[119,120]))
 output={'schemaVersion':1,'provider':'Copernicus / ESA / EU; public AWS hosted by Sinergise',
  'sourcePage':'https://registry.opendata.aws/copernicus-dem/','tiles':records,'licenseUrl':LICENSE,
  'status':'source-verified-not-ground-or-road-validation'}
 (ROOT/'data/hangzhou/dsm-source-manifest.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
