"""Freeze the five axial halls from the fixed Geofabrik extract; no bpy import."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'scripts'))
from city_config import load_city

OUT = Path(__file__).resolve().parent
PREFIX = str(OUT.relative_to(ROOT))
DATE = '2026-10-13'


def write(name, data):
    p = OUT / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return hashlib.sha256(p.read_bytes()).hexdigest()


def centroid(points):
    twice = cx = cy = 0.0
    for p, q in zip(points, points[1:] + points[:1]):
        cross = p[0] * q[1] - q[0] * p[1]
        twice += cross
        cx += (p[0] + q[0]) * cross
        cy += (p[1] + q[1]) * cross
    return cx / (3 * twice), cy / (3 * twice), abs(twice) / 2


def rectangle(points):
    # Four roof outlines are rectangles; Medicine Hall has collinear subdivisions.
    choices = []
    for p, q in zip(points, points[1:] + points[:1]):
        a = math.atan2(q[1] - p[1], q[0] - p[0])
        while a < -math.pi / 4:
            a += math.pi / 2
        while a >= math.pi / 4:
            a -= math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        uv = [(x * ca + y * sa, -x * sa + y * ca) for x, y in points]
        u0, u1 = min(p[0] for p in uv), max(p[0] for p in uv)
        v0, v1 = min(p[1] for p in uv), max(p[1] for p in uv)
        choices.append(((u1 - u0) * (v1 - v0), a, u1 - u0, v1 - v0))
    _, angle, width, depth = min(choices)
    return angle, width, depth


def main():
    city = load_city('hangzhou')
    geo = city['geography']
    east, north = geo['eastMetresPerDegree'], geo['northMetresPerDegree']
    buildings_path = ROOT / 'data/processed/hangzhou/buildings.geojson'
    buildings = json.loads(buildings_path.read_text())
    ids = [434365023, 434365024, 434365025, 434366739, 434366741]
    selected = {f['properties']['osm_id']: f for f in buildings['features']
                if f['properties']['osm_id'] in ids + [195189679]}
    assert set(selected) == set(ids + [195189679])
    assert selected[195189679]['properties']['tags']['shop'] == 'ticket'
    anchor_ring = selected[434365024]['geometry']['coordinates'][0][0][:-1]
    # Translate before area arithmetic to avoid subtraction of large WGS84 products.
    origin = anchor_ring[0]
    metric = [((x - origin[0]) * east, (y - origin[1]) * north) for x, y in anchor_ring]
    ax, ay, _ = centroid(metric)
    anchor = [origin[0] + ax / east, origin[1] + ay / north]
    names = ['天王殿', '大雄宝殿', '药师殿', '法堂/直指堂/藏经楼', '华严殿']
    heights = [20.0, 33.6, 24.0, 23.0, 23.0]
    height_errors = [6.0, None, 7.0, 6.0, 7.0]
    halls = []
    for i, ident in enumerate(ids):
        f = selected[ident]
        ring = f['geometry']['coordinates'][0][0][:-1]
        local = [((x - anchor[0]) * east, (y - anchor[1]) * north) for x, y in ring]
        cx, cy, area = centroid(local)
        a, w, d = rectangle([(x - cx, y - cy) for x, y in local])
        halls.append({'id': ['kings', 'grand', 'medicine', 'dharma', 'huayan'][i],
                      'name': names[i], 'axisOrder': i + 1,
                      'sourceFeatureIds': [f'way/{ident}'], 'sourceOsmName': f['properties']['name'],
                      'centroidWGS84': [anchor[0] + cx / east, anchor[1] + cy / north],
                      'offsetEastNorthM': [cx, cy], 'footprintWGS84': ring,
                      'footprintLocalMetres': local, 'footprintAreaM2': area,
                      'widthM': w, 'depthM': d, 'widthAxisRadiansEastCCW': a,
                      'frontBearingNorthClockwise': (180 - math.degrees(a)) % 360,
                      'frontBearingBasis': 'estimated',
                      'frontBearingMethod': 'polygon width axis plus official downhill/front to uphill/back hall sequence; not a measured entrance bearing',
                      'heightM': heights[i], 'heightBasis': 'reported' if i == 1 else 'estimated',
                      'heightAllowanceM': height_errors[i],
                      'eaveTiers': 3 if i == 1 else 2,
                      'bayCount': 7, 'bayCountBasis': 'reported' if i in [1, 2] else 'estimated',
                      'baseElevationRelativeM': 0,
                      'roofType': 'xieshan-reference-informed',
                      'roofTypeBasis': 'reported' if i in [1, 2] else 'estimated',
                      'sourceIds': ['osm-geofabrik', 'temple-2014',
                                    ['kings-official', 'grand-official', 'medicine-official',
                                     'dharma-official', 'huayan-official'][i]],
                      'pending': ['exact rear facade', 'surveyed ground/terrace datum',
                                  'precise roof profiles and decorative carving']})
    source_hash = hashlib.sha256((ROOT / 'data/raw/hangzhou/zhejiang-261011.osm.pbf').read_bytes()).hexdigest()
    expected = '4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    assert source_hash == expected
    feature_hash = write('geofabrik-lingyin-features.geojson', {
        'type': 'FeatureCollection', 'crs': 'EPSG:4326', 'license': 'ODbL-1.0',
        'sourceSnapshotSha256': source_hash, 'features': [selected[i] for i in ids + [195189679]]})
    source = lambda ident, url, date=None: {
        'id': ident, 'url': url, 'publisher': '杭州灵隐寺（运营方官网）',
        'accessedAt': DATE, 'sourceDate': date, 'status': 'available',
        'license': 'Copyright retained by publisher; reference only; photographs not bundled'}
    sources = [
        {'id': 'osm-geofabrik', 'url': 'https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf',
         'publisher': 'OpenStreetMap contributors / Geofabrik', 'accessedAt': DATE,
         'sourceDate': '2026-10-11T20:21:06Z', 'status': 'available', 'license': 'ODbL-1.0',
         'sha256': source_hash, 'localPath': 'data/raw/hangzhou/zhejiang-261011.osm.pbf'},
        source('temple-2014', 'https://www.lingyinsi.org/detail_44_7946.html', '2014-08-08'),
        source('grand-official', 'https://en.lingyinsi.org/detail_1141.html', '2013-01-18'),
        source('kings-official', 'https://en.lingyinsi.org/list_82.html'),
        source('medicine-official', 'https://en.lingyinsi.org/list_144.html'),
        source('dharma-official', 'https://en.lingyinsi.org/list_145.html'),
        source('huayan-official', 'https://en.lingyinsi.org/list_146.html'),
        source('exhibition-official', 'https://en.lingyinsi.org/list_271.html'),
        source('axis-photo-2020', 'https://www.lingyinsi.org/detail_55_14277.html', '2020-09-24'),
        source('hall-photo-2020', 'https://www.lingyinsi.org/detail_128_14533.html', '2020-10-13'),
        source('roof-photo-2021', 'https://lingyinsi.org/detail_1050_15763.html', '2021-10-06'),
        source('intro-official', 'https://lingyinsi.org/detail_747.html', '2013-10-15')]
    estimates = {
        'secondaryHeights': {'basis': 'estimated', 'value': {h['id']: [h['heightM'], h['heightAllowanceM']]
                       for h in halls if h['heightBasis'] == 'estimated'},
          'unit': '[metres, allowance metres]', 'sourceIds': ['kings-official', 'medicine-official',
                  'dharma-official', 'huayan-official', 'axis-photo-2020', 'hall-photo-2020'],
          'method': 'Coarse width-to-height proportions and number of visible eaves/levels in official street photos, using OSM width as contextual bound. Cropping/occlusion and perspective prevent calibrated photogrammetry. Broad candidate values, not pixel-derived survey.',
          'uncertainty': '±6–7m planning allowance; not a statistical confidence interval; exact roof finial and ground datum unknown'},
        'roofProfiles': {'basis': 'estimated', 'sourceIds': ['axis-photo-2020', 'hall-photo-2020', 'roof-photo-2021'],
          'value': {'twoTierEaveHeightFractions': [.40, .72], 'twoTierTopHeightFractions': [.58, 1],
                    'threeTierEaveHeightFractions': [.36, .62, .83], 'threeTierTopHeightFractions': [.50, .73, 1],
                    'threeTierUpperPlanFactors': [.86, .72], 'twoTierUpperPlanFactors': [.82, .76],
                    'cornerLiftFraction': .045, 'roofThicknessM': .16, 'topRidgeDecorationAllowanceM': .72},
          'method': 'Visible stacked eaves, upturned corners and hipped-gabled roof rhythm simplified into curved surfaces. Ratios reproduce silhouette without asserting joinery survey.',
          'uncertainty': 'height fractions ±.06; plan factors ±.10; corner lift ±.8m; rear roof evidence incomplete'},
        'facade': {'basis': 'estimated', 'sourceIds': ['grand-official', 'axis-photo-2020', 'hall-photo-2020'],
          'value': {'bodyPlanFactor': .88, 'doorHeightFraction': .26, 'pillarRadiusM': .22,
                    'plinthHeightM': .5, 'latticePitchM': .60},
          'method': 'Visible yellow end walls, red pillars/doors, pale stone bases, green windows, gold plaque frames. Simplified repeated mesh detail; exact traditional components unknown.',
          'uncertainty': 'body inset ±.05, door fraction ±.06, pillar radius ±.10m, plinth ±.5m; plaque lettering pending'}}
    pending = ['whole monastery cadastral boundary', 'all auxiliary halls/grounds',
               'actual mountain DEM and terrace elevations', 'stairs and accessible entry/arrival',
               'full rear/side facade survey', 'plaque lettering and accurate painted decoration',
               'night appearance', 'runtime collision/browser/performance verification']
    spec = {'schemaVersion': 1, 'id': 'lingyin-temple', 'cityId': 'hangzhou',
            'scope': 'Five axial hall exterior candidates only; no claim of the full monastery or surveyed mountain terrain.',
            'anchor': {'lon': anchor[0], 'lat': anchor[1], 'basis': 'measured-on-OSM',
                       'method': 'area centroid of Grand Hall way434365024'},
            'sourceSnapshotSha256': source_hash,
            'sourceFeatureIds': [f'way/{i}' for i in ids], 'baseBuildingIdsToExclude': ids,
            'excludedFromObject': {'ticketBuildingWay': 195189679,
                                   'reason': 'shop=ticket and multilingual ticket-office names; not monastery extent'},
            'halls': halls, 'estimates': estimates, 'pendingSubscopes': pending,
            'groundPolicy': {'status': 'pending', 'candidate': 'all five halls at lm.y with zero relative ground offset',
                            'warning': 'A neutral isolated candidate base, not a factual terrain/terrace reconstruction; integration must bind actual elevations and paths before acceptance.'},
            'coordinatePolicy': {'cityId': 'hangzhou', 'sourceCRS': 'EPSG:4326',
                                 'dimensions': 'unscaled real metres; lm x/z/y already game units',
                                 'blenderAxes': ['east', 'north', 'up'], 'scaleOnce': geo['scale']},
            'materialAliases': {'walls': 'gold', 'wood': 'civicred', 'tiles': 'roof',
                                'window': 'darkglass', 'stone': 'concrete', 'paint': 'landmarkglass'},
            'materialLimit': 'Uses existing B materials; gold wall alias is only a provisional color and must become matte ochre before visual acceptance.',
            'budget': {'maxTriangles': 25000, 'maxMaterials': 8, 'lights': 0}}
    spec_hash = write('spec.json', spec)
    claims = {'scope': spec['scope'], 'sources': sources,
              'identityLinks': [{'osm_id': 434366739, 'osmName': '灵隐寺文物展厅',
                 'interpretation': 'the same mapped fourth axial compound as Dharma Hall/Sutra Library',
                 'basis': 'reported-and-location-cross-check',
                 'sourceIds': ['dharma-official', 'exhibition-official', 'osm-geofabrik'],
                 'reason': 'Official exhibition page places it on first basement floor of Dharma Hall north of Medicine Hall; no extra sixth hall fabricated.'}],
              'conflicts': ['Official2013 area130亩 vs official2014 >150亩; cadastral boundary unknown, no boundary invented.',
                            f"Grand Hall reported area1200m² vs OSM roof polygon area{halls[1]['footprintAreaM2']:.1f}m²: measurement endpoints/roof overhang not equivalent.",
                            'English GrandHall one-story/three-floored wording is ambiguous; Chinese single-layer three-eave roof controls shell, not three occupiable floors.',
                            'Official overview illustration is uncalibrated artwork, not measured layout or photogrammetry.']}
    claims_hash = write('source-claims.json', claims)
    evidence = {'schemaVersion': 1, 'placeId': 'lingyin-temple', 'scope': spec['scope'],
                'identity': {'status': 'confirmed', 'sourceIds': ['temple-2014', 'intro-official', 'osm-geofabrik']},
                'location': {'crs': 'EPSG:4326', 'center': anchor, 'status': 'confirmed', 'sourceIds': ['osm-geofabrik']},
                'sources': sources, 'observations': [
                    {'kind': 'footprint', 'value': {'fiveHallWays': ids, 'count': 5}, 'unit': 'EPSG:4326',
                     'basis': 'measured', 'sourceIds': ['osm-geofabrik', 'exhibition-official'],
                     'uncertainty': 'Measured on fixed OSM polygon data; source survey accuracy unknown; planning tolerance±5m. Roof/body boundaries not distinguished in OSM.'},
                    {'kind': 'height', 'value': {'grandM': 33.6},
                     'unit': 'm', 'basis': 'reported', 'sourceIds': ['grand-official', 'temple-2014'],
                     'uncertainty': 'Official reported height, not field-measured. Decimal precision does not establish survey accuracy or absolute ground datum.'},
                    {'kind': 'height', 'value': {'secondaryCandidateM': [20, 24, 23, 23]},
                     'unit': 'm', 'basis': 'estimated', 'sourceIds': ['kings-official','medicine-official','dharma-official','huayan-official','axis-photo-2020','hall-photo-2020'],
                     'uncertainty': 'Other four coarse estimated±6–7m as detailed in spec; cropped/occluded photos do not support calibrated photogrammetry; absolute ground elevations unknown.'},
                    {'kind': 'orientation', 'value': {'widthAxisEastCCWDeg': [math.degrees(h['widthAxisRadiansEastCCW']) for h in halls]},
                     'unit': 'degrees', 'basis': 'measured', 'sourceIds': ['osm-geofabrik', 'temple-2014'],
                     'uncertainty': 'Computed minimum-area rectangles of source polygons; planning±3deg, not measured survey accuracy. Southeast facade/uphill northwest linked by official hall sequence.'},
                    {'kind': 'silhouette', 'value': 'Five distinct axial shells; Grand Hall triple eaves/hipped-gabled roof; other visible paired eaves, upward corners, red timber rhythm and yellow end walls.',
                     'unit': None, 'basis': 'estimated', 'sourceIds': ['temple-2014', 'axis-photo-2020', 'hall-photo-2020', 'roof-photo-2021'],
                     'uncertainty': 'Reference-informed exterior only; Huayan and Kings roof extents partly obscured/cropped; exact roof joinery, ornament and backside pending.'}],
                'blockers': [], 'pendingSubscopes': pending, 'conflicts': claims['conflicts'],
                'sourceSnapshots': {f'{PREFIX}/geofabrik-lingyin-features.geojson': feature_hash,
                                    f'{PREFIX}/source-claims.json': claims_hash, f'{PREFIX}/spec.json': spec_hash},
                'photosBundled': False, 'stageLimit': 'evidence-ready for five-shell candidate scope only; no modelled/verified without actual GLB and named current checks'}
    write('evidence.json', evidence)
    write('task-catalog.json', {'places': [{'id': 'lingyin-temple', 'name': '灵隐寺五重殿外壳候选',
        'kind': 'building-group', 'location': {'center': anchor}, 'sources': sources,
        'modeling': {'blockers': []}, 'scope': spec['scope']}]})
    print(json.dumps({'hallWays': ids, 'anchor': anchor, 'heightBasis': [h['heightBasis'] for h in halls],
                      'specSha256': spec_hash, 'buildingExtractSha256': hashlib.sha256(buildings_path.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
