"""Evidence-qualified water/ground advice; no shared application writes."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent;DATE='2026-10-14'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,d):(OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    sources=[
      {'id':'westlake-plan2017','url':'https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web149/site/attach/0/00438d0707364b9497e1561b6f3f61ac.pdf',
       'publisher':'杭州西湖风景名胜区管理委员会办公室；杭西管办[2017]107号','accessedAt':DATE,'sourceDate':'2017;PDFmetadata2017-12-26',
       'sha256':digest(Path('<TEMP>/hz-water-westlake-plan-2017.pdf')),'bytes':4390929,'review':'actual PDF page6(left printed6),section4.4.3 rendered/read; scanned text extraction empty',
       'license':'unknown, reference only; PDF/pages not bundled','claims':'routine Yellow Sea7.18±.05m for>=292days outside abnormal rain; do not imply every day/current measured value'},
      {'id':'westlake-performance2022','url':'https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web3174/site/attach/-1/2309251544584554963.pdf',
       'publisher':'杭州西湖风景名胜区西湖引配水运行经费绩效自评','accessedAt':DATE,'sourceDate':'2022assessment;PDFcreated2023-09-25',
       'sha256':digest(Path('<TEMP>/hz-water-westlake-performance-2022.pdf')),'bytes':136865,'review':'actual text and rendered PDF page1 table read',
       'license':'unknown, reference only; PDF/page not bundled','claims':'target7.18±.05m Yellow Sea,reported352days achieved in2022; historical performance, no2026live measurement'},
      {'id':'copernicus-product','url':'https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM',
       'publisher':'Copernicus Data Space / ESA','accessedAt':DATE,'sourceDate':None,'review':'actual official page read',
       'license':'project original DSM license/attribution unchanged','claims':'DSM includes surfaces/vegetation/buildings,water flattening/river flow edits,WGS84/EPSG3855,global vertical<4mLE90 not local road-floor certainty'},
      {'id':'copernicus-height-api','url':'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html',
       'publisher':'Copernicus Data Space / Sentinel Hub official documentation','accessedAt':DATE,'sourceDate':None,'review':'actual official page read',
       'license':'reference only','claims':'default Copernicus heights orthometric relative EGM2008; optional adding geoid height returns WGS84 ellipsoid height. No Yellow Sea datum transformation supplied'},
      {'id':'qiantang-forecast2025','url':'https://ls.hangzhou.gov.cn/art/2025/6/7/art_1622550_59029625.html',
       'publisher':'杭州市林业水利局潮汐预报','accessedAt':DATE,'sourceDate':'forecast2025-06-08/published2025-06-07','review':'search-index table read; direct page timeout',
       'license':'unknown,reference only','claims':'CityBalcony(奥体) two forecast high tides4.40/4.30m and zero predicted bore for this small tide day; height datum not in accessible excerpt, no lower tide or mean inferred'},
      {'id':'zhejiang-design-tides','url':'https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web3028/site/attach/0/c361d2f7455b4cc58d07ba68d3cf421f.pdf',
       'publisher':'浙江省海塘安澜千亿工程建设技术指南附录B','accessedAt':DATE,'sourceDate':None,'review':'search-index tableB.1read; direct PDF403/unavailable',
       'license':'unknown,reference only','claims':'explicit1985datum;Zhakou/Qibao100year8.70m/300year9.30m design high tides. NOT regular/localCityBalcony water plane'},
      {'id':'gongshu-riverplan','url':'https://zjjcmspublicnew.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/cms_files/jcms1/web2096/site/attach/0/ae621e99f5c34b6c89a8fb1fa2f16c4e.pdf',
       'publisher':'拱墅区重点流域水生态环境保护官方公开文件','accessedAt':DATE,'sourceDate':None,'review':'search-index table25read; directPDF403, edition/datum unverified',
       'license':'unknown,reference only','claims':'several canal-eastern polders have1.35~1.6m landscape control band and conditional pumping/sluicing; cannot apply to all rivers or infer EGM conversion'},
      {'id':'temple-operator','url':'https://www.lingyinsi.org/detail_44_7946.html','publisher':'灵隐寺运营方官网','accessedAt':DATE,'sourceDate':'2014-08-08;referenceimageupload2020',
       'review':'existing source text/photo review reused read-only, actual temple wide/stair photographs newly inspected','license':'publisher copyright;reference only; no photographs bundled',
       'claims':'five main halls on rising hillside axis; exact five-floor elevations/steps not provided'},
      {'id':'unesco-nomination','url':'https://whc.unesco.org/uploads/nominations/1334.pdf','publisher':'中国缔约国申遗档案/UNESCO World Heritage Centre',
       'accessedAt':DATE,'sourceDate':'2011archive;Lingyin aerialcaption2007','sha256':'5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442',
       'review':'existing actual PDF main-text printed178/179 read; five-hall order/300m axis/templearea, not a ground elevation survey',
       'license':'unknown,reference only;PDF/page not bundled','claims':'northsouth five-hall identity/order; no five-hall step/absolute elevation data in reviewed main text'},
      {'id':'balcony-construction','url':'https://news.sohu.com/20070126/n247846969.shtml','publisher':'浙江在线今日早报总工苏永会施工采访/搜狐刊载',
       'accessedAt':DATE,'sourceDate':'2007-01-26','sha256':digest(Path('<TEMP>/hz-balcony-construction.html')),
       'review':'actual full interview read, reused reference','license':'reference only','claims':'two public levels,piers/skylights/steelconnections;lift/roomuses planned then, absolute ground and deck elevations not given'},
      {'id':'balcony-photographer','url':'https://dp.pconline.com.cn/photo/list_1941203.html','publisher':'原作者石上清流/太平洋摄影部落','accessedAt':DATE,'sourceDate':'2010-09-27',
       'review':'prior9actualimages inspected; source hashes remain in city-balcony-round2/photo-review.json','license':'authorcopyright,unlicensedcommercialphoto use prohibited;reference only',
       'claims':'shorebridge undercroft and public paved areas observable; no calibrated absolute height/step count'},
      {'id':'theatre-architect','url':'https://carlosott.com/?project=hangzhou-grand-theatre','publisher':'Carlos Ott主创官网','accessedAt':DATE,'sourceDate':None,
       'review':'existing actual designer references/source hashes reused read-only','license':'unknown,reference only','claims':'pool/lowstage/raisedentry shape context; no georeferenced pond boundary/ground datum supplied'},
      {'id':'theatre-owner-news','url':'https://www.hzsc.com.cn/content/content_9587063.html','publisher':'杭州拥江发布/上城区新闻报道中心','accessedAt':DATE,'sourceDate':'2023-08-12',
       'review':'actual page read','license':'unknown,reference only','claims':'theatre-facing music fountain,water landscape and sunken outdoorstage described as different site elements; not exact water level/footprint'},
      {'id':'commons-theatre-high','url':'https://commons.wikimedia.org/wiki/File:20190717杭州大剧院.jpg','publisher':'原创摄影师MasaneMiyaPA/WikimediaCommons','accessedAt':DATE,'sourceDate':'2019-07-17 12:58:16',
       'review':'actual current source-cache thumbnail viewed; verified metadata in grand-theatre-round2/commons-thumb-fetches.json',
       'license':'CC BY-SA4.0 per prior source metadata; reference only,no pixels or photo-derived georeferenced polygon bundled',
       'claims':'horseshoe-like pool with straight breaks and central sunken theatre/island, raised building frontage and broad stairways; no surveyed levels'},
      {'id':'commons-theatre-front','url':'https://commons.wikimedia.org/wiki/File:Hangzhou_Grand_Theatre_18.jpg','publisher':'原创摄影师钉钉/WikimediaCommons','accessedAt':DATE,'sourceDate':'2019-11-08 14:34:26',
       'review':'actual source-cache thumbnail viewed, metadata reused','license':'CC BY-SA4.0 per prior source metadata;reference only,no pixels bundled',
       'claims':'low pool curb next to paved pedestrian ground,curved pool edge/sculpture/raisedentry; exact depth/absolute height unavailable'}]
    blockers=[
      {'id':'yellowSea-version','scope':'WestLake','reason':'Both official7.18references state Yellow Sea but no1956/1985edition; cannot silently label asEPSG5737.'},
      {'id':'vertical-tie','scope':'all','reason':'No local trustedEGM2008to national/local benchmark tie; available non-ballparkPROJoperation count0.'},
      {'id':'river-current-stage','scope':'Qiantang','reason':'Tides/storm/flood/time/location vary; no complete same-datum current or representative CityBalcony tide series.'},
      {'id':'canal-datum-zones','scope':'urban canals','reason':'Per-basin gate/pump control and datum unverified; no common1.35/1.5/3m plane justified for all.'},
      {'id':'balcony-floor-levels','scope':'CityBalcony','reason':'Absolute lower floor/shoredeck and true upper separation/entry stair/ramp/lift surveys missing; centroidDSMmay sample upper deck/room roofs.'},
      {'id':'theatre-pool-polygon','scope':'GrandTheatre','reason':'Actual pool evident, but no independently georeferenced pool outer/innerrings or site section; processedwater geometry intersects sitebox0features.'},
      {'id':'temple-steps','scope':'Lingyin five halls','reason':'Five axial stair/terrace profiles,count,rise/tread/entry positions and benchmark height missing. Nearby3stepsways are52–129m from five-hall envelope, noele/step_count.'}]
    write('source-claims.json',{'schemaVersion':1,'sources':sources,'reported':[{'parameter':'WestLake routine level','valueM':7.18,'operationalBandM':.05,
      'basis':'reported','sourceIds':['westlake-plan2017','westlake-performance2022'],'datum':'Yellow Sea edition unknown','uncertainty':'±.05 is routine control band, NOT transformation/survey uncertainty or all-weather bound'},
      {'parameter':'Qiantang CityBalcony forecast high tides for2025-06-08','valuesM':[4.4,4.3],'basis':'reported-index-only','sourceIds':['qiantang-forecast2025'],'datum':'unknown in accessible excerpt','notApplicableAs':'normal mean/low tide/currentEGMplane'},
      {'parameter':'Zhakou/Qibao100/300year design highs','valuesM':[8.7,9.3],'basis':'reported-index-only','sourceIds':['zhejiang-design-tides'],'datum':'1985NationalHeight','notApplicableAs':'normal water plane'},
      {'parameter':'selected Gongshu polders landscape control band','rangeM':[1.35,1.6],'basis':'reported-index-only','sourceIds':['gongshu-riverplan'],'datum':'unknown in accessible excerpt','notApplicableAs':'all canals common plane'}],
      'blockers':blockers,'rejectedNumericalShortcuts':['secondary7.15WestLake as current definitive value instead of official7.18',
        '7.5-7.18=.32 as surveyed EGMtoYellowSea offset','design8.7/9.3 as day-to-day river water',
        'OSMheight6 as an absolute CityBalcony floor elevation','DSM/filtered hall samples as measured stair levels',
        'a personal-phoneGPS110m Huayan blog as national datum floor survey',
        'nearby govt temple article about GaoLiTemple10m ground as Lingyin datum',
        'nearby rivers or building footprint as exact theatre pool boundary']})
    dat=json.loads((OUT/'fixed-data-check.json').read_text())
    parameters={'schemaVersion':1,'cityId':'hangzhou','status':'research-only-not-runtime-accepted','verticalScaleOnce':.6,
      'WestLake':{'waterFeatureId':'relation/2308774','reportedRoutineHeightM':7.18,'reportedBandM':.05,'reportedDatum':'Yellow Sea; editionunknown',
        'sameSourceEditedDSMHeightM':7.5,'sameSourceDatum':'EGM2008','provisionalGameHeightIfSameSourceZeroReference':4.5,
        'basis':'candidate source-consistent edited-water value, not measured actual lake level','datumOffsetToApplyM':None,
        'conservativeAllowance':'product global<4mLE90 is source specification, not local guarantee; datum error unknown. Keep ground/water visual and collar check pending.',
        'recommendation':'Separate water plane from road/bridge deck and whole-lake shoreline mask. Retain source7.5only as explicitly provisional EGM-consistent candidate until benchmark tie verified.'},
      'Qiantang':{'waterFeatureId':'relation/8227206','sameSourceEditedDSMReferenceHeightM':1.5,'sameSourceDatum':'EGM2008',
        'provisionalGameReferenceHeightIfSameSourceZeroReference':.9,'normalActualAbsoluteHeightM':None,'tideAmplitudeM':None,
        'basis':'candidate DSMedited water reference at two verified in-polygon points; not timestamped tide or gauged mean',
        'conservativeAllowance':'edited-water epoch/flattening + tide/flood + unknown datum conversion prevent a defensible local±metre water guarantee',
        'recommendation':'Keep river references/data dates/vertical datum distinct from lake. Do not add fake sinusoid or real-world tide status to game without time-series phase/source.'},
      'Canals':{'commonAbsoluteHeightM':None,'datum':None,'recommendation':'Use separate source waterbody/sluice-reach groups; derive approximate editedDSMplane within each large actual polygon only as candidate. Narrow/tunnelled channels and controlled pools remain blockers.'},
      'CityBalcony':{'lowerFloorAbsoluteHeightM':None,'upperFloorAbsoluteHeightM':None,'existingIsolatedLowerM':0,'existingEstimatedUpperSeparationM':6,
        'separationAllowanceM':2,'sampledCentroid':dat['platformSamples']['cityBalcony-footprintCentroid'],
        'recommendation':'Do not bind lower-floor lm.y to centralDSMorfiltered value as survey. Use authoritative shore benchmark/level plan; until then keep isolated/source-estimated platform with entry/floor collision pending.'},
      'GrandTheatre':{'poolOuterWGS84':None,'poolInnerRingsWGS84':None,'poolAbsoluteWaterHeightM':None,'poolDepthM':None,
        'observedHierarchy':['outer public plaza/pool edge','shallow decorative water around protected sunken theatre island','sunken theatre seating/stage','raised theatre forecourt with broad entry stairs'],
        'basis':'reported official context/actual source photos; numerical geometry unknown',
        'recommendation':'Root base-water pipeline only, separate pool polygon with drystage holes/ground walkways. Never fill sunken theatre or derive pool from building/whole river footprint; trace needs georeferenced controls/source permit and estimated accuracy report.'},
      'Lingyin':{'hallGroundAbsoluteHeightsM':[None]*5,'sourceSamples':dat['halls'],'candidateHillOnlyAllowanceM':15,
        'allowanceBasis':'modelling guard band only for wooded/built slope; not calibrated error or guaranteed local floor bound',
        'recommendation':'Use DSMonly for broad hillside context. Five terraces require independent local stair/retaining-wall profiles/level plans before lifting halls as if measured. Do not force all five on one flat floor or treat3x3filter as survey.'},
      'runtimeAcceptanceRequired':['water/drygroundmask/shoreline clipping','exact public-floor/bridge heights and shared endpoints',
        'layer-separated tunnels/raised bridges','height-awarecolliders','walkable validated arrival without water/curb/wall obstruction','current day/night views/current real-driving checks'],
      'blockers':blockers}
    write('integration-parameters.json',parameters)
    refs=[]
    lrefs=json.loads((ROOT/'docs/hangzhou/research/core/lingyin-round2/photo-review.json').read_text())['photos']
    for ident,path,obs in [('grand-wide','<TEMP>/hz-lingyin-grand-wide.jpg','raised main plinth/front stair run visibly occluded by people/incense; no complete riser inventory'),
      ('medicine','<TEMP>/hz-lingyin-medicine.jpg','stone platform/rail below red pillars; stair and lower yard hidden'),
      ('dharma-wide','<TEMP>/hz-lingyin-dharma-wide.jpg','high stone retaining wall and sloping/stepped side balustrade; floor-to-yard height uncalibrated'),
      ('huayan-wide','<TEMP>/hz-lingyin-huayan-wide.jpg','white terrace rail and side stair with people; full rise and ground datum hidden')]:
        r=next(x for x in lrefs if x['id']==ident);assert digest(Path(path))==r['sha256'];refs.append({'id':ident,'url':r['url'],'sha256':r['sha256'],'observation':obs,
          'reviewedAt':DATE,'method':'actual temporary-cache view_image','bundled':False,'cameraCalibration':None,'use':'qualitativeground/step evidence only'})
    for r in json.loads((ROOT/'docs/hangzhou/research/core/grand-theatre-round2/commons-thumb-fetches.json').read_text()):
        assert digest(Path(r['temporaryPath']))==r['sha256'];refs.append({'id':r['id'],'url':r['url'],'sha256':r['sha256'],'captureDate':r['captureDate'],
          'reviewedAt':DATE,'method':'actual temporary-cache view_image','license':r['license'],'bundled':False,
          'observation':'curved shallow pool with dry central sunken theatre / low curb beside pedestrian pavement and elevated forecourt; uncalibrated/no exact georeferenced boundary'})
    write('photo-ground-review.json',{'references':refs,'photosBundled':False,'numericStepCounts':None,'numericPoolBoundary':None,
      'limitations':'Actual photographs support qualitative layers; no calibrated camera/georeferenced level drawing or survey-derived vertices.'})
    write('attempts.json',{'date':DATE,'networkFailures':[{'source':'zhejiang-design-tides','result':'curl403/webunavailable; indexedtableonly'},
      {'source':'qiantang-forecast2025','result':'directwebtimeout; indexedforecastonly'},{'source':'gongshu-riverplan','result':'curl403/web403;indexedtableonly'},
      {'source':'qiantang EIA72a355...','result':'curl403/webunavailable;not adopted as measured daily/localdatum'},
      {'source':'oldprovincialwetdryEIAffd6a3...','result':'direct404;not adopted as a verified current gauge series'}],
      'pdfAttempts':[{'source':'westlake-plan2017','result':'downloaded/scannedtextempty;actual page6 printed6 visually read;page8blank,page7otherchapter not height evidence'},
        {'source':'westlake-performance2022','result':'actualPDFpage1 text/table visually read;2022assessmentnot2026weather'}],
      'cpuChecks':'existing OSM/DSMhashes,sampled values,sourcepolygon inclusion and localPROJdatumoperations checked; ICC API contract checked separately',
      'BlenderBrowser':'notrun','sharedWrites':'onlyICCmodule API added at root explicitrequest; existingBfaces/spec unchanged, no totalassets/config/runtime writes'})
    print(json.dumps({'primarySources':len(sources),'groundPhotosActuallyReviewed':len(refs),'blockers':len(blockers),'runtimeHeightsAccepted':0},ensure_ascii=False))
if __name__=='__main__':main()
