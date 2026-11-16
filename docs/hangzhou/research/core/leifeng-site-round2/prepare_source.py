"""Fixed OSM land/water/source paths + hashed GLO30-v3 estimated ground."""
from pathlib import Path
import hashlib
import json
import math
import sys
sys.dont_write_bytecode=True
import numpy as np
from shapely.geometry import shape,Polygon,Point,LineString,box,mapping
from shapely.ops import transform,triangulate,unary_union
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
IDS=[975357010,340652169,1448129176,1448327494,1448327495,62124942]
def write(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    city=load_city('hangzhou');g=city['geography'];scale=g['scale'];tower_spec=ROOT/'docs/hangzhou/research/core/leifeng-round2/spec.json';tower=json.loads(tower_spec.read_text());anchor=tower['anchor'];ax,az=project(anchor['lon'],anchor['lat'],city)
    def en(x,y,z=None):return ((x-anchor['lon'])*g['eastMetresPerDegree'],(y-anchor['lat'])*g['northMetresPerDegree'])
    def wgs(x,y):return [anchor['lon']+x/g['eastMetresPerDegree'],anchor['lat']+y/g['northMetresPerDegree']]
    layers={k:json.loads((ROOT/f'data/processed/hangzhou/{k}.geojson').read_text())['features'] for k in ['green','water','roads','buildings','pois']}
    park=next(f for f in layers['green'] if f['id']=='way/975360504');land=transform(en,shape(park['geometry']));base=Polygon([en(*q) for q in tower['base']['footprintWGS84']]);area=land.area
    waters=[f for f in layers['water'] if f['id'] in ['relation/2308774','way/62124950']];wet=unary_union([transform(en,shape(f['geometry'])) for f in waters]);dry=land.difference(wet.buffer(2))
    buildings=[f for f in layers['buildings'] if transform(en,shape(f['geometry'])).intersects(land)];building_mask=unary_union([transform(en,shape(f['geometry'])) for f in buildings]);pad=base.buffer(3,join_style=2).difference(base);terrain_mask=dry.difference(building_mask.union(pad))
    terrain=ROOT/'artifacts/cities/hangzhou/terrain-glo30-v3';manifest=json.loads((terrain/'manifest.json').read_text());grid=manifest['grid'];arrays={}
    for name in ['dsm-egm2008-metres.bin','ground-estimate-egm2008-metres.bin']:
        p=terrain/name;assert sha(p)==manifest['files'][name]['sha256'];arrays[name]=np.fromfile(p,dtype='<f4').reshape(grid['rows'],grid['columns'])
    ground=arrays['ground-estimate-egm2008-metres.bin'];raw=arrays['dsm-egm2008-metres.bin']
    def sample(x,y,array=ground):
        u=(ax+x*scale-grid['x0'])/grid['step'];v=(az+y*scale-grid['z0'])/grid['step'];i=math.floor(u);j=math.floor(v);fx=u-i;fy=v-j
        a,b,c,d=[float(array[jj,ii]) for jj,ii in [(j,i),(j,i+1),(j+1,i+1),(j+1,i)]]
        return a+(b-a)*fx+(d-a)*fy if fx+fy<=1 else c+(d-c)*(1-fx)+(b-c)*(1-fy)
    padheight=sample(0,0);surfaces=[]
    def triangle_patches(poly,height,part):
        polygons=list(poly.geoms) if poly.geom_type=='MultiPolygon' else [poly] if poly.geom_type=='Polygon' else []
        for p in polygons:
            for tri in triangulate(p):
                if not p.covers(tri):continue
                points=list(tri.exterior.coords)[:-1]
                surfaces.append({'part':part,'verticesMetresENU':[[x,y,height(x,y)] for x,y in points]})
    xmin,ymin,xmax,ymax=terrain_mask.bounds;i0=max(0,math.floor((ax+xmin*scale-grid['x0'])/grid['step']));i1=min(grid['columns']-1,math.ceil((ax+xmax*scale-grid['x0'])/grid['step']));j0=max(0,math.floor((az+ymin*scale-grid['z0'])/grid['step']));j1=min(grid['rows']-1,math.ceil((az+ymax*scale-grid['z0'])/grid['step']))
    for j in range(j0,j1):
        for i in range(i0,i1):
            x=(grid['x0']+i*grid['step']-ax)/scale;y=(grid['z0']+j*grid['step']-az)/scale;step=grid['step']/scale
            corners=[(x,y),(x+step,y),(x+step,y+step),(x,y+step)]
            for ids in [[0,1,3],[1,2,3]]:
                triangle_patches(Polygon([corners[k] for k in ids]).intersection(terrain_mask),sample,'ground-estimate')
    terrain_count=len(surfaces);triangle_patches(pad.intersection(dry),lambda x,y:padheight,'base-apron-estimate')
    sourcepaths=[];road_features=[];profile_triangles=[]
    for ident in IDS:
        f=next(f for f in layers['roads'] if f['id']==f'way/{ident}');road_features.append(f);q=f['geometry']['coordinates'];points=[en(*p) for p in q];is_main=ident==340652169;is_step=f['properties']['tags'].get('highway')=='steps';width=12 if is_main else 2.8 if is_step else 3
        lengths=[0.0]
        for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a,b))
        heights=[sample(*p) for p in points];poly=LineString(points).buffer(width/2,cap_style=2,join_style=2).intersection(dry.difference(building_mask))
        def h_at(x,y):
            p=Point(x,y);best=None
            for i,(a,b) in enumerate(zip(points,points[1:])):
                line=LineString([a,b]);distance=line.distance(p);t=line.project(p)/line.length;h=heights[i]+(heights[i+1]-heights[i])*t
                if best is None or distance<best[0]:best=(distance,h)
            return best[1]+.06
        begin=len(surfaces);triangle_patches(poly,h_at,'path-'+str(ident));path_triangles=surfaces[begin:]
        profiles=[{'coordinateWGS84':p,'pointLocalMetresEN':list(v),'heightEstimatedEgm2008M':h,'sourceNodeId':n} for p,v,h,n in zip(q,points,heights,f['properties']['nodeIds'])]
        sourcepaths.append({'id':f['id'],'tags':f['properties']['tags'],'coordinatesWGS84':q,'nodeIds':f['properties']['nodeIds'],'sourceLengthM':lengths[-1],
          'estimatedWidthM':width,'widthErrorM':3 if is_main else 1.5,'profile':profiles,'clippedFootprintLocalMetres':mapping(poly),'surfaceTriangleCount':len(path_triangles),'status':'candidate-estimated','traversalAccepted':False,
          'type':'outdoor-escalator-plus-flanking-stairs static visual estimate; OSM tagged steps/name电梯' if is_main else 'steps' if is_step else 'footway',
          'heightErrorM':12,'heightMethod':'GLO30-v3 morph-filtered grid, piecewise-linear interpolation at exact source vertices; 50m real sample, no survey/stepscale precision'})
    main=next(p for p in sourcepaths if p['id']=='way/340652169');upper=max(main['profile'],key=lambda p:p['coordinateWGS84'][1]);point=Point(upper['pointLocalMetresEN']);gap=point.distance(base)
    epaths=[f for f in layers['roads'] if '3479012380' in f['properties'].get('nodeIds',[]) and f['id']!='way/340652169'];lowerjoins=[f['id'] for f in layers['roads'] if '3479012381' in f['properties'].get('nodeIds',[])];peak=next(f for f in layers['pois'] if f['id']=='node/5580634151');px,py=en(*peak['geometry']['coordinates'])
    # Shoreline follows frozen lake boundary; no invented water strip or shore wall.
    shoreline=land.intersection(wet).boundary.intersection(land.boundary.buffer(.1))
    sources=[park,*waters,*road_features,peak,*buildings]
    write('fixed-site-features.geojson',{'type':'FeatureCollection','sourcePbfSha256':tower['sourceSnapshotSha256'],'features':sources})
    spec={'schemaVersion':1,'id':'leifeng-site','cityId':'hangzhou','anchor':anchor,
      'scope':'finite mappedpark hill-ground estimate, source footways, static exterior escalator/flanking steps and narrow baseapron estimate; full plaza/gates/base-door/internal elevators/safe arrival unresolved',
      'sourceSnapshotSha256':tower['sourceSnapshotSha256'],'sourceHillParkId':park['id'],'sourcePeakId':peak['id'],'sourceWaterIds':[f['id'] for f in waters],
      'landMaskLocalMetres':mapping(dry),'terrainMaskLocalMetres':mapping(terrain_mask),'wetMaskLocalMetres':mapping(wet.intersection(land.buffer(15))),'terrainPatches':surfaces,'sourcePaths':sourcepaths,
      'renderTerrain':True,'renderWater':False,'baseBuildingIdsToExclude':[],
      'towerPlacement':{'frozenSpecPath':str(tower_spec.relative_to(ROOT)),'frozenSpecSha256':sha(tower_spec),'frozenModuleSha256':sha(ROOT/'scripts/landmarks/leifeng_pagoda.py'),
          'groundEstimateEgm2008M':padheight,'errorM':12,'heightBasis':'estimated filtered DSM; NOT archaeologicalground/architecturalfinishedfloor survey','recommendedYOffsetGameForEgmZero0':padheight*scale},
      'mainExteriorLift':{'sourceWayId':'way/340652169','sourceLengthM':main['sourceLengthM'],'estimatedWidthM':12,'widthErrorM':3,'lanes':2,'stairsFlankingEachWidthM':4,'beltEachWidthM':1.4,
          'geometryBasis':'original static abstract geometry from designerfrontphoto; no mechanicaloperation/animation, no surveyed tread/gradient/width','heightBasis':'filtered DSM candidate ±12m, physically inaccurate until profile measured'},
      'sourceEntranceGap':{'upperNode':upper['sourceNodeId'],'coordinateWGS84':upper['coordinateWGS84'],'distanceToMappedTowerM':gap,'upperOtherSourceRoadIds':[f['id'] for f in epaths],'lowerSharedNode':'3479012381','lowerSourceRoadIds':lowerjoins,
           'decision':'no invented navigation edge across gap; frozen basewalls remain continuous, actual door/modelopening unresolved'},
      'estimates':{'apronBufferM':{'value':3,'errorM':2,'method':'narrow ground-apron interpretation around mappedbasement from designersection, exact semantic/widthunknown'},'siteHeights':{'errorM':12,'method':'GLO30 30m native, prepared grid50m real,3×3min/max/mean covers150m real neighborhood; broadcanopy/slopespike bias remains'},
          'railHeightM':{'value':1.1,'errorM':.3,'method':'representative static exterior guardrails readfrontphoto; not measured'}},
      'verticalContract':'lm.y = game ordinate for EGM2008 zero; absolute estimated source heights realmetres *scale ONCE +lm.y. Tower original build instead receives tower_placement().y as its game base.',
      'terrainInput':{'manifestPath':str((terrain/'manifest.json').relative_to(ROOT)),'manifestSha256':sha(terrain/'manifest.json'),'groundPath':str((terrain/'ground-estimate-egm2008-metres.bin').relative_to(ROOT)),'groundSha256':manifest['files']['ground-estimate-egm2008-metres.bin']['sha256'],'rawDsmSha256':manifest['files']['dsm-egm2008-metres.bin']['sha256'],'sampleSpacingRealM':50},
      'budget':{'maxTriangles':18000,'maxMaterials':12,'maxBytes':8388608},
      'blockers':['source mainlift uppernode-to-towerfootprint gap has no source connection or surveyed gate/door','frozen originalbase walls/ground collision envelope do not expose entrance; externalsite cannot make throughwall traversal valid','actualground/plaza/stair/escalatorfinishedlevels and water/shore collision datum not surveyed; DSM estimated ±12m','no currentoperatorentrance map/current all-direction closephotos obtained; whole plaza/internal elevator/access not complete']}
    write('spec.json',spec)
    write('measurements.json',{'sourceParkAreaM2':area,'dryMaskAreaM2':dry.area,'sourceTerrainTriangles':terrain_count,'allSurfaceTriangles':len(surfaces),'towerGroundEgm2008EstimatedM':padheight,'towerRawDsmInterpolatedM':sample(0,0,raw),'peakGroundEgmEstimatedM':sample(px,py),
      'sourceMainLiftLengthM':main['sourceLengthM'],'mainLiftHeightEndpointsM':[p['heightEstimatedEgm2008M'] for p in main['profile']],'gapToTowerM':gap,'sourceUpperOtherRoads':[f['id'] for f in epaths],'sourceLowerJoins':lowerjoins,
      'method':'source-node plan lengths/project config and mapmask clipping; separately interpolated estimated sourceheight; no field measurements or safe route claimed','error':'plan±5m, ground±12m; interpolating finer doesnot add native resolution'})
    print(json.dumps({'terrainTriangles':terrain_count,'surfaceTriangles':len(surfaces),'groundEstimateM':padheight,'mainLiftLengthM':main['sourceLengthM'],'gapM':gap,'otherUpperRoads':len(epaths)}))
if __name__=='__main__':main()
