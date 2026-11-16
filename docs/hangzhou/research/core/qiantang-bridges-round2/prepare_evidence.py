"""Finite appearance versus separately blocked bridge/tunnel profile jobs."""
from pathlib import Path
import copy
import hashlib
import json
import math
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(ident,url,publisher,use,date=None,license='unknown; reference only',**kwargs):
    return dict(id=ident,url=url,publisher=publisher,accessedAt='2026-10-14',sourceDate=date,status='available; actual page/figure read',license=license,use=use,**kwargs)
def obs(kind,value,basis,ids,uncertainty,unit=None):return dict(kind=kind,value=value,basis=basis,sourceIds=ids,uncertainty=uncertainty,unit=unit)
def main():
    spec=read(HERE/'spec.json');bridges=spec['bridges'];prefix=HERE.relative_to(ROOT);tmp=Path('<TEMP>/qiantang-bridges-research')
    sf={r['id']:r for r in read(HERE/'source-fetches.json')};pf={r['id']:r for r in read(HERE/'photo-page-fetches.json')};images={r['id']:r for r in read(HERE/'photo-image-fetches.json')};ss={r['id']:r for r in read(HERE/'status-source-fetches.json')}
    sources=[source('osm-geofabrik','https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf','OpenStreetMap contributors / Geofabrik','exact EPSG4326 way/node transport identities and raw outer-boundary continuation; OSM is not a current surveying certificate','2026-10-11T20:21:06Z','ODbL-1.0',localPath='data/raw/hangzhou/zhejiang-261011.osm.pbf',sha256=spec['sourcePbfSha256']),
      source('qiantang-school',sf['qiantang-school']['url'],'西南交通大学土木工程学院','16 Warren trusses,1072m main,65.84m calculation span,10.7m truss,6.1m roadway+1.52m sidewalks each; reported historical engineering summary, not field elevations','2019-09-28',sha256=sf['qiantang-school']['sha256']),
      source('fuxing-gov',sf['fuxing-gov']['url'],'上城史志 / 杭州政协','reported two190m/nine85m arches and1376m; real elevated near-axis photo. Lower bus/slow-use history is not complete current per-way access policy','2026-09-20',sha256=sf['fuxing-gov']['sha256']),
      source('fuxing-paper',sf['fuxing-paper']['url'],'陈宝春 / 福州大学；中外公路28(4),2008,95–100','p98 figure8 and text:11 calculation spans2×85+190+5×85+190+2×85,26.4/32m widths. Estimate heights/rise ratios from original drawing. 2008 centralmetro reservation not drawn as a current track','2008-08',sha256=sf['fuxing-paper']['sha256']),
      source('zhijiang-paper',sf['zhijiang-paper']['url'],'曹一山/徐强/李克冰；交通运输部公路科学研究所/北京交通大学；公路交通科技33(5),2016,73–77','primary engineering study, fig1:116+246+116m,90.5m steel tower,ellipse73.95/22.2m,steelbox3.5×41.36m. Figure96.5m overall versus steel90.5 datum not silently conflated','2016-05',sha256=sf['zhijiang-paper']['sha256']),
      source('zhijiang-environment',pf['zenvpdf']['url'],'浙江省环境监测中心 / 杭州市生态环境部门公开竣工验收调查报告','p14 table2-2 actual2.98% maxgrade/350m minlength;3760m includes approach/landviaduct; p12 barriers1.1–1.2m, two barrier lines3m apart; p13 map qualitative context only, not WGS source','2016-07-22',sha256=pf['zenvpdf']['sha256']),
      source('binjiang-gazette',read(HERE/'gazette-read.json')['url'],'杭州市滨江区地方志编纂机构 / 杭州高新区（滨江）政府','actual PDF p23 printed colorplates30–31, photos by杜剑挥(Fuxing) and孙国尧(Zhijiang); completion-year captions are not image capture dates',None,sha256=read(HERE/'gazette-read.json')['sha256']),
      source('xixing-closure',ss['xixing-closure']['url'],'杭州日报记者吴佳妮/谢珂，市交通运输局/市建委/公安交管发布会，杭州政协发布','2025-11-22 closed to vehicles/pedestrians; primary detour recommendation explicitly includes driving via Fuxing lowerfloor, in tension with simplified2026 localhistory use list','2025-11-10',sha256=ss['xixing-closure']['sha256']),
      source('xixing-current',ss['xixing-current']['url'],'上城史志 / 杭州政协','81m/1280m/15pairs describe OLD bridge;2024-11 reconstruction started,2027-end planned, not completed present model','2026-10-12',sha256=ss['xixing-current']['sha256'])]
    photo_info={
      'q2024':('Windmemories','2024-01-28','CC BY-SA4.0','north-bank nearly side-on, looks toward built-up southbank; repeated Warren diamonds/15pier pattern andlowerrail visible; not a deck/datum survey'),
      'qside':('Zhangzhugang','2012-05-18','CC BY-SA4.0/GFDL','high Liuhepagoda northwest view, southward across bridge; wholelongaxis androad/rail composition, historical2012surface condition'),
      'qair':('David290','2019-11-17','CC BY-SA4.0','WGS camera120.126387,30.196298 west of northshore; northeast-facing drone view to northriverbank approach, transverse construction visible; coordinates metadata notsurvey'),
      'f1':('Huandy618','2012-09-25','CC BY-SA3.0','riverbank low oblique approaching bridge axis, mountain opposite shore supports southbank-looking north identification±25°; lowerdeck/piers/open gap andblue arch lattice clearlyvisible'),
      'f7':('Huandy618','2012-09-25','CC BY-SA3.0','stone officialbridge inscription underroad close context; not counted as second structuraldirection or actualdimensions survey'),
      'zair':('Charlie fong','2020-12-17','CC BY-SA4.0','elevated westernbank view east across red portals towardBinjiang(right perauthorcaption); two transversearches, dualstayplanes, concretepier gaps andfurther eastapproach visible')}
    photo_review=[]
    for key,(author,date,lic,view) in photo_info.items():
        row=images[key];sources.append(source(key,pf[key]['url'],author+' own photograph / Wikimedia Commons',view,date,lic+'; reference only',sha256=row['sha256']))
        photo_review.append({'id':key,'sourceUrl':pf[key]['url'],'imageUrl':row['url'],'temporaryLocalPath':row['path'],'sha256':row['sha256'],'author':author,'date':date,'license':lic,'type':'actual built-photo','viewAndObservation':view,'reviewedBy':'Codex child leifeng_candidate','reviewedAt':'2026-10-14','bundled':False})
    sources.append(source('fgovphoto',sf['fuxing-gov']['url'],'上城史志 / 杭州政协','actual elevated north-bank near-axis view south toward buildings, two blue largearches and nine lowarches;capturedateunknown, governmentpagepublished2026',None,sha256=pf['fgovphoto']['sha256']))
    photo_review.append({'id':'fgovphoto','sourceUrl':sf['fuxing-gov']['url'],'imageUrl':pf['fgovphoto']['url'],'temporaryLocalPath':pf['fgovphoto']['localPath'],'sha256':pf['fgovphoto']['sha256'],'author':'not separatelycredited','date':'unknown; page2026-09-20','license':'unknown','type':'actual built-photo','viewAndObservation':'north elevated axis view to south, direction opposite low f1 appearance; major bluepaired ribs and underdeck spaces visible','reviewedBy':'Codex child leifeng_candidate','reviewedAt':'2026-10-14','bundled':False})
    for key,author,view,index in [('gazette-fuxing','杜剑挥','night high bank-sweep view to bigarches; geometry context only, no emittedlights/lightingrecipe reconstructed',5),('gazette-zhijiang','孙国尧','broad river-side high view landward to bankapproach andbranchroads; different view from zair acrosswater toward opposite buildings. Exactbank/cardinalcamera notgeoreferenced, no coordinate derived; portalclosefacades notresolved',6)]:
        path=tmp/f'zgazette-p23-{index}.png';photo_review.append({'id':key,'sourceId':'binjiang-gazette','sourceUrl':read(HERE/'gazette-read.json')['url'],'pdfPage':23,'printedPages':'30–31','author':author,'captureDate':'unknown; captionyear meanscompletion','temporaryLocalPath':str(path),'sha256':sha(path),'license':'unknown','type':'actual built-photo','viewAndObservation':view,'reviewedBy':'Codex child leifeng_candidate','reviewedAt':'2026-10-14','bundled':False})
    write(HERE/'photo-review.json',{'reviewedAt':'2026-10-14','reviewedBy':'Codex child leifeng_candidate','photos':photo_review,
     'coverage':{'qiantang':'side/northwesthigh/westdrone; 2012/2019/2024, no present2026all-sides claim','fuxing':'lowbankoblique vsnorthhighaxis +independentbanknight context; notperwaycurrentdriverpermission','zhijiang':'western highportal view2020 +different landwardbankapproach real governmentphoto unknowndate; exactcamera/cableanchorsandnorth/south closefacades pending'},
     'figureReviews':[{'sourceId':'fuxing-paper','page':4,'printedPage':98,'figure':8,'readVia':'pdfplumber pdfium220dpi; originaldata, not photograph editing or asset','finding':'spansequence+variablewidth; gap/endapproach placementestimated, do not borrow adjacent Zhengzhou/Lanzhou bridges dimensions'},
       {'sourceId':'zhijiang-paper','figure':1,'sha256':sf['zhijiang-layout']['sha256'],'finding':'two transverseellipseportals, twinplanes/116+246+116; 96.5m figureextent vs90.5m steelreported needsheightconvention, notwater-relativeheight'}],
     'noPhotographyAssetsPublished':True})
    write(HERE/'source-observations.json',{'observations':[{'id':b['id'],'reported':b['reported'],'estimated':b['estimates'],'pending':b['pending']} for b in bridges],
      'conflicts':[{'id':'qiantang','values':'officialheritageportal71m unqualified height versus10.7m engineeringtruss; widths6.1travel/9.14summedsidewalks versusotherunqualified10.10m','decision':'useexplicitcomponentdimensions only; no unqualified bridgeheight treated as deck/waterclearance'},
        {'id':'fuxing-lower-use','sources':['fuxing-gov','xixing-closure'],'values':'2026 localhistorybus/slow use versus2025 primarytransportannouncementlowerfloorcar detour','decision':'no carban invented, no perwaypermissionfrozen; source primary road geometry retained'},
        {'id':'zhijiang','values':'90.5m steelheight /96.5m drawn overallextent; 40.5m roadmainwidth /41.36m steelboxincludingnose /38m environmentalroadbedwidth','decision':'distinctheight/widthconventions;90.5notdeckclearance;40.5road/41.36structshell;datum stillunknown'}],
      'sourceCoordinateWarning':'environment report p9 prints29°1N118°12E, inconsistent with bridge/localmap. Do NOT use that text orcommercialbackgroundmap ascoordinates; exact GeofabrikEPSG4326 only.',
      'rawAreaCorrection':'way826790145 closedman_madebridge area; true railwayway154142001. Additionalrail804826075 is south smallrail approach outside finitevisual main, no new road.'})
    # All own mutable review/spec files become hashed snapshots in the job.
    snapshot_names=['fixed-bridge-features.geojson','endpoint-adjacency.json','measurements.json','spec.json','photo-review.json','source-observations.json','source-fetches.json','photo-page-fetches.json','photo-image-fetches.json','status-source-fetches.json','gazette-read.json']
    snapshots={str(prefix/name):sha(HERE/name) for name in snapshot_names}
    write(HERE/'catalog.json',{'schemaVersion':1,'cityId':'hangzhou','sources':sources,'places':[
      {'id':'qiantang-bridges','name':'钱塘江三座桥梁有限外观','kind':'bridge structural exterior collection','location':{'center':[spec['anchor']['lon'],spec['anchor']['lat']]},'modeling':{'blockers':[]}},
      {'id':'qiantang-bridges-decks','name':'钱塘江桥面与多层道路剖面','kind':'bridge deck profiles','location':{'center':[spec['anchor']['lon'],spec['anchor']['lat']]},'modeling':{'blockers':['真实绝对桥面/水位/地面标高与复杂多层引桥剖面尚未知。']}},
      {'id':'xixing-bridge-current','name':'西兴大桥当前施工状态与道路','kind':'bridge under reconstruction','modeling':{'blockers':['断流施工；不能用旧桥/未来计划替代当前完工道路。']}},
      {'id':'boao-tunnel-profile','name':'博奥隧道地下车行剖面','kind':'underground tunnel profiles','modeling':{'blockers':['地下深度/入口标高/真实坡度未知，命名页面403。']}}]})
    args=[str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/landmark_tasks.py'),'generate','--city-id','hangzhou','--source',str(prefix/'catalog.json'),'--agent','codex-leifeng-candidate','--output',str(prefix/'task-bundles')]
    r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stderr+r.stdout
    write(HERE/'task-generation-result.json',json.loads(r.stdout))
    kinds=[obs('footprint',{b['id']:{'mainLengthM':b['reported'].get('mainLengthM',478),'sourceRoadIds':[r['id'] for r in b['roads']],'mappedPhysicalLengthsM':[r['sourceLengthM'] for r in b['roads']]} for b in bridges},'measured',['osm-geofabrik'],'measured exact frozen OSMaxis/chain coordinates by Hangzhouplanarcoefficients, not fielddimensions; reportedmainextent distinguished from roadway/approachextent; OSMplan±5m',unit='physical metres'),
      obs('height',{b['id']:{'nominalRoadDeckRelativeWaterM':b['profile'].get('upperWaterRelativeM',b['profile'].get('singleWaterRelativeM')),'relativeStructuralHeightM':b['reported'].get('trussHeightM',b['reported'].get('steelPylonHeightM',47.5))} for b in bridges},'estimated',['qiantang-school','fuxing-paper','zhijiang-paper','q2024','f1','zair'],'photo/diagram ratios, truss/crown/towerreported values separate from estimated waterrelative decks;Q19±5,F22±6(lower12±4),Z18±5m, tide andabsolute datumunknown. Nominal candidate only.',unit='physical metres'),
      obs('orientation',{b['id']:b['bearingDegreesFromNorth'] for b in bridges},'measured',['osm-geofabrik'],'physical EN bearings from source-area/river-crossing/pairedshape-break axis; 0degreesnorth clockwise. roadaxis±2°, mainstructureposition±45/35/70m stillestimated.',unit='degrees from north clockwise'),
      obs('silhouette',{'qiantang':'16 Warren triangle trusses,15 riverpiers, upperroad/lower singletrack railway','fuxing':'two largearches+nine smallarches, doubledeck andbluefour-chordbig-rib lattice','zhijiang':'two transverseellipse redsteelportals, dualplane cablefans, shallow broad steelbox'},'reported',['qiantang-school','fuxing-gov','fuxing-paper','zhijiang-paper','q2024','qside','f1','fgovphoto','zair','binjiang-gazette'],'finite originalmesh informed by actualdifferentdirections;2012/2019/2020/2024photos and2026pageunknowncapturedate. Current all-side/PBR/anchor dimensions notaccepted.')]
    evidence={'schemaVersion':1,'placeId':'qiantang-bridges','cityId':'hangzhou','scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','qiantang-school','fuxing-gov','zhijiang-paper']},
      'location':{'crs':'EPSG:4326','center':[spec['anchor']['lon'],spec['anchor']['lat']],'status':'confirmed','sourceIds':['osm-geofabrik'],'notes':'aggregatebuildanchor at mapped firstbridge centroid; perbridgecenters spec; pier/pylon longitudinalplacements estimated'},
      'sources':sources,'observations':kinds,'referenceImages':photo_review,'estimatedParameters':[{b['id']:b['estimates']} for b in bridges],
      'blockers':[],'pendingSubscopes':[{'scope':'all three measured deck/datum/multilayer ramp navigation','job':str(prefix/'task-bundles/qiantang-bridges-decks/job.json'),'status':'blocked'},
        {'scope':'xixing current reconstruction','job':str(prefix/'task-bundles/xixing-bridge-current/job.json'),'status':'blocked'},
        {'scope':'boao undergroundprofiles','job':str(prefix/'task-bundles/boao-tunnel-profile/job.json'),'status':'blocked'}]+[{'scope':b['id'],'pending':b['pending']} for b in bridges],
      'sourceSnapshots':snapshots,'photosBundled':False,'modelled':False,'verified':False}
    write(HERE/'evidence.json',evidence)
    profiles=copy.deepcopy(evidence);profiles.update(placeId='qiantang-bridges-decks',scope='Measured absolute threebridge source-road profiles including grade/ramp/networkboundary/actorconnection; no finiteappearance exception',blockers=['真实绝对桥面/水位/地面标高尚未取得；不能把照片估计或layer×6m写成实测。','复兴上下层复杂引桥及各lowerway许可未冻结，当前通用source-node tierclearance不能完成实桥剖面。','之江西侧源接续已从固定PBF提取且root v5已连主分量；完整互通曲线/入口坡道/实际桥面仍未验证。']);profiles['observations']=[o if o['kind']!='height' else obs('height',None,'unknown',[],'no absolute measured/profile datum available') for o in kinds];profiles['pendingSubscopes']=[]
    # Additional blocked current-state records retain exact fixed-source IDs.
    allroads={f['id']:f for f in read(ROOT/'data/processed/hangzhou/roads.geojson')['features']};fixed={f['id']:f for f in read(HERE/'fixed-bridge-features.geojson')['features']}
    xids=['way/'+str(i) for i in [5041735,28596734,28596757,331859982,331860328,331860329,340388832,346585778,388018764,420013388,420013389]];xrows=[allroads[i] for i in xids if i in allroads]
    write(HERE/'xixing-fixed-source.geojson',{'type':'FeatureCollection','sourcePbfSha256':spec['sourcePbfSha256'],'features':xrows})
    def blocked_record(ident,name,rows,source_ids,blockers):
        coords=[p for f in rows for p in f['geometry']['coordinates']];center=[sum(p[k] for p in coords)/len(coords) for k in [0,1]]
        record={'schemaVersion':1,'placeId':ident,'cityId':'hangzhou','scope':name,'identity':{'status':'confirmed','sourceIds':source_ids},'location':{'crs':'EPSG:4326','center':center,'status':'confirmed','sourceIds':['osm-geofabrik']},'sources':sources,'observations':[
         obs('footprint',{'sourceIds':[r['id'] for r in rows]},'measured',['osm-geofabrik'],'exact source refs/coordinates; not constructionplan'),
         obs('height',None,'unknown',[],'no current complete underground/constructedheight/verticaldatum'),
         obs('orientation','sourcewaychains in fixedWGS84','measured',['osm-geofabrik'],'source-nodepath direction; ramp height unknown'),
         obs('silhouette','under reconstruction, old completedshape excluded' if ident.startswith('xixing') else 'underground road tunnel, no surface bridge','reported',source_ids,'sourceperiod/status, no current fullprofile mesh')],
         'blockers':blockers,'sourceSnapshots':copy.deepcopy(snapshots),'photosBundled':False,'modelled':False,'verified':False}
        return record
    xi=blocked_record('xixing-bridge-current','current closed reconstruction only, no old/futurecompletedbridge',xrows,['osm-geofabrik','xixing-current','xixing-closure'],['2025-11-22禁止车辆/行人断流，2026-10-12资料仍描述改建计划2027，当前可行驶桥模型未成立。','未取得本快照日期全部施工构件外观/高度/施工便桥及可进入区；无模型输出。'])
    xi['sourceSnapshots'][str(prefix/'xixing-fixed-source.geojson')]=sha(HERE/'xixing-fixed-source.geojson')
    bo=blocked_record('boao-tunnel-profile','fixed underground identity and unresolved portals/depth only',[fixed['way/546241781'],fixed['way/607103735']],['osm-geofabrik','xixing-closure'],['地下真实埋深/道路标高/坡道入口和净高未知；不作任意负layer×6m或地表桥面。','旧命名页本次403；9m单管/总宽未确认。2025发布会禁止隧道行人与非机动车，无actorpath acceptance。'])
    entries={'qiantang-bridges':evidence,'qiantang-bridges-decks':profiles,'xixing-bridge-current':xi,'boao-tunnel-profile':bo}
    for ident,ev in entries.items():
        folder=HERE/'task-bundles'/ident;job=read(folder/'job.json');job['ownership']['workerFiles']=['scripts/landmarks/qiantang_bridges.py'];job['ownership']['workerDirectories']=[str(prefix)];job['ownership']['integrationOwner']='root';write(folder/'job.json',job);write(folder/'evidence.json',ev)
        model=read(folder/'model.json');model.update(sourceModule='scripts/landmarks/qiantang_bridges.py',sourceModuleSha256=sha(ROOT/'scripts/landmarks/qiantang_bridges.py'),sourceSpec=str(prefix/'spec.json'),sourceSpecSha256=sha(HERE/'spec.json'),artifactPath=None,sha256=None,buildCommand=None,
           accuracyClaim='finite sourcebound structuralexterior candidate; blocked deck/datum/navigation, GLB pending' if ident=='qiantang-bridges' else 'blocked scope; no physical model accepted',estimatedParameters=evidence['estimatedParameters'] if ident=='qiantang-bridges' else []);write(folder/'model.json',model)
        r=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/landmark_tasks.py'),'check','--job',str(folder/'job.json'),'--stage','evidence-ready','--record'],cwd=ROOT,capture_output=True,text=True)
        output=json.loads(r.stdout);write(folder/'evidence-ready-result.json',{'exitCode':r.returncode,'result':output});print(json.dumps({'id':ident,'exitCode':r.returncode,'recordedStage':output.get('recordedStage'),'currentStage':output.get('currentStage'),'evidenceErrors':output.get('errors',{}).get('evidence-ready')},ensure_ascii=False))
    write(HERE/'stage-status.json',{'scope':'finite threebridge exterior e-ready separate from blocked profiles/currentconstruction/undergroundgeometry','jobs':[{ 'id':i,'checkExitCode':read(HERE/'task-bundles'/i/'evidence-ready-result.json')['exitCode'],'status':read(HERE/'task-bundles'/i/'job.json')['stage']} for i in entries],
     'cpu':read(HERE/'cpu-geometry-validation.json')['checks'],'GLB':'pending root export','runtime':'pending root integration and actual driving/named screenshots/performance'})
if __name__=='__main__':main()
