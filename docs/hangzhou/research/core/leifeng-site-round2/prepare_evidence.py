"""Record finite-ground evidence gate separately from blocked full entry."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    spec=read(HERE/'spec.json');measure=read(HERE/'measurements.json');old=read(ROOT/'docs/hangzhou/research/core/leifeng-round2/evidence.json');prefix=HERE.relative_to(ROOT);terrain=spec['terrainInput'];manifest=read(ROOT/terrain['manifestPath']);tile=next(t for t in manifest['sources'] if 'E120' in t['localPath'])
    sources=[copy.deepcopy(s) for s in old['sources'] if s['id'] in ['osm-geofabrik','thupdi-design','tsinghua-leifeng','wgly-leifeng']]
    for s in sources:s['accessedAt']='2026-10-14'
    sources.append({'id':'glo30-v3','url':tile['url'],'publisher':'Copernicus programme / DLR / Airbus / European Union / ESA; existing root terrain-v3 prepared source',
      'accessedAt':'2026-10-14','sourceDate':'AWS Copernicus DEM2021 release, DSM acquired2010–2014/2014–2018, not2026site survey','status':'available; verified localpreparedgrid hashes/read',
      'licenseUrl':tile['licenseUrl'],'localPath':tile['localPath'],'sha256':tile['sha256'],'use':'only filtered ground estimate ±12m; 30mnative/50mreal preparedsamples, no new measured resolution','derivativeNotice':tile['derivativeNotice']})
    refs=[]
    for r in old['referenceImages']:
        if r['id'] not in ['thupdi-south-front','thupdi-lake-day','thupdi-section']:continue
        q=copy.deepcopy(r);q['reviewedAt']='2026-10-14';q['reviewedBy']='Codex child leifeng_candidate';q['observed']=dict(
          **({'approach':'southfront axis two narrow outdoor escalatorbelts flanked by stone stairs, whitebalustrade/darkbasement opening; lower stairs partiallyoccluded byfrontroof/trees','limits':'exactgatewidth, towerdoorWGS/threshold/worldheight, contemporary2026condition unknown'} if r['id']=='thupdi-south-front' else
             {'hill':'forested hill belowtower andreal WestLakeshore inforeground','limits':'trees obscureterrain/plaza, capturedateunknown, no 3Dground survey or shorewall inferred'} if r['id']=='thupdi-lake-day' else
             {'section':'protectivebasement level relationships/terraces inarchitecturalrelative datum','limits':'architectural0 andnegativebasementlevels notEGM2008 andnotGLOdatum; do notfreezeexactexternalthreshold'}))
        refs.append(q)
    write(HERE/'photo-review.json',{'reviewedBy':'Codex child leifeng_candidate','reviewedAt':'2026-10-14','images':refs,'actualLocalImagesViewed':['<TEMP>/leifeng-research/1782-433c3093-3e40-467a-b56a-c146ed350aee.jpg','<TEMP>/leifeng-research/1782-1a0c8347-9121-473f-ac1c-d657ec4624d3.jpg','<TEMP>/leifeng-research/1782-ff648dd2-a130-499a-9eac-2c5139ac1019.jpg'],
      'license':'unknown; reference-only; no textures copied/bundled','operatorStatus':'HTTPSpublic endpoints certificateverification failed; actual route/gate map unavailable, no SSLbypass used','notClaimed':['all sides/currententrymapping','actualoperator entrance approval','stairs/elevator operation','no wall penetration/waterfalls acceptance']})
    snapshots={str(prefix/f):sha(HERE/f) for f in ['spec.json','measurements.json','fixed-site-features.geojson','photo-review.json','operator-fetches.json','bridge-profile-recheck.json']}
    snapshots.update({terrain['manifestPath']:terrain['manifestSha256'],terrain['groundPath']:terrain['groundSha256'],spec['towerPlacement']['frozenSpecPath']:spec['towerPlacement']['frozenSpecSha256'],'scripts/landmarks/leifeng_pagoda.py':spec['towerPlacement']['frozenModuleSha256']})
    center=[spec['anchor']['lon'],spec['anchor']['lat']]
    write(HERE/'catalog.json',{'schemaVersion':1,'cityId':'hangzhou','sources':sources,'places':[
      {'id':'leifeng-site','name':'雷峰夕照映射场地有限地形与通道候选','kind':'finite park hill terrain exterior','location':{'center':center},'modeling':{'blockers':[]}},
      {'id':'leifeng-site-entry','name':'雷峰塔完整广场/门洞/入口与安全通达','kind':'full site entry and plaza','location':{'center':center},'modeling':{'blockers':spec['blockers']}}]})
    args=[str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/landmark_tasks.py'),'generate','--city-id','hangzhou','--source',str(prefix/'catalog.json'),'--agent','codex-leifeng-candidate','--output',str(prefix/'task-bundles')]
    r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr;write(HERE/'task-generation-result.json',json.loads(r.stdout))
    finite={'schemaVersion':1,'placeId':'leifeng-site','cityId':'hangzhou','scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','thupdi-design']},'location':{'crs':'EPSG:4326','center':center,'status':'confirmed','sourceIds':['osm-geofabrik']},
      'sources':sources,'referenceImages':refs,'photosBundled':False,'observations':[
        {'kind':'extent','value':{'parkId':'way/975360504','mapAreaM2':measure['sourceParkAreaM2'],'dryMaskAreaM2':measure['dryMaskAreaM2'],'waterIds':spec['sourceWaterIds'],'sourcePaths':[p['id'] for p in spec['sourcePaths']]},'unit':'physical metres/m²','basis':'measured','sourceIds':['osm-geofabrik'],'uncertainty':'measured map-derivedplan/clip only, OSMapprox±5m; park polygon is not a surveyed hillfootboundary or fullplaza.2mshorepadding is conservative gameproposal, not measured shorewall'},
        {'kind':'elevation_profile','value':{'towerEstimatedGroundEgm2008M':measure['towerGroundEgm2008EstimatedM'],'peakEstimatedGroundEgm2008M':measure['peakGroundEgmEstimatedM'],'sourceTerrainTriangles':measure['sourceTerrainTriangles'],'mainLiftEndpointGroundEstimatesM':measure['mainLiftHeightEndpointsM']},'unit':'physical metres aboveEGM2008','basis':'estimated','sourceIds':['glo30-v3'],'uncertainty':'GLO30source30m, prepared50mreal; 3×3 morphologicalmin/max/mean still broadcanopy/roof/steepslopebias.±12m heuristic envelope, not statistical survey confidence; stairs/plaza/movingstairsfinishedlevels unknown'},
        {'kind':'silhouette','value':'originalclip-triangulated lowhill ground estimate in mappedpark/nearshore, mapped6paths, twoSTATICmid-axisbelts plusflankingstairs andestimatednarrowbaseapron; noipsoid/no lakeplane','basis':'estimated','sourceIds':['osm-geofabrik','glo30-v3','thupdi-design'],'uncertainty':'designersouthfront/lakephotos capturedateunknown andpartlyoccluded.12±3m approachwidth/3±2m apron/1.1±.3m representativeguardrails estimated; staticcounts andverticalgeometry not precise finishedsite or electromechanicalsimulation'}],
      'estimatedParameters':spec['estimates'],'blockers':[],'pendingSubscopes':[{'scope':'fullplaza/entrance/doors/elevators/actualsafearrival','job':str(prefix/'task-bundles/leifeng-site-entry/job.json'),'status':'blocked','blockers':spec['blockers']}],
      'sourceSnapshots':snapshots,'modelled':False,'verified':False}
    blocked=copy.deepcopy(finite);blocked.update(placeId='leifeng-site-entry',scope='Complete current publicgate/plaza/threshold/inside connection and physicallysafe arrival to frozen tower',blockers=spec['blockers'],pendingSubscopes=[],observations=[
      {'kind':'footprint','value':{'sourceMainLift':'way/340652169','upperNode':'3479012380','gapToTowerMetres':measure['gapToTowerM'],'knownMappedTower':'way/229726934'},'unit':'physicalmetres','basis':'measured','sourceIds':['osm-geofabrik'],'uncertainty':'source-derived gap14.116m and no connectedupperway; no syntheticedge added'},
      {'kind':'height','value':None,'basis':'unknown','sourceIds':[],'uncertainty':'actual current finishedground/threshold/steps/elevatorheight notsurveyed; GLOground cannot certify it'},
      {'kind':'orientation','value':'main source3479012381 south to3479012380 north; exactactualgate/inside direction notfrozen','basis':'measured','sourceIds':['osm-geofabrik'],'uncertainty':'mapline direction only, no currentoperatorgatepoint'},
      {'kind':'silhouette','value':'sourcefront actual two escalatorbelts/flankingstairs/visible darkbasementportal, door dimension/semantics unresolved','basis':'reported','sourceIds':['thupdi-design'],'uncertainty':'capturedateunknown/trees andfrontroof occlude lowerentry, no contemporaryall-sides/full access model'}])
    write(HERE/'evidence.json',finite);write(HERE/'entry-blockers.json',blocked)
    results=[]
    for ident,ev in [('leifeng-site',finite),('leifeng-site-entry',blocked)]:
        folder=HERE/'task-bundles'/ident;job=read(folder/'job.json');job['ownership']['workerFiles']=['scripts/landmarks/leifeng_site.py'];job['ownership']['workerDirectories']=[str(prefix)];job['ownership']['integrationOwner']='root'
        job['budget']['maxTriangles']=18000;job['budget']['maxBytes']=8388608;job['budget']['reason']='finite source terrain/site candidate; CPU1279 only, actualGLB/runtime stillpending';write(folder/'job.json',job);write(folder/'evidence.json',ev)
        model=read(folder/'model.json');model.update(sourceModule='scripts/landmarks/leifeng_site.py',sourceModuleSha256=sha(ROOT/'scripts/landmarks/leifeng_site.py'),sourceSpec=str(prefix/'spec.json'),sourceSpecSha256=sha(HERE/'spec.json'),artifactPath=None,sha256=None,buildCommand=None,
          accuracyClaim='finite estimated source-ground/site preview, complete safe entrance blocked' if ident=='leifeng-site' else 'blocked entry; no accepted entrance geometry',estimatedParameters=spec['estimates']);write(folder/'model.json',model)
        r=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/landmark_tasks.py'),'check','--job',str(folder/'job.json'),'--stage','evidence-ready','--record'],cwd=ROOT,capture_output=True,text=True);out=json.loads(r.stdout);write(folder/'evidence-ready-result.json',{'exitCode':r.returncode,'result':out});results.append({'id':ident,'exitCode':r.returncode,'recordedStage':out['recordedStage'],'currentStage':out['currentStage'],'evidenceErrors':out['errors']['evidence-ready']});print(json.dumps(results[-1],ensure_ascii=False))
    write(HERE/'stage-status.json',{'jobs':results,'cpuCandidate':{'triangles':read(HERE/'cpu-geometry-validation.json')['triangleCountBeforeExport'],'materials':read(HERE/'cpu-geometry-validation.json')['materials']},'BlenderGLB':'pending','safeArrival':'blocked; original towerdoor/fullprofile/currentoperatorentry unknown','rootIntegrationAndRuntime':'pending','bridgeProfileReadonlyCheck':read(HERE/'bridge-profile-recheck.json')})
if __name__=='__main__':main()
