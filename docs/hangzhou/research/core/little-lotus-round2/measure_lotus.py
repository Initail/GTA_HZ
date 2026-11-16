"""Measure the fixed little-lotus outline; never import scene-initializing mesh."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    city=load_city('hangzhou');g=city['geography']
    data=ROOT/'data/processed/hangzhou/buildings.geojson';all_features=json.loads(data.read_text())['features']
    f=next(f for f in all_features if f['id']=='relation/9874418');far=next(f for f in all_features if f['id']=='way/626826731')
    ring=f['geometry']['coordinates'][0][0];origin=ring[0]
    p=[((x-origin[0])*g['eastMetresPerDegree'],(y-origin[1])*g['northMetresPerDegree']) for x,y in ring[:-1]]
    pairs=list(zip(p,p[1:]+p[:1]));area=sum(x*v-u*y for (x,y),(u,v) in pairs)/2
    cx=sum((x+u)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area);cy=sum((y+v)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area)
    center=[origin[0]+cx/g['eastMetresPerDegree'],origin[1]+cy/g['northMetresPerDegree']]
    local=[[x-cx,y-cy] for x,y in p];radii=[math.hypot(x,y) for x,y in local]
    far_ring=far['geometry']['coordinates'][0][0][:-1];fx=sum(x for x,y in far_ring)/len(far_ring);fy=sum(y for x,y in far_ring)/len(far_ring)
    distance=math.hypot((fx-center[0])*g['eastMetresPerDegree'],(fy-center[1])*g['northMetresPerDegree'])
    result={'cityId':'hangzhou','crs':'EPSG:4326','sourceFeatureId':f['id'],'sourcePbfSha256':digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'),
            'sourceSnapshot':'2026-10-11T20:21:06Z','buildingsSourceSha256':digest(data),'centerWGS84':center,'centerGameEN':project(*center,city),
            'footprintWGS84':ring,'footprintLocalMetresEN':local,'mappedAreaM2':abs(area),
            'bboxEastM':max(x for x,y in local)-min(x for x,y in local),'bboxNorthM':max(y for x,y in local)-min(y for x,y in local),
            'outerTipRadiiM':radii[::2],'insetRadiiM':radii[1::2],
            'mappedFirstTipAngleDegreesFromEast':math.degrees(math.atan2(local[0][1],local[0][0])),
            'mappedTipCount':len(local)//2,'baseBuildingIdsToExclude':['relation/9874418'],
            'nearbyCandidateRejected':{'id':'way/626826731','vertexMeanWGS84':[fx,fy],'distanceM':distance,
                                       'bboxEastM':(max(x for x,y in far_ring)-min(x for x,y in far_ring))*g['eastMetresPerDegree'],
                                       'bboxNorthM':(max(y for x,y in far_ring)-min(y for x,y in far_ring))*g['northMetresPerDegree'],
                                       'decision':'outside little-lotus outline; not inner bowl or roof part; preserve, function not determined from proximity'},
            'method':'area centroid, bbox and polar tip/inset radii from fixed WGS84 map vectors with city_config Hangzhou coefficients; physical metres before .60 scale',
            'uncertainty':'Mapped-outline accuracy unverified: ±5m plan allowance and ±3° exterior-petal orientation. Footprint semantics (wall tips/roof envelope) not a cadastral survey. source height=5 is not a verified full roof height and is not adopted.'}
    (HERE/'geofabrik-little-lotus-features.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[f,far]},ensure_ascii=False,indent=2)+'\n')
    (HERE/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
