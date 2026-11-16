"""Freeze City Balcony references and source geometry without importing bpy."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys
from shapely.geometry import LineString, Polygon, shape
from shapely.ops import transform
from shapely import constrained_delaunay_triangles

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city
OUT=Path(__file__).resolve().parent
PREFIX=str(OUT.relative_to(ROOT));DATE='2026-10-14'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    p=OUT/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return digest(p)
def triangles(poly):
    # Offset clipping can leave numerically collinear triangles on one edge.
    # Remove zero-area construction faces, while requiring preserved coverage.
    ts=[list(t.exterior.coords)[:-1] for t in constrained_delaunay_triangles(poly).geoms if t.area>1e-8]
    ts=[t if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(t,t[1:]+t[:1]))>0 else t[::-1] for t in ts]
    assert abs(sum(Polygon(t).area for t in ts)-poly.area)<1e-6, 'incomplete constrained source triangulation'
    return [[[float(v) for v in p] for p in t] for t in ts]

def main():
    geo=load_city('hangzhou')['geography'];e,n=geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    buildings=json.loads((ROOT/'data/processed/hangzhou/buildings.geojson').read_text())['features'];byid={f['id']:f for f in buildings}
    main=byid['relation/8718551'];parts=[byid['way/'+str(i)] for i in [626826744,626826741,626826742]]
    assert main['properties']['name']=='城市阳台';p=shape(main['geometry']);assert len(p.geoms)==1
    p=p.geoms[0];assert len(p.interiors)==3
    anchor=[p.centroid.x,p.centroid.y]
    metric=transform(lambda x,y,z=None:((x-anchor[0])*e,(y-anchor[1])*n),p)
    rc=list(metric.minimum_rotated_rectangle.exterior.coords)
    edges=[(math.dist(a,b),math.atan2(b[1]-a[1],b[0]-a[0])) for a,b in zip(rc,rc[1:])]
    axis=max(edges)[1]%math.pi;ca,sa=math.cos(axis),math.sin(axis)
    def uv(ring):return [[(x-anchor[0])*e*ca+(y-anchor[1])*n*sa,-(x-anchor[0])*e*sa+(y-anchor[1])*n*ca] for x,y in ring]
    outer=uv(list(p.exterior.coords)[:-1]);holes=[uv(list(h.coords)[:-1]) for h in p.interiors]
    upper=Polygon(outer,holes)
    paving_band=LineString(outer[:7]).buffer(11,single_sided=True,join_style=2).intersection(upper)
    rest=upper.difference(paving_band)
    upper_triangles=triangles(paving_band)+triangles(rest)
    upper_materials=['roof']*len(triangles(paving_band))+['concrete']*len(triangles(rest))
    assert abs(sum(Polygon(t).area for t in upper_triangles)-upper.area)<1e-6
    # Source rear vertices delineate two explicitly mapped approach fingers. The lower
    # public body stops at their shore-side junctions; no floor seals the space
    # beneath both mapped bridges. This is a source-registered candidate section.
    lower_ring=[outer[i] for i in [0,1,2,3,4,5,6,7,11,12,17]]
    lower=Polygon(lower_ring,holes);assert lower.is_valid
    entrances=[{'id':'west','sourceEdgeVertexIndices':[13,16], 'outerUVMetres':[(outer[13][i]+outer[16][i])/2 for i in [0,1]]},
               {'id':'east','sourceEdgeVertexIndices':[9,10], 'outerUVMetres':[(outer[9][i]+outer[10][i])/2 for i in [0,1]]}]
    for ent in entrances:
        u,v=ent['outerUVMetres'];ent['wgs84']=[anchor[0]+(u*ca-v*sa)/e,anchor[1]+(u*sa+v*ca)/n]
        ent['basis']='measured-on-source outer approach edge midpoint; not a verified arrival'
    radius=p.buffer(.00055)
    context={}
    for kind in ['roads','green','water','places']:
        fs=json.loads((ROOT/('data/processed/hangzhou/'+kind+'.geojson')).read_text())['features']
        context[kind]=[f for f in fs if radius.intersects(shape(f['geometry'])) and
          not (kind=='places' and f['properties'].get('tags',{}).get('boundary'))]
    ph=digest(ROOT/'data/raw/hangzhou/zhejiang-261011.osm.pbf')
    assert ph=='4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9'
    for part,hole in zip(parts,holes):
        assert shape(part['geometry']).symmetric_difference(Polygon(list(p.interiors)[parts.index(part)])).area<1e-13
    snapshot=write('geofabrik-balcony-features.geojson',{'type':'FeatureCollection','crs':'EPSG:4326','license':'ODbL-1.0',
      'sourceSnapshotSha256':ph,'features':[main,*parts],'contextOnly':context})
    sources=[
      {'id':'osm-geofabrik','url':'https://download.geofabrik.de/asia/china/zhejiang-261011.osm.pbf','publisher':'OpenStreetMap contributors / Geofabrik',
       'accessedAt':DATE,'sourceDate':'2026-10-11T20:21:06Z','license':'ODbL-1.0','localPath':'data/raw/hangzhou/zhejiang-261011.osm.pbf','sha256':ph},
      {'id':'owner-project','url':'https://www.hzyjfz.cn/index.php?a=detail&id=45&m=project','publisher':'杭州钱江新城建设管理委员会项目网站（页脚署名；正文信息来源标为网络）',
       'accessedAt':DATE,'sourceDate':'2018-05-03','status':'actual TLS curl HTML/text read','sha256':digest(Path('<TEMP>/hz-balcony-owner.html')),
       'license':'unknown; reference only','use':'main80m projection/max320m width/28000m²; wings are separate2.4km landscape/garage/tunnel scope'},
      {'id':'zju-teaching','url':'https://cmicce.zju.edu.cn/mobile/teacher_case.aspx?id=208','publisher':'浙江大学传媒与国际文化学院继续教育中心',
       'accessedAt':DATE,'sourceDate':'2020-05-18','status':'actual web text read; direct curl/image timed out','license':'unknown; reference only',
       'use':'main322m long/80m projection,twolevels/24000m² per floor, identity; no roof/deck numerical survey'},
      {'id':'construction-engineer','url':'https://news.sohu.com/20070126/n247846969.shtml','publisher':'浙江在线·今日早报原创施工采访；搜狐刊载；记者钟黎明/总工苏永会',
       'accessedAt':DATE,'sourceDate':'2007-01-26','status':'actual native curl full interview read','sha256':digest(Path('<TEMP>/hz-balcony-construction.html')),
       'license':'unknown; reference only','use':'near200 concrete piers,steel/concrete structure,round roughly2m skylights; lower glass/upper open park and lifts were construction plans, not current operation verification'},
      {'id':'government-2020','url':'https://www.ehangzhou.gov.cn/2020-04/09/c_242801.htm','publisher':'杭州市人民政府新闻办公室英文门户',
       'accessedAt':DATE,'sourceDate':'2020-04-09','status':'actual page and official night aerial viewed','license':'unknown; reference only',
       'use':'one main/two side parks, identity/site night silhouette.12000m² on page is exhibition hall, NOT balcony area'},
      {'id':'ihg-context','url':'https://www.ihg.com/intercontinental/hotels/cn/zh/hangzhou/hghha/hoteldetail','publisher':'IHG / 杭州洲际酒店运营方',
       'accessedAt':DATE,'sourceDate':None,'status':'actual official hotel aerial viewed; Balcony is background context','license':'unknown; reference only',
       'use':'source-bound rear bridges and platform night outline/lamps, no surveyed or independent close balcony facade'},
      {'id':'photographer-2010','url':'https://dp.pconline.com.cn/photo/list_1941203.html','publisher':'摄影师石上清流原创照片 / 太平洋摄影部落',
       'accessedAt':DATE,'sourceDate':'2010-09-27','status':'actual page and9 original street-level photographs viewed',
       'sha256':digest(Path('<TEMP>/hz-balcony-pconline.html')),'license':'author copyright; page explicitly prohibits unlicensed commercial photo use; reference only, no released photos',
       'use':'actual multiple directions: glass rails, tiled/wood-like deck, rear raised bridge with beams/piers, glazed room/pit, circle skylights; not calibrated or current2026 survey'},
      {'id':'hangzhou-publish-2020','url':'https://hznews.hangzhou.com.cn/chengshi/content/2020-08/14/content_7792495_0.htm','publisher':'杭州发布项目消息 / 杭州网刊载',
       'accessedAt':DATE,'sourceDate':'2020-08-14','status':'actual web text read','license':'unknown; reference only',
       'use':'glass-room identity and riverside promenade; interactive lighting described in2020, current fixtures/timing not verified'},
      {'id':'glass-2011','url':'https://zjnews.zjol.com.cn/05zjnews/system/2011/07/15/017681168.shtml','publisher':'浙江在线/现场记者姜晓蓉',
       'accessedAt':DATE,'sourceDate':'2011-07-15','status':'search-index original report text read','license':'unknown; reference only',
       'use':'tempered glass rails/lower restaurant context only. Historical maintenance incident not asserted as current condition.'}]
    est={
      'levels':{'basis':'estimated','value':{'lowerM':0,'upperM':6,'slabThicknessM':.65,'foundationDepthM':3},
       'sourceIds':['osm-geofabrik','construction-engineer','photographer-2010'],
       'method':'neutral isolated lower public-floor datum0; main OSM unverified height6 used as plausible separation, cross-checked with uncalibrated bridge/person proportions. Not a building height measurement or water elevation.',
       'uncertainty':'upper separation±2m/slab±.35m/foundation±2m; absolute ground and river levels unknown'},
      'glazedHeads':{'basis':'estimated','value':{'roofRiseM':3,'mullionPitchM':4.8},
       'sourceIds':['osm-geofabrik','photographer-2010','hangzhou-publish-2020'],
       'method':'three exact mapped glazed part footprints; low transparent heads and lower glazed walls inferred from real street photos. Uniform3m head is a limited reference-informed candidate, not mapped14/9/10m tag adopted as survey.',
       'uncertainty':'rise±1.5m, roof shape and full lower volume/atrium layout unknown; OSM absolute min6/top14/9/10 conflict retained'},
      'rails':{'basis':'estimated','value':{'heightM':1.2,'panelPitchM':2.7,'frameWidthM':.085},
       'sourceIds':['photographer-2010','glass-2011'],'method':'glass-panel and adult/bench contextual ratios, fine dark-metal top rail visible in actual opposing river directions',
       'uncertainty':'height±.25m,pitch±.7m,frame±.04m; full current panel inventory unknown'},
      'structure':{'basis':'estimated','value':{'pierPitchM':14,'pierWidthM':1.25,'bridgeBeamDepthM':.8},
       'sourceIds':['construction-engineer','photographer-2010','osm-geofabrik'],
       'method':'coarse interior grid under true platform/source approach fingers; rear bridge transverse beams/rectangular piers visible. Report near200 original piers does not locate them.',
       'uncertainty':'grid phase±7m,pitch±4m,width±.5m; representative piers are not actual surveyed200 positions'},
      'skylights':{'basis':'estimated','value':{'radiusM':1,'count':6,'railInsetM':8},
       'sourceIds':['construction-engineer','photographer-2010'],'method':'reported roughly2m diameter circle skylights and actual photos;6 representative circles spaced on rear-free public deck, exact positions/count pending',
       'uncertainty':'radius±.25m,position±8m,count unknown; candidate represents observed feature without claiming inventory'},
      'paving':{'basis':'estimated','value':{'riverBandDepthM':11,'tilePitchM':4.5,'jointWidthM':.035},
       'sourceIds':['photographer-2010'],'method':'dark gray/light gray pavement and warmer slatted strip from actual ground views; sparse seams/strip within source polygon, not copied texture',
       'uncertainty':'band depth±4m,tile coarse representation not actual measured unit; all current park furniture/planting pending'}}
    pending=['surveyed platform/ground/river elevations and independent upper/lower floor section',
      'actual current steps/ramps/lifts/door locations and accessible road-to-walking arrival route',
      'lower museums/art/restaurant operation and interiors;2007 proposal is not current playable content',
      'precise3glass-room roofs/pits and OSM6/14/9/10 vertical tag reconciliation',
      'all foundation/piers and riverbank retaining/protection geometry',
      'full2.4km side balconies/CBDpark, wave culture city relation8718552 and landscaping',
      'actual skylight inventory/pavement joints/furniture/planting/signs',
      'night fixtures/current projection program, current in-game day/night3views, collision and performance']
    spec={'schemaVersion':1,'id':'city-balcony','cityId':'hangzhou',
      'scope':'Limited main balcony exterior: exact source cantilever plan and two explicitly mapped shore approach fingers, open upper park and lower glazed facade/public-floor outline, three mapped glass heads, transparent rails, representative structural beams/piers and round skylights. No invented stair/ramp/lift operation or whole side parks.',
      'anchor':{'lon':anchor[0],'lat':anchor[1],'basis':'measured-on-OSM','method':'area centroid subtracting three inner rings'},
      'axisRadiansEastCCW':axis,'sourceSnapshotSha256':ph,
      'sourceFeatureIds':['relation/8718551',*['way/'+str(i) for i in [626826744,626826741,626826742]]],
      'baseBuildingIdsToExclude':[8718551,626826744,626826741,626826742],
      'upperOuterWGS84':list(p.exterior.coords)[:-1],'upperOuterUVMetres':outer,'glazedFootprintsUVMetres':holes,
      'lowerOuterUVMetres':lower_ring,'upperTrianglesUVMetres':upper_triangles,'upperTriangleMaterials':upper_materials,
      'lowerTrianglesUVMetres':triangles(lower),
      'shoreApproachEdges':entrances,'estimates':est,'pendingSubscopes':pending,
      'coordinatePolicy':{'dimensions':'unscaled real metres','lmAnchor':'already game-unit x/z/y; y is neutral lower floor unless integrator binds surveyed datum','scaleOnce':geo['scale'],'blenderAxes':['east','north','up']},
      'budget':{'maxTriangles':28000,'maxMaterials':7,'maxBytes':8388608,'lights':0},
      'waterPolicy':{'createWaterMeshes':False,'sourceContextWaterId':'relation/8227206','datum':'unknown; base pipeline owns Qiantang River'},
      'integrationContract':{'groundFootprints':'Only actual candidate piers/glass-wall strips, not a whole balcony cylinder. deck_height_game handles explicit floor selection; underlying main terrain/water/topology stays independent.',
       'sourceExclusions':'Only this main relation and its3parts. Leave separate unnamedway626891122, wave culture city8718552, theatre/ICC,green/water and all roads.',
       'roads':'157967583/585 are layer-1 Zhijiang road tunnels. Their geometric crossing with platform is not a road junction; no shared pedestrian source node proves connected entrance.',
       'arrival':'Two mapped outer-edge midpoints are candidate shore connectors, not verified arrival points. No source stair/ramp location; no invented accessible-route claim.',
       'materials':'Existing concrete/darkglass/landmarkglass/steel/roof/park aliases are provisional. Main integrator owns transparent glass, subtle paving/vegetation, reflection/night budget.',
       'formalAcceptance':'All eight skill checks remain unknown; host triangles/previews only.'}}
    sh=write('spec.json',spec)
    mh=write('osm-measurements.json',{'anchorWGS84':anchor,'axisDegreesEastCCW':math.degrees(axis),
      'upperSourceAreaM2':upper.area,'lowerCandidateAreaM2':lower.area,'upperBoundsUVMetres':upper.bounds,
      'minimumRotatedRectangleM':[max(x[0] for x in edges),min(x[0] for x in edges)],
      'method':'fixed local e/n coefficients; source polygon centroid excluding holes, source minimum rotated rectangle axis; not land survey',
      'sourceHeightTags':{f['id']:f['properties']['tags'] for f in [main,*parts]},
      'contextFeatureIds':{k:[f['id'] for f in fs] for k,fs in context.items()},
      'sourceAccuracy':'unknown; planning placement±5m/orientation±3deg is a modelling estimate, not statistical precision',
      'sourceDifferences':['reported320/322/332m labels differ; map envelope≈325m includes approaches, projection80m is bank-relative, not the full162.9m envelope.',
        'owner28000m²/teachingonefloor24000m²/press20000m² describe differing scopes. Source main-minusholes28348.8m² is map area, not building survey.',
        'source mainheight6 andparts14/9/10 min6 are unverified tags, not auto measured. Actual head section keptestimated3±1.5m above candidate deck.',
        'near200piers and lift/restaurant/museum plans are2007 construction account; no current operation, exact structure count or path claim.']})
    ch=write('source-claims.json',{'sources':sources,'reported':{'primaryWidthM':320,'constructionLengthM':322,'projectionFromBankM':80,
      'ownerAreaM2':28000,'teachingOneFloorAreaM2':24000,'twoMainLevels':True,'upperOpenPark':True,'lowerGlazed':True,
      'constructionPierCountApprox':200,'skylightDiameterApproxM':2},'estimates':est,'pendingSubscopes':pending})
    evidence={'schemaVersion':1,'placeId':'city-balcony','scope':spec['scope'],
      'identity':{'status':'confirmed','sourceIds':['osm-geofabrik','owner-project','government-2020']},
      'location':{'crs':'EPSG:4326','center':anchor,'status':'confirmed','sourceIds':['osm-geofabrik']},'sources':sources,
      'observations':[
        {'kind':'footprint','value':{'relationId':8718551,'mappedInnerGlazedParts':3,'areaM2':upper.area,'axisEnvelopeM':max(x[0] for x in edges)},'unit':'m/EPSG:4326','basis':'measured',
         'sourceIds':['osm-geofabrik'],'uncertainty':'map geometry calculation only; actual source accuracy unknown, planning±5m'},
        {'kind':'height','value':est['levels']['value'],'unit':'m relative to isolated lower floor','basis':'estimated','sourceIds':est['levels']['sourceIds'],'uncertainty':est['levels']['uncertainty']},
        {'kind':'orientation','value':math.degrees(axis),'unit':'degrees east CCW','basis':'measured','sourceIds':['osm-geofabrik','ihg-context'],'uncertainty':'mapped long axis and primary night aerial match; modelling phase±3deg not survey'},
        {'kind':'silhouette','value':'elongated cantilever body with open park above glazed lower frontage, three source-mapped glass heads/skylight wells and separate shore approach fingers, clear glass rails and rectangular beams/piers',
         'basis':'reported','unit':None,'sourceIds':['owner-project','construction-engineer','photographer-2010','government-2020','ihg-context'],
         'uncertainty':'two official aerial/context and9actualstreet views; exact vertical section, lower full facades/entries and current2026 condition unverified'}],
      'blockers':[],'pendingSubscopes':pending,'photosBundled':False,
      'sourceSnapshots':{PREFIX+'/geofabrik-balcony-features.geojson':snapshot,PREFIX+'/osm-measurements.json':mh,PREFIX+'/source-claims.json':ch,PREFIX+'/spec.json':sh},
      'stageLimit':'limited source-bound exterior evidence-ready, no model/export/runtime/whole-site claim'}
    write('evidence.json',evidence)
    write('task-catalog.json',{'places':[{'id':'city-balcony','name':'城市阳台主挑台独立候选','kind':'civic-platform','location':{'center':anchor},'sources':sources,'scope':spec['scope'],'modeling':{'blockers':[]}}]})
    print(json.dumps({'anchorWGS84':anchor,'axisDegrees':math.degrees(axis),'areaM2':upper.area,'triangulationAreaVerified':True,'specSha256':sh}))

if __name__=='__main__':main()
