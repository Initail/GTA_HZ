"""Freeze a finite C-campus exterior candidate, from existing source snapshots.

No network, Blender, shared-data writes or height tag inference. Run once before
the task evidence gate. Re-running updates only this object's independent files.
"""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
from city_config import load_city


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def cyclic(a, b):
    a, b = [tuple(p) for p in a[:-1]], [tuple(p) for p in b[:-1]]
    if len(a) != len(b):
        return None
    for reversed_order, candidate in ((False,b),(True,list(reversed(b)))):
        for start in range(len(b)):
            if a == candidate[start:]+candidate[:start]:
                return {'startIndex':start,'reverse':reversed_order,'allCoordinatesExact':True}
    return None


def main():
    ref = importlib.util.spec_from_file_location('source_metrics',HERE.parent/'measure_osm.py')
    measure = importlib.util.module_from_spec(ref); ref.loader.exec_module(measure)
    fixed = json.loads((HERE/'geofabrik-footprints.json').read_text())
    manifest = json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert sha(ROOT/'data/processed/hangzhou/buildings.geojson') == fixed['sourceBuildingsSha256'] == manifest['sha256']['buildings']
    overpass = json.loads((HERE.parent/'snapshots/overpass-alibaba-buildings.json').read_text())
    earlier = {(e['type'],e['id']):e for e in overpass['elements']}
    metric = {}; correspondence = []
    for feature in fixed['features']:
        props = feature['properties']; key = (props['osm_type'],props['osm_id'])
        obj = earlier[key]
        outer,inner,unresolved = measure.rings(obj)
        assert not unresolved and len(outer)==1
        source_rings = feature['geometry']['coordinates'][0]
        matched = [cyclic(source_rings[0],outer[0])]
        matched += [next((v for ring in inner if (v:=cyclic(r,ring))),None) for r in source_rings[1:]]
        assert all(matched), 'fixed source footprint differs: '+feature['id']
        metric[feature['id']] = measure.summarize(obj)
        correspondence.append({'baseBuildingId':feature['id'],'modelPart':props['name'] or 'Ali/Media Roof',
            'fixedSnapshotPolygonCount':len(feature['geometry']['coordinates']),
            'outerAndInnerRingMatches':matched,'overpassVersion':obj['version'],
            'overpassObjectTimestamp':obj['timestamp'],
            'exclusionScope':'this source building only, not parcel/nearby structures'})
    save(HERE/'footprint-correspondence.json',{'sourcePbfSha256':manifest['source']['sha256'],
        'sourceExtractSha256':fixed['sourceBuildingsSha256'],'auxiliaryOverpassSha256':sha(HERE.parent/'snapshots/overpass-alibaba-buildings.json'),
        'method':'All rings compared exactly allowing reversed order and cyclic first vertex; no buffering/parcel-wide exclusion',
        'matches':correspondence})
    save(HERE/'measured-plan.json',{'method':'WGS84 ellipsoid ECEF to footprint-centred east/north; actual game uses centralized local projection',
        'basis':'measured-from-mapped-OSM, not survey','units':'unscaled metres','features':metric})
    origin = [120.0185145,30.28575155]
    heights = {'C6':(10,54,12),'C5':(11,59.2,12),'C4':(12,64.4,11),
               'C3':(15,80,8),'C2':(14,74.8,11),'C1':(12,64.4,12),'访客中心':(7,38.4,10)}
    references = json.loads((HERE/'references/manifest.json').read_text())['sources']
    existing = json.loads((HERE.parent/'sources.json').read_text())['sources']
    sources = [dict(s,localPath=s.get('localPath',s['path'])) for s in existing
               if s['id'] in ['nihonsekkei-phase5','aspect-park-c','credaward-park-c','nihonsekkei-report-2026','osm-site-geometries','osm-alibaba-buildings']]
    sources += references
    sources += [{'id':'geofabrik-fixed','url':manifest['source']['sourceUrl'],
        'publisher':'Geofabrik / OpenStreetMap contributors','accessedAt':'2026-10-13','sourceDate':manifest['source']['osmReplicationTimestamp'],
        'status':'source-verified','license':'ODbL-1.0; © OpenStreetMap contributors',
        'localPath':'data/processed/hangzhou/buildings.geojson','sha256':fixed['sourceBuildingsSha256'],
        'use':'Only mapped EPSG:4326 plan geometry; heights absent and OSM layer is not storey count'}]
    save(HERE/'source-list.json',{'places':[{'id':'alibaba-c','name':'阿里巴巴西溪 C 区（五期）',
        'kind':'building-group','location':{'center':origin},'sources':sources,
        'modeling':{'status':'planned','blockers':[]}}]})
    pending = ['逐栋竣工高度/层数与屋顶机械设备测绘；C3=80m仅为候选归属，不是逐栋reported',
        '全侧立面及方案图到竣工状态差异；入口门洞准确落位、安检与可交互内部',
        '多层景观基座/地下室地形标高与地面道路衔接；Exchange Ring全路径及可通行性',
        '中央湖面必须由基础water管线接入；环形景观雨棚及树木家具另立范围',
        '真实字牌字形、安装位置与许可；夜景照明事实',
        '基础楼体/近景立面排除、GLB导出、当前资产碰撞/导航、昼夜实机三视角与性能']
    observations = []
    observations.append({'kind':'footprint','basis':'measured','unit':'WGS84 + m',
        'value':{'sourceIds':[f['id'] for f in fixed['features']],
            'sixOfficeAtriumRings':6,'visitorLengthM':metric['way/1363020716']['minimumRotatedEnvelope']['lengthM'],
            'mediaRoofLengthM':metric['way/1363020718']['minimumRotatedEnvelope']['lengthM']},
        'sourceIds':['geofabrik-fixed'],
        'uncertainty':'Measured from volunteered mapped vertices with WGS84 ECEF→ENU, exact cyclic matches to auxiliary Overpass. OSM absolute/outline error unknown; no survey accuracy claim. All holes retained.'})
    observations.append({'kind':'height','basis':'reported','unit':'m / storeys',
        'value':{'projectHeightM':80,'projectBasementFloors':2,'projectAboveGroundFloorMetric':15},
        'sourceIds':['nihonsekkei-report-2026'],
        'uncertainty':'Completed project sheet pp49–50 reports aggregate Height80m / Floor15F B2F. It does not identify each building height. Awards appendix inconsistent140m/520000m² retained as conflict, not used.'})
    observations.append({'kind':'height','basis':'estimated','unit':'m',
        'value':{name:{'candidateHeightM':h,'errorPlusMinusM':err,'candidateFacadeCourses':n} for name,(n,h,err) in heights.items()},
        'sourceIds':['nihon-sekkei-2022-01-17-104535','nihon-sekkei-878862bd4ed9bfa26f6c2bb5913c2085',
                     'aspect-studios-ASPECTStudios_SHA_Alibaba-Xixi-Campus-Park-C_04','nihonsekkei-report-2026'],
        'uncertainty':'Candidate floor-course ratios roughly10:11:12:15:14:12 and visitor7 from architect aerial scheme, checked against completed courtyard photos (C4/3/2). Using maximum80m and2m parapet gives pitch(80-2)/15=5.2m; H=2+5.2N. Counts and roof correspondence may differ as-built. ±8–12m includes ~1–2 courses, perspective/occlusion, scheme-to-built variation; C3 maximum allocation itself remains estimated. No absent OSM height is asserted as known.'})
    observations.append({'kind':'orientation','basis':'measured','unit':'degree clockwise from north modulo180',
        'value':{f['properties']['name'] or 'Media Roof':metric[f['id']]['minimumRotatedEnvelope']['longAxisBearingDegreesClockwiseFromNorthModulo180'] for f in fixed['features']},
        'sourceIds':['geofabrik-fixed'],
        'uncertainty':'Minimum-area oriented envelope computed from fixed WGS84 mapped vertices after ECEF→ENU. Bearings do not prove entrance direction; no commercial-map coordinates used.'})
    observations.append({'kind':'silhouette','basis':'reported','unit':'building group',
        'value':{'offices':6,'visitorCenter':1,'layout':'U around south-opening garden',
            'connection':'Second-floor Exchange Ring connects seven units',
            'southGateway':'approximately480m Media Roof / Ali Roof'},
        'sourceIds':['nihonsekkei-phase5','nihonsekkei-report-2026','credaward-park-c'],
        'uncertainty':'Layout is architect-reported and crosschecked on mapped C parcel. Exact link deck widths/heights and completed roof profiles not dimensioned; candidate estimates separately frozen. Phase6 and A/B campuses excluded.'})
    observations.append({'kind':'facade','basis':'estimated','unit':'m + visual description',
        'value':{'material':'dark blue-grey glass with silver vertical mullions',
            'horizontalRhythm':'fine storey rails, projecting belt/fins every three candidate courses',
            'verticalBayM':3.4,'finProjectionM':1.05,'roof':'flat perimeter, recessed roof gardens and central linear skylight/frame'},
        'sourceIds':['aspect-studios-ASPECTStudios_SHA_Alibaba-Xixi-Campus-Park-C_04','aspect-studios-ASPECTStudios_SHA_Alibaba-Xixi-Campus-Park-C_14',
            'nihon-sekkei-2022-01-17-104535','nihon-sekkei-db7b08af02c209e4893c2b01ec399caf'],
        'uncertainty':'Visual manual comparison of two completed courtyard/elevated directions and scheme aerial/section. Relative rhythm is supported; bay3.4±0.8m and fin1.05±0.6m estimated from ~104m mapped office width / visible columns, perspective affected. Sparse authored facade panels are visual abstraction, not window inventory.'})
    # Fix explicit image id spelling, with no reliance on permissive CLI lookup.
    observations[2]['sourceIds'][0] = 'nihon-sekkei-2022-01-17-104535'
    observations.append({'kind':'source-object-crosswalk','basis':'estimated','unit':'source geometry / object identity',
        'value':{'mappedRoofId':'way/1363020718','mappedLongAxisLengthM':486.4,'architectSchemeMediaRoofLengthM':480,
            'role':'south continuous elevated Media/Ali Roof'},
        'sourceIds':['geofabrik-fixed','nihonsekkei-phase5','nihon-sekkei-2022-01-17-104535'],
        'uncertainty':'Unnamed source roof outline is aligned at the south edge and matches the architect plan/render scale480m vs mapped486.4m (1.3% variation). This is source/photo crosswalk, not an OSM name or surveyed as-built roof specification. Exact completed roof elevations, ends and supports pending.'})
    snapshots = {s['localPath']:s['sha256'] for s in sources}
    snapshots[str((HERE/'geofabrik-footprints.json').relative_to(ROOT))] = sha(HERE/'geofabrik-footprints.json')
    snapshots[str((HERE/'footprint-correspondence.json').relative_to(ROOT))] = sha(HERE/'footprint-correspondence.json')
    evidence = {'schemaVersion':1,'placeId':'alibaba-c','scope':'Finite source-bound exterior candidate: C1–C6, visitor, inter-unit bridges and south Media/Ali Roof; no full campus completion claim',
        'identity':{'status':'confirmed','sourceIds':['nihonsekkei-phase5','aspect-park-c','credaward-park-c'],
            'notes':'C campus=Phase5; C6 named office is not distinct Phase6/DingTalk headquarters'},
        'location':{'crs':'EPSG:4326','center':origin,'status':'confirmed','sourceIds':['geofabrik-fixed'],
            'notes':'OSM parcel bbox reference, not an arrival/spawn position'},
        'sources':sources,'sourceSnapshots':snapshots,'observations':observations,
        'blockers':[],'pendingSubscopes':pending,
        'conflicts':[{'sourceId':'nihonsekkei-report-2026','value':'Awards appendix lists140m/520000m², inconsistent with completed project sheet80m/970000m²',
            'resolution':'Use actual completed project sheet; all per-building values remain estimates'}],
        'unknownObservations':[{'kind':'individual-as-built-height','status':'unknown',
            'objects':['C1','C2','C3','C4','C5','C6','访客中心'],
            'notes':'Candidate estimated heights provide finite silhouette; reported project15F/B2/80m does not resolve each object.'},
            {'kind':'entrance','status':'unknown','notes':'Visitor south exterior glazing accent is candidate, not verified security entrance/arrival.'},
            {'kind':'night','status':'unknown','notes':'No illumination inference from daylight or scheme imagery.'},
            {'kind':'ground-datum','status':'unknown','notes':'Multilevel podium exists; source footprint layer2 is not a physical elevation.'}]}
    task = HERE/'task/alibaba-c'
    if task.exists():
        save(task/'evidence.json',evidence)
    else:
        save(HERE/'frozen-evidence.json',evidence)
    buildings = []
    for f in fixed['features'][:-1]:
        name = f['properties']['name']; n,h,err = heights[name]
        buildings.append({'label':name,'sourceId':f['id'],'ringsWGS84':f['geometry']['coordinates'][0],
            'height':{'value':h,'unit':'m','basis':'estimated','errorPlusMinusM':err,
                'method':'H=2m parapet +5.2m*estimated visible facade courses; project80m/15F only sets common reference pitch. '+str(n)+' candidate courses, not verified storeys'},
            'facadeCourses':n,'roofSetbackM':{'value':3,'basis':'estimated','errorPlusMinusM':2,
                'method':'Scheme roof garden/frame recess visually compared to~104m mapped long edge; not surveyed'}})
    spec = {'schemaVersion':1,'id':'alibaba-c','cityId':'hangzhou','status':'source-bound-exterior-candidate',
        'scope':evidence['scope'],'anchor':{'lon':origin[0],'lat':origin[1]},
        'sourceSnapshotSha256':manifest['source']['sha256'],
        'sourceFootprintsPath':str((HERE/'geofabrik-footprints.json').relative_to(ROOT)),
        'sourceFootprintsSha256':sha(HERE/'geofabrik-footprints.json'),
        'evidencePath':str((task/'evidence.json').relative_to(ROOT)),
        'evidenceSha256':sha(task/'evidence.json') if task.exists() else sha(HERE/'frozen-evidence.json'),
        'coordinateConfigSha256':sha(ROOT/'config/cities/hangzhou.json'),
        'baseBuildingIdsToExclude':[f['id'] for f in fixed['features']],
        'buildings':buildings,
        'mediaRoof':{'sourceId':fixed['features'][-1]['id'],'ringsWGS84':fixed['features'][-1]['geometry']['coordinates'][0],
            'deckTopM':12,'deckThicknessM':1.4,'columnPitchM':25,
            'basis':'estimated','errorDeckPlusMinusM':4,'method':'Three scheme floor-equivalent heights beneath480m roof; source outline486.4m measured separately. Sparse open support columns25±8m rhythm are candidate, not measured'},
        'exchangeRing':{'sequence':['C6','C5','C4','C3','C2','C1','访客中心'],
            'deckTopM':6.2,'deckThicknessM':0.8,'widthM':7,'glassRailM':1.2,
            'basis':'estimated','errorDeckPlusMinusM':2,'errorWidthPlusMinusM':2.5,
            'method':'Architect reported second-floor ring + completed photo proportions; outside segments follow successive source footprints toward courtyard. Through-building routing and exact link position unverified'},
        'facade':{'bayM':3.4,'majorEveryCourses':3,'majorFinProjectionM':1.05,'ribWidthM':0.13,
            'method':'Completed photos04/14; candidate bay/rib/panel distribution simplified, no photo textures'},
        'visitorEntry':{'widthM':16,'heightM':7,'recessM':1.0,'basis':'estimated',
            'method':'South-facing long visitor facade marked by recessed glazed vestibule under Media Roof; exact security entry unknown, not selected as arrival'},
        'budget':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},
        'pendingSubscopes':pending,'noPhotoTextures':True,'noNewLights':True,
        'groundDatum':{'status':'pending','candidateBaseMetres':0,'lmYUnit':'already-scaled game units',
            'notes':'Do not infer podium elevation from OSM layer2; central terrain integration owner must verify ground/road connection.'}}
    save(HERE/'spec.json',spec)
    print('Frozen8 exact source footprints; candidate height estimates only; task evidence must be checked before module.')


if __name__ == '__main__':
    main()
