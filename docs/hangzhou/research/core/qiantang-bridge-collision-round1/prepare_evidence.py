"""Write this independent adapter task's inputs/evidence; no shared edits."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
ORIGINAL=ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2'
MODULE=ROOT/'scripts/landmarks/qiantang_bridge_collision.py'
FROZEN=ROOT/'scripts/landmarks/qiantang_bridges.py'


def inputs():
    original=read(ORIGINAL/'spec.json');evidence=read(ORIGINAL/'task-bundles/qiantang-bridges/evidence.json')
    spec={'schemaVersion':1,'id':'qiantang-bridge-collision','cityId':'hangzhou',
      'scope':'CPU collision envelope adapter for the exact frozen rendered three-bridge main structures; source decks are separate surfaces and known gaps stay blocked from acceptance',
      'anchor':original['anchor'],'sourceModule':'scripts/landmarks/qiantang_bridges.py','sourceModuleSha256':sha(FROZEN),
      'sourceSpec':str((ORIGINAL/'spec.json').relative_to(ROOT)),'sourceSpecSha256':sha(ORIGINAL/'spec.json'),
      'associatedAppearanceArtifact':'artifacts/cities/hangzhou/landmarks/qiantang-bridges-v1/qiantang-bridges.glb',
      'associatedAppearanceArtifactSha256':'cb88432457045d60fe51f424ec4b3d766f4465eedd3779895c8422ae506676fd',
      'waterDisplayHeightGame':{'value':.9,'basis':'estimated parent display datum','uncertainty':'not a surveyed water/ground elevation; original photo deck estimates ±5m real height retained',
        'method':'exact source appearance delivery baseYGame; lm.y passed unchanged in game units'},
      'interfaces':{'ground_footprints':'solid EN polygons with explicit minYGame/maxYGame; bridges decks excluded',
        'walk_surfaces':'road top rectangles; mode rail explicitly separate',
        'source_road_profiles':'15 source road profiles and finite actual deck regions; estimated opt-in required',
        'surface_at_game':'one way plus mode; height None on actual coverage/height mismatch',
        'profile_geometry_audit':'source nodes and <=20m samples with actual deck gaps/height differences',
        'collision_report':'nonempty source counts, bounds and pending collision acceptance'},
      'boundaryMethod':'replay original isolated B.face; tube ring vertices from actual emitted quads; pylon consecutive emitted rows; convex EN projection x explicit Y interval. Inclined tubes subdivided <=4game m horizontal and <=1.2game m rise; original3D vertices retained',
      'contactUncertainty':'conservative projected prisms can overblock sloped/curved members; no precise actor sweep or measured clearance claim',
      'unmodelledKinds':['bank-abutments','approach structural supports/sloped deck slabs','surveyed actor-clearance portals'],
      'missingGeometryNotTrafficClosure':True,'baseBuildingIdsToExclude':[],
      'budget':{'status':'provisional CPU envelope budget','maxEnvelopes':10000,'newRenderedTriangles':0,'sourceRenderedTriangles':24148,'sourceMaterials':5,'runtimePerformance':'pending'},
      'pending':['bridge source road core/approach curve mismatch','absolute deck/terrain/water datum','parent surface/slab contacts and source-way actor selection',
        'fine height-aware collision narrow phase','precise bank abutments','actor radii/height and lane permissions','real driving/walking no walls/falls','in-game views/browser/night/performance']}
    write(HERE/'spec.json',spec)
    center=[original['anchor']['lon'],original['anchor']['lat']]
    places=[{'id':'qiantang-bridge-collision','name':'钱塘江三桥现有模型实体碰撞边界适配','kind':'finite bridge mesh collision adapter','location':{'center':center},'modeling':{'blockers':[]}},
      {'id':'qiantang-bridge-passage','name':'钱塘江三桥完整桥路通行与岸台衔接','kind':'bridge complete passage and clearance','location':{'center':center},
       'modeling':{'blockers':['complete source approaches/curves are absent from frozen finite structural model; no measured deck profile, bank abutments or runtime actor clearance']}}]
    write(HERE/'catalog.json',{'cityId':'hangzhou','places':places,'sources':evidence['sources']})
    command=[sys.executable,str(ROOT/'scripts/landmark_tasks.py'),'generate','--city-id','hangzhou','--source',str(HERE/'catalog.json'),'--output',str(HERE/'task-bundles'),'--agent','codex-leifeng-candidate']
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);write(HERE/'task-generation-result.json',{'command':command,'exitCode':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==0
    for ident in ['qiantang-bridge-collision','qiantang-bridge-passage']:
        job=HERE/'task-bundles'/ident/'job.json';value=read(job);value['ownership']['workerFiles']=[str(MODULE.relative_to(ROOT))];value['ownership']['workerDirectories']=[str(HERE.relative_to(ROOT))];value['ownership']['integrationOwner']='root';write(job,value)


def evidence():
    cpu=read(HERE/'cpu-validation.json');original=read(ORIGINAL/'task-bundles/qiantang-bridges/evidence.json');spec=read(HERE/'spec.json');summaries=read(HERE/'source-profile-summary.json')
    center=[spec['anchor']['lon'],spec['anchor']['lat']]
    snapshots={str(FROZEN.relative_to(ROOT)):sha(FROZEN),str((ORIGINAL/'spec.json').relative_to(ROOT)):sha(ORIGINAL/'spec.json'),
      spec['associatedAppearanceArtifact']:spec['associatedAppearanceArtifactSha256'],str(MODULE.relative_to(ROOT)):sha(MODULE),str((HERE/'spec.json').relative_to(ROOT)):sha(HERE/'spec.json')}
    values={
      'footprint':{'solidEnvelopes':cpu['solidEnvelopeCount'],'piers':41,'pierCrossbeams':11,'roadDeckRegions':48,'railDeckRegions':1,'boundaryAPI':'explicit polygons plus minYGame/maxYGame; no bridge slab building obstacle'},
      'height':{'minGame':cpu['actualReplayBoundsGameENU']['min'][2],'maxGame':cpu['actualReplayBoundsGameENU']['max'][2],
        'roadNominalGame':{'qiantangUpper':12.3,'fuxingUpper':14.1,'fuxingLower':8.1,'zhijiangSingle':11.7},'railNominalGame':5.88,'displayWaterGame':.9},
      'orientation':'exact original CPU B frame, per-bridge source axis, original GLB float32 ENU vertex sets match (GLB north sign restored)',
      'silhouette':{'solidKinds':cpu['solidKinds'],'portalSections':84,'portalVoids':'original 2 red portal centres remain open at deck probe; no merged pylon hull','voidUnderPairedPier':'separate Fuxing concrete legs retained'}}
    observations=[{'kind':kind,'value':value,'basis':'reported','unit':'candidate mesh game units; not field survey',
      'method':'actual hash-bound B.face replay and exported float32 geometry comparison; original reference estimates remain estimates',
      'sourceIds':['osm-geofabrik','qiantang-school','fuxing-paper','zhijiang-paper'],'uncertainty':'candidate boundary numerical replay exact to float32; hull x height is conservative and contact precision unknown; real-world original deck ±5m/position/member estimates retained'} for kind,value in values.items()]
    scope='Finite adapter evidence for actual exported candidate solid boundaries only; full bridge physical passage, measured elevations and approach geometry excluded'
    ev={'schemaVersion':1,'placeId':'qiantang-bridge-collision','cityId':'hangzhou','scope':scope,
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','qiantang-school','fuxing-gov','zhijiang-paper']},
      'location':{'crs':'EPSG:4326','center':center,'status':'confirmed','sourceIds':['osm-geofabrik'],'notes':'aggregate original first-bridge anchor; source way/node positions exact fixed snapshot, pier placements estimated'},
      'sources':original['sources'],'observations':observations,'sourceSnapshots':snapshots,'blockers':[],
      'sourcePhotoReview':str((ORIGINAL/'photo-review.json').relative_to(ROOT)),
      'machineEvidence':{'cpuValidation':str((HERE/'cpu-validation.json').relative_to(ROOT)),'profileGeometryAudit':str((HERE/'source-profile-geometry-audit.json').relative_to(ROOT))},
      'estimated':spec['waterDisplayHeightGame'],'pendingFullObject':spec['pending'],'noImagesBundled':True,'navigationAccepted':False,'runtimeCollisionAccepted':False}
    write(HERE/'task-bundles/qiantang-bridge-collision/evidence.json',ev)
    full=json.loads(json.dumps(ev));full['placeId']='qiantang-bridge-passage';full['scope']='Full bank-to-bank physical roadway / lower rail separation, measured ramps, solid abutments and actor clearance'
    full['blockers']=[f"actual frozen structure leaves {cpu['missingSourceNodes']} source road way/node occurrences ({cpu['missingUniqueSourceNodeCount']} unique nodes) and {cpu['missingSourceSamples']} interpolation samples uncovered; not a traffic-closure claim",
      'bank-abutments and complete sloped approach structural decks absent from original build','absolute node/deck/water/terrain datum still estimated and unmeasured',
      'fine runtime contact, slab underside, actor clearance/lane permissions and genuine no-wall/no-fall physical traversal not tested']
    full['observations']=[o for o in full['observations'] if o['kind']!='height']+[{'kind':'height','value':None,'basis':'unknown','sourceIds':[],'uncertainty':'measured absolute profile and complex ramp clearances unavailable'}]
    write(HERE/'task-bundles/qiantang-bridge-passage/evidence.json',full)
    for ident in ['qiantang-bridge-collision','qiantang-bridge-passage']:
        path=HERE/'task-bundles'/ident/'model.json';value=read(path);value.update(sourceModule=str(MODULE.relative_to(ROOT)),sourceModuleSha256=sha(MODULE),
          accuracyClaim='actual frozen rendered mesh envelope CPU adapter; associated original GLB does not prove runtime collision',
          buildCommand='.venv/bin/python -B docs/hangzhou/research/core/qiantang-bridge-collision-round1/validate_candidate.py',
          estimatedParameters=spec['pending']);write(path,value)
    write(HERE/'geometry-scope.json',{'cpuChecks':cpu['checks'],'actualSourceHashes':{k:snapshots[k] for k in snapshots},
      'sourceRoadProfiles':summaries['profiles'],'currentEstimatedDatumGameY':.9,'measuredElevations':False,
      'acceptance':{'finiteAdapterBoundaries':'CPU audited','completeBridgeCollision':'pending','navigation':False,'runtime':False,'bankAbutments':'missing'}})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['inputs','evidence']);args=p.parse_args();globals()[args.phase]()
