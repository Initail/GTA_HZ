"""Prepare only this standalone estimated Fuxing alignment candidate."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
from datetime import datetime,timezone
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];OLD=ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2'
sys.path.insert(0,str(ROOT/'scripts'))
MODULE=ROOT/'scripts/landmarks/fuxing_alignment.py'
def read(p):return json.loads(p.read_text())
def write(name,v):(HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_module():
    loader=importlib.util.spec_from_file_location('fuxing_alignment_inputs',MODULE);m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m);return m


def inputs():
    m=load_module();fit=m.axis_evidence();full,bridge=m._original();center=fit['candidateCenterWGS84']
    spec={'schemaVersion':1,'id':'fuxing-alignment','cityId':'hangzhou',
      'scope':'Standalone original1376m Fuxing structural main bridge with estimated paired-source structural-axis correction only. Original widths/members/vertical estimates retained; complete roadway envelope or navigation not accepted',
      'anchor':{'lon':center[0],'lat':center[1]},'candidateAxis':{'centerWGS84':center,'radiansEastCCW':fit['candidateAxisRadiansEastCCW']},
      'sourceModule':str(m.ORIGINAL_MODULE.relative_to(ROOT)),'sourceModuleSha256':m.SOURCE_SHA,'sourceSpec':str(m.ORIGINAL_SPEC.relative_to(ROOT)),'sourceSpecSha256':m.SPEC_SHA,
      'sourceCollisionModule':str(m.COLLISION_MODULE.relative_to(ROOT)),'sourceCollisionModuleSha256':m.COLLISION_SHA,
      'sourcePbfSha256':full['sourcePbfSha256'],'sourceFeatureSubset':str((OLD/'fixed-bridge-features.geojson').relative_to(ROOT)),'sourceFeatureSubsetSha256':sha(OLD/'fixed-bridge-features.geojson'),
      'axisInference':{'basis':'estimated map-derived paired-carriageway midpoint fit','fitWindowM':[-500,500],'stationSpacingM':10,
        'shiftTransverseM':fit['selectedUpperPairFit']['transverseShiftM'],'angleDeltaDegrees':fit['selectedUpperPairFit']['angleDeltaDegrees'],
        'upperPairMaxResidualM':fit['selectedUpperPairFit']['maxResidualM'],'lowerOuterPairCrossCheckShiftM':fit['lowerOuterPairCrossCheck']['transverseShiftM'],
        'uncertainty':fit['placementAllowance'],'absoluteMapAccuracy':fit['absoluteMapAccuracy']},
      'widthPolicy':{'smallM':26.4,'largeM':32,'basis':'reported; Chen Baochun2008 p98 text; both decks same width by span type','error':'reported source value, no current as-built width survey','changeFromOriginal':0},
      'heightPolicy':{'upperRelativeWaterM':22,'lowerRelativeWaterM':12,'basis':'original estimate retained','error':'upper±6m lower±4m separation±2m; tide/absolute datum unknown','waterDisplayBaseYGame':.9,'lmYAlreadyGameUnits':True},
      'minimumIdentifiableObjectBoundary':{'centralSourceConsistentIntervalM':[-416.9,416.9],'centralLengthEstimatedM':833.8,'centralRecognizableStructure':'two190m large arches +five central85m small arches, double deck; original estimated hinge stations, not measured boundary',
        'wholeMainCandidateIntervalM':[-688,688],'mainLengthReportedM':1376,'wholeMainRecognizableStructure':'two190m large arches +nine85m small arches; near-end road alignment remains unresolved',
        'planStationUncertainty':'original arch/pier stations±35m; no bridge-edge/abutment survey','excluded':'full source approach roads/interchanges, bank elevators/platforms and measured longitudinal grades'},
      'budget':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},'baseBuildingIdsToExclude':[],
      'roadsRelocated':False,'roadTopPlanes':False,'renderWater':False,'navigationAccepted':False,
      'pending':['remaining northern lower source-road mismatch after axis correction','actual lane/road-edge widths and source placement accuracy','reported-width applicability to cantilevers/viewing decks and approaches',
        'measured absolute height/longitudinal grade/bank abutments','actor clearance and road-specific permissions','parent export/placement/replacement/collisions','in-game views/night/browser/performance']}
    write('spec.json',spec);write('axis-fit-evidence.json',fit)
    original_ev=read(OLD/'task-bundles/qiantang-bridges/evidence.json');keep={'osm-geofabrik','fuxing-paper','fuxing-gov','f1','fgovphoto','binjiang-gazette'}
    sources=[s for s in original_ev['sources'] if s['id'] in keep]
    sources.append({'id':'osm-way-semantics','url':'https://wiki.openstreetmap.org/w/index.php?title=Way&oldid=3045544','publisher':'OpenStreetMap community primary mapping documentation','accessedAt':'2026-10-16','sourceDate':'2026-05-31',
      'status':'read via web tool','license':'CC BY-SA2.0; reference paraphrase only','use':'a linear highway is a generalized main-lane/carriageway centreline, excludes sidewalk and does not encode bridge deck edges; not proof of these specific source ways position accuracy'})
    catalog={'cityId':'hangzhou','places':[{'id':'fuxing-alignment','name':'复兴大桥有限主桥轴线修正候选','kind':'finite bridge axis hypothesis and structural candidate','location':{'center':center},'modeling':{'blockers':[]}},
      {'id':'fuxing-complete-alignment','name':'复兴大桥全部源道路实体及引桥通行匹配','kind':'complete bridge road/deck match and passage','location':{'center':center},'modeling':{'blockers':['all-way source envelopes, approaches, accurate edge/height and physical passage still unresolved']}}],
      'sources':sources};write('catalog.json',catalog)
    command=[sys.executable,str(ROOT/'scripts/landmark_tasks.py'),'generate','--city-id','hangzhou','--source',str(HERE/'catalog.json'),'--output',str(HERE/'task-bundles'),'--agent','codex-leifeng-candidate'];result=subprocess.run(command,text=True,capture_output=True,cwd=ROOT)
    write('task-generation-result.json',{'command':command,'exitCode':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==0
    for ident in ['fuxing-alignment','fuxing-complete-alignment']:
        job_path=HERE/'task-bundles'/ident/'job.json';job=read(job_path);job['ownership']['workerFiles']=[str(MODULE.relative_to(ROOT))];job['ownership']['workerDirectories']=[str(HERE.relative_to(ROOT))];job['ownership']['integrationOwner']='root';job_path.write_text(json.dumps(job,ensure_ascii=False,indent=2)+'\n')
    photos=read(OLD/'photo-review.json');reviewed=[]
    for photo in photos['photos']:
        if photo['id'] not in ['f1','fgovphoto']:continue
        p=dict(photo);p['alignmentReviewAt']='2026-10-16';p['alignmentReviewBy']='Codex child leifeng_candidate';p['alignmentUse']='upper central divider and overall two-deck symmetric structure visible; no WGS georeferencing or deck-edge survey derived';reviewed.append(p)
    write('source-review.json',{'reviewedBy':'Codex child leifeng_candidate','reviewedAt':'2026-10-16',
      'primaryWidthDocument':{'url':next(s['url'] for s in sources if s['id']=='fuxing-paper'),'temporaryPath':'<TEMP>/qiantang-bridges-research/fuxing-paper.pdf','sha256':sha(Path('<TEMP>/qiantang-bridges-research/fuxing-paper.pdf')),
        'read':'cached original PDF p98 text and figure8 manually inspected; live web fetch timed out2026-10-16','finding':'upper/lower same widths,26.4m small arches/32m large; no support to widen an entire bridge simply to contain road lines',
        'notUsed':'adjacent case studies in same paper are other bridges, not Fuxing dimensions; figure8 bank-end grade annotations are not a surveyed current road profile'},
      'photos':reviewed,'additionalWebReads':[{'url':'https://www.hzzx.gov.cn/zxyw/content/2026-09/20/content_9311674.htm','status':'web reread succeeded2026-10-16','support':'1376m, double deck,2large9small arches, six upper lanes; photo not an absolute coordinate survey'},
        {'url':'https://wiki.openstreetmap.org/w/index.php?title=Way&oldid=3045544','status':'web read succeeded2026-10-16','support':'road centerline versus deck-edge distinction'}],
      'inputDataUncertainty':'fixed source numeric values exact; original individual mapping dates/source imagery/placement/width tags unknown, absolute positional accuracy unknown','noPhotosBundled':True})


def evidence():
    spec=read(HERE/'spec.json');fit=read(HERE/'axis-fit-evidence.json');cpu=read(HERE/'cpu-validation.json');catalog=read(HERE/'catalog.json');center=[spec['anchor']['lon'],spec['anchor']['lat']]
    snapshots={str(MODULE.relative_to(ROOT)):sha(MODULE),spec['sourceModule']:spec['sourceModuleSha256'],spec['sourceSpec']:spec['sourceSpecSha256'],spec['sourceCollisionModule']:spec['sourceCollisionModuleSha256'],spec['sourceFeatureSubset']:spec['sourceFeatureSubsetSha256'],str((HERE/'spec.json').relative_to(ROOT)):sha(HERE/'spec.json')}
    obs=[{'kind':'footprint','value':{'mainLengthM':1376,'reportedSmallWidthM':26.4,'reportedLargeWidthM':32,'axisShiftM':fit['selectedUpperPairFit']['transverseShiftM'],'sourceRoadsModified':'none'},'basis':'estimated','unit':'physical metres',
       'sourceIds':['osm-geofabrik','fuxing-paper'],'uncertainty':fit['placementAllowance']+'; width source reported2008, current as-built edges unmeasured'},
      {'kind':'height','value':{'upperRelativeWaterM':22,'lowerRelativeWaterM':12,'waterBaseGame':.9},'basis':'estimated','unit':'physical metres except explicitly game datum','sourceIds':['fuxing-paper','f1','fgovphoto'],'uncertainty':'original source estimate retained, upper±6m/lower±4m; no measured tide or vertical datum'},
      {'kind':'orientation','value':{'radiansEastCCW':fit['candidateAxisRadiansEastCCW'],'correctionDegrees':fit['selectedUpperPairFit']['angleDeltaDegrees'],'samplingWindowM':[-500,500]},'basis':'estimated','unit':'radians/degrees as named','sourceIds':['osm-geofabrik','osm-way-semantics'],
       'uncertainty':'sample-window sensitivity explicitly axis-fit-evidence.json; absolute OSM/axis survey accuracy unknown, ±5m game adaptation allowance is not confidence interval'},
      {'kind':'silhouette','value':'original two190m large/nine85m small blue arches and double deck retained; rigid frame correction, no source width/member changes','basis':'reported','unit':'structural arrangement','sourceIds':['fuxing-paper','fuxing-gov','f1','fgovphoto'],'uncertainty':'finite original exterior only, original member/height/station estimates retained; not whole bridge arrival/current-all-side acceptance'}]
    ev={'schemaVersion':1,'placeId':'fuxing-alignment','cityId':'hangzhou','scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','fuxing-paper','fuxing-gov']},'location':{'crs':'EPSG:4326','center':center,'status':'confirmed','sourceIds':['osm-geofabrik'],'notes':'map-derived aggregate structure anchor inside fixed bridge source; estimated, not field geodetic centre'},
      'sources':catalog['sources'],'observations':obs,'sourceSnapshots':snapshots,'blockers':[],
      'pendingSubscopes':spec['pending'],'absoluteMapAccuracy':'unknown','navigationAccepted':False,'modelledAccepted':False,'referenceImagesPublished':False,
      'machineEvidence':['axis-fit-evidence.json','cpu-validation.json','source-alignment-audit.json','all-way-comparison.json','negative-controls.json']}
    write('task-bundles/fuxing-alignment/evidence.json',ev)
    full=json.loads(json.dumps(ev));full['placeId']='fuxing-complete-alignment';full['scope']='All fixed upper/lower source roads and approach structures physically matched with accurate edges/grades/actor clearance'
    full['blockers']=[f"new candidate still has {cpu['remainingMainMismatchNodeOccurrences']} in-main way/node mismatches and {cpu['remainingMainMismatchSamples']} in-main sample mismatches on other source road(s)",
      'actual source-carriageway placement and road-edge widths unavailable; cannot assign remaining mismatch to mapping error or missing physical widening/ramp',
      'full approach roads exceed finite1376m main structure; precise banks/abutments/grades not reconstructed','absolute vertical datum/real actor clearance/current per-way permissions/browser/performance pending']
    write('task-bundles/fuxing-complete-alignment/evidence.json',full)
    for ident in ['fuxing-alignment','fuxing-complete-alignment']:
        path=HERE/'task-bundles'/ident/'model.json';value=read(path);value.update(sourceModule=str(MODULE.relative_to(ROOT)),sourceModuleSha256=sha(MODULE),
          buildCommand='.venv/bin/python -B docs/hangzhou/research/core/fuxing-alignment-round1/validate_candidate.py',accuracyClaim='reference-informed estimated rigid main-structure axis correction; CPU candidate only, no new GLB',estimatedParameters=spec['pending']);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['inputs','evidence']);args=parser.parse_args();globals()[args.phase]()
