"""Freeze finite source-bound Bai/Su paths, green banks and seven bridge candidates.

Only this object's research directory is written. No Blender or city_mesh import.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
from city_config import load_city

BAI = [4326974,29416781,28538285,28538286,28538289,28538290]
SU = [4335991,975869980,30072125,30072127,30075392,30075393,30072130,
      30072131,30072139,30072138,30072144,30072145,30072147,30072148]
# Original government publication gives per-bridge core body length/net width/span.
REPORTED = {30072125:('跨虹桥',21.1,4.3,8.1),30075392:('东浦桥',16.8,4.3,5.9),
            30072130:('压堤桥',16.9,4.0,6.3),30072139:('望山桥',16.9,7.0,4.7),
            30072144:('锁澜桥',16.9,6.4,6.2),30072147:('映波桥',17.0,7.0,7.4)}
GREEN = [30072122,30072129,30072136,30072142,975357027,28538305,20083745]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,j):
    p=HERE/name;p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');return sha(p)
def metric(p,a,g): return [(p[0]-a[0])*g['eastMetresPerDegree'],(p[1]-a[1])*g['northMetresPerDegree']]
def length(points): return sum(math.dist(p,q) for p,q in zip(points,points[1:]))
def area(r): return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(r,r[1:]+r[:1]))/2)

def main():
    manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    g=load_city('hangzhou')['geography'];anchor=[120.138,30.246]
    for key in ('roads','green','water','places'):
        assert sha(ROOT/f'data/processed/hangzhou/{key}.geojson')==manifest['sha256'][key]
    roads=json.loads((ROOT/'data/processed/hangzhou/roads.geojson').read_text())['features']
    byid={f['properties']['osm_id']:f for f in roads}
    selected=[byid[i] for i in BAI+SU]
    green=json.loads((ROOT/'data/processed/hangzhou/green.geojson').read_text())['features']
    greens=[next(f for f in green if f['properties']['osm_id']==i) for i in GREEN]
    water=next(f for f in json.loads((ROOT/'data/processed/hangzhou/water.geojson').read_text())['features'] if f['properties']['osm_id']==2308774)
    jindai=next(f for f in json.loads((ROOT/'data/processed/hangzhou/places.geojson').read_text())['features'] if f['properties']['osm_id']==1466925248)
    correspondences=[]
    for ix,way in [(17,30072122),(18,30072129),(19,30072136),(23,30072142),(28,28538305)]:
        wr=water['geometry']['coordinates'][0][ix]
        gr=next(f for f in greens if f['properties']['osm_id']==way)['geometry']['coordinates'][0][0]
        assert set(map(tuple,wr))==set(map(tuple,gr))
        correspondences.append({'waterFeature':'relation/2308774','waterPolygon':0,'waterHole':ix,'greenFeature':f'way/{way}',
                                'coordinateSetExact':True,'note':'source geometry correspondence, not a surveyed land/bridge height'})
    sources=[{'id':'geofabrik-fixed','url':manifest['source']['sourceUrl'],'publisher':'OpenStreetMap contributors / Geofabrik',
        'sourceDate':manifest['source']['osmReplicationTimestamp'],'accessedAt':'2026-10-14','status':'fixed-source-verified',
        'license':'ODbL-1.0; © OpenStreetMap contributors','localPath':'data/processed/hangzhou/roads.geojson','sha256':manifest['sha256']['roads'],
        'pbfSha256':manifest['source']['sha256'],'use':'EPSG:4326 node IDs/geometry; not commercial map coordinates or field survey'},
       {'id':'unesco-nomination','url':'https://whc.unesco.org/uploads/nominations/1334.pdf',
        'publisher':'China State Party nomination, published by UNESCO World Heritage Centre','accessedAt':'2026-10-14',
        'sourceDate':'2011 PDF metadata; aerial photographs 2006; elevation survey date unknown','status':'read-local-original-and-rendered',
        'sha256':'5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442','bytes':79121258,'pages':1342,
        'localPath':None,'license':'unknown; reference only; page images excluded from runtime/release texture assets',
        'reviewedPages':[{'pdfPage':59,'printedPage':64,'figures':['2a-7','2a-8'],'use':'reported dimensions, two causeways and aerial layouts'},
                         {'pdfPage':70,'printedPage':75,'use':'six named stone arches, willow/peach and relative water height'},
                         {'pdfPage':78,'printedPage':83,'figure':'2a-22','use':'six separate arch elevations, gradual bridge approaches; survey epoch unknown'}]},
       {'id':'hangzhou-release-six-bridges','url':'https://m.thepaper.cn/newsDetail_forward_19443734',
        'publisher':'杭州发布 · 杭州市人民政府新闻办公室官方账号；资料/杭州西湖风景名胜区管委会',
        'title':'苏堤上的六座桥你能认全吗？谁取的名？一起探寻西湖里的小秘密','sourceDate':'2022-08-13',
        'accessedAt':'2026-10-14','status':'downloaded-and-photos-reviewed','license':'unknown; reference only; not runtime textures',
        'localPath':str((HERE/'references/hangzhou-release-six-bridges.html').relative_to(ROOT)),
        'sha256':sha(HERE/'references/hangzhou-release-six-bridges.html'),
        'use':'individual bridge reported core length/net width/clear span; photographed stone arches and railings'},
       {'id':'jindai-original-photographer','url':'https://historicbridges.org/bridges/browser/photos.php?bridgebrowser=china/jindaibridge/&gallerynum=2&gallerysize=2',
        'publisher':'Nathan Holth / HistoricBridges.org original photographic documentation',
        'accessedAt':'2026-10-14','sourceDate':'2017-10-05 gallery documentation date','status':'downloaded-and-original-photos-reviewed',
        'localPath':str((HERE/'references/jindai-photographer-gallery.html').relative_to(ROOT)),
        'sha256':sha(HERE/'references/jindai-photographer-gallery.html'),
        'license':'© Nathan Holth / HistoricBridges.org. All rights reserved; reference only. No runtime photo textures.',
        'use':'explicitly captioned western Jindai views: single arch amid long ramps; plain low stone parapet, courses; no metric claim'}]
    paths=[];chains=[]
    for group,ids in [('bai',BAI),('su',SU)]:
        chain=[];total=0
        for i in ids:
            f=byid[i];ps=f['geometry']['coordinates'];nodes=f['properties']['nodeIds'];l=length([metric(p,anchor,g) for p in ps])
            if chain:
                assert chain[-1]['endNode']==nodes[0] and chain[-1]['endWGS84']==ps[0], 'Noncontinuous source chain'
            chain.append({'wayId':i,'startNode':nodes[0],'endNode':nodes[-1],'startWGS84':ps[0],'endWGS84':ps[-1],'lengthM':l})
            total+=l
            bridge=None
            if i in REPORTED:
                name,core,width,span=REPORTED[i]
                assert f['properties']['name']==name and f['properties']['tags']['bridge']=='yes'
                bridge={'archCount':1,'coreBodyLengthM':core,'netTravelWidthM':width,'clearArchSpanM':span,'basis':'reported',
                    'sourceIds':['hangzhou-release-six-bridges'],'notes':'source core length differs from OSM bridge-and-approach way; not a current survey',
                    'archPositionFraction':.5,'archPositionUncertaintyM':3.0,'springHeightM':-1.15,
                    'archRingThicknessM':.55,'pavementThicknessM':.20,'parapetStyle':'open-stone-rail',
                    'railHeightM':1.0,'railPitchM':2.7,'estimatedVerticalUncertaintyM':.9}
            elif i==28538285:
                bridge={'archCount':1,'coreBodyLengthM':10.0,'netTravelWidthM':8.6,'clearArchSpanM':6.5,'basis':'estimated',
                    'sourceIds':['geofabrik-fixed','jindai-original-photographer'],'notes':'mapped bridge-area width plus adult/parapet proportions in original oblique photographs; no copied Broken Bridge metric as reported',
                    'widthUncertaintyM':1.5,'spanUncertaintyM':2.0,'coreLengthUncertaintyM':3.0,
                    'archPositionFraction':.5,'archPositionUncertaintyM':12.0,'springHeightM':-1.5,
                    'archRingThicknessM':.60,'pavementThicknessM':.20,'parapetStyle':'solid-stone-panel',
                    'railHeightM':.85,'railPitchM':3.0,'estimatedVerticalUncertaintyM':1.2}
            if i!=28538289:
                paths.append({'sourceId':f'way/{i}','wayId':i,'label':f['properties']['name'],'causeway':group,
                    'nodes':nodes,'coordinatesWGS84':ps,'sourceLengthM':l,'tags':f['properties']['tags'],'bridge':bridge,
                    'flatTravelWidthM':8.6 if group=='bai' else 7.2,
                    'widthBasis':'estimated; source ways have no width tag; approach widths taper from candidate flat width to individual bridge net width',
                    'widthUncertaintyM':2.0})
        chains.append({'causeway':group,'sequence':chain,'lengthM':total,'continuity':'exact node IDs AND coordinates match; no invented geometric junction',
            'externalBridgeOwner':'scripts/landmarks/broken_bridge.py' if group=='bai' else None})
    save('source-geometry.geojson',{'type':'FeatureCollection','crs':'EPSG:4326','license':'ODbL-1.0',
        'pbfSha256':manifest['source']['sha256'],'features':selected+greens+[jindai]})
    save('source-water-boundary.geojson',{'type':'FeatureCollection','crs':'EPSG:4326','license':'ODbL-1.0','features':[water],
        'note':'read-only shoreline reference. Candidate never builds water geometry.'})
    save('shoreline-correspondence.json',{'exactLandWaterHoleMatches':correspondences,
        'baiWesternGreen':'relation/20083745 is a source-bound strip joined to Gushan, not the entire Gushan island',
        'suSouthernGreen':'way/975357027 is the mapped southern bank strip; underlying lake exterior boundary remains owned by base water pipeline',
        'knownConflict':'Bai 29416781 road is near the old island edge; source centerline and shore are independently retained, no guessed re-registration. Source accuracy unknown.'})
    save('path-connectivity.json',{'chains':chains,'externalWayNotBuilt':28538289,
        'sourceExtractsSha256':{k:manifest['sha256'][k] for k in ('roads','green','water','places')},
        'method':'canonical Hangzhou WGS84 local e/n unscaled metric, original source node chain; lengths include stated source endpoints, not survey endpoints'})
    land=[{'sourceId':f"{f['properties']['osm_type']}/{f['properties']['osm_id']}",
        'ringsWGS84':f['geometry']['coordinates'][0],'tags':f['properties']['tags'],
        'topHeightM':-.03,'heightBasis':'estimated neutral road endpoint datum; not surveyed vegetation/ground height'} for f in greens]
    pending=['current road endpoints/absolute terrain and lake water level; UNESCO0.4m is historical relative water offset, not DEM sea-level height',
        'exact per-bridge arch position/spring/crest/ramp vertical profiles; Jindai net width/span/body length remain estimated',
        'Bai source road/old shore offset; banks and travel ribbons retain independent source positions until runtime/water seam inspection',
        'full current carved rail motifs/bridge inscriptions/lamps/stele pavilion, junction gates, benches and stair geometry',
        'exact willow/peach tree counts/locations and pruning/canopy avoidance; base vegetation must be reconciled by main integrator',
        'water/green duplicate visual exclusion, pedestrian surface heights, source branch tie-ins, collision and arrival validation',
        'actual GLB export and daytime/nighttime game top/street/distant screenshots; browser/performance acceptance']
    spec={'schemaVersion':1,'id':'west-lake-causeways','cityId':'hangzhou',
        'scope':'Fixed Bai/Su centerline travel ribbons, seven distinct single-arch bridges and seven source land strips/shore coping; external Broken Bridge, water, exact planted tree inventory and pavilion excluded.',
        'anchor':{'lon':anchor[0],'lat':anchor[1],'basis':'source bounding-area local modeling origin, not a named destination'},
        'sourceSnapshotSha256':manifest['source']['sha256'],'sourceExtractsSha256':{k:manifest['sha256'][k] for k in ('roads','green','water','places')},
        'sourceFeatureIds':[f"way/{i}" for i in BAI+SU if i!=28538289]+[f"{f['properties']['osm_type']}/{f['properties']['osm_id']}" for f in greens]+['way/1466925248','relation/2308774'],
        'paths':paths,'landStrips':land,'externalWayIds':[28538289],'keepNavigationWayIds':BAI+SU,
        'baseBuildingIdsToExclude':[],'baseRoadIdsToSuppressVisual':[i for i in BAI+SU if i!=28538289],
        'baseGreenIdsToSuppressVisual':[f"{f['properties']['osm_type']}/{f['properties']['osm_id']}" for f in greens],
        'bankBottomM':-1.0,'bankCopingTopM':.06,'bankCopingWidthM':.28,'bankHeightBasis':'estimated ±.5m vertical, ±.15m coping; independent of historical0.4m relative lake report',
        'landSurfacePolicy':'subtract all travel ribbons and bridge corridors from grass caps; not generic solid building colliders; source boundaries not moved',
        'coordinatePolicy':{'horizontalAndVerticalScaleOnce':.6,'dimensions':'unscaled real metres','lm':'x/z/y already game units; y is source-road endpoint datum','axes':['east','north','up']},
        'waterPolicy':{'createMeshes':False,'sourceLake':'relation/2308774','datum':'unknown; parent/base-water controls current datum','bridgeVoid':'open beneath semicircle; do not extend flat land caps across bridge road ways'},
        'integrationContract':{'walking':'bind bridge_height_at and walk_surfaces; preserve original source nodes/nav edges; flat endpoints meet lm.y',
            'collision':'main travel/green surfaces are walkable; do not place them in solid-building ground_footprints; rail barriers separate',
            'topology':'no joining based on geometric crossings; external Broken Bridge exact shared nodes retained',
            'vehicleRouting':'source motorcar/motor_vehicle bans retained; choose permitted road then walking transfer for driving jobs; scenic electric tour-car handling remains parent policy',
            'water':'main water pipeline retains source lake holes/channels; candidate has no water meshes; inspect arch spring and bank bottom against current runtime water'},
        'pendingSubscopes':pending,'budget':{'maxTriangles':60000,'maxMaterials':12,'maxBytes':12582912,'lights':0,'textures':0}}
    save('spec.json',spec)
    # Photos are research references only, never supplied to B mesh/material interfaces.
    image_sources=[]
    for file,parent in [('fetches.json','hangzhou-release-six-bridges'),('jindai-fetches.json','jindai-original-photographer')]:
        for f in json.loads((HERE/'references'/file).read_text()):
            if f.get('sha256'):image_sources.append(dict(f,parentSourceId=parent,use='research-only',license='copyright/permission not established for asset publication'))
    save('reference-manifest.json',{'sources':sources,'images':image_sources,'runtimePhotoTextures':False,'releaseImagesAuthorized':False,
         'renderedReferencePages':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'sourceId':'unesco-nomination','use':'research-only'} for p in (HERE/'references').glob('unesco-*.png')]})
    save('photo-review.json',{'reviewedAt':'2026-10-14','reviewedBy':'ali_evidence',
        'views':[{'source':'unesco-nomination','file':'references/unesco-causeway-aerial-p59.png','view':'aerial Su/Bai, photographed2006',
            'supports':'long narrow planted banks; two geometrically distinct causeways, six Su crossings; not precise current shoreline or tree count'},
           {'source':'unesco-nomination','file':'references/unesco-six-elevations-p78.png','view':'six side elevations; survey date unknown',
            'supports':'single arch per named bridge, distinct envelope sizes and sloping ramps; printed Zhenlan label crosswalk is contextual Suolan, not a seventh bridge'},
           {'source':'hangzhou-release-six-bridges','files':['references/hangzhou-release-879.jpg','references/hangzhou-release-887.jpg','references/hangzhou-release-891.jpg','references/hangzhou-release-892.jpg','references/hangzhou-release-893.jpg','references/hangzhou-release-895.jpg','references/hangzhou-release-897.jpg'],
            'view':'elevated long view, pedestrian rail closeups and water-side bridge elevations',
            'supports':'mapped north/south bridge sequence; semicircular void, visible rectangular stone courses, low open carved rail panels, willows near water; no surveyed georegistration'},
           {'source':'jindai-original-photographer','files':['references/little_7westlakecausewaywalk_brg_09582.jpg','references/little_7westlakecausewaywalk_brg_09588.jpg','references/little_7westlakecausewaywalk_brg_09519.jpg'],
            'view':'captioned western Jindai oblique side, near/far side along ramps, ordinary Bai rail closeup',
            'supports':'one small arch amid long asphalt approaches, stone courses, low plain parapet; exact dimensions/night lights not verified'}],
        'notArchitectureEvidence':['hangzhou-release-882 is a historical painting, not a current measured plan'],
        'differences':['UNESCO general6–8m span conflicts with specific2022 Wangshan4.7m, Dongpu5.9m; per-bridge reported values adopted.',
            '2011 Su/Bai widths include planted land, while narrow bridge net width/core length differ; OSM line lengths include approaches.',
            'No current2026 field photographs or calibrated bridge vertical alignment; geometry remains finite reference-informed candidate.']})
    sources_path=save('source-list.json',{'places':[{'id':'west-lake-causeways','name':'西湖白堤/苏堤有限堤岸与七桥候选','kind':'area',
        'location':{'center':anchor},'sources':sources,'modeling':{'blockers':[]}}]})
    snapshots={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in ['source-geometry.geojson','source-water-boundary.geojson','shoreline-correspondence.json','path-connectivity.json','spec.json','photo-review.json','reference-manifest.json']}
    snapshots.update({str(p.relative_to(ROOT)):sha(p) for p in (HERE/'references').iterdir() if p.is_file() and p.suffix in ('.png','.jpg','.html')})
    evidence={'schemaVersion':1,'placeId':'west-lake-causeways','scope':spec['scope'],
        'identity':{'status':'confirmed','sourceIds':['geofabrik-fixed','unesco-nomination','hangzhou-release-six-bridges']},
        'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['geofabrik-fixed']},
        'sources':sources,'sourceSnapshots':snapshots,'blockers':[],'pendingSubscopes':pending,
        'observations':[{'kind':'extent','basis':'measured','unit':'m / EPSG:4326','value':{c['causeway']:c['lengthM'] for c in chains},'sourceIds':['geofabrik-fixed'],
            'uncertainty':'canonical unscaled WGS84 local projection of exact source-node polylines; includes source-defined approaches. OSM positional error unknown; not a field survey.'},
           {'kind':'extent','basis':'reported','unit':'m','value':{'baiLength':987,'baiLandWidth':33,'suLength':2797,'suLandWidthRange':[30,40]},'sourceIds':['unesco-nomination'],
            'uncertainty':'nomination2011 reportedland dimensions and different endpoints; not travel strip width or current survey. Model keeps fixed2026 mapped shape.'},
           {'kind':'layout','basis':'measured','unit':'source graph','value':{'sourceWays':20,'candidatePaths':19,'externalBridge':28538289,'suStoneBridgesNorthToSouth':[REPORTED[i][0] for i in SU if i in REPORTED],
               'landStrips':GREEN,'exactLakeHoleCrosswalks':{c['greenFeature']:c['waterHole'] for c in correspondences}},'sourceIds':['geofabrik-fixed','hangzhou-release-six-bridges'],
            'uncertainty':'all chain endpointnode IDs and coordinates exact; no geometry-only junction. Sourcegreen tags broad, not measured planting inventory; main coast/path registration remains pending.'},
           {'kind':'silhouette','basis':'reported','unit':'bridge construction','value':'six distinct Su single semicircular stone arches, gently sloped asphalt bridges with carved stone railings; interplanted willow/peach causeway banks',
            'sourceIds':['unesco-nomination','hangzhou-release-six-bridges'],'uncertainty':'official2006–2022 views/elevations, no claim of precise modern carving/tree/lighting reconstruction; see finite excluded subscopes.'},
           {'kind':'silhouette','basis':'estimated','unit':'m','value':{'jindaiSingleArchSpan':6.5,'netWidth':8.6,'archBodyLength':10,'archCenterFraction':.5},
            'sourceIds':['geofabrik-fixed','jindai-original-photographer'],'uncertainty':'mapped area plus photo proportions; span±2m,width±1.5m,body±3m,arch position±12m. Source photos confirm single arch/long ramps and low parapet; metric bounds not surveyed.'},
           {'kind':'bridge-dimensions','basis':'reported','unit':'m','value':{v[0]:{'coreLength':v[1],'netWidth':v[2],'clearSpan':v[3]} for v in REPORTED.values()},
            'sourceIds':['hangzhou-release-six-bridges'],'uncertainty':'individual2022government-page reported values, not all bridges6–8m; current source corridor lengths differ by approach extent.'},
           {'kind':'height','basis':'estimated','unit':'m above source endpoint neutral datum','value':{'suArchSpring':-1.15,'suRing':.55,'jindaiSpring':-1.5,'jindaiRing':.6,'pavement':.2,'grassTop':-.03,'stoneRailHeightRange':[.85,1.0]},
            'sourceIds':['unesco-nomination','hangzhou-release-six-bridges','jindai-original-photographer'],
            'uncertainty':'semicircle radius follows per-bridge span; spring/cover inferred from elevation and adult/rail proportions: crest±.9m(Su),±1.2m(Jindai), rails±.25m; absolute terrain/lake datum unknown.'}],
        'photosBundled':False,'researchReferencesArchived':True,'runtimePhotoTextures':False,
        'stageLimit':'evidence-ready finite candidate; no exported GLB, real game screenshot, collision or performance pass'}
    save('evidence.json',evidence)
    print(json.dumps({'pathCounts':len(paths),'bridgeCount':sum(bool(p['bridge']) for p in paths),'landCount':len(land),
        'lengths':{c['causeway']:c['lengthM'] for c in chains},'pbfSha256':manifest['source']['sha256'],'sourceManifestSha256':sources_path}))

if __name__=='__main__':main()
