"""Reproduce frozen finite B-campus evidence/spec from primary and fixed sources."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def cyclic(a,b):
    a,b=[tuple(p) for p in a[:-1]],[tuple(p) for p in b[:-1]]
    if len(a)!=len(b):return None
    for reverse,c in ((False,b),(True,list(reversed(b)))):
        for k in range(len(c)):
            if a==c[k:]+c[:k]:return {'startIndex':k,'reverse':reverse,'allCoordinatesExact':True}


def main():
    r=importlib.util.spec_from_file_location('osm_measure',HERE.parent/'measure_osm.py')
    measure=importlib.util.module_from_spec(r);r.loader.exec_module(measure)
    fixed=json.loads((HERE/'geofabrik-footprints.json').read_text());manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert sha(ROOT/'data/processed/hangzhou/buildings.geojson')==manifest['sha256']['buildings']==fixed['sourceBuildingsSha256']
    earlier=json.loads((HERE.parent/'snapshots/overpass-alibaba-buildings.json').read_text());earlier={e['id']:e for e in earlier['elements'] if e['type']=='way'}
    metrics={};matches=[]
    for f in fixed['features']:
        id=f['properties']['osm_id'];obj=earlier[id];outer,inner,unresolved=measure.rings(obj);assert len(outer)==1 and not inner and not unresolved
        match=cyclic(f['geometry']['coordinates'][0][0],outer[0]);assert match
        metrics[f['id']]=measure.summarize(obj)
        matches.append({'sourceId':f['id'],'fixedPolygonMatchesAuxiliary':match,'version':obj['version'],'timestamp':obj['timestamp']})
    roles={
        721:('visitor','southwest-visitor',18.5,5,0,4),
        722:('west','west-south-arm',25.4,7,6,4),723:('west','west-north-folded-arm',34,8,6,6),
        724:('west','west-inner-folded-arm',34,8,6,6),725:('west','west-junction-north',19.6,6,6,3),
        726:('west','west-junction-south',14.4,5,6,2),727:('west','west-southwest-link-arm',25.4,7,6,4),
        728:('west','west-southeast-link-arm',25.4,7,6,4),729:('west','west-short-connector',14.4,5,6,2),
        730:('west','west-central-junction',19.6,6,6,3),
        731:('east','east-north-folded-arm',34,8,6,6),732:('east','east-west-arm',34,8,6,6),
        733:('east','east-south-folded-arm',34,8,6,6),734:('east','east-inner-short-arm',25.4,7,6,4),
        735:('east','east-north-junction',19.6,6,6,3),736:('east','east-middle-junction',14.4,5,6,2),
        737:('east','east-southeast-junction',19.6,6,6,3),738:('east','east-outer-short-arm',25.4,7,6,4),
        739:('west','visitor-to-west-junction',14.4,5,6,2)}
    active=[];groupmap=[]
    for f in fixed['features']:
        suffix=f['properties']['osm_id']-1363020000
        if suffix in (741,742):
            groupmap.append({'sourceId':f['id'],'group':'central-unresolved','role':'mapped roof only, functional/height crosswalk unresolved','status':'blocker-outside-finite-scope','modeled':False,'excludeBase':False});continue
        if suffix in (740,743):
            group='west' if suffix==740 else 'east';role=group+'-stepped-green-roof'
            entry={'sourceId':f['id'],'label':role,'group':group,'kind':'garden-roof',
                'ringsWGS84':f['geometry']['coordinates'][0],'height':{'value':5.8,'unit':'m','basis':'estimated','errorPlusMinusM':2.5,
                    'method':'Completed NBBJ rooftop/photo person-scale and one high public storey. OSM layer1 is only ordering, not elevation.'},
                'bodyBottomM':5.0,'courses':1}
        else:
            group,role,h,error,bottom,courses=roles[suffix]
            entry={'sourceId':f['id'],'label':role,'group':group,'kind':'visitor' if suffix==721 else ('junction' if suffix in (725,726,729,730,735,736,737,739) else 'office-arm'),
                'ringsWGS84':f['geometry']['coordinates'][0],
                'height':{'value':h,'unit':'m','basis':'estimated','errorPlusMinusM':error,
                    'method':'Manual visible facade courses4–6 plus approximately6m public/pilotis level, 4.2–4.7m office pitch and1m parapet, compared to mapped20–40m arm widths. No verified individual storey/height or80m extrapolation.'},
                'bodyBottomM':bottom,'courses':courses}
        active.append(entry)
        groupmap.append({'sourceId':f['id'],'group':entry['group'],'role':entry['label'],'kind':entry['kind'],'status':'reference-informed-candidate','modeled':True,'excludeBase':True,
            'physicalBuildingNumber':None,'confidence':'estimated photo/plan crosswalk; not a named-building cadastral map'})
    save(HERE/'measured-plan.json',{'basis':'measured-from-mapped-OSM, not survey','unit':'unscaled metres','method':'WGS84 ECEF→local ENU at each source footprint','features':metrics})
    save(HERE/'footprint-correspondence.json',{'sourcePbfSha256':manifest['source']['sha256'],'sourceExtractSha256':fixed['sourceBuildingsSha256'],
        'auxiliaryOverpassSha256':sha(HERE.parent/'snapshots/overpass-alibaba-buildings.json'),'method':'Every polygon compared exactly, cyclic first vertex and reversal only; no parcel buffer exclusion','matches':matches})
    save(HERE/'object-groups.json',{'mainLayout':'two connected hexagonal office clusters plus southwest visitor;23 OSM features are not23 buildings','sourceFootprintCount':23,'activeFootprintCount':21,
        'physicalBuildingCount':'unknown; multi-arm continuous building groups, public numbered building crosswalk pending',
        'groupEvidence':['nbbj-phase4','benoy-phase4','nbbj-photo-DJI_0999_screenview'],
        'groups':groupmap,'unresolved':[{'sourceIds':['way/1363020741','way/1363020742'],'blocker':'Exact central sports/canteen/roof functional crosswalk, as-built height and rooftop profile unconfirmed. Retain source building/roof tags and base objects; no guessed published model.'},
            {'subject':'historical PhaseIV masterplan versus modern B zone terminology','blocker':'Historical preliminary phases/areas and exact NBBJ office-building numbers are not resolved by current page/photos. This finite source-bound model covers only mapped B parcel shapes; no earlier conceptual footprint expansion.'}]})
    refs=json.loads((HERE/'references/manifest.json').read_text())['sources'];sources=list(refs)
    old=json.loads((HERE.parent/'sources.json').read_text())['sources']
    for s in old:
        if s['id'] in ('osm-site-geometries','osm-alibaba-buildings','people-xixi-zones'):
            if s.get('path'):sources.append(dict(s,localPath=s['path']))
    sources.append({'id':'geofabrik-fixed','url':manifest['source']['sourceUrl'],'publisher':'Geofabrik / OpenStreetMap contributors',
        'sourceDate':manifest['source']['osmReplicationTimestamp'],'accessedAt':'2026-10-14','status':'source-verified',
        'localPath':'data/processed/hangzhou/buildings.geojson','sha256':fixed['sourceBuildingsSha256'],'license':'ODbL-1.0; © OpenStreetMap contributors',
        'use':'Mapped EPSG:4326 footprint23 objects of B parcel, no measured heights or elevations'})
    center=[120.02267895,30.27828295]
    save(HERE/'source-list.json',{'places':[{'id':'alibaba-b','name':'阿里巴巴西溪 B 区（NBBJ四期现状有限外观）','kind':'building-group',
        'location':{'center':center},'sources':sources,'modeling':{'status':'planned','blockers':[]}}]})
    snapshots={s['localPath']:s['sha256'] for s in sources if s.get('localPath') and s.get('sha256')}
    for name in ('geofabrik-footprints.json','object-groups.json','footprint-correspondence.json'):
        snapshots[str((HERE/name).relative_to(ROOT))]=sha(HERE/name)
    pending=['中央roof0741/0742功能/形体/标高crosswalk blocker，未建模、未排除基础对象',
        '历史四期期次/概念总图与现代B名称/编号关系blocker，有限范围仅当前B源足印',
        '逐栋实测高度/楼层；Benoy室内页面134feet高度字段范围未明确，不统套任一楼群',
        '所有地面玻璃体/架空支柱/入口/门洞的准确配准；真实内部与交互',
        '屋顶花园/种植/设备精确分区、绿顶防水构造和三角天窗数量/高度；外侧全立面',
        '多层基座与路面标高、屋顶/架空层实际可通行路径、地面与雨棚避让',
        '真实B编号/Logo与夜景灯具配准；不创建虚构标牌、灯光',
        'GLB导出/城市双排除/实际碰撞/可达到达点/昼夜实机三视角/FPS及内存']
    obs=[{'kind':'footprint','basis':'measured','unit':'EPSG:4326 / m','value':{'mappedObjects':23,'finiteModeledObjects':21,
        'visitorLengthM':metrics['way/1363020721']['minimumRotatedEnvelope']['lengthM'],'parcelWayId':544285896},
        'sourceIds':['geofabrik-fixed','osm-site-geometries'],
        'uncertainty':'Source vertices measured using WGS84 ECEF→ENU, all23 exact cyclic matches to auxiliary snapshot. Volunteered OSM plan precision unknown. Object counts are source ways/roofs, not independent main buildings.'},
        {'kind':'height','basis':'estimated','unit':'m','value':{o['label']:{'heightM':o['height']['value'],'errorPlusMinusM':o['height']['errorPlusMinusM']} for o in active},
        'sourceIds':['nbbj-photo-DJI_0999_screenview','nbbj-photo-DSC07936_screenview-2000x1334','nbbj-photo-DSF1342_screenview-2000x1347'],
        'uncertainty':'Manual person-relative pilotis around6±2m and4–6 visible facade courses, 4.2–4.7m pitch, bounded against mapped20–40m arm width and two street directions. Candidate high34±8m, lower25.4±7m, link14.4–19.6±5–6m, visitor18.5±5m, garden roof5.8±2.5m. Per-object values remain estimates, not a surveyed floor inventory.'},
        {'kind':'orientation','basis':'measured','unit':'degrees from north modulo180','value':{i:m['minimumRotatedEnvelope']['longAxisBearingDegreesClockwiseFromNorthModulo180'] for i,m in metrics.items()},
        'sourceIds':['geofabrik-fixed'],'uncertainty':'Oriented minimum-area envelope from WGS84 ENU. Every folded arm follows its complete source polygon; a single campus bearing would be insufficient. No commercial-map coordinate conversion.'},
        {'kind':'silhouette','basis':'reported','unit':'campus layout','value':{'mainClusters':'east and west connected beehive/hexagonal groups','visitor':'southwest','sports':'central between groups','features':'roof gardens and open/public exchange spaces'},
        'sourceIds':['nbbj-phase4','benoy-phase4'],'uncertainty':'Completed architect aerial strongly matches mapped folded arm network. Central sports/canteen exactsourceId remains outside finite scope blocker; reported public functions do not authorize imaginary internal gameplay.'},
        {'kind':'roof-and-facade','basis':'estimated','unit':'visual / m','value':{'outer':'warm orange vertical sunshade fins over dark glass','courtyard':'silver horizontal louvers and glass','gardenRoofs':'hexagonal stepped planted cells with triangle rooflights','pilotis':'exposed lower support level and covered connectors','candidateFacadeFinSamplingM':1.8,'candidateGardenCellRadiusM':11},
        'sourceIds':['nbbj-photo-DJI_0456_screenview-2000x1263','nbbj-photo-DSF1342_screenview-2000x1347','nbbj-photo-DSC07966R_screenview-2000x1334','nbbj-photo-DSF0994R_screenview-2000x1330'],
        'uncertainty':'Completed top/elevated/ground pictures manually compared; fin sampling1.8m abstracts denser observed shades, green cells11±3m radius and triangular glazing5±2m are proportional estimates against source87–115m roof extent/person scale. Gold shared material is a warm-color candidate, not finalized orange surface.'},
        {'kind':'reported-project-metric','basis':'reported','unit':'ft / m²','value':{'benoyPageHeightFeet':134,'benoyInteriorSizeM2':55000,'nbbjProjectAreaM2':180000},
        'sourceIds':['benoy-phase4','nbbj-phase4'],'uncertainty':'Benoy current interior case page lists2025,55,000m²,Height134feet(~40.84m) but metric scope not explained. NBBJ180,000m² is project program area, not footprint. No listed metric is silently attributed to all individual wings.'}]
    evidence={'schemaVersion':1,'placeId':'alibaba-b','scope':'Finite currentB mapped exterior:19 connected building-arm/junction/visitor sourceways +2 confirmed low green roof outlines; no fullPhaseIV or entireB completion claim',
        'identity':{'status':'confirmed','sourceIds':['nbbj-phase4','benoy-phase4','geofabrik-fixed'],
            'notes':'Current mappedB544285896 unique two-cluster folded plan matchesNBBJ completed aerial. Historical phases/numbers and central roof crosswalk remain pending outside finite scope.'},
        'location':{'crs':'EPSG:4326','center':center,'status':'confirmed','sourceIds':['geofabrik-fixed','osm-site-geometries'],
            'notes':'Mapped parcel reference only, not spawn/arrival'},'sources':sources,'sourceSnapshots':snapshots,'observations':obs,
        'blockers':[],'pendingSubscopes':pending,'excludedSubscopeBlockers':json.loads((HERE/'object-groups.json').read_text())['unresolved'],
        'unknownObservations':[{'kind':'individual-height-and-name','status':'unknown','notes':'All21 parts use bounded reference-informed estimates; no B1..B6 number mapping or individual height is asserted.'},
            {'kind':'entrance-and-lighting','status':'unknown','notes':'Visitor exterior accent is not a verified entrance. Artificial-light photos establish lights exist but exact lamp positions/photometry and usage remain pending; no new lights.'}]}
    task=HERE/'task/alibaba-b';save(task/'evidence.json' if task.exists() else HERE/'frozen-evidence.json',evidence)
    spec={'schemaVersion':1,'id':'alibaba-b','cityId':'hangzhou','status':'source-bound-exterior-candidate','scope':evidence['scope'],
        'anchor':{'lon':center[0],'lat':center[1]},'sourceSnapshotSha256':manifest['source']['sha256'],
        'coordinateConfigSha256':sha(ROOT/'config/cities/hangzhou.json'),'sourceFootprintsPath':str((HERE/'geofabrik-footprints.json').relative_to(ROOT)),
        'sourceFootprintsSha256':sha(HERE/'geofabrik-footprints.json'),'evidencePath':str((task/'evidence.json').relative_to(ROOT)),
        'evidenceSha256':sha(task/'evidence.json' if task.exists() else HERE/'frozen-evidence.json'),
        'baseBuildingIdsToExclude':[o['sourceId'] for o in active],'objects':active,
        'groupCenters':{'west':[120.021450,30.27825],'east':[120.024300,30.27865]},
        'facade':{'finPitchM':1.8,'innerBayM':3.6,'finProjectionM':.28,'ribWidthM':.10,
            'groundInsetM':2.4,'columnPitchM':14,'columnSideM':.8,'insetPurpose':'estimated recessed ground glass/pilotis, not measured footprint'},
        'gardenRoof':{'cellRadiusM':11,'cellPitchM':22,'cellRiseM':.55,'triangleSideM':5,'roofThicknessM':.8,
            'basis':'estimated','method':'NBBJ completed roof/ground photos; hex cells fitted only fully within each source roof outline, exact count/placement unverified'},
        'visitorEntry':{'widthM':15,'heightM':5,'basis':'estimated','method':'Southwest visitor byBenoy layout; accent on south-facing long edge, exact security gate pending'},
        'budget':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},
        'groundDatum':{'status':'pending','candidateBaseMetres':0,'lmYUnit':'already-scaled game units','notes':'Pilotis and green roof surfaces are estimated; root verifies current terrain and connected street datum'},
        'pendingSubscopes':pending,'excludedSubscopeBlockers':evidence['excludedSubscopeBlockers'],
        'materialHints':{'gold':'Warm orange sunshade approximation using shared existing material; final color requires serial material/GLB review','leaf':'Authored green roof cover, no sampled photographic texture'},
        'noPhotoTextures':True,'noNewLights':True}
    save(HERE/'spec.json',spec)
    print('23 exactsource matches;21 source-bound exterior objects frozen;2 unknown centralroof objects retained as blockers.')


if __name__=='__main__':main()
