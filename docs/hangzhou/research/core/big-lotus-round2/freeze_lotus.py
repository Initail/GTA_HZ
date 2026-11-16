"""Freeze a limited Big Lotus shell scope against fixed Geofabrik geometry.

No Blender import and no downloaded photographs are distributed by this script.
"""
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
PART_IDS=[626826698,626826700,626826703,626826704,626826708,626826715,626826717,
  626826718,626826727,626826729,626826730,626826734,626826736,626826739,626832622,
  626832624,626832626,626832627,626832631,626832632,626832634,626832640,626832644,
  626832648,626832651,626832656,626832661,626832664,626832665,626832666,626832667,
  626832669,626832671,626832674,626832675,626832677,626832679,626832680,626832682]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,d):
    p=OUT/name;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');return digest(p)


def moments(ring,origin,e,n):
    q=[((p[0]-origin[0])*e,(p[1]-origin[1])*n) for p in ring]
    a=x=y=xx=yy=xy=0
    for (u,v),(s,t) in zip(q,q[1:]):
        cr=u*t-s*v;a+=cr;x+=(u+s)*cr;y+=(v+t)*cr
        xx+=(u*u+u*s+s*s)*cr;yy+=(v*v+v*t+t*t)*cr
        xy+=(2*u*v+u*t+s*v+2*s*t)*cr
    a/=2;cx=x/(6*a);cy=y/(6*a)
    vx=xx/(12*a)-cx*cx;vy=yy/(12*a)-cy*cy;vxy=xy/(24*a)-cx*cy
    angle=.5*math.atan2(2*vxy,vx-vy)
    if math.sin(angle)<0:angle+=math.pi
    pts=[((u-cx)*math.cos(angle)+(v-cy)*math.sin(angle),
          -(u-cx)*math.sin(angle)+(v-cy)*math.cos(angle)) for u,v in q]
    return {'areaM2':abs(a),'centroidWGS84':[origin[0]+cx/e,origin[1]+cy/n],
      'axisRadiansEastCCW':angle,'axisDegreesEastCCW':math.degrees(angle),
      'majorMinorBoundsM':[max(p[i] for p in pts)-min(p[i] for p in pts) for i in [0,1]],
      'method':'uniform polygon area centroid and second moments, not uneven-vertex PCA'}


def inside(p,ring):
    x,y=p;ok=False
    for (a,b),(c,d) in zip(ring,ring[1:]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:ok=not ok
    return ok


def ring_edges(ring):
    return {tuple(sorted((tuple(a),tuple(b)))) for a,b in zip(ring,ring[1:])}


def main():
    geo=load_city('hangzhou')['geography'];e,n=geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    bf=ROOT/'data/processed/hangzhou/buildings.geojson'
    features=json.loads(bf.read_text())['features'];byid={f['id']:f for f in features}
    main_feature=byid['relation/8718531'];outer,inner=main_feature['geometry']['coordinates'][0]
    assert main_feature['properties']['tags']['leisure']=='stadium'
    mo=moments(outer,outer[0],e,n);mi=moments(inner,outer[0],e,n)
    anchor=mi['centroidWGS84'];axis=mi['axisRadiansEastCCW'];ca,sa=math.cos(axis),math.sin(axis)
    def uv(ring):
        return [[(p[0]-anchor[0])*e*ca+(p[1]-anchor[1])*n*sa,
                 -(p[0]-anchor[0])*e*sa+(p[1]-anchor[1])*n*ca] for p in ring[:-1]]
    parts=[];qualified=[]
    for ident in PART_IDS:
        f=byid['way/'+str(ident)];ring=f['geometry']['coordinates'][0][0]
        tags=f['properties']['tags'];q=ring[:-1]
        center=[sum(p[i] for p in q)/len(q) for i in [0,1]]
        assert tags.get('colour')=='#eaeaea' and tags.get('height')=='26' and inside(center,outer)
        parts.append(f);qualified.append({'id':f['id'],'reason':'mapped stadium petal-shaped roof component; anonymous pale shell within main outer-ring centroid area',
          'centroidWGS84':center,'verticesInsideMainOuter':sum(inside(p,outer) for p in q),
          'vertices':len(q),'heightTag':'26','heightUse':'not adopted as full roof height',
          'featureSha256':hashlib.sha256(json.dumps(f,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
    field=byid['way/626826721'];assert ring_edges(field['geometry']['coordinates'][0][0])==ring_edges(inner)
    api_path=Path('<TEMP>/hz-big-lotus-osm-full.json');api=json.loads(api_path.read_text())
    nodes={x['id']:[x['lon'],x['lat']] for x in api['elements'] if x['type']=='node'}
    for ident,ring in [(626832662,outer),(626826721,inner)]:
        w=next(x for x in api['elements'] if x['type']=='way' and x['id']==ident)
        assert ring_edges([nodes[z] for z in w['nodes']])==ring_edges(ring)
    relation=next(x for x in api['elements'] if x['type']=='relation')
    (OUT/'osm-relation-8718531-aux.json').write_bytes(api_path.read_bytes())
    pbf=ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf';ph=digest(pbf)
    assert ph=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    snap_hash=write('geofabrik-stadium-features.geojson',{'type':'FeatureCollection',
      'sourceSnapshotSha256':ph,'crs':'EPSG:4326','license':'ODbL-1.0',
      'features':[main_feature,field,*parts]})
    measurement_hash=write('osm-measurements.json',{'mainRelation':8718531,'outerMemberWay':626832662,
      'innerMemberWay':626826721,'outer':mo,'innerRoofOpening':mi,'anchorWGS84':anchor,
      'axisRadiansEastCCW':axis,'axisUse':'the inner opening area-moment major axis; the shell lobes are retained as a source radial boundary, not rotated to its different major axis',
      'outerUVMetres':uv(outer),'innerUVMetres':uv(inner),'qualifiedPetalFeatures':qualified,
      'mappedPetalCount':39,'reportedPetalCount':55,'petalCountInterpretation':'OSM mapping is incomplete;39 mapped pieces are not evidence of39 total constructed petals.',
      'mainHeightTag':'2','mainHeightUse':'rejected as full stadium roof height',
      'fieldPartHeightTags':{'height':'3','min_height':'2','use':'unverified; not used as field datum'},
      'apiRelation':{'version':relation['version'],'timestamp':relation['timestamp'],'changeset':relation['changeset'],
        'auxSnapshotSha256':digest(OUT/'osm-relation-8718531-aux.json'),'memberRingsMatchFixedSnapshot':True},
      'doNotExclude':['way/626826731','all small-lotus / tennis center sources','district-wide bounding-box contents'],
      'uncertainty':'Dimensions measured on OSM geometry with the canonical WGS84 local coefficients; not a field survey. Ground/source accuracy unknown; planning envelope ±5m, axis ±2deg. Outer and inner map axes differ by4.24deg; no claim of surveying precision.'})
    sources=[
      {'id':'osm-geofabrik','url':'https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf',
       'publisher':'OpenStreetMap contributors / Geofabrik','accessedAt':DATE,'sourceDate':'2026-10-11T20:21:06Z',
       'license':'ODbL-1.0','localPath':'data/raw/hangzhou/zhejiang-261011.osm.pbf','sha256':ph},
      {'id':'osm-aux','url':'https://api.openstreetmap.org/api/0.6/relation/8718531/full.json',
       'publisher':'OpenStreetMap contributors / OpenStreetMap API','accessedAt':DATE,
       'sourceDate':relation['timestamp'],'license':'ODbL-1.0','localPath':PREFIX+'/osm-relation-8718531-aux.json',
       'sha256':digest(OUT/'osm-relation-8718531-aux.json'),'use':'member IDs/version corroboration; fixed Geofabrik remains the city source'},
      {'id':'nbbj','url':'https://www.nbbj.cn/work/hangzhou-olympic-sports-center/',
       'publisher':'NBBJ, project architect partnered with CCDI','accessedAt':DATE,'sourceDate':None,
       'status':'actual text and multiple project photographs reviewed','sha256':digest(Path('<TEMP>/hz-big-lotus-nbbj.html')),
       'license':'unknown; references only, images not bundled or used as textures'},
      {'id':'operator','url':'https://www.bjatzxjq.com/',
       'publisher':'杭州滨江奥体博览城开发建设运营管理有限公司','accessedAt':DATE,
       'sourceDate':'page undated; copyright2025 and news2025 do not date the photograph',
       'status':'actual stadium-specific text and aerial photograph reviewed','sha256':digest(Path('<TEMP>/hz-big-lotus-operator.html')),
       'license':'unknown; references only, images not bundled or used as textures'},
      {'id':'ccdi-project','url':'https://www.archina.com/index.php?g=works&m=index&a=show&id=3484',
       'publisher':'CCDI悉地国际 project post on ARCHINA; publication credits verified, host notes third-party submissions',
       'accessedAt':DATE,'sourceDate':'2019-09-13','status':'actual HTML fetched/read; web-tool redirect error, CDN image TLS failed',
       'sha256':digest(Path('<TEMP>/hz-big-lotus-ccdi.html')),
       'license':'unknown; reference only, no images bundled; not CCD interior design company'},
      {'id':'asian-games','url':'https://www.hangzhou2022.cn/hzhyn/mlhz/202105/t20210514_26126.shtml',
       'publisher':'Hangzhou2022 official organizer portal; credits 杭州日报','accessedAt':DATE,
       'sourceDate':'URL2021-05-14; text contextual date2019 (Alibaba20th anniversary/three years until2022)',
       'license':'unknown; reference only','use':'28large/27small petals and staggered translucent shell; reprint period mismatch retained'}]
    est={
      'petalCurve':{'basis':'estimated','value':{'wallTipHeightM':2.5,'maxHeightM':59.4,'innerEdgeHeightM':46.5,
          'thicknessM':.32,'outerBaseRadiusFraction':.91,'bulgeRadiusFraction':1.0,'uAtMaximum':.73},
        'sourceIds':['nbbj','operator','ccdi-project'],'method':'piecewise radial/up profile fitted by eye to street, aerial and interior photographs, constrained by source outer/inner rings and reported overall height; no calibrated scan or structural section',
        'uncertainty':'tips ±3m, inner roof edge ±5m, bulge/roof sweep ±8m, thickness ±.25m, curve phase ±half a petal pitch;59.4m uses operator height with datum conflict pending'},
      'petalWidth':{'basis':'estimated','value':{'largeMaxHalfPitch':.49,'smallMaxHalfPitch':.18,
          'smallHeightFactor':.94,'largeHalfPitchProfile':[[0,.027],[.16,.25],[.38,.46],
              [.62,.44],[.73,.43],[.88,.44],[1,.49]]},'sourceIds':['nbbj','operator'],
        'method':'broad outer blades and narrow translucent interleaving blades visible in ground and aerial views;55 source count does not determine seam placement',
        'uncertainty':'width/small-petal height ±20%; independent27-small distribution is approximate; north entrance asymmetry pending'},
      'bowl':{'basis':'estimated','value':{'tiers':3,'tierRangesM':[[3,12],[15,25],[29,40]],
          'trackMajorMinorM':[176,92],'pitchLengthWidthM':[105,68],
          'tierCanopyRadialFractions':[[None,.13],[.17,.38],[.42,.72]]},
        'sourceIds':['nbbj','operator'],'method':'three visible seating tiers in actual NBBJ interior photo; representative football/running layout proportioned to the mapped opening, with tier heights and seat rows reduced for candidate budget',
        'uncertainty':'tier height ±4m, track axes ±10m, standard pitch dimensions are a representation choice not surveyed stadium dimensions; permanent field/current event deck pending'},
      'entranceRhythm':{'basis':'estimated','value':{'slots':28,'lowestFacadeHeightM':8,'facadeTopM':35},
        'sourceIds':['nbbj','operator'],'method':'recurring gaps/columns behind independent petal tips; a slot per large-petal cadence represents street permeability without asserting signed gate names',
        'uncertainty':'phase ±half-pitch; true gate count/labels/entry level unknown; exact large gap and current entrance use pending'},
      'roofRibs':{'basis':'estimated','value':{'ribWidthM':.18,'visibleShellPanelBands':8},
        'sourceIds':['nbbj','operator','ccdi-project'],'method':'coarse curve-following ribs and transverse seams, informed by photographed panel/louver rhythm and reported pipe trusses; representative not structural simulation',
        'uncertainty':'rib and seam dimensions ±50%; full structural bracing/connectors and panel inventory unknown'}}
    pending=['surveyed stadium base elevation, surrounding raised platform, ramps and pedestrian bridges',
      '59.4m building-height versus60.7m structural-level datum reconciliation',
      'precise asymmetric petal phase/curves, north opening and all-side geometric fit',
      'real gate labels/count, entry levels, connected safe arrival and collision',
      'photographed matte white cladding/translucent louvers, current seating pattern and field configuration',
      'basements, concourses, museum/retail interiors and auxiliary structures',
      'small lotus is a different object and not included',
      'night light fixtures/control, current in-game top/street/distant views and performance']
    ids=['relation/8718531','way/626826721',*['way/'+str(i) for i in PART_IDS]]
    spec={'schemaVersion':1,'id':'big-lotus','cityId':'hangzhou',
      'scope':'Source-bound main-stadium shell candidate:28 broad exterior petals,27 interleaved narrow petals, open roof, three seating tiers and a representative field/track. Site terraces, interiors and small lotus excluded.',
      'anchor':{'lon':anchor[0],'lat':anchor[1],'basis':'measured-on-OSM','method':'inner-ring polygon area centroid'},
      'sourceSnapshotSha256':ph,'sourceFeatureIds':ids,'baseBuildingIdsToExclude':[8718531,626826721,*PART_IDS],
      'sourceBoundaryMemberIds':['way/626832662','way/626826721'],'excludedNeighbourIds':['way/626826731'],
      'outerFootprintWGS84':outer[:-1],'innerRoofOpeningWGS84':inner[:-1],
      'outerUVMetres':uv(outer),'innerUVMetres':uv(inner),'axisRadiansEastCCW':axis,
      'outerMajorMinorM':mo['majorMinorBoundsM'],'openingMajorMinorM':mi['majorMinorBoundsM'],
      'largePetalCount':28,'smallPetalCount':27,'petalCountBasis':'reported',
      'heightM':59.4,'heightBasis':'reported','heightSourceId':'operator',
      'heightConflict':{'valueM':60.7,'sourceId':'ccdi-project','meaning':'highest roof structure level; base datum unknown'},
      'reportedLevels':{'aboveGround':6,'belowGround':2,'basis':'reported','sourceId':'operator','rendering':'not full floor interiors'},
      'reportedSeats':[{'value':80800,'sourceId':'operator'},{'value':80912,'sourceId':'ccdi-project'}],
      'estimates':est,'coordinatePolicy':{'dimensions':'unscaled real metres','lmAnchor':'already game-unit x/z/y; isolated model base only',
        'scaleOnce':geo['scale'],'blenderAxes':['east','north','up']},
      'budget':{'maxTriangles':28000,'maxMaterials':10,'maxBytes':8388608,'lights':0},
      'pendingSubscopes':pending,'integrationContract':{'excludeSources':'Only listed41 actual extracted building IDs, in both base building and facade builds. No district-wide deletion and no626826731.',
        'ground':'Isolated lm.y datum is not surveyed main concourse or field elevation. Do not mark surrounding platforms/arrival as verified.',
        'field':'OSM inner part mapped at2–3m is replaced by representative field geometry at isolated candidate base; correct full level binding pending.',
        'opening':'Roof and seating must leave the central field open; model field/track does not imply playable sports.',
        'materials':'Existing material aliases are provisional. Matte off-white cladding, louvers and red/blue seating require main visual material review.',
        'water':'No water mesh in candidate; main Qiantang/river water pipeline remains authoritative.'}}
    spec_hash=write('spec.json',spec)
    claims_hash=write('source-claims.json',{'sources':sources,'reported':{
      'architects':'NBBJ + CCDI悉地国际','largePetals':28,'smallPetals':27,'operatorHeightM':59.4,
      'designRoofStructureLevelM':60.7,'operatorLevels':[6,2],'operatorSeatCount':80800,'designerSeatCount':80912},
      'differences':['59.4m operator building height and60.7m designer structural level remain distinct, with unknown base datum.',
        'Operator216000m² and design248983m² total area refer to different reported scopes/periods; neither defines the mapped roof footprint.',
        'NBBJ37000m² scope is not explained enough to treat as stadium roof area.',
        '39 mapped partial roof features do not override officially reported28+27 petal count.',
        'OSM relation height2 and petal height26 are unverified tags and rejected as whole-stadium roof heights.',
        'Operator full aerial and banner are duplicate photographs; NBBJ05/N69 duplicate a far view.',
        'Main roof has a fixed open central void. Small-lotus rotating roof mechanism belongs to a separate object.']})
    evidence={'schemaVersion':1,'placeId':'big-lotus','scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','nbbj','operator','ccdi-project']},
      'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['osm-geofabrik','osm-aux']},
      'sources':sources,'observations':[
        {'kind':'footprint','value':{'outerRing':626832662,'innerRing':626826721,'outerBoundsM':mo['majorMinorBoundsM'],
          'openingBoundsM':mi['majorMinorBoundsM']},'unit':'metres/EPSG:4326','basis':'measured',
          'sourceIds':['osm-geofabrik','osm-aux'],'uncertainty':'Canonical coefficients and uniform polygon area-moments; OSM source accuracy unknown, planning±5m. Some roof component vertices extend beyond coarse main ring; exact final cladding envelope pending.'},
        {'kind':'height','value':{'buildingHeightM':59.4,'alternativeStructureLevelM':60.7},'unit':'m','basis':'reported',
          'sourceIds':['operator','ccdi-project'],'uncertainty':'Different terms/periods; base datum unknown. Candidate uses operator59.4m overall height at isolated neutral base; roof edge estimates not surveyed.'},
        {'kind':'orientation','value':math.degrees(axis),'unit':'degrees east counterclockwise','basis':'measured',
          'sourceIds':['osm-geofabrik','osm-aux'],'uncertainty':'Inner opening uniform polygon moments; planning±2deg, not field confidence interval; shell area-moment axis differs4.24deg and source shell boundary is independently retained.'},
        {'kind':'silhouette','value':'elliptic concrete bowl,28 broad pale curled petals plus27 narrow interleaved translucent petals, a large open central roof and visible three seating tiers',
          'unit':None,'basis':'reported','sourceIds':['nbbj','operator','ccdi-project','asian-games'],
          'uncertainty':'Official actual street/interior/aerial images checked; camera calibration and capture dates mostly unknown. Full asymmetric phase, section and all-current-side reconstruction pending.'}],
      'blockers':[],'pendingSubscopes':pending,'sourceSnapshots':{
        PREFIX+'/geofabrik-stadium-features.geojson':snap_hash,PREFIX+'/osm-measurements.json':measurement_hash,
        PREFIX+'/osm-relation-8718531-aux.json':digest(OUT/'osm-relation-8718531-aux.json'),
        PREFIX+'/source-claims.json':claims_hash,PREFIX+'/spec.json':spec_hash},
      'photosBundled':False,'stageLimit':'limited main-shell exterior evidence-ready; no exported/visual/runtime completion claim'}
    write('evidence.json',evidence)
    write('task-catalog.json',{'places':[{'id':'big-lotus','name':'大莲花主体育场开口与花瓣候选',
      'kind':'building','location':{'center':anchor},'sources':sources,'scope':spec['scope'],'modeling':{'blockers':[]}}]})
    print(json.dumps({'anchor':anchor,'outerM':mo['majorMinorBoundsM'],'openingM':mi['majorMinorBoundsM'],
      'petals':[28,27],'sourceExclusions':len(ids),'specSha256':spec_hash},ensure_ascii=False))


if __name__=='__main__':main()
