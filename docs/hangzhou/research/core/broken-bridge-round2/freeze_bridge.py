"""Freeze fixed OSM line/area and the original UNESCO single-arch bridge evidence."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city
OUT=Path(__file__).resolve().parent
PREFIX=str(OUT.relative_to(ROOT))
DATE='2026-10-13'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,data):
    p=OUT/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return digest(p)


def main():
    geo=load_city('hangzhou')['geography'];e,n=geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    roads=json.loads((ROOT/'data/processed/hangzhou/roads.geojson').read_text())['features']
    places=json.loads((ROOT/'data/processed/hangzhou/places.geojson').read_text())['features']
    road=next(f for f in roads if f['properties']['osm_id']==28538289)
    area=next(f for f in places if f['properties']['osm_id']==1466925249)
    assert road['properties']['tags']['bridge']=='yes'
    assert area['properties']['tags']['man_made']=='bridge'
    assert road['properties']['name']==area['properties']['name']=='断桥'
    a,b=road['geometry']['coordinates'];anchor=[(a[0]+b[0])/2,(a[1]+b[1])/2]
    dx,dy=(b[0]-a[0])*e,(b[1]-a[1])*n;length=math.hypot(dx,dy)
    ca,sa=dx/length,dy/length
    ring=area['geometry']['coordinates'][0][0][:-1]
    assert a in ring, 'shared southern point no longer matches'
    metric=[((x-anchor[0])*e,(y-anchor[1])*n) for x,y in ring]
    uv=[[x*ca+y*sa,-x*sa+y*ca] for x,y in metric]
    bearings=math.degrees(math.atan2(dx,dy))%360
    connections=[f for f in roads if f['properties']['osm_id']!=28538289
                 and set(f['properties'].get('nodeIds',[])) & set(road['properties']['nodeIds'])]
    assert {f['properties']['osm_id'] for f in connections}=={28538286,28538290}
    pbf_hash=digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf')
    assert pbf_hash=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    features_hash=write('geofabrik-bridge-features.geojson',{'type':'FeatureCollection',
        'sourceSnapshotSha256':pbf_hash,'crs':'EPSG:4326','license':'ODbL-1.0',
        'features':[road,area,*connections]})
    measurements={'anchorWGS84':anchor,'anchorMethod':'road endpoint midpoint, not a surveyed arch center',
        'roadWayId':28538289,'areaWayId':1466925249,'roadNodeIds':road['properties']['nodeIds'],
        'roadLengthM':length,'bearingNorthClockwise':bearings,
        'bridgeAxisRadiansEastCCW':math.atan2(dy,dx),'polygonUVMetres':uv,
        'lineAreaIdentityChecks':['same Chinese/English name','both explicitly tagged bridge',
             'identical SW source point','NE line point within about1m of area end',
             'UNESCO plan matches long narrow corridor to north-side pavilion cluster'],
        'footprintInterpretation':'OSM122.6m corridor includes sloping approaches; 8.8m reported describes the short arch body, not the entire approaches.',
        'uncertainty':'measured on source geometry, not a field survey; OSM accuracy unknown; planning±5m/±3deg; edge spread includes uncertain approach boundaries'}
    measurements_hash=write('osm-measurements.json',measurements)
    sources=[
      {'id':'osm-geofabrik','url':'https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf',
       'publisher':'OpenStreetMap contributors / Geofabrik','accessedAt':DATE,
       'sourceDate':'2026-10-11T20:21:06Z','status':'available','license':'ODbL-1.0',
       'localPath':'data/raw/hangzhou/zhejiang-261011.osm.pbf','sha256':pbf_hash},
      {'id':'unesco-nomination','url':'https://whc.unesco.org/uploads/nominations/1334.pdf',
       'publisher':'China State Party nomination / UNESCO World Heritage Centre publication',
       'accessedAt':DATE,'sourceDate':'2011 (PDF creation/modification metadata; underlying surveys undated)',
       'status':'available-read-and-rendered','sha256':'5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442',
       'bytes':79121258,'pages':1342,'license':'unknown; reference only; PDF/page images not bundled',
       'reviewedPages':[{'pdfPage':100,'printedPage':105,'use':'stone semicircular arch, asphalt slopes,8.8m length/8.6m width/6.1m clear span'},
                        {'pdfPage':107,'printedPage':112,'figure':'2a-59','use':'plan and north arrow/corridor/pavilion layout'},
                        {'pdfPage':108,'printedPage':113,'figure':'2a-61','use':'single small central arch and long gradual slopes with ruler'}]},
      {'id':'government-2018','url':'https://www.ehangzhou.gov.cn/2018-06/14/c_242889.htm',
       'publisher':'Information Office of Hangzhou Municipal People’s Government','accessedAt':DATE,
       'sourceDate':'2018-06-14','status':'available-read-and-photo-reviewed','license':'unknown; reference only; no image texture'},
      {'id':'government-rain2020','url':'https://www.ehangzhou.gov.cn/2020-06/05/c_271613_2.htm',
       'publisher':'Hangzhou government English portal / China Daily photographer Xiao Da','accessedAt':DATE,
       'sourceDate':'2020-06-05','status':'available-photo-reviewed','license':'unknown; reference only; no image texture'},
      {'id':'government-night2023','url':'https://www.ehangzhou.gov.cn/2023-08/17/c_286564.htm',
       'publisher':'Hangzhou government English portal; photo credited IC','accessedAt':DATE,
       'sourceDate':'2023-08-17','status':'available-photo-reviewed','license':'unknown; reference only; no image texture'}]
    estimates={
      'archPosition':{'value':.45,'unit':'fraction from source SW road endpoint','basis':'estimated',
        'sourceIds':['unesco-nomination'],'method':'visual ratio along full longitudinal elevation2a-61, registered to OSM endpoint corridor; no georeferenced arch survey',
        'uncertainty':'±.05 of corridor (about±6.1m); old drawing/current placement tie-in pending'},
      'archSpringRelativeM':{'value':-1.5,'unit':'m relative to bridge road endpoint height','basis':'estimated',
        'sourceIds':['unesco-nomination','government-2018','government-rain2020'],
        'method':'semicircular clear span fixes radius3.05m; low arch spring and shallow slopes inferred from elevation and side photographs; neutral endpoint datum',
        'uncertainty':'±.7m; real lake water/abutment datum unknown'},
      'archRingThicknessM':{'value':.60,'unit':'m','basis':'estimated','sourceIds':['unesco-nomination'],
        'method':'coarse ring-to-clear-span proportion in figure2a-61; not a measured structural section',
        'uncertainty':'±.25m; 1921 historical secondary report not used as field measurement'},
      'pavementThicknessM':{'value':.20,'unit':'m','basis':'estimated','sourceIds':['unesco-nomination'],
        'method':'thin asphalt deck above arch ring, for candidate geometry; material is reported, thickness is not',
        'uncertainty':'±.15m'},
      'railHeightM':{'value':1.0,'unit':'m','basis':'estimated','sourceIds':['unesco-nomination','government-night2023'],
        'method':'elevation rail-to-span and adult-height contextual proportion in street photograph; not calibrated imagery',
        'uncertainty':'±.25m'},
      'railPostPitchM':{'value':2.7,'unit':'m','basis':'estimated','sourceIds':['unesco-nomination','government-2018'],
        'method':'coarse repeated railing interval in full elevation; candidate repetition, actual post count unknown',
        'uncertainty':'±.7m; precise ornamental sections pending'},
      'railPostWidthM':{'value':.22,'unit':'m','basis':'estimated','sourceIds':['unesco-nomination'],
        'method':'coarse line-weight/rail-width proportion; representative low-poly stone post',
        'uncertainty':'±.10m'},
      'slopeProfile':{'value':'smooth sine approaches to one crest over the arch','basis':'estimated',
        'sourceIds':['unesco-nomination','government-2018'],'method':'preserves gradual asphalt slopes and exact endpoint heights; not a surveyed vertical alignment',
        'uncertainty':'crest about2.35±.9m over neutral endpoints; road/collision height and current water datum pending'}}
    pending=['current surveyed arch position/ground/water elevations','runtime deck-height/collision and connected walking verification',
             'precise railing/post ornamental survey','pavilion/stele/waterside structures and landscaping',
             'lamps and day/night material integration','current in-game top/street/distant views','performance and whole-city acceptance']
    spec={'schemaVersion':1,'id':'broken-bridge','cityId':'hangzhou',
        'scope':'Source-bound single-arch stone body with continuous sloping asphalt approaches and railings; lake water and pavilion groups excluded.',
        'anchor':{'lon':anchor[0],'lat':anchor[1],'basis':'measured-on-OSM','method':'source road endpoint midpoint'},
        'sourceSnapshotSha256':pbf_hash,'sourceFeatureIds':['way/28538289','way/1466925249'],
        'baseBuildingIdsToExclude':[],'baseRoadIdsToSuppressVisual':[28538289],
        'keepNavigationWayIds':[28538289,28538286,28538290],
        'sourceRoadNodeIds':road['properties']['nodeIds'],'endpointsWGS84':[a,b],
        'bridgeLengthM':length,'bridgeWidthM':8.6,'widthBasis':'reported','coreArchBodyLengthM':8.8,
        'clearArchSpanM':6.1,'archCount':1,'spanBasis':'reported','axisRadiansEastCCW':math.atan2(dy,dx),
        'polygonWGS84':ring,'polygonUVMetres':uv,'estimates':estimates,'pendingSubscopes':pending,
        'coordinatePolicy':{'dimensions':'unscaled real metres','lmAnchor':'existing game-unit x/z/y; y is shared endpoint height','scaleOnce':geo['scale'],'blenderAxes':['east','north','up']},
        'waterPolicy':{'createWaterMeshes':False,'datum':'unknown; underlying main water pipeline owns the lake',
                       'note':'arch opening and lower abutments are geometry only, no candidate water patch or flat park slab'},
        'integrationContract':{'visualRoadExclusion':'Suppress the flat road strip for this bridge if duplicate; retain its topology.',
          'walking':'Bind runtime height to returned real-metre deck profile and ensure both source endpoints meet connected paths.',
          'candidateFootArrival':{'sourceNode':'13454786643','wgs84':b,'basis':'measured-on-OSM north endpoint; arrival/collision not verified'},
          'motorVehicleRouting':'OSM prohibits motor vehicles/cars on this pedestrian bridge; vehicle arrivals require a nearby permitted road and walking transfer.',
          'widthConflict':'OSM corridor edges range~7.7–11.4m;8.6m core width is reported, not surveyed approach width. Candidate keeps8.6m travel strip; broad edge uncertainty pending.'},
        'budget':{'maxTriangles':12000,'maxMaterials':4,'lights':0}}
    spec_hash=write('spec.json',spec)
    claims_hash=write('source-claims.json',{'scope':spec['scope'],'sources':sources,
        'reported':{'stoneArch':'one semicircular arch built with rectangular stone blocks',
                    'pavement':'asphalt with gradual slopes','coreBodyLengthM':8.8,'widthM':8.6,'clearSpanM':6.1},
        'sourceDifferences':['122.6m OSM line/area is the bridge-and-approach corridor;8.8m arch body does not describe its full length.',
            'Wikimedia/English Wikipedia three-span claim is not adopted; original UNESCO elevation and actual side photo show one central opening.',
            '2011 nomination geometry is not a current2026 field survey; current vertical datum and exact ornament pending.']})
    evidence={'schemaVersion':1,'placeId':'broken-bridge','scope':spec['scope'],
        'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','unesco-nomination','government-2018']},
        'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['osm-geofabrik']},
        'sources':sources,'observations':[
            {'kind':'footprint','value':{'lineWay':28538289,'areaWay':1466925249,'corridorLengthM':length},'unit':'EPSG:4326/metres',
             'basis':'measured','sourceIds':['osm-geofabrik','unesco-nomination'],
             'uncertainty':'OSM geometry measured, not field measured; unknown source accuracy, planning±5m; area includes approaches.'},
            {'kind':'height','value':{'clearSpanM':6.1,'semicircleRadiusM':3.05},'unit':'m','basis':'reported',
             'sourceIds':['unesco-nomination'],'uncertainty':'reported span; radius follows reported semicircle, not measured arch rise/current water clearance.'},
            {'kind':'height','value':{'candidateCrestAboveEndpointsM':2.35,'railHeightM':1.0},'unit':'m','basis':'estimated',
             'sourceIds':['unesco-nomination','government-2018','government-night2023'],
             'uncertainty':'crest±.9m/rail±.25m; endpoint ground and lake elevations pending; isolated shared endpoint datum only.'},
            {'kind':'orientation','value':bearings,'unit':'degrees north clockwise','basis':'measured',
             'sourceIds':['osm-geofabrik','unesco-nomination'],'uncertainty':'source endpoints and plan north arrow checked; planning±3deg, not survey confidence interval.'},
            {'kind':'silhouette','value':'one small semicircular stone arch amid long continuous shallow asphalt slopes, narrow stone rails; bridge is intact',
             'unit':None,'basis':'reported','sourceIds':['unesco-nomination','government-2018','government-rain2020'],
             'uncertainty':'Old plan/elevation and actual2018/2020/2023 photo views; precise current height/post ornament and full abutments pending.'}],
        'blockers':[],'pendingSubscopes':pending,'sourceSnapshots':{
            PREFIX+'/geofabrik-bridge-features.geojson':features_hash,PREFIX+'/osm-measurements.json':measurements_hash,
            PREFIX+'/source-claims.json':claims_hash,PREFIX+'/spec.json':spec_hash},
        'photosBundled':False,'stageLimit':'limited exterior evidence-ready only; no GLB/visual/runtime claim'}
    write('evidence.json',evidence)
    write('task-catalog.json',{'places':[{'id':'broken-bridge','name':'断桥单拱与引道候选','kind':'bridge',
        'location':{'center':anchor},'sources':sources,'scope':spec['scope'],'modeling':{'blockers':[]}}]})
    print(json.dumps({'anchor':anchor,'corridorLengthM':length,'reportedClearSpanM':6.1,'archCount':1,
                      'specSha256':spec_hash},ensure_ascii=False))


if __name__=='__main__':main()
