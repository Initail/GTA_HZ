"""Freeze independently owned ICC shell evidence; no bpy or scene initialization."""
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
DATE='2026-10-14'
IDS=[626826759,626826760,626826766,626826767,626826768,626826769,626826770,
  626826771,626826772,626826773,626826774,626826775,626826776,626826777,626826778,
  626826779,626838539,626838541,626838542,626838543,626838544,626838545,626838546,
  626838547,626838548,626838549,626838551,626838553,626838555,626838557,626838559,626838560]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,d):
    p=OUT/name;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');return digest(p)


def moments(ring,e,n):
    origin=ring[0];q=[((p[0]-origin[0])*e,(p[1]-origin[1])*n) for p in ring]
    a=x=y=xx=yy=xy=0
    for (u,v),(s,t) in zip(q,q[1:]):
        c=u*t-s*v;a+=c;x+=(u+s)*c;y+=(v+t)*c
        xx+=(u*u+u*s+s*s)*c;yy+=(v*v+v*t+t*t)*c;xy+=(2*u*v+u*t+s*v+2*s*t)*c
    a/=2;cx=x/(6*a);cy=y/(6*a)
    vx=xx/(12*a)-cx*cx;vy=yy/(12*a)-cy*cy;vxy=xy/(24*a)-cx*cy
    axis=.5*math.atan2(2*vxy,vx-vy)
    if math.sin(axis)<0:axis+=math.pi
    pts=[((u-cx)*math.cos(axis)+(v-cy)*math.sin(axis),-(u-cx)*math.sin(axis)+(v-cy)*math.cos(axis)) for u,v in q]
    return {'areaM2':abs(a),'centroidWGS84':[origin[0]+cx/e,origin[1]+cy/n],
      'axisRadiansEastCCW':axis,'axisDegreesEastCCW':math.degrees(axis),
      'boundsMajorMinorM':[max(p[i] for p in pts)-min(p[i] for p in pts) for i in [0,1]],
      'method':'polygon area centroid/second moments using fixed WGS84 local coefficients; not uneven-vertex average'}


def main():
    geo=load_city('hangzhou')['geography'];e,n=geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    source=ROOT/'data/processed/hangzhou/buildings.geojson'
    f=json.loads(source.read_text())['features'];byid={x['id']:x for x in f}
    main=byid['way/626838544'];ball=byid['way/626838542'];front=byid['way/626838543'];back=byid['way/626838541']
    assert main['properties']['name']=='杭州市国际会议中心'
    assert ball['properties']['tags']['building:part']=='金球'
    rings={k:x['geometry']['coordinates'][0][0] for k,x in [('main',main),('sphereBase',ball),('front',front),('back',back)]}
    measured={k:moments(r,e,n) for k,r in rings.items()}
    anchor=measured['sphereBase']['centroidWGS84'];axis=measured['main']['axisRadiansEastCCW'];ca,sa=math.cos(axis),math.sin(axis)
    def uv(ring):
        return [[(lon-anchor[0])*e*ca+(lat-anchor[1])*n*sa,
                 -(lon-anchor[0])*e*sa+(lat-anchor[1])*n*ca] for lon,lat in ring[:-1]]
    sources_features=[byid['way/'+str(i)] for i in IDS]
    for feature in sources_features:
        assert feature['properties']['tags'].get('colour')=='#ffdb7a'
        c=moments(feature['geometry']['coordinates'][0][0],e,n)['centroidWGS84']
        assert abs(c[0]-anchor[0])<.001 and abs(c[1]-anchor[1])<.001
    theatre=byid['way/626838819'];tc=moments(theatre['geometry']['coordinates'][0][0],e,n)['centroidWGS84']
    theatre_bearing=math.atan2((tc[1]-anchor[1])*n,(tc[0]-anchor[0])*e)
    ph=digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf')
    assert ph=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    snap_hash=write('geofabrik-icc-features.geojson',{'type':'FeatureCollection','crs':'EPSG:4326',
      'license':'ODbL-1.0','sourceSnapshotSha256':ph,'features':sources_features,
      'orientationContextOnlyFeature':theatre})
    qualified=[{'id':feature['id'],'role':'mainPodium' if feature['id']=='way/626838544' else
      'sphereBase' if feature['id']=='way/626838542' else 'frontGlazedCorridor' if feature['id']=='way/626838543' else
      'rearEntrance' if feature['id']=='way/626838541' else 'mappedSphereLevel',
      'tags':feature['properties']['tags'],'centroidWGS84':moments(feature['geometry']['coordinates'][0][0],e,n)['centroidWGS84'],
      'featureSha256':hashlib.sha256(json.dumps(feature,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
      'interpretation':'named body/podium or identical-colour same-centre nested building part; height tags not automatically measured'} for feature in sources_features]
    measure_hash=write('osm-measurements.json',{'anchorWGS84':anchor,'sourceFeatures':qualified,
      'mainAndComponents':measured,'orientationAxisRadiansEastCCW':axis,
      'frontRelativeRadians':-math.pi/2,'frontWorldDegreesEastCCW':math.degrees(axis-math.pi/2),
      'theatreReference':{'sourceFeatureId':'way/626838819','centroidWGS84':tc,
        'bearingFromICCdegreesEastCCW':math.degrees(theatre_bearing),'use':'orientation/context only; no exclusion'},
      'sourceDifferences':{'mainHeightTag':20,'sphereTopTag':88,'maxMappedSphereBoundsM':moments(byid['way/626826776']['geometry']['coordinates'][0][0],e,n)['boundsMajorMinorM'],
        'reportedDiameterM':85,'heightUse':'all tags unverified; main/podium20 vs reported13, sphere top88 vs reported85, mapped108m ring vs reported85 remain conflicts'},
      'orientationBasis':'main source footprint area-moment axis; theatre-facing side is the perpendicular NE side, consistent with actual source front-glass corridor and official photo',
      'uncertainty':'OSM/source map precision unknown. Planning ±5m placement/podium, front phase ±5deg. Nested height/diameter tags do not establish actual steel sphere dimensions.'})
    sources=[
      {'id':'osm-geofabrik','url':'https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf','publisher':'OpenStreetMap contributors / Geofabrik',
       'accessedAt':DATE,'sourceDate':'2026-10-11T20:21:06Z','license':'ODbL-1.0','localPath':'data/raw/hangzhou/zhejiang-261011.osm.pbf','sha256':ph},
      {'id':'petroff','url':'https://www.petroff.com/projects/hangzhou','publisher':'PETROFF Partnership Architects, project architect/prime consultant',
       'accessedAt':DATE,'sourceDate':'page month/day Nov12, year not explicit; states project completion2010',
       'status':'actual text and four reference images reviewed','sha256':digest(Path('<TEMP>/hz-icc-petroff.html')),
       'license':'unknown; reference-only; no photograph bundled or used as texture'},
      {'id':'chinaasc','url':'https://www.chinaasc.org.cn/news/117011.html','publisher':'Architectural Society of China; structural engineer 葛家琪 first-person report',
       'accessedAt':DATE,'sourceDate':'2017-09-16','status':'actual report text read','sha256':digest(Path('<TEMP>/hz-icc-chinaasc.html')),
       'license':'unknown; reference-only','use':'Carlos Ott/CUC architecture,85m diameter, outer mesh-shell/inner steel frame, doubleC functional arrangement'},
      {'id':'hunter','url':'https://ap.hunterdouglas.asia/project/hangzhou-international-conference-center','publisher':'Hunter Douglas facade product supplier',
       'accessedAt':DATE,'sourceDate':None,'status':'actual text and five actual exterior photo views reviewed',
       'sha256':digest(Path('<TEMP>/hz-icc-hunter.html')),'license':'unknown; reference-only; no photographs/atlas bundled',
       'use':'85m height/diameter,13m oval annex, golden glass and gold honeycomb panels; architect field conflict retained'},
      {'id':'ihg','url':'https://www.ihg.com/intercontinental/hotels/cn/zh/hangzhou/hghha/hoteldetail','publisher':'InterContinental / IHG hotel operator',
       'accessedAt':DATE,'sourceDate':None,'status':'actual current page read and two actual exterior photos reviewed',
       'license':'unknown; reference-only; no photograph texture','use':'ICC identity/address, golden globe with opposite theatre, current facade/glazed wedge and podium arrangement'},
      {'id':'zjol2017','url':'https://town.zjol.com.cn/czjsb/201712/t20171214_6044540.shtml','publisher':'浙江在线 / 浙江日报集团，记者刘健、通讯员李云雁',
       'accessedAt':DATE,'sourceDate':'2017-12-14','status':'actual engineering interview and aerial context photo reviewed',
       'sha256':digest(Path('<TEMP>/hz-icc-zjol.html')),'license':'unknown; reference-only',
       'use':'13m annex/85m sphere,18floor label,1/3 honeycomb and2/3glass per level, concealed lighting interview; not a2026 structural survey'},
      {'id':'tsinghua-lighting','url':'https://www.tsinghua.edu.cn/info/2066/68498.htm','publisher':'Tsinghua University; affiliated lighting project account',
       'accessedAt':DATE,'sourceDate':'2016-09-08 16:53:38',
       'status':'actual page read; numerical fixture placement/current control still pending','license':'unknown; reference-only',
       'use':'warm layer-by-layer LED lighting and shielding; do not infer real fixture count or current show timing'},
      {'id':'government-cuc','url':'https://hzbjzx.gov.cn/data/2021/07/t20251225201139817.htm','publisher':'杭州市滨江区政协',
       'accessedAt':DATE,'sourceDate':'2021-07-05 (page indexed publication; URL contains a2025 token)',
       'status':'search-index excerpt read; direct web page cache miss, only CUC project association corroborated',
       'license':'unknown; reference-only','use':'government identity context only, not height/section evidence'}]
    est={
      'sphereSection':{'basis':'estimated','value':{'centerHeightM':46,'lowerCutM':20,'goldSkinTopM':81.5,
        'skyRoofTopM':85,'skylightBaseM':81.5},'sourceIds':['hunter','ihg','chinaasc'],
        'method':'85m diameter/overall height constraints plus actual side/aerial proportions; sphere centre and lower/top cuts chosen to reproduce truncated body with shallow glass roof, not a complete85m ball stacked atop13m annex',
        'uncertainty':'centre±5m, lower cut±4m, gold top/skylight base±3m; neutral base not surveyed; OSM max ring108m conflicting and not scaled to force fit'},
      'floorBands':{'basis':'estimated','value':{'bands':15,'glassFraction':2/3,'recessM':.8},
        'sourceIds':['chinaasc','zjol2017','hunter','ihg'],
        'method':'representative15 sphere-floor bands from engineering scope, terrace/gold-glass alternation observed; label18 press and19 historical whole-building counts not asserted as the same quantity',
        'uncertainty':'actual current bands/floor datum and terrace depths unknown; recess±.6m, glass ratio reported but actual segment inventory unmeasured'},
      'glazedFace':{'basis':'estimated','value':{'halfAngleRadians':.39,'recessM':1.8},
        'sourceIds':['ihg','chinaasc','osm-geofabrik'],
        'method':'theatre-facing glazed wedge visible in official operator view; axis follows source corridor toward theatre, width by approximate frontal proportion',
        'uncertainty':'angular width±.12rad, depth±1.5m; precise curved glass mounting/buttress layout pending'},
      'podium':{'basis':'estimated','value':{'innerRoofRadiusM':31,'outerRoofBaseM':3.5,'roofMaximumM':13,
        'frontGapHalfRadians':.25,'rearGapHalfRadians':.18,'roofRadialStations':[[0,5],[.18,9],[.5,13],[.82,10],[1,3.5]]},
        'sourceIds':['hunter','ihg','osm-geofabrik'],
        'method':'rounded gold oval wings divided by source front/rear glazed corridors; curved section fitted to actual supplier close view and operator aerial, outer plan follows source ring',
        'uncertainty':'section/radius±4m, gap phase±5deg;13m overall annex is reported, individual roof intersections are estimated; source podium tag20 rejected'},
      'entryGlazing':{'basis':'estimated','value':{'frontInnerRoofM':20,'frontOuterRoofM':5.5,
        'rearInnerRoofM':16,'rearOuterRoofM':7.5,'canopyProjectionM':7,'doorHeightM':3.2,
        'rearConnectorWidthM':22,'frontConnectorMouthWidthM':16},
        'sourceIds':['hunter','ihg','osm-geofabrik'],'method':'source front/rear corridor polygons with sloping glazed roof and a shallow steel/glass projecting canopy seen in real entry photograph',
        'uncertainty':'heights±4m, canopy projection±3m, door placement±4m; connector widths±5m fill the partial-source gap to the observed central lobby, not surveyed whole-entry geometry; current signed entry accessibility/collision unknown'},
      'panelRhythm':{'basis':'estimated','value':{'sphereAngularPanels':96,'podiumAngularPanels':96,'seamWidthM':.07},
        'sourceIds':['hunter','ihg'],'method':'coarse curved vertical and floor seam grid from actual photographs; not all>10000 reported unique facade panels reproduced',
        'uncertainty':'panel count/pitch±35%; seam width±.05m; actual each different panel shape unknown'}}
    pending=['surveyed ground/base elevation, podium levels, true entrance route and collision',
      '85m reported diameter/height versus108m/88m OSM layer conflict and full surveyed section',
      'precise sphere centre/cuts, terraces, glass wedge shape, skylight section and full panel inventory',
      '15sphere/18label/19historical total floor scope reconciliation',
      'architect roles conflict in supplier GS/Xia field; PETROFF/CarlosOtt/CUC primary attribution preferred with remaining role detail pending',
      'hotel/conference interiors, basements, pool, sculptures and fountains',
      'gold tinted glass and honeycomb final material, sign/logos and all-side current geometry',
      'warm lighting fixture positions/current control, real day/night top/street/distant views and performance']
    spec={'schemaVersion':1,'id':'international-conference-center','cityId':'hangzhou',
      'scope':'Limited ICC exterior candidate: truncated golden sphere with terraced floor/window rhythm, theatre-facing glazed wedge and glass skylight; source-bound rounded podium wings/front/rear glazed entries. Hotel interiors/site levels/fountains excluded.',
      'anchor':{'lon':anchor[0],'lat':anchor[1],'basis':'measured-on-OSM','method':'polygon area centroid of labelled lower sphere part way626838542'},
      'sourceSnapshotSha256':ph,'sourceFeatureIds':['way/'+str(i) for i in IDS],
      'baseBuildingIdsToExclude':IDS,'orientationContextOnlyIds':['way/626838819'],
      'outerPodiumWGS84':rings['main'][:-1],'outerPodiumUVMetres':uv(rings['main']),
      'sphereBaseWGS84':rings['sphereBase'][:-1],'sphereBaseUVMetres':uv(rings['sphereBase']),
      'frontEntryWGS84':rings['front'][:-1],'frontEntryUVMetres':uv(rings['front']),
      'rearEntryWGS84':rings['back'][:-1],'rearEntryUVMetres':uv(rings['back']),
      'axisRadiansEastCCW':axis,'glazedFaceRelativeRadians':-math.pi/2,
      'diameterM':85,'heightM':85,'annexHeightM':13,'dimensionBasis':'reported; not a ground-survey datum',
      'estimates':est,'pendingSubscopes':pending,
      'coordinatePolicy':{'dimensions':'unscaled real metres','lmAnchor':'already game-unit x/z/y, neutral isolated base',
        'scaleOnce':geo['scale'],'blenderAxes':['east','north','up']},
      'budget':{'maxTriangles':26000,'maxMaterials':7,'maxBytes':8388608,'lights':0},
      'integrationContract':{'sourceExclusions':'Only these32 main/part IDs from the same ICC object, in base and facades. Do not exclude theatre way626838819 or transport N2way1023947435.',
        'arrival':'Sphere/podium anchor is not an entry. Bind current connected entry outside the source glass corridors after terrain/collision verification.',
        'materials':'Existing gold/darkglass/landmarkglass aliases are provisional; tint golden glass and test reflections through the main material process.',
        'night':'Source confirms warm LED/hidden grooves, but module emits zero lights until main fixture/control integration and visual performance review.',
        'water':'No candidate water, fountain, park slab or claimed interior gameplay.'}}
    spec_hash=write('spec.json',spec)
    claims_hash=write('source-claims.json',{'sources':sources,'reported':{'diameterM':85,'totalHeightM':85,'ovalAnnexM':13,
      'primaryArchitectRoles':'PETROFF project architect / Carlos Ott associate schematic architect / China United local architecture; society first-person report corroboratesCarlosOtt/CUC',
      'sphereFloorScope':15,'pressFloorLabel':18,'shellMaterials':'golden glass + gold honeycomb cladding'},
      'sourceConflicts':['Supplier English Architect/Specifier field namesGS/XiaBangjie, whereas project architect official and engineer account supportCarlosOtt/PETROFF/CUC. Retained, not silently discarded.',
        'Mapped floor rings extend108m and tag top88; primary engineering diameter85m/total height85m chosen, exact section remains pending.',
        'OSM main/podium20m, supplier reported13m, secondary12m not silently unified.',
        'Engineer15 floor sphere scope, press18label, historic19total count may cover different levels; no exact floor mapping asserted.',
        'Supplier gold honeycomb product is supported; claims of solid gold or plain titanium sphere are not used.',
        'Hotel/current384 rooms vs designer379/historical393 are operation-period differences, not geometric parameters.',
        'The International Expo Center on the south bank is a different site/object.']})
    evidence={'schemaVersion':1,'placeId':spec['id'],'scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','petroff','chinaasc','ihg']},
      'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['osm-geofabrik']},
      'sources':sources,'observations':[
        {'kind':'footprint','value':{'mainWay':626838544,'mainBoundsM':measured['main']['boundsMajorMinorM'],
          'sphereLowerPartWay':626838542,'reportedSphereDiameterM':85},'unit':'metres/EPSG:4326','basis':'measured',
          'sourceIds':['osm-geofabrik','hunter','chinaasc'],'uncertainty':'OSM footprint measured with canonical local coefficients, source accuracy unknown, planning±5m; sphere85 is separately reported and not a mapped108m ring measurement.'},
        {'kind':'height','value':{'overallM':85,'annexM':13,'sphereDiameterM':85},'unit':'m','basis':'reported',
          'sourceIds':['hunter','chinaasc'],'uncertainty':'Supplier overall/annex height and first-person engineer diameter; true neutral ground/centre/cuts not surveyed. Not85m complete sphere stacked on13m annex.'},
        {'kind':'orientation','value':{'podiumMajorDegreesEastCCW':math.degrees(axis),
          'theatreFacingGlazedSideDegreesEastCCW':math.degrees(axis-math.pi/2)},'unit':'degrees','basis':'measured',
          'sourceIds':['osm-geofabrik','ihg'],'uncertainty':'Source area moments and actual NE corridor/theatre context; curve and true façade seam phase estimated±5deg.'},
        {'kind':'silhouette','value':'truncated golden globe with terraced gold/window bands, theatre-facing tall glazed wedge, shallow round glass skylight, two rounded oval podium wings and recessed glazed entry roof/canopy',
          'unit':None,'basis':'reported','sourceIds':['hunter','ihg','petroff','chinaasc'],
          'uncertainty':'Multiple actual exterior directions/aerial/interior skylight reviewed; detailed curve/section and all current side elevations remain reference-informed estimates.'}],
      'blockers':[],'pendingSubscopes':pending,'sourceSnapshots':{PREFIX+'/geofabrik-icc-features.geojson':snap_hash,
        PREFIX+'/osm-measurements.json':measure_hash,PREFIX+'/source-claims.json':claims_hash,PREFIX+'/spec.json':spec_hash},
      'photosBundled':False,'stageLimit':'limited exterior evidence-ready only; no full-site/current visual/export/runtime claim'}
    write('evidence.json',evidence)
    write('task-catalog.json',{'places':[{'id':spec['id'],'name':'杭州国际会议中心金球与裙楼候选',
      'kind':'building','location':{'center':anchor},'sources':sources,'scope':spec['scope'],'modeling':{'blockers':[]}}]})
    print(json.dumps({'anchor':anchor,'sourceExclusions':len(IDS),'podiumBoundsM':measured['main']['boundsMajorMinorM'],
      'sphereDiameterReportedM':85,'specSha256':spec_hash},ensure_ascii=False))


if __name__=='__main__':main()
