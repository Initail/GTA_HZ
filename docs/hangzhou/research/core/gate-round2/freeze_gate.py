"""Freeze a source-bound exterior candidate. Does not write shared catalog/assets."""
from pathlib import Path
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    measurement = json.loads((HERE/'osm-footprints-and-measurements.json').read_text())
    osm = {o['id']: o for o in measurement['objects']}
    source = json.loads((REPO/'data/hangzhou/source-manifest.json').read_text())
    sources = [
        {'id': 'osm-geofabrik', 'url': source['sourceUrl'], 'publisher': 'OpenStreetMap contributors / Geofabrik',
         'accessedAt': '2026-10-12', 'sourceDate': source['osmReplicationTimestamp'], 'status': 'available',
         'license': 'ODbL-1.0', 'sha256': source['sha256'], 'localPath': 'data/raw/hangzhou/zhejiang-261011.osm.pbf',
         'use': 'WGS84 footprints; Geofabrik subset equals OSM API rings'},
        {'id': 'osm-api', 'url': measurement['sourceUrl'], 'publisher': 'OpenStreetMap contributors',
         'accessedAt': '2026-10-12', 'status': 'available', 'license': 'ODbL-1.0',
         'localPath': str((HERE/'osm-local-map.json').relative_to(REPO)), 'sha256': digest(HERE/'osm-local-map.json'),
         'use': 'auxiliary exact node/way version provenance; not replacement for main Geofabrik city'},
        {'id': 'ecadi-primary', 'url': 'https://www.thepaper.cn/newsDetail_forward_21768064',
         'publisher': '华建集团华东建筑设计研究院有限公司供稿 / 澎湃号政务平台',
         'accessedAt': '2026-10-12', 'sourceDate': '2023-02-01', 'status': 'available',
         'license': 'unknown; reference only; images not bundled',
         'use': 'T1/T2 identity, 310m, bridge/curtain elevations, official photos and SOM section image'},
        {'id': 'som-primary', 'url': 'https://www.som.com/projects/greenland-hangzhou-century-center/',
         'publisher': 'SOM', 'accessedAt': '2026-10-12', 'status': 'available-indexed', 'sourceDate': None,
         'license': 'unknown; reference only', 'use': 'twin towers, H/arched bridge, flowing glass enclosure, 64 stories; indexed text, direct fetch 403'},
    ]
    photos = []
    for ident, title, author, direction, observations in [
        (681, '长三角最高双塔建筑', '沙鹏', {'view': 'full-front aerial oblique', 'azimuth': 'unknown; potential180deg ambiguity; no EXIF'},
         '双塔横断轮廓圆滑；塔冠外侧高内侧低；低区幕帘为U形；宴会厅下腹拱形，工地地面未完成。'),
        (698, '俯瞰钢拱连廊帘幕', '沙鹏', {'view': 'oblique-downward', 'azimuth': 'unknown'},
         '双曲马鞍/悬垂面有深度；板块与缝形成镂空节奏，不是两塔间一张平面实心屏。'),
        (682, '塔冠停机坪远眺钱江北岸', '华东院', {'view': 'tower crown towards NW river/north-bank, estimated', 'bearingTowardDegrees': 307.5, 'allowanceDegrees': 20},
         '反向视角确认屋顶弧形边缘和内侧结构/平台；无EXIF和尺度，停机坪精确尺寸未冻结。'),
    ]:
        temp = Path(f'<TEMP>/hz-gate-reference-{ident}.jpg')
        assert temp.exists() and temp.stat().st_size > 10000
        photos.append({'id': f'ecadi-photo-{ident}', 'sourceId': 'ecadi-primary',
                       'url': f'https://imagepphcloud.thepaper.cn/pph/image/236/615/{ident}.jpg',
                       'caption': title, 'creditedTo': author, 'capturedAt': None,
                       'publishedAt': '2023-02-01', 'reviewedAt': '2026-10-12',
                       'reviewMethod': 'actual Chrome native UI image view via cua_repl; not search-generated description',
                       'viewDirection': direction, 'observations': observations,
                       'sha256': digest(temp), 'downloadBytes': temp.stat().st_size,
                       'license': 'unknown', 'bundled': False,
                       'hashMethod': 'temporary research cache after visual review, outside repository; no release texture'})
    estimated = {
        'bodySections': {'value': [[0, 1.0, 1.0], [34.6, 1.02, 1.0], [103.6, .89, .94],
                                   [160, .91, .94], [235, .94, .92], [280, .90, .87]],
                         'unit': '[z_m, footprint_axis_u_factor, footprint_axis_v_factor]',
                         'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                         'method': 'OSM base fixed; photographed smooth outline sampled at broad height fractions of reported 310m. Factors are coarse proportional visual estimates, not photogrammetry.',
                         'uncertainty': 'height breakpoints ±15m, width/depth factors ±0.08; independent back-side facade pending'},
        'crownDropM': {'value': 24, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                       'method': 'outer/inner sloped rim difference visually proportioned from full frontal photo using 310m total; no exact crown survey',
                       'uncertainty': '±10m; exact roof/helipad level and underside unknown'},
        'curtainDepthM': {'value': 42, 'basis': 'estimated', 'sourceIds': ['osm-geofabrik', 'ecadi-primary'],
                         'method': 'bounded by mapped middle feature front-axis extent 45.037m and reviewed saddle photograph; rectangular candidate support depth',
                         'uncertainty': '±6m, not actual curved curtain plan'},
        'curtainCrossCamberM': {'value': 10, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                               'method': 'SOM bridge section image 689 and actual oblique photo 698 show convex cross-direction roof; representative rise selected relative to 60m reported span',
                               'uncertainty': '±5m; engineering catenary/rationalised panel coordinates not obtained'},
        'curtainPanelThicknessM': {'value': .10, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                                  'method': 'thin closed volume represents reviewed panel and makes both sides visible with existing material culling; no measured construction thickness',
                                  'uncertainty': 'rendering allowance, physical panel/frame thickness unknown'},
        'archUndersideRiseM': {'value': 20, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                              'method': 'frontal arch void fitted below reported banquet floor at22m, leaving central passage and side abutments',
                              'uncertainty': '±4m; engineering soffit profile not obtained'},
        'facadeHorizontalBandM': {'value': .20, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                                'method': 'thin repeated structural/floor rhythm observed in official photos; thickness is game-visible representation', 'uncertainty': '±.10m'},
        'facadeVerticalRibM': {'value': .12, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                             'method': 'reviewed narrow mullion rhythm; width chosen for low-poly candidate, not measured', 'uncertainty': '±.08m'},
        'facadePerimeterDivisions': {'value': 96, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                                    'method': 'approx2m bay spacing from196m mapped tower perimeter and photograph rhythm; actual mullion count not claimed', 'uncertainty': '±24 divisions'},
        'bridgeGlazingInsetM': {'value': .25, 'basis': 'estimated', 'sourceIds': ['ecadi-primary'],
                               'method': 'avoid coplanar surfaces in candidate; exact rebate not obtained', 'uncertainty': 'rendering allowance'},
    }
    spec = {'schemaVersion': 1, 'id': 'hangzhou-gate', 'cityId': 'hangzhou',
            'scope': 'Source-bound exterior candidate for twin towers, arched banquet bridge and open curtain; full retail, interiors, rooftop equipment and exact entrance details pending.',
            'anchor': {'lon': measurement['anchorWgs84'][0], 'lat': measurement['anchorWgs84'][1]},
            'coordinateContract': 'scripts/city_config.py load_city(hangzhou) at build; all source WGS84 and real metres; model scale once; lm.x/lm.z/lm.y already game units',
            'sourceSnapshotSha256': source['sha256'],
            'baseBuildingIdsToExclude': ['way/1015040645', 'way/1015040646', 'way/1015040647'],
            'towers': [{'id': label, 'osmWayId': ident, 'functionalIdentity': function,
                        'footprintWGS84': osm[ident]['wgs84'], 'centroidWGS84': osm[ident]['centroidWgs84'],
                        'heightM': 310, 'heightBasis': 'reported', 'heightSourceIds': ['ecadi-primary', 'som-primary']}
                       for ident, label, function in [(1015040645, 'west-t1', 'office'), (1015040647, 'east-t2', 'office-and-hotel')]],
            'bridge': {'spanM': 60, 'banquetFloorM': 22, 'roofGardenM': 34.6,
                       'curtainHighM': 103.6, 'curtainLowM': 53.381,
                       'basis': 'reported', 'sourceIds': ['ecadi-primary'],
                       'uncertainty': 'source design elevations relative project datum; datum/ground must be aligned by main integration; span source says approximately'},
            'facade': {'floorBandDivisions': 64,
                       'divisionBasis': 'SOM reports64stories; ECADI reports63 above-ground. Candidate64 bands express rhythm, not exact floor count reconstruction.',
                       'materialNames': ['landmarkglass', 'darkglass', 'silver', 'steel', 'concrete'],
                       'materialBasis': 'existing PBR palette as estimated appearance; no copied official photo textures, no new lights'},
            'estimates': estimated, 'sources': sources, 'photos': photos,
            'pendingSubscopes': ['retail podium details', 'precise entrances and landscaping', 'complete all-side facade survey',
                                'exact roof crown/helipad dimensions', 'night material/lighting rendering', 'collision/arrival/runtime/performance'],
            'budget': {'maxTriangles': 25000, 'maxMaterials': 12, 'maxBytes': 8388608},
    }
    write(HERE/'spec.json', spec)
    evidence = {'schemaVersion': 1, 'placeId': 'hangzhou-gate', 'scope': spec['scope'],
                'identity': {'status': 'confirmed', 'sourceIds': ['ecadi-primary', 'som-primary', 'osm-geofabrik']},
                'location': {'crs': 'EPSG:4326', 'center': measurement['anchorWgs84'], 'status': 'confirmed', 'sourceIds': ['osm-geofabrik', 'osm-api']},
                'sources': sources, 'photos': photos,
                'observations': [
                    {'kind': 'footprint', 'value': {'towerWayIds': [1015040645, 1015040647], 'ringsPath': str((HERE/'geofabrik-gate-features.geojson').relative_to(REPO))},
                     'unit': 'EPSG:4326', 'basis': 'measured', 'sourceIds': ['osm-geofabrik', 'osm-api'],
                     'uncertainty': 'OSM data polygons matched verbatim between raw API and fixed Geofabrik; not field survey; source accuracy unknown, planning tolerance±5m.'},
                    {'kind': 'height', 'value': {'towersM': 310, 'bridgeFloorM': 22, 'gardenM': 34.6, 'curtainHighM': 103.6, 'curtainLowM': 53.381},
                     'unit': 'm', 'basis': 'reported', 'sourceIds': ['ecadi-primary', 'som-primary'],
                     'uncertainty': 'reported design elevations; precision of printed decimals not a claim of survey accuracy; main integration must resolve project datum.'},
                    {'kind': 'orientation', 'value': {'towerPairBearingNorthClockwise': measurement['axis']['bearingDegreesFromNorthClockwise'], 'northwestGateNormalBearing': 307.5219454676},
                     'unit': 'degrees', 'basis': 'measured', 'sourceIds': ['osm-geofabrik', 'osm-api'],
                     'uncertainty': 'azimuth calculated from OSM polygon area centroids by measure_gate.py; planning allowance±3deg is not a measured confidence interval. Transverse normal is mathematical; precise entrance facade is not assigned.'},
                    {'kind': 'silhouette', 'value': 'curved paired tower footprints, outer-high/inner-low crowns, low arched banquet bridge and deep perforated saddle curtain; facade horizontal bands/narrow vertical ribs.',
                     'unit': None, 'basis': 'estimated', 'sourceIds': ['ecadi-primary', 'som-primary'],
                     'uncertainty': 'reviewed official full-front, downward saddle and opposite crown views. Late-construction photos, not2026 capture. Coarse profile/rib estimates and error allowances in spec.estimates.'},
                ],
                'blockers': [],
                'pendingSubscopes': spec['pendingSubscopes'],
                'conflicts': ['SOM64stories vsECADI63above-ground; no silent resolution;64 candidate band rhythm.',
                              'SOM completion2023 vsECADI project archive2022; geometry photos published2023, original capture datesunknown.',
                              'OSM middle wayheight50 is unverified and replaced by official bridge/curtain elevations; no50m solid connector box.',
                              'OSM mapped inner edgegap54.183m vsreported approximate curtainspan60m are different measurement endpoints.'],
                'sourceSnapshots': {str((HERE/f).relative_to(REPO)): digest(HERE/f) for f in
                                    ('osm-local-map.json', 'osm-way-1015040645-full.json', 'geofabrik-gate-features.geojson', 'osm-footprints-and-measurements.json', 'spec.json')},
                'photosBundled': False,
                'stageLimit': 'Core exterior evidence scope only; no modelled/verified claim without actual GLB and visual/runtime checks.'}
    write(HERE/'evidence.json', evidence)
    catalog = json.loads((REPO/'data/hangzhou/landmarks.json').read_text())
    record = copy.deepcopy(next(p for p in catalog['places'] if p['id'] == 'hangzhou-gate'))
    record.update({'location': evidence['location'], 'sources': sources, 'scope': spec['scope'],
                   'researchEvidence': str((HERE/'evidence.json').relative_to(REPO))})
    write(HERE/'catalog.json', {'schemaVersion': 1, 'cityId': 'hangzhou', 'places': [record]})


if __name__ == '__main__':
    main()
