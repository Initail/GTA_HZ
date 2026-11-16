"""Collision adapter for the frozen three-bridge structural candidate.

Replays the original CPU B build in an isolated module, capturing emitted faces.
No Blender import, scene/export/public write, or replacement geometry. lm.y is
ALREADY the original model's river-display game height (delivery currently .9).
Road/rail deck rectangles are surfaces, never full-height building obstacles.
The projected solid envelopes are conservative contact candidates, not a
certificate of bridge clearance, abutment coverage or present driving access.
"""
from __future__ import annotations
import functools
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MODULE = ROOT/'scripts/landmarks/qiantang_bridges.py'
SOURCE_SPEC = ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2/spec.json'
SOURCE_MODULE_SHA256 = '2c4bb9829077ce7da1b9608d487001656c5cff3b0075b02959b5d5a058734734'
SOURCE_SPEC_SHA256 = '648777e9482509e7130ce633bcd8a26ed1a5759963586e122f90bd0fe5063f58'
ADAPTER_ID = 'qiantang-bridge-collision'


def _sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(spec):
    # A modified original or an unchecked clone cannot silently reuse collisions.
    if _sha(SOURCE_MODULE)!=SOURCE_MODULE_SHA256 or _sha(SOURCE_SPEC)!=SOURCE_SPEC_SHA256:
        raise ValueError('Frozen bridge source changed: collision re-review required')
    original=json.loads(SOURCE_SPEC.read_text())
    if spec.get('id')=='qiantang-bridges':
        if spec!=original:raise ValueError('Bridge collision requires the exact frozen source spec')
    elif spec.get('id')==ADAPTER_ID and spec.get('cityId')=='hangzhou':
        for k,v in [('sourceModuleSha256',SOURCE_MODULE_SHA256),('sourceSpecSha256',SOURCE_SPEC_SHA256)]:
            if spec.get(k)!=v:raise ValueError('Adapter binding differs: '+k)
    else:raise ValueError('Expected Hangzhou frozen bridge or collision-adapter spec')
    return original


def _hull(points):
    pts=sorted(set((float(p[0]),float(p[1])) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in pts:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=1e-12:lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=1e-12:upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1]+upper[:-1]]


def _area(poly):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2


def _covers(poly,x,z,tol=1e-8):
    return all((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0])>=-tol for a,b in zip(poly,poly[1:]+poly[:1]))


def _distance(poly,x,z):
    if _covers(poly,x,z):return 0.0
    result=math.inf
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dz=b[0]-a[0],b[1]-a[1];f=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
        result=min(result,math.hypot(x-a[0]-f*dx,z-a[1]-f*dz))
    return result


class _CaptureB:
    """Exact standard-library implementation of B.pt / B.face only."""
    def __init__(self):self.frame=(77,-63,.73);self.faces=[]
    def face(self,mat,pts,uv=None):
        x,z,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((mat,[(x+u*c-v*s,z+u*s+v*c,h) for u,v,h in pts]))


def _kind(owner,mat,a,b,source_bridge):
    vertical=math.hypot(a[0]-b[0],a[1]-b[1])<1e-7
    if owner=='_rails':return 'guardrail-post' if vertical else 'guardrail-bar'
    if mat=='concrete':return 'bridge-pier' if vertical else 'pier-crossbeam'
    if owner=='_zhijiang':return 'stay-cable'
    if owner=='_qiantang':
        # These two full-length rails are actual separate lower railway geometry.
        nominal=source_bridge['profile']['lowerWaterRelativeM']+.13
        if abs(a[2]-nominal)<1e-8 and abs(b[2]-nominal)<1e-8 and math.dist(a,b)>1000:return 'railway-rail'
        return 'truss-member'
    return 'arch-member'


def _volume(vertices,ident,bridge_id,kind,material,source_face_range,split=None):
    poly=_hull(vertices);low=min(p[2] for p in vertices);high=max(p[2] for p in vertices)
    if len(poly)<3 or _area(poly)<=1e-12 or high<=low:raise ValueError('Degenerate captured solid '+ident)
    return {'id':ident,'bridgeId':bridge_id,'kind':kind,'material':material,
      'polygonGame':poly,'minYGame':low,'maxYGame':high,
      'verticesGameENU':[list(v) for v in vertices],'sourceFaceRange':list(source_face_range),
      'sourcePrimitiveSubdivision':split,'mode':'rail' if kind=='railway-rail' else 'structure',
      'approximation':'conservative convex EN projection x vertical interval; 3D vertices retained for narrower contact tests',
      'status':'actual-candidate-mesh-envelope; runtime contact unverified'}


@functools.lru_cache(maxsize=4)
def _replay_cached(x,z,water,lon,lat,scale,coordinate_config_sha256):
    loader=importlib.util.spec_from_file_location('_private_frozen_qiantang_collision_replay',SOURCE_MODULE)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    original=json.loads(SOURCE_SPEC.read_text());b=_CaptureB();before=b.frame
    active={'bridge':None};solids=[];decks=[];primitive_index=0
    base_mesh=module._Mesh;original_deck=module._deck
    def world(mesh,points):
        # The same _Mesh scaling and B frame as the immediately replayed faces.
        ox,oz,angle=b.frame;c,s=math.cos(angle),math.sin(angle);result=[]
        for px,pz,py in points:
            u,v=(px+mesh.offset[0])*mesh.scale,(pz+mesh.offset[1])*mesh.scale
            result.append((ox+u*c-v*s,oz+u*s+v*c,py*mesh.scale+mesh.water))
        return result
    class TraceMesh(base_mesh):
        def tube(self,mat,a,end,r,n=4,cap=True):
            nonlocal primitive_index
            start=len(b.faces);caller=sys._getframe(1).f_code.co_name
            super().tube(mat,a,end,r,n,cap)
            if len(b.faces)==start:return
            faces=b.faces[start:];ring1=[f[1][0] for f in faces[:n]];ring2=[f[1][3] for f in faces[:n]]
            # Both rings come from faces actually passed to B, not a second tube implementation.
            c1=[sum(v[k] for v in ring1)/n for k in range(3)];c2=[sum(v[k] for v in ring2)/n for k in range(3)]
            horizontal=math.hypot(c2[0]-c1[0],c2[1]-c1[1]);rise=abs(c2[2]-c1[2])
            # Vertical/level members have an exact constant interval. Inclined
            # members use smaller emitted-ring interpolants to limit overblocking.
            parts=max(1,math.ceil(max(horizontal/4,rise/1.2))) if horizontal>1e-7 and rise>1e-7 else 1
            kind=_kind(caller,mat,a,end,active['bridge']);primitive_index+=1
            for j in range(parts):
                rows=[[(1-f)*u[k]+f*v[k] for k in range(3)] for f in [j/parts,(j+1)/parts] for u,v in zip(ring1,ring2)]
                ident=f"{active['bridge']['id']}:tube:{primitive_index}:{j}"
                solids.append(_volume(rows,ident,active['bridge']['id'],kind,mat,(start,len(b.faces)),[j,parts]))
        def face(self,mat,points):
            nonlocal primitive_index
            caller=sys._getframe(1)
            # The two red portals emit four faces per consecutive pair of rows.
            # Capture each actual section separately, retaining the driving void.
            portal=caller.f_code.co_name=='_zhijiang' and mat=='civicred' and caller.f_locals.get('i')==0
            start=len(b.faces);super().face(mat,points)
            if portal:
                primitive_index+=1;rows=world(self,caller.f_locals['r1']+caller.f_locals['r2'])
                solids.append(_volume(rows,f"{active['bridge']['id']}:portal:{primitive_index}",active['bridge']['id'],'pylon-section',mat,(start,start+4)))
    def trace_deck(mesh,pt,a,end,width,height,thick,top=False,mat='concrete'):
        start=len(b.faces);original_deck(mesh,pt,a,end,width,height,thick,top,mat)
        vertices=[p for material,face in b.faces[start:] for p in face];poly=_hull(vertices)
        bridge=active['bridge'];nominals=bridge['profile'];deck=next(k for k in ['upper','lower','single'] if k+'WaterRelativeM' in nominals and abs(nominals[k+'WaterRelativeM']-height)<1e-8)
        mode='rail' if bridge['id']=='qiantang-bridge' and deck=='lower' else 'road'
        paths=bridge['railways'] if mode=='rail' else bridge['roads']+bridge.get('outsideOldBoundsContinuations',[])
        decks.append({'id':f"{bridge['id']}:deck:{len(decks)}",'bridgeId':bridge['id'],'deck':deck,'mode':mode,
          'sourceWayIds':[p['id'] for p in paths if p['deck']==deck],'polygonGame':poly,
          'heightGame':max(p[2] for p in vertices),'undersideYGame':min(p[2] for p in vertices),
          'sourceFaceRange':[start,len(b.faces)],'renderedTopFace':top,
          'status':'nominal top of actually rendered deck sides; road top plane supplied by parent pipeline',
          'navigationAccepted':False})
    module._Mesh=TraceMesh;module._deck=trace_deck
    for identifier,name in [('qiantang-bridge','_qiantang'),('fuxing-bridge','_fuxing'),('zhijiang-bridge','_zhijiang')]:
        function=getattr(module,name)
        def wrap(mesh,bridge,xy,function=function):
            active['bridge']=bridge;return function(mesh,bridge,xy)
        setattr(module,name,wrap)
    lm={'x':x,'z':z,'y':water,'lon':lon,'lat':lat};report=module.build(b,lm,original,scale)
    if b.frame!=before:raise ValueError('Frozen B build did not restore frame')
    vertices=[p for material,face in b.faces for p in face]
    if not all(math.isfinite(v) for p in vertices for v in p):raise ValueError('Nonfinite replay')
    triangle_count=sum(len(face)-2 for material,face in b.faces)
    if triangle_count!=24148 or triangle_count!=report['triangleCountBeforeExport']:raise ValueError('Replay changed original geometry count')
    return {'solids':solids,'decks':decks,'faces':b.faces,'primitiveCount':primitive_index,'frameRestored':True,
      'triangleCount':triangle_count,'boundsGameENU':{'min':[min(p[k] for p in vertices) for k in range(3)],'max':[max(p[k] for p in vertices) for k in range(3)]}}


def _replay(lm,spec,scale):
    original=_source(spec)
    if 'y' not in lm:raise ValueError('lm.y must explicitly be the original model water-display height in game units')
    values=[float(lm[k]) for k in ['x','z','y']]+[float(lm.get(k,original['anchor'][k])) for k in ['lon','lat']]+[float(scale)]
    if not all(math.isfinite(v) for v in values) or scale<=0:raise ValueError('Finite pose/datum and positive scale required')
    return _replay_cached(*values,_sha(ROOT/'config/cities/hangzhou.json'))


def ground_footprints(lm,spec,scale=.6):
    """Nonempty actual solid envelopes with minYGame/maxYGame; no deck slabs.

    Treat polygon AND vertical bounds together. Fine guardrail posts are smaller
    than .01 square game metres; consumers must not discard or inflate them.
    Exact lower railway rail members are mode=rail, never roadway surfaces.
    """
    return copy.deepcopy(_replay(lm,spec,scale)['solids'])


def walk_surfaces(lm,spec,scale=.6,mode='road'):
    """Deck top regions; rail mode requires a separate explicit request."""
    if mode not in ['road','rail']:raise ValueError('Expected explicit road or rail mode')
    return copy.deepcopy([d for d in _replay(lm,spec,scale)['decks'] if d['mode']==mode])


def _profile_rows(lm,spec,scale,endpoint_heights_game,allow_estimated,mode):
    original=_source(spec);replay=_replay(lm,spec,scale)
    loader=importlib.util.spec_from_file_location('_private_frozen_qiantang_profile',SOURCE_MODULE)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    city,g,origin,xy=module._context(original);lm_projection=module.project(lm.get('lon',original['anchor']['lon']),lm.get('lat',original['anchor']['lat']),city)
    offset=[float(lm[k])+(origin[j]-lm_projection[j])/g['scale']*scale-origin[j] for j,k in enumerate(['x','z'])]
    if mode=='road':rows=module.source_road_profiles(original,float(lm['y']),endpoint_heights_game,scale,allow_estimated,True)
    else:rows=module.source_rail_profiles(original,float(lm['y']),scale,allow_estimated)
    for row in rows:
        row['points']=[[p[0]+offset[0],p[1]+offset[1]] for p in row['points']]
        for sample in row.get('profileSamples',[]):sample['point']=[sample['point'][j]+offset[j] for j in range(2)]
        row['actualDeckRegions']=copy.deepcopy([d for d in replay['decks'] if d['mode']==mode and d['bridgeId']==row['bridgeId'] and d['deck']==row['deck']])
        bridge=next(v for v in original['bridges'] if v['id']==row['bridgeId']);center=xy(bridge['centerWGS84']);angle=bridge['axisRadiansEastCCW']
        row['actualMainAxisGame']={'center':[origin[j]+center[j]*scale+offset[j] for j in range(2)],
          'longitudinalUnit':[math.cos(angle),math.sin(angle)],'mainInterval':[v*scale for v in bridge['profile']['mainIntervalM']]}
        row['collisionAdapterSourceModuleSha256']=SOURCE_MODULE_SHA256
        row['actualDeckCoverageAccepted']=False;row['navigationAccepted']=False
    return rows


def source_road_profiles(lm,spec,scale=.6,endpoint_heights_game=None,allow_estimated=False):
    """Exact source roads plus actual finite deck regions; no synthesized ramps."""
    return _profile_rows(lm,spec,scale,endpoint_heights_game,allow_estimated,'road')


def source_rail_profiles(lm,spec,scale=.6,allow_estimated=False):
    return _profile_rows(lm,spec,scale,None,allow_estimated,'rail')


def surface_at_game(way_id,x,z,lm,spec,scale=.6,endpoint_heights_game=None,allow_estimated=False,mode='road'):
    """One way/one mode only. Height is returned ONLY where source and mesh agree.

    The raw source profile is retained when a model gap or overridden height
    mismatch prevents returning an actual candidate surface. Finite model
    geometry coverage remains an additional constraint, not a fabricated ramp.
    """
    if not all(math.isfinite(v) for v in [x,z]):raise ValueError('Finite game EN point required')
    if mode not in ['road','rail']:raise ValueError('Explicit road/rail mode required')
    ident=str(way_id);ident=ident if ident.startswith('way/') else 'way/'+ident
    for row in _profile_rows(lm,spec,scale,endpoint_heights_game,allow_estimated,mode):
        if row['id']!=ident:continue
        best=None
        for j,(a,b) in enumerate(zip(row['points'],row['points'][1:])):
            dx,dz=b[0]-a[0],b[1]-a[1];f=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
            distance=math.hypot(x-a[0]-f*dx,z-a[1]-f*dz)
            if best is None or distance<best[0]:best=(distance,j,f,row['heights'][j]+f*(row['heights'][j+1]-row['heights'][j]))
        matching=[d for d in row['actualDeckRegions'] if _covers(d['polygonGame'],x,z)]
        result={'sourceWayId':ident,'bridgeId':row['bridgeId'],'mode':mode,'deck':row['deck'],'sourceProfileHeightGame':best[3],
          'sourceSegmentIndex':best[1],'sourceSegmentFraction':best[2],'distanceFromSourceCenterlineGame':best[0],
          'actualDeckHeightGame':matching[0]['heightGame'] if matching else None,
          'actualDeckRegionIds':[d['id'] for d in matching],'heightGame':None,'navigationAccepted':False,
          'heightBasis':'estimated frozen model water-relative profile; absolute datum unknown','blockers':[]}
        if best[0]>25*scale:result['blockers'].append('outside original source-way lookup distance; not a mapped actor lane')
        if not matching:result['blockers'].append('no actual finite structural deck at this source point; approach/curve not modelled')
        if matching:
            result['heightDifferenceGame']=best[3]-matching[0]['heightGame']
            if abs(result['heightDifferenceGame'])>1e-7:result['blockers'].append('source profile proposal differs from rigid exported structural deck')
        if not result['blockers']:result['heightGame']=matching[0]['heightGame']
        return result
    return None


def profile_geometry_audit(lm,spec,scale=.6,endpoint_heights_game=None,allow_estimated=False):
    """Source-node and <=20m sample comparisons; reports gaps, never fixes them."""
    result=[]
    for row in source_road_profiles(lm,spec,scale,endpoint_heights_game,allow_estimated):
        regions=row['actualDeckRegions'];values=[];nodes=[]
        for category,items in [('source-node',[{'nodeId':n,'point':p,'height':h} for n,p,h in zip(row['nodeIds'],row['points'],row['heights'])]),('interpolation-sample',row['profileSamples'])]:
            for item in items:
                x,z=item['point'];matching=[d for d in regions if _covers(d['polygonGame'],x,z)]
                delta=item['height']-matching[0]['heightGame'] if matching else None
                axis=row['actualMainAxisGame'];a=[item['point'][j]-axis['center'][j] for j in range(2)];u=axis['longitudinalUnit']
                station=a[0]*u[0]+a[1]*u[1];transverse=-a[0]*u[1]+a[1]*u[0]
                absent=None if matching else ('outside finite model main-span longitudinal interval' if station<axis['mainInterval'][0]-1e-7 or station>axis['mainInterval'][1]+1e-7 else 'source point laterally outside actual deck width/alignment')
                checked={**item,'kind':category,'actualDeckHeightGame':matching[0]['heightGame'] if matching else None,
                  'actualDeckRegionIds':[d['id'] for d in matching],'planDistanceToActualDeckGame':min((_distance(d['polygonGame'],x,z) for d in regions),default=None),
                  'heightDifferenceGame':delta,'candidateSurfaceAvailable':bool(matching) and abs(delta)<1e-7,
                  'mainStationGame':station,'mainTransverseGame':transverse,'geometryAbsenceReason':absent}
                (nodes if category=='source-node' else values).append(checked)
        result.append({'sourceWayId':row['id'],'bridgeId':row['bridgeId'],'mode':'road','deck':row['deck'],
          'sourceNodes':nodes,'profileSamples':values,'actualDeckRegionIds':[r['id'] for r in regions],
          'missingGeometryNodeCount':sum(not n['actualDeckRegionIds'] for n in nodes),
          'missingGeometrySampleCount':sum(not n['actualDeckRegionIds'] for n in values),
          'profileMismatchNodeCount':sum(n['heightDifferenceGame'] is not None and abs(n['heightDifferenceGame'])>1e-7 for n in nodes),
          'maxPlanGapGame':max((n['planDistanceToActualDeckGame'] or 0 for n in nodes+values),default=0),
          'status':'partial-actual-geometry-only; gaps remain blockers','navigationAccepted':False})
    return result


def collision_report(lm,spec,scale=.6):
    replay=_replay(lm,spec,scale);counts={};by_bridge={}
    for v in replay['solids']:
        counts[v['kind']]=counts.get(v['kind'],0)+1
        by_bridge[v['bridgeId']]=by_bridge.get(v['bridgeId'],0)+1
    return {'id':ADAPTER_ID,'status':'candidate-not-runtime-verified','sourceModuleSha256':SOURCE_MODULE_SHA256,'sourceSpecSha256':SOURCE_SPEC_SHA256,
      'coordinateConfigSha256':_sha(ROOT/'config/cities/hangzhou.json'),
      'poseGame':{k:float(lm[k]) for k in ['x','z','y']},'scale':scale,'lmYMeaning':'original rendered water-display game height; never multiply by scale',
      'actualReplayTriangles':replay['triangleCount'],'actualReplayBoundsGameENU':replay['boundsGameENU'],'frameRestored':replay['frameRestored'],
      'solidEnvelopeCount':len(replay['solids']),'sourcePrimitiveCount':replay['primitiveCount'],'solidKinds':counts,'byBridge':by_bridge,
      'roadDeckRegionCount':sum(d['mode']=='road' for d in replay['decks']),'railDeckRegionCount':sum(d['mode']=='rail' for d in replay['decks']),
      'minimumPolygonAreaGame2':min(_area(v['polygonGame']) for v in replay['solids']),'noBlockingDeckFootprints':True,
      'unmodelledKinds':['bank-abutments','approach supports and sloped structural decks','surveyed clearances and passage portals'],
      'blockers':['frozen main structural model does not cover complete source road/approach geometry',
        'absolute deck/water datum and node elevations estimated, not surveyed',
        'projected envelopes are conservative; fine collision narrow phase and actor radius/height need runtime review',
        'road tops and bridge slab underside contacts require parent height-surface pipeline',
        'bank-abutments and full approach supports absent from original build',
        'height-aware collisions, deck-specific actors, physical road continuity, real driving, browser and performance pending'],
      'navigationAccepted':False,'baseBuildingIdsToExclude':[]}
