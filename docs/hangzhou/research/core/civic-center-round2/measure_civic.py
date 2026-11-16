"""Measure fixed civic-center rings and component plans without scene imports."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project

IDS={'A':'way/336830558','B':'way/336830559','C':'way/336830561',
     'D':'way/336830562','E':'way/336830564','F':'way/336830565',
     'H':'way/336828914','J':'way/336828913','K':'way/336828912','L':'way/336828911',
     'G-roof-pavilion':'way/582480145','roof-oval':'way/582480146'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(ring,g,origin):
    pts=[((x-origin[0])*g['eastMetresPerDegree'],(y-origin[1])*g['northMetresPerDegree']) for x,y in ring[:-1]]
    pairs=list(zip(pts,pts[1:]+pts[:1]));area=sum(x*v-u*y for (x,y),(u,v) in pairs)/2
    cx=sum((x+u)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area)
    cy=sum((y+v)*(x*v-u*y) for (x,y),(u,v) in pairs)/(6*area)
    return area,(cx,cy),pts


def main():
    city=load_city('hangzhou');g=city['geography'];src=ROOT/'data/processed/hangzhou/buildings.geojson'
    features={f['id']:f for f in json.loads(src.read_text())['features']};main=features['relation/4762996']
    rings=main['geometry']['coordinates'][0];origin=rings[0][0]
    ms=[stats(r,g,origin) for r in rings];area=sum(s[0] for s in ms)
    cx=sum(s[0]*s[1][0] for s in ms)/area;cy=sum(s[0]*s[1][1] for s in ms)/area
    center=[origin[0]+cx/g['eastMetresPerDegree'],origin[1]+cy/g['northMetresPerDegree']]
    components=[]
    for name,ident in IDS.items():
        f=features[ident];ring=f['geometry']['coordinates'][0][0];a,c,p=stats(ring,g,center)
        longest=max(zip(p,p[1:]+p[:1]),key=lambda e:math.dist(*e))
        angle=math.degrees(math.atan2(longest[1][1]-longest[0][1],longest[1][0]-longest[0][0]))
        components.append({'name':name,'id':ident,'tags':f['properties']['tags'],'footprintWGS84':ring,
            'footprintLocalMetresEN':p,'centroidLocalMetresEN':c,'mappedAreaM2':abs(a),
            'bboxEastM':max(x for x,y in p)-min(x for x,y in p),'bboxNorthM':max(y for x,y in p)-min(y for x,y in p),
            'bearingDegreesFromEast':math.degrees(math.atan2(c[1],c[0])),
            'longestEdgeAngleDegreesFromEast':angle,'role':('tower' if name in 'ABCDEF' and len(name)==1 else 'podium' if name in 'HJKL' else 'roof-pavilion')})
    localrings=[[[x-cx,y-cy] for x,y in s[2]] for s in ms]
    allpoints=[p for c in components for p in c['footprintLocalMetresEN']]
    result={'cityId':'hangzhou','crs':'EPSG:4326','sourceFeatureId':'relation/4762996',
        'sourcePbfSha256':digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf'),
        'sourceSnapshot':'2026-10-11T20:21:06Z','buildingsSourceSha256':digest(src),
        'centerWGS84':center,'centerGameEN':project(*center,city),
        'ringFootprintsWGS84':rings,'ringFootprintsLocalMetresEN':localrings,
        'mappedAnnulusAreaM2':abs(area),'ringRadialMetres':[[min(math.hypot(*p) for p in r),max(math.hypot(*p) for p in r)] for r in localrings],
        'components':components,'baseBuildingIdsToExclude':['relation/4762996']+list(IDS.values()),
        'componentEnvelopeEastM':max(x for x,y in allpoints)-min(x for x,y in allpoints),
        'componentEnvelopeNorthM':max(y for x,y in allpoints)-min(y for x,y in allpoints),
        'preserveUndergroundIds':['way/336828917','way/336828929'],
        'method':'Signed outer-minus-hole area centroid; each mapped polygon retained exactly and projected with Hangzhou city_config ellipsoidal coefficients before .60 scale.',
        'uncertainty':'Map geometry is not survey: ±5m allowance / ±3° tower and podium direction. OSM tower height120 and H height80 are unverified and not adopted. G/unnamed oval map parts correspond to roof pavilion form by source-photo comparison, not the whole garden building.'}
    subset=[main]+[features[i] for i in IDS.values()]+[features[i] for i in result['preserveUndergroundIds']]
    (HERE/'geofabrik-civic-features.geojson').write_text(json.dumps({'type':'FeatureCollection','features':subset},ensure_ascii=False,indent=2)+'\n')
    (HERE/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'center':center,'gameEN':result['centerGameEN'],'ringRadii':result['ringRadialMetres'],'components':[{k:v for k,v in c.items() if k not in ['footprintWGS84','footprintLocalMetresEN','tags']} for c in components]},ensure_ascii=False))


if __name__=='__main__':main()
