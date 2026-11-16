"""Freeze current A source geometries and bounded KKAA exterior candidates.

Historical sixunit/modern numbered-campus crosswalk is deliberately unresolved.
No source height tag becomes a surveyed height or unsupported phase assignment.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def cyclic(a,b):
    a,b=[tuple(p) for p in a[:-1]],[tuple(p) for p in b[:-1]]
    if len(a)!=len(b):return None
    for reverse,c in ((False,b),(True,list(reversed(b)))):
        for k in range(len(c)):
            if a==c[k:]+c[:k]:return {'startIndex':k,'reverse':reverse,'allCoordinatesExact':True}


def main():
    r=importlib.util.spec_from_file_location('osm_measure',HERE.parent/'measure_osm.py');measure=importlib.util.module_from_spec(r);r.loader.exec_module(measure)
    fixed=json.loads((HERE/'geofabrik-footprints.json').read_text());manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert sha(ROOT/'data/processed/hangzhou/buildings.geojson')==manifest['sha256']['buildings']==fixed['sourceBuildingsSha256']
    prior=json.loads((HERE.parent/'snapshots/overpass-alibaba-buildings.json').read_text());earlier={(o['type'],o['id']):o for o in prior['elements']}
    metrics={};matches=[];objects=[];groups=[]
    for f in fixed['features']:
        p=f['properties'];obj=earlier[(p['osm_type'],p['osm_id'])];outer,inner,unresolved=measure.rings(obj)
        assert len(outer)==1 and not unresolved
        source=f['geometry']['coordinates'][0];mapped=[cyclic(source[0],outer[0])]
        mapped += [next((m for r in inner if (m:=cyclic(ring,r))),None) for ring in source[1:]]
        assert all(mapped)
        metrics[f['id']]=measure.summarize(obj)
        matches.append({'sourceId':f['id'],'outerAndInnerRingMatches':mapped,'auxiliaryVersion':obj['version'],'auxiliaryTimestamp':obj['timestamp']})
        name=p['name']
        if name=='A9楼':
            groups.append({'sourceId':f['id'],'mappedName':name,'status':'blocker-outside-finite-scope','modeled':False,'excludeBase':False,
                'notes':'Distinct curved public/visitor building is not proved one of KKAA sixoffices; identity, current exterior and height unresolved.'});continue
        kind='office' if name else 'link'
        if name in ('A1楼','A2楼','A3楼'):height,error,courses=26,6,6
        elif name=='A4楼':height,error,courses=26.5,5,6
        elif name:height,error,courses=28.5,5,6
        else:height,error,courses=14.5,4,2
        label=name[:2] if name else 'link-'+str(p['osm_id'])
        objects.append({'sourceId':f['id'],'label':label,'kind':kind,'ringsWGS84':source,
            'height':{'value':height,'unit':'m','basis':'estimated','errorPlusMinusM':error,
                'method':'KKAA completedphoto6–7 facade courses with approximate3.7–4.2m pitch and1–2m roof frame; source mappedlevels6 are not measured floors. Linktwo visible levels above~6m ground clearance; individual heights/photo registration remain approximate.'},
            'courses':courses,'bodyBottomM':6 if kind=='link' else 0,'mappedLevelTag':p['tags'].get('building:levels'),
            'mappedMinLevelTag':p['tags'].get('building:min_level'),
            'historicalUnitNumber':None,'phase':None})
        groups.append({'sourceId':f['id'],'mappedName':name or 'anonymous elevated-link polygon','role':kind,'status':'source-bound-reference-informed-candidate','modeled':True,'excludeBase':True,
            'historicalArchitectUnit':None,'phase':None,'confidence':'mapped identity/plan; facade family byarchitect site and plan comparison, allside/modern phase crosswalk unresolved'})
    save(HERE/'measured-plan.json',{'basis':'measured-from-mapped-OSM, not survey','units':'unscaled metres','method':'WGS84 ECEF→local ENU at footprint centers','features':metrics})
    save(HERE/'footprint-correspondence.json',{'sourcePbfSha256':manifest['source']['sha256'],'sourceExtractSha256':fixed['sourceBuildingsSha256'],
        'auxiliaryOverpassSha256':sha(HERE.parent/'snapshots/overpass-alibaba-buildings.json'),'method':'All outer and inner rings compared exactly allowing cyclicfirstpoint and reversal only; no parcelbuffer exclusion','matches':matches})
    blockers=[{'subject':'historical6offices vs currentA1–A9','blocker':'Architect2013 sixunit/7F project includes multiple connectedplates, while currentA has expansions and namedA1–A9. Officialplan legend numbers are functions, not A buildingnumbers. No automatic1..6 mapping; phase/year/officialname crosswalk pending.'},
        {'sourceIds':['way/456731145'],'subject':'A9 currentcurvedbuilding','blocker':'Public/visitor building identity, architect, modern exterior/height/entrance not confirmed; base object retained.'},
        {'subject':'complete>1km linknetwork','blocker':'Four fixed mappedlinks are finite subset; architect reported>1km entire network and exact sourcefunction/hall/cafe/library mappings not established.'}]
    save(HERE/'object-groups.json',{'mappedResearchObjects':13,'modeledObjects':12,'officeMappedNames':['A1','A2','A3','A4','A5','A6','A7','A8'],
        'modelScope':'Eightcurrentnamedoffice sourcegeometries andfourmappedlinks; not a claimthattheseeightare the2013sixunits','groups':groups,'unresolved':blockers})
    sources=[]
    for s in json.loads((HERE.parent/'sources.json').read_text())['sources']:
        if s['id'] in ('kkaa-taobao-city','alibaba-esg-campus','people-xixi-zones','osm-site-geometries','osm-alibaba-buildings') and s.get('path'):
            sources.append(dict(s,localPath=s['path']))
    sources+=json.loads((HERE/'references/manifest.json').read_text())['sources']
    sources.append({'id':'geofabrik-fixed','url':manifest['source']['sourceUrl'],'publisher':'Geofabrik / OpenStreetMap contributors','sourceDate':manifest['source']['osmReplicationTimestamp'],
        'accessedAt':'2026-10-14','status':'source-verified','localPath':'data/processed/hangzhou/buildings.geojson','sha256':fixed['sourceBuildingsSha256'],
        'license':'ODbL-1.0; © OpenStreetMap contributors','use':'EPSG:4326 outlines/holes/sourceIDs; mapped floor tags are volunteered labels, not metric height evidence'})
    anchor=[120.0212740,30.2815813]
    save(HERE/'source-list.json',{'places':[{'id':'alibaba-a','name':'阿里巴巴西溪 A 区（当前主办公楼/links有限外观）','kind':'building-group',
        'location':{'center':anchor},'sources':sources,'modeling':{'status':'planned','blockers':[]}}]})
    snapshots={s['localPath']:s['sha256'] for s in sources if s.get('sha256') and s.get('localPath')}
    for name in ('geofabrik-footprints.json','object-groups.json','footprint-correspondence.json'):snapshots[str((HERE/name).relative_to(ROOT))]=sha(HERE/name)
    pending=['历史一期六个architectunits与现行A1–A9/各期映射blocker；官方平面功能图例数字不是楼号',
        'A9身份/建筑师/现状外观/高度/入口blocker，未建模或排除；其他停车/商城/总站/服务/历史院落保留基础对象',
        '完整>1km links及剧场/体育/图书/食堂等具体sourcefunction crosswalk blocker',
        '每栋竣工楼高/课程与楼层/海拔地面基准；6levelOSM标签与项目7F口径不直接等同',
        'A1–A4源无内环，屋顶玻璃条仅estimated外观，地面院落/入口/内部分区不当真实可通行结构',
        '全侧折叠幕墙及镂空铝网真实网格/编织尺度、橙白色各link配准、屋顶设备/绿化/栏杆布局',
        'links地面净高/支柱/台阶和地形接合/车辆穿行，四个源link孔洞只代表mapped数据',
        '园内湿地/水面/植被进入基础管线；准确门洞/字牌/夜景灯具与光度',
        'GLB导出、双排除/地面碰撞/道路可到达点/存档与驾驶、昼夜实机三视角、性能']
    observations=[{'kind':'footprint','basis':'measured','unit':'EPSG:4326 / m','value':{'finiteObjects':12,'fixedResearchObjects':13,'mappedNamedOfficeObjects':8,'mappedLinkObjects':4,'parcelWayId':645135612},
        'sourceIds':['geofabrik-fixed','osm-site-geometries'],'uncertainty':'All source outer/inner rings exactlymatch auxiliary snapshot. ECEF→ENU metric measurements of volunteered polygons, absolute mapping accuracy unknown. Current IDs/names do not resolve architect historicaloffice count/phase.'},
        {'kind':'height','basis':'reported','unit':'project floors','value':{'architectProjectFloorMetric':'7F'},'sourceIds':['kkaa-taobao-city'],
        'uncertainty':'2013 project sheet labels7F. Projectlevel metric only; no individual building heights. CurrentOSM tags6levels may differ byfloorcount/date/roofuse; do not autoassign7storeys to A1–A9.'},
        {'kind':'height','basis':'estimated','unit':'m','value':{o['label']:{'heightM':o['height']['value'],'errorPlusMinusM':o['height']['errorPlusMinusM']} for o in objects},
        'sourceIds':['kkaa-ref-MG_6222','kkaa-ref-MG_0643','kkaa-ref-MG_0866','kkaa-ref-Alibaba-section-s1000'],
        'uncertainty':'Manual6–7 facadecourse count with3.7–4.2m officepitch using publishedapproximately20m plate depth/100m length andsourceenvelopes; main26–28.5±5–6m, links14.5±4m withestimated6±2m lowestdeck. Perspective/occlusion and modern expansion crosswalk uncertain. Sections arenot suppliedgeoreferenced height measurements.'},
        {'kind':'orientation','basis':'measured','unit':'degree clockwisefromnorth modulo180','value':{id:m['minimumRotatedEnvelope']['longAxisBearingDegreesClockwiseFromNorthModulo180'] for id,m in metrics.items()},
        'sourceIds':['geofabrik-fixed'],'uncertainty':'Orientedenvelopes measured inWGS84ENU; builduses full sourcepolygon ratherthan allobjects sharingonebearing. Dominant plateedge near17°aboveeast. Link turns/holes retained. Commercialmaps notused.'},
        {'kind':'silhouette','basis':'reported','unit':'architectprojectstructure','value':{'officeUnit':'parallelplates aroundgreen courtyard','reportedPlateDepthM':20,'reportedPlateLengthM':100,'historicalDispersedOfficeCount':6,'links':'bridge-like spaces, entire length>1km','glassFoldDepthM':.3,'eaveDepthM':2},
        'sourceIds':['kkaa-taobao-city'],'uncertainty':'Architect qualitative/approximate2013description; sourcefootprints/currentbuildingnames usedseparately. Current footprint orlesscomplete research scope does not prove allreportedunits/bridges completed inmodel.'},
        {'kind':'facade-and-links','basis':'estimated','unit':'visual / m','value':{'office':'pleatedglass withprojectingwhitefloorfins','links':'orange/silverwovenmesh folded eaves andVtrusses, sourceholesretained','candidateBayM':3.1,'candidateOfficeFinM':1.25,'candidateMeshSampleM':1.6},
        'sourceIds':['kkaa-ref-MG_1636','kkaa-ref-MG_1352','kkaa-ref-MG_0866','kkaa-ref-MG_6222','kkaa-ref-001'],
        'uncertainty':'Realphotos compared in severalground/elevated directions; exactgeolocation of each photo face andweave inventory unknown.0.30mfold/2meave widths reported; modelbay3.1±0.8m and1.25±.6m whitefin visuallyestimated; mesh sampled coarser than real wovenaluminum forbudget, not highfidelity texture.'}]
    evidence={'schemaVersion':1,'placeId':'alibaba-a','scope':'Finite currentA1–A8 source-shaped exterior and4source links, reference-informedKKAA facade family; no fullcurrentA/historicalsixunit/networkcompletion claim',
        'identity':{'status':'confirmed','sourceIds':['geofabrik-fixed','osm-site-geometries','kkaa-taobao-city','alibaba-esg-campus'],
            'notes':'NamedA parcel andcurrentmappednames confirmed; model does not inferhistoricalphase/architectunitnumber. Taobao City evidence kept separate from otherAlibaba HQs.'},
        'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['geofabrik-fixed','osm-site-geometries'],'notes':'Referenceanchor only, notarrival/spawn'},
        'sources':sources,'sourceSnapshots':snapshots,'observations':observations,'blockers':[],'excludedSubscopeBlockers':blockers,'pendingSubscopes':pending,
        'unknownObservations':[{'kind':'currentphase-andheight','status':'unknown','notes':'MappedA1–A8 geometry isknown; allindividualheights/floors/date/architectspecificunitcrosswalk remainestimated/pending.'},
            {'kind':'exactentries-andnight','status':'unknown','notes':'No inferredrealgates ornewlightfixtures, no interactable offices.'}]}
    task=HERE/'task/alibaba-a';save(task/'evidence.json' if task.exists() else HERE/'frozen-evidence.json',evidence)
    spec={'schemaVersion':1,'id':'alibaba-a','cityId':'hangzhou','status':'source-bound-exterior-candidate','scope':evidence['scope'],'anchor':{'lon':anchor[0],'lat':anchor[1]},
        'sourceSnapshotSha256':manifest['source']['sha256'],'coordinateConfigSha256':sha(ROOT/'config/cities/hangzhou.json'),
        'sourceFootprintsPath':str((HERE/'geofabrik-footprints.json').relative_to(ROOT)),'sourceFootprintsSha256':sha(HERE/'geofabrik-footprints.json'),
        'evidencePath':str((task/'evidence.json').relative_to(ROOT)),'evidenceSha256':sha(task/'evidence.json' if task.exists() else HERE/'frozen-evidence.json'),
        'baseBuildingIdsToExclude':[o['sourceId'] for o in objects],'objects':objects,
        'facade':{'bayM':3.1,'foldDepthM':.30,'floorFinM':1.25,'finThicknessM':.15,'roofRailHeightM':1.0,'roofEquipmentHeightM':1.5},
        'links':{'eaveDepthM':2,'eaveSlopeM':2.0,'meshSampleM':1.6,'trussPitchM':9,'columnPitchM':18,'columnSideM':.8,
            'warmSourceIds':['relation/6752593','relation/6752573'],'notes':'Colourregistration estimated fromcentralplaza photos; otherlinks silver, exactallsideassignment pending'},
        'unmappedRooflight':{'widthM':10,'lengthFraction':.52,'basis':'estimated','method':'Non-hole mappedoffice polygons get source-contained glazedroofstrip only, not inventedgroundcourtyard orreportedatriumoutline'},
        'budget':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},
        'groundDatum':{'status':'pending','candidateBaseMetres':0,'lmYUnit':'already-scaledgameunits','notes':'Terrain/roadandlinkdeckdatumverifiedbymainintegrator;layer/minleveltags notmetricheight'},
        'pendingSubscopes':pending,'excludedSubscopeBlockers':blockers,'noPhotoTextures':True,'noNewLights':True}
    save(HERE/'spec.json',spec)
    print('13exactsource matches;12objects frozen;A9/historicalsixunit/fullnetworkblockers retained.')


if __name__=='__main__':main()
