"""Fixed-source mapped theatre components; no scene imports."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project

IDS=['way/626838819','way/626838817','way/626838818','way/626838816']+[f'way/{i}' for i in range(626826745,626826755)]
PRESERVE=['way/582256524','way/626826761','way/626838543','way/626838908','way/600800340','way/600800341','way/600800342']


def main():
    city=load_city('hangzhou');g=city['geography'];source=ROOT/'data/processed/hangzhou/buildings.geojson'
    features={f['id']:f for f in json.loads(source.read_text())['features']};origin=features[IDS[0]]['geometry']['coordinates'][0][0][0]
    def stats(ring):
        q=[((x-origin[0])*g['eastMetresPerDegree'],(y-origin[1])*g['northMetresPerDegree']) for x,y in ring[:-1]]
        pairs=list(zip(q,q[1:]+q[:1]));area=sum(x*v-u*y for (x,y),(u,v) in pairs)/2
        c=[sum((x+u)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area),sum((y+v)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area)]
        return area,c,q
    area,anchor,q=stats(features[IDS[0]]['geometry']['coordinates'][0][0]);center=[origin[0]+anchor[0]/g['eastMetresPerDegree'],origin[1]+anchor[1]/g['northMetresPerDegree']]
    parts=[]
    for ident in IDS:
        f=features[ident];raw=f['geometry']['coordinates'][0][0];a,c,points=stats(raw);p=[[x-anchor[0],y-anchor[1]] for x,y in points]
        parts.append({'id':ident,'tags':f['properties']['tags'],'footprintWGS84':raw,'footprintLocalMetresEN':p,
            'centroidLocalMetresEN':[c[0]-anchor[0],c[1]-anchor[1]],'mappedAreaM2':abs(a),
            'bboxEastM':max(x for x,y in p)-min(x for x,y in p),'bboxNorthM':max(y for x,y in p)-min(y for x,y in p),
            'splitIndexLowestNorth':min(range(len(p)),key=lambda i:p[i][1])})
    core=next(c for c in parts if c['id']=='way/626838816');shell=next(c for c in parts if c['id']=='way/626838817')
    delta=[core['centroidLocalMetresEN'][i]-shell['centroidLocalMetresEN'][i] for i in range(2)];bearing=(90-math.degrees(math.atan2(delta[1],delta[0])))%360
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result={'cityId':'hangzhou','crs':'EPSG:4326','sourceFeatureId':IDS[0],'centerWGS84':center,'centerGameEN':project(*center,city),
        'sourcePbfSha256':sha(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'),'sourceSnapshot':'2026-10-11T20:21:06Z',
        'buildingsSourceSha256':sha(source),'components':parts,'frontBearingDegreesFromNorth':bearing,'baseBuildingIdsToExclude':IDS,
        'preserveNeighborIds':PRESERVE,'method':'signed polygon centroid and exact plans with Hangzhou config physical metres; front normal from mapped crescent centroid to front circular part; nested crescents split at lowest north point for separate inside/outside curves',
        'uncertainty':'plan±5m/direction±5°; nonstandard height<min_height parts are contour order only, not survey/standard elevations; main height3 is not full theatre height. Fixed water/places have no isolated pool polygon/POI in bounded site search.'}
    (HERE/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (HERE/'geofabrik-theatre-features.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[features[i] for i in IDS+PRESERVE]},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'centerWGS84':center,'centerGameEN':result['centerGameEN'],'frontBearing':bearing,'componentCount':len(parts)},ensure_ascii=False))


if __name__=='__main__':main()
