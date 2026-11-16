"""Freeze exact source chains and finite exterior parameters; no Blender."""
from pathlib import Path
import hashlib
import json
import math
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
def write(name,data):(HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    city=load_city('hangzhou');g=city['geography'];src=json.loads((HERE/'fixed-bridge-features.geojson').read_text());fs={f['id']:f for f in src['features']}
    def road(i,level,mode='road'):
        f=fs['way/'+str(i)];q=f['geometry']['coordinates'];p=[project(*a,city) for a in q]
        return {'id':f['id'],'nodeIds':f['properties']['nodeIds'],'coordinatesWGS84':q,'tags':f['properties']['tags'],
                'mode':mode,'deck':level,'sourceLengthM':sum(math.dist(a,b) for a,b in zip(p,p[1:]))/g['scale']}
    def estimate(v,error,method,sources):return {'value':v,'basis':'estimated','error':error,'method':method,'sourceIds':sources}
    bridges=[
        {'id':'qiantang-bridge','name':'钱塘江大桥','type':'double-deck-warren-truss','centerWGS84':[120.134374525,30.195734025],
         'axisSourceEndpointsWGS84':[[120.1316223,30.2011833],[120.13712675,30.19028475]],
         'roads':[road(4348186,'upper')],'railways':[road(154142001,'lower','rail')],
         'sourceAreaId':'way/826790145','reported':{'mainLengthM':1072,'trussCount':16,'pierCountInRiver':15,'pierPitchM':67,
           'calculationSpanM':65.84,'trussHeightM':10.7,'trussCenterWidthM':6.1,'roadTravelWidthM':6.1,'sidewalkEachM':1.52,
           'northHistoricApproachM':288,'southHistoricApproachM':93,'railGaugeM':1.435},
         'widthM':9.14,'profile':{'upperWaterRelativeM':19,'lowerWaterRelativeM':8.3,'upperThicknessM':.65,'lowerThicknessM':.7,
           'mainIntervalM':[-536,536],'transitionM':240,'absoluteDatum':'unknown','waterDatum':'caller supplied game y; lm.y in build',
           'previewPolicy':'flat main + optional caller source-endpoint interpolation; no default layer multiplier','maxReportedGradient':None},
         'estimates':{'deckWaterRelativeM':estimate({'upper':19,'lower':8.3},'±5m; water/tide epoch unknown','2024 side photo lower chord-to-water pixel ratio≈0.7–0.9 of reported10.7m truss; upper=lower+10.7, envelope rounding',['qiantang-school','q2024']),
          'mainPosition':estimate('1072m main centered on mapped bridge area long axis','±45m longitudinal; ±5m plan','source area centroid/axis + reported16×67; north/ south spans visually checked; no mapped pier survey',['osm-geofabrik','qside','qair']),
          'members':estimate({'diagonalRadiusM':.15,'chordRadiusM':.24,'verticalRadiusM':.14,'railHeightM':1.1,'pierRadiusM':2.7},'members±35%; piers±1m','original low-poly interpretation from truss and river-pier photos; not structural design',['q2024','qside'])},
         'pending':['current exact deck/water/ground datum and both road approach grades','three north/one south historic approach arches and Y-shaped north junction not modeled','rail profile/actor modes and catenary','current close deck railings/material weathering and night lighting']},
        {'id':'fuxing-bridge','name':'复兴大桥','type':'double-deck-multi-arch','centerWGS84':[120.17483865006083,30.209770029145536],
         'axisSourceEndpointsWGS84':[[120.17201374335801,30.214159629462202],[120.17766355676366,30.205380428828867]],
         'roads':[road(i,'upper') for i in [29169666,154135283,29170042,154135290]]+[road(i,'lower') for i in [336983476,340648409,589429905]],'railways':[],
         'reported':{'mainLengthM':1376,'archSequenceCalculationM':[85,85,190,85,85,85,85,85,190,85,85],
          'largeArches':2,'smallArches':9,'smallDeckWidthM':26.4,'largeDeckWidthM':32,'upperMotorLanes':6,
          'lowerCurrentUse':'public transport + nonmotor + walking (2026 official); 2008 central metro reservation is historical, no track drawn'},
         'widthM':26.4,'profile':{'upperWaterRelativeM':22,'lowerWaterRelativeM':12,'upperThicknessM':1.25,'lowerThicknessM':1.15,
          'mainIntervalM':[-688,688],'transitionM':380,'absoluteDatum':'unknown','waterDatum':'caller supplied game y; lm.y in build','maxReportedGradient':None},
         'estimates':{'deckWaterRelativeM':estimate({'upper':22,'lower':12},'upper±6m, lower±4m, separation±2m','figure8 and side photo show lower deck near arch springs and upper ≈10m above; pier-to-water ratio estimated, tide unknown',['fuxing-paper','f1','fgovphoto']),
          'archRiseM':estimate({'large':47.5,'small':12.15},'large±4m, small±2m','figure8 pixel rise/span proportions≈1/4 and1/7; author figure + side photo, values not source text measurements',['fuxing-paper','f1']),
          'archStations':estimate({'endApproachEachM':91.5,'gapBetweenCalculationSpansM':4.8},'station±35m, gap±3m','figure8 91.5m unarched end + 11 calculation spans1145m; distribute remaining48m over ten hinge gaps to close1376m; NOT as-built pier chain',['fuxing-paper','osm-geofabrik','fgovphoto']),
          'members':estimate({'largeRibCentersM':29.4,'smallRibCentersM':10.4,'largeRibSectionM':[2.6,4.5],'smallTubeDiameterM':1.7,'hangerRadiusM':.07,'railHeightM':1.15},'rib dimensions±20%, hanger radius±40%','bounded original lattice from fig8 + two real directions; construction specification not obtained',['fuxing-paper','f1','fgovphoto'])},
         'pending':['surveyed lower/top/river absolute heights; exact double-level approach/branch ramps and source actor permissions','current riverbank elevators, eight viewing platforms and stair/elevator access','hinge station chain/structural joint dimensions and close railings','source lower OSM primary tags do not establish general-car permission']},
        {'id':'zhijiang-bridge','name':'之江大桥','type':'twin-arch-pylon-cable-stayed','centerWGS84':[120.120353875,30.160933725],
         'axisSourceEndpointsWGS84':[[120.11809645,30.16000225],[120.1226113,30.1618637]],
         'roads':[road(i,'single') for i in [306360721,589558021,306360739]],'railways':[],
         'outsideOldBoundsContinuations':[road(i,'single') for i in [306360714,306360716,306360719,589558020]],
         'reported':{'mainSpanSequenceM':[116,246,116],'steelPylonHeightM':90.5,'ellipseMajorSemiAxisM':73.95,'ellipseMinorSemiAxisM':22.2,
          'steelBoxHeightM':3.5,'steelBoxTotalWidthIncludingNoseM':41.36,'roadMainWidthM':40.5,
          'pylonTransverseSectionM':3.6,'pylonLongitudinalSectionTopM':4,'pylonLongitudinalSectionBottomM':6,
          'maxLongitudinalGradient':.0298,'minimumGradeLengthM':350,'sidewalkBarrierHeightM':[1.1,1.2],
          'roadNetworkLengthWithConnectionsM':4700,'bridgeWithApproachAndViaductActualM':3760},
         'widthM':40.5,'profile':{'singleWaterRelativeM':18,'singleThicknessM':3.5,'mainIntervalM':[-239,239],'transitionM':650,
          'absoluteDatum':'unknown','waterDatum':'caller supplied game y; lm.y in build','maxReportedGradient':.0298},
         'estimates':{'deckWaterRelativeM':estimate(18,'±5m, tide/datum unknown','airphoto tower base/deck/water relationship + figure1; 73.95m curved tower portion above deck gives steel base≈deck-16.55; datum not surveyed',['zhijiang-paper','zair']),
          'mainPosition':estimate('main center from midpoints of opposite-road source points3112466945/3112466938 and3112466946/3112466939','±70m longitudinal, ±5m transverse','fixed shape-break interval≈480m near reported478m + photo western-position constraint; those nodes NOT measured pylon feet',['osm-geofabrik','zair','binjiang-gazette']),
          'cableLayout':estimate({'stationsPerFan':14,'radiusM':.055,'anchorsByTowerHeight':'0.35..0.92 of73.95m'},'anchor stations±3m, radius±40%; cablecount not certified','figure1 fan and real tower silhouette; 14 original representative cables each of4 longitudinal fans×2 planes, not as-built cable inventory',['zhijiang-paper','zair'])},
         'pending':['absolute tower footing/deck/water datum and90.5m steel-height versus diagram96.5m overall-height convention','actual towerWGS and cable anchors; complex highway/bankwalk elevator and ramps','root v5 sourcegraph extended to30.15 now connects west ends; geometry/driving still pending','complete viaduct/approach pier stations and collision permissions']}
    ]
    anchor=bridges[0]['centerWGS84']
    for b in bridges:
        a,c=b['axisSourceEndpointsWGS84'];dx=(c[0]-a[0])*g['eastMetresPerDegree'];dy=(c[1]-a[1])*g['northMetresPerDegree'];angle=math.atan2(dy,dx)
        b['axisRadiansEastCCW']=angle;b['bearingDegreesFromNorth']=(90-math.degrees(angle))%360;b['centerGameEN']=list(project(*b['centerWGS84'],city))
    spec={'schemaVersion':1,'id':'qiantang-bridges','cityId':'hangzhou','scope':'Three finite source-bound bridge structural exteriors; road surfaces, measured absolute deck/navigation profiles, complicated interchanges and current driving acceptance excluded',
       'anchor':{'lon':anchor[0],'lat':anchor[1]},'bridges':bridges,'budget':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},
       'coordinatePolicy':'Hangzhou city_config project; physical metres; scale once. lm.x/lm.z/lm.y already game units. lm.y is caller river-display surface datum, NOT ground or EGM2008 measured elevation.',
       'deckShellPolicy':'undersides/sides only; no road top planes (root road pipeline). Lower single-track railway top and rails are appearance, not navigation.',
       'baseBuildingIdsToExclude':[],'renderWater':False,'renderRoadTops':False,
       'suggestedMaterials':{'carpaint':{'color':[.42,.67,.76],'roughness':.35,'metallic':.5,'use':'blue Fuxing painted steel, estimate'},'civicred':{'color':[.72,.055,.035],'roughness':.4,'metallic':.45,'use':'red Zhijiang steel, estimate'}},
       'sourcePbfSha256':src['sourcePbfSha256'],'sourceSnapshotSha256':src['sourcePbfSha256'],'sourceSnapshot':src['sourceSnapshot'],'sourceFeatureSubsetSha256':sha(HERE/'fixed-bridge-features.geojson'),
       'specialBlockers':{'xixing-bridge':'2025-11-22 closure for reconstruction; 2026 source construction status, no current completed bridge/deck candidate.',
          'boao-tunnel':'source underground tunnel ways546241781/607103735; no depth/portals/measured grade; no surface bridge or navigation depth invented.'}}
    write('spec.json',spec)
    write('measurements.json',{'cityId':'hangzhou','sourceCRS':'EPSG:4326','projectionConfigSha256':sha(ROOT/'config/cities/hangzhou.json'),
      'sourcePbfSha256':src['sourcePbfSha256'],'bridges':[{'id':b['id'],'centerWGS84':b['centerWGS84'],'centerGameEN':b['centerGameEN'],
      'bearingDegreesFromNorth':b['bearingDegreesFromNorth'],'sourceRoadLengthsM':{r['id']:r['sourceLengthM'] for r in b['roads']},
      'sourceRoadIds':[r['id'] for r in b['roads']],'structuralPositionStatus':'estimated on exact source axes; no pier/pylon survey'} for b in bridges],
      'identityCorrection':'826790145 is closed man_made bridge area, NOT rail centerline;154142001 is actualrailway; shared node3351280499 is sourceplan crossing across separate layer/mode, not a driving junction.',
      'method':'exact fixed node refs/WGS chains; Hangzhou config planar physical-metres arc lengths; bridge-center/superstructure stations finite estimates with explicit bounds.'})
    print(json.dumps({'bridgeCount':len(bridges),'roads':sum(len(b['roads']) for b in bridges),'railways':1,'baseBuildingExclusions':[]},ensure_ascii=False))
if __name__=='__main__':main()
