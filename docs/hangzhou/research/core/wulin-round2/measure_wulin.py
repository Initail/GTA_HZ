"""Fixed-map Wulin area/fountain identity, through Hangzhou projection only."""
from pathlib import Path
import json
import hashlib
import math
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ids=json.loads((ROOT/'data/hangzhou/osm-identities.json').read_text())
    assert ids['objects']['wulin-square']['sourceFeatureIds']==['way/589390765']
    city=load_city('hangzhou');geo=city['geography']
    places=ROOT/'data/processed/hangzhou/places.geojson'
    pois=ROOT/'data/processed/hangzhou/pois.geojson'
    square=next(f for f in json.loads(places.read_text())['features'] if f['id']=='way/589390765')
    fountain=next(f for f in json.loads(pois.read_text())['features'] if f['id']=='node/4228526321')
    ring=square['geometry']['coordinates'][0][0]
    en=[tuple(v/geo['scale'] for v in project(*p,city)) for p in ring[:-1]]
    edges=list(zip(en,en[1:]+en[:1]))
    area=sum(x*v-u*y for (x,y),(u,v) in edges)/2
    cx=sum((x+u)*(x*v-u*y) for (x,y),(u,v) in edges)/(6*area)
    cy=sum((y+v)*(x*v-u*y) for (x,y),(u,v) in edges)/(6*area)
    center=[geo['originWGS84'][0]+cx/geo['eastMetresPerDegree'],geo['originWGS84'][1]+cy/geo['northMetresPerDegree']]
    fc=fountain['geometry']['coordinates'];fg=project(*fc,city)
    result={'cityId':'hangzhou','crs':'EPSG:4326','sourceFeatureId':square['id'],'sourcePbfSha256':digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'),
            'sourceSnapshot':'2026-10-11T20:21:06Z','osmIdentitiesSha256':digest(ROOT/'data/hangzhou/osm-identities.json'),
            'processedSourceSha256':{'places':digest(places),'pois':digest(pois)},
            'footprintWGS84':ring,'centerWGS84':center,'centerGameEN':project(*center,city),
            'mappedAreaM2':abs(area),'bboxEastM':max(x for x,y in en)-min(x for x,y in en),
            'bboxNorthM':max(y for x,y in en)-min(y for x,y in en),
            'fountainSourceFeatureId':fountain['id'],'fountainWGS84':fc,'fountainGameEN':fg,
            'fountainOffsetRealEN':[fg[0]/geo['scale']-cx,fg[1]/geo['scale']-cy],
            'axisBearingTowardExhibitionHallDegrees':0,'axisBasis':'estimated map/photo cardinal relationship, ±3°',
            'method':'area centroid of fixed WGS84 mapped ring using city_config Hangzhou coefficients; fountain is mapped POI, not measured basin center',
            'uncertainty':'OSM vector accuracy unverified, plan allowance ±5m. Mapped area excludes northern exhibition forecourt beyond polygon; not a cadastral survey. Fountain point center ±3m; no mapped basin outline/diameter.'}
    (HERE/'geofabrik-wulin-features.geojson').write_text(json.dumps({'type':'FeatureCollection','cityId':'hangzhou','features':[square,fountain]},ensure_ascii=False,indent=2)+'\n')
    (HERE/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
