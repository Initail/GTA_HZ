"""Standalone estimated axis correction of the frozen Fuxing main structure.

The original three-bridge model/spec and every source road WGS/node stay frozen.
Fit the bridge body's axis to opposite upper carriageway midpoints. Keep the
reported 26.4/32m widths and all other finite structural parameters unchanged.
No Blender imports, scene setup, export, public writes or synthesized road tops.
lm.x/lm.z/lm.y are game units; lm.y is the original river-display datum (.9).
"""
from __future__ import annotations
import copy
import functools
import hashlib
import importlib.util
import json
import math
from pathlib import Path
try:
    from city_config import load_city,project,unproject
except ImportError:
    from scripts.city_config import load_city,project,unproject

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL_MODULE=ROOT/'scripts/landmarks/qiantang_bridges.py'
ORIGINAL_SPEC=ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2/spec.json'
COLLISION_MODULE=ROOT/'scripts/landmarks/qiantang_bridge_collision.py'
SOURCE_SHA='2c4bb9829077ce7da1b9608d487001656c5cff3b0075b02959b5d5a058734734'
SPEC_SHA='648777e9482509e7130ce633bcd8a26ed1a5759963586e122f90bd0fe5063f58'
COLLISION_SHA='f7c661b027b1551604259f6d72a57fe9da1522541c718459dd17b8ee40377fa3'
UPPER_A=['way/29169666','way/154135283']
UPPER_B=['way/29170042','way/154135290']


def _sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def _guard():
    for path,expected in [(ORIGINAL_MODULE,SOURCE_SHA),(ORIGINAL_SPEC,SPEC_SHA),(COLLISION_MODULE,COLLISION_SHA)]:
        if _sha(path)!=expected:raise ValueError('Changed frozen input: '+str(path))


@functools.lru_cache(maxsize=1)
def _dependencies():
    values=[]
    for path,name in [(ORIGINAL_MODULE,'_fuxing_frozen_geometry'),(COLLISION_MODULE,'_fuxing_frozen_collision')]:
        loader=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module);values.append(module)
    return values


def _original():
    _guard();full=json.loads(ORIGINAL_SPEC.read_text());return full,next(b for b in full['bridges'] if b['id']=='fuxing-bridge')


def _station_coordinates(bridge,city):
    scale=city['geography']['scale'];center=project(*bridge['centerWGS84'],city);a=bridge['axisRadiansEastCCW'];u=(math.cos(a),math.sin(a));n=(-u[1],u[0]);result={}
    for row in bridge['roads']:
        points=[]
        for wgs in row['coordinatesWGS84']:
            p=project(*wgs,city);d=[(p[j]-center[j])/scale for j in range(2)];points.append([d[0]*u[0]+d[1]*u[1],d[0]*n[0]+d[1]*n[1]])
        result[row['id']]=points
    return result


def _crossing(roads,ids,station):
    values=[]
    for ident in ids:
        for a,b in zip(roads[ident],roads[ident][1:]):
            if min(a[0],b[0])-1e-8<=station<=max(a[0],b[0])+1e-8 and abs(b[0]-a[0])>1e-9:
                values.append(a[1]+(b[1]-a[1])*(station-a[0])/(b[0]-a[0]))
    if not values:raise ValueError('Source chain does not cover fitting station')
    if max(values)-min(values)>1e-5:raise ValueError('Ambiguous source chain crossing')
    return math.fsum(values)/len(values)


def _fit(roads,ids_a,ids_b,window,step=10):
    count=round(2*window/step);stations=[-window+2*window*j/count for j in range(count+1)]
    rows=[{'stationM':s,'sideAM':_crossing(roads,ids_a,s),'sideBM':_crossing(roads,ids_b,s)} for s in stations]
    for row in rows:row['midpointM']=(row['sideAM']+row['sideBM'])/2
    mean_s=math.fsum(stations)/len(stations);mean_t=math.fsum(r['midpointM'] for r in rows)/len(rows)
    slope=math.fsum((r['stationM']-mean_s)*(r['midpointM']-mean_t) for r in rows)/math.fsum((s-mean_s)**2 for s in stations);intercept=mean_t-slope*mean_s
    residuals=[r['midpointM']-intercept-slope*r['stationM'] for r in rows]
    return {'sourceSideA':ids_a,'sourceSideB':ids_b,'windowM':[-window,window],'sampleStepM':step,'sampleCount':len(rows),
      'transverseShiftM':intercept,'slope':slope,'angleDeltaRadians':math.atan(slope),'angleDeltaDegrees':math.degrees(math.atan(slope)),
      'maxResidualM':max(map(abs,residuals)),'rmsResidualM':math.sqrt(math.fsum(v*v for v in residuals)/len(residuals)),
      'sourceLineSeparationM':[min(abs(r['sideAM']-r['sideBM']) for r in rows),max(abs(r['sideAM']-r['sideBM']) for r in rows)],'samples':rows}


def axis_evidence():
    """Map-derived relative inference, never field survey or road relocation."""
    full,bridge=_original();city=load_city('hangzhou');scale=city['geography']['scale'];roads=_station_coordinates(bridge,city)
    selected=_fit(roads,UPPER_A,UPPER_B,500);lower=_fit(roads,['way/336983476'],['way/589429905'],500)
    a=bridge['axisRadiansEastCCW'];n=(-math.sin(a),math.cos(a));old=project(*bridge['centerWGS84'],city);corrected=[old[j]+n[j]*selected['transverseShiftM']*scale for j in range(2)]
    return {'basis':'estimated map-derived structural axis from paired carriageway midpoints',
      'originalCenterWGS84':bridge['centerWGS84'],'originalAxisRadiansEastCCW':a,
      'candidateCenterWGS84':list(unproject(*corrected,city)),'candidateCenterGameEN':corrected,'candidateAxisRadiansEastCCW':a+selected['angleDeltaRadians'],
      'selectedUpperPairFit':selected,'lowerOuterPairCrossCheck':lower,'windowSensitivity':[_fit(roads,UPPER_A,UPPER_B,w) for w in [400,550,600]],
      'absoluteMapAccuracy':'unknown; both layers may share imagery/mapping provenance; agreement is not an independent geodetic survey',
      'placementAllowance':'±5 physical metres (±3 game units at .60) assumed reconstruction allowance, not measured error bound or statistical confidence; station datum remains original estimate±35m',
      'widthDecision':'preserve reported26.4m small /32m large on both decks; road centerlines do not measure deck edges',
      'roadsRelocated':False,'navigationAccepted':False}


def _context(spec):
    if spec.get('id')!='fuxing-alignment' or spec.get('cityId')!='hangzhou':raise ValueError('Expected Hangzhou standalone Fuxing alignment spec')
    for field,value in [('sourceModuleSha256',SOURCE_SHA),('sourceSpecSha256',SPEC_SHA),('sourceCollisionModuleSha256',COLLISION_SHA)]:
        if spec.get(field)!=value:raise ValueError('Wrong frozen input binding: '+field)
    full,old=_original();fit=axis_evidence();axis=spec['candidateAxis']
    if not math.isclose(axis['radiansEastCCW'],fit['candidateAxisRadiansEastCCW'],abs_tol=1e-11) or any(not math.isclose(a,b,abs_tol=1e-11) for a,b in zip(axis['centerWGS84'],fit['candidateCenterWGS84'])):
        raise ValueError('Candidate axis must equal the reviewed fixed-source paired fit')
    if [spec['anchor']['lon'],spec['anchor']['lat']]!=axis['centerWGS84']:raise ValueError('Standalone anchor must be candidate structure centre')
    city=load_city('hangzhou');bridge=copy.deepcopy(old);bridge['centerWGS84']=axis['centerWGS84'];bridge['axisRadiansEastCCW']=axis['radiansEastCCW'];bridge['centerGameEN']=list(project(*axis['centerWGS84'],city));bridge['bearingDegreesFromNorth']=(90-math.degrees(axis['radiansEastCCW']))%360
    return full,old,bridge,city


def build(b,lm,spec,scale=.6):
    full,old,bridge,city=_context(spec)
    if not math.isfinite(scale) or scale<=0 or 'y' not in lm:raise ValueError('Positive scale and explicit original water-display lm.y game units required')
    if not all(math.isfinite(float(lm[k])) for k in ['x','z','y']):raise ValueError('Finite game pose required')
    module,collision=_dependencies();g=city['geography'];anchor=project(spec['anchor']['lon'],spec['anchor']['lat'],city);lm_projection=project(lm.get('lon',spec['anchor']['lon']),lm.get('lat',spec['anchor']['lat']),city)
    offset=[(anchor[j]-lm_projection[j])/g['scale'] for j in range(2)]
    def xy(p):
        q=project(*p,city);return [(q[j]-anchor[j])/g['scale'] for j in range(2)]
    # Rotate the emitted ORIGINAL primitive vertices as one rigid body. Merely
    # rebuilding tubes with a changed axis would choose different global tube
    # basis vectors for near-vertical polygonal sections and break exact matching
    # between the original geometry and its transformed collision envelopes.
    old_center=project(*old['centerWGS84'],city);local=[(old_center[j]-anchor[j])/g['scale'] for j in range(2)];angle=bridge['axisRadiansEastCCW']-old['axisRadiansEastCCW'];c,s=math.cos(angle),math.sin(angle)
    class RigidMesh(module._Mesh):
        def face(self,material,points):
            transformed=[]
            for px,pz,py in points:
                u,v=px-local[0],pz-local[1];transformed.append((u*c-v*s,u*s+v*c,py))
            super().face(material,transformed)
    before=b.frame;mesh=RigidMesh(b,scale,offset,float(lm['y']))
    try:
        b.frame=(float(lm['x']),float(lm['z']),0);part=module._fuxing(mesh,old,xy)
    finally:b.frame=before
    return {'id':spec['id'],'sourceBridgeId':'fuxing-bridge','triangleCountBeforeExport':mesh.triangles,'faceCountBeforeExport':mesh.faces,'materials':sorted(mesh.materials),
      'part':part,'correction':'rigid structural-axis correction only; reported deck widths unchanged','sourceRoadsRelocated':False,
      'candidateRoadTopPlanes':0,'candidateWaterPlanes':0,'baseBuildingIdsToExclude':[],'navigationAccepted':False,
      'verticalDatum':'lm.y is original estimated water-display base in game units; source flat deck profiles retained'}


def _transform(lm,spec,scale):
    full,old,bridge,city=_context(spec)
    if not math.isfinite(scale) or scale<=0 or 'y' not in lm:raise ValueError('Positive scale and explicit original water-display lm.y required')
    if not all(math.isfinite(float(lm[k])) for k in ['x','z','y']):raise ValueError('Finite game pose required')
    anchor=project(full['anchor']['lon'],full['anchor']['lat'],city);old_center=project(*old['centerWGS84'],city);g=city['geography'];source_center=[anchor[j]+(old_center[j]-anchor[j])*scale/g['scale'] for j in range(2)]
    new_anchor=project(spec['anchor']['lon'],spec['anchor']['lat'],city);lm_projection=project(lm.get('lon',spec['anchor']['lon']),lm.get('lat',spec['anchor']['lat']),city);new_center=[float(lm[k])+(new_anchor[j]-lm_projection[j])*scale/g['scale'] for j,k in enumerate(['x','z'])]
    a=bridge['axisRadiansEastCCW']-old['axisRadiansEastCCW'];c,s=math.cos(a),math.sin(a)
    def point(p):
        x,z=p[0]-source_center[0],p[1]-source_center[1];return [new_center[0]+x*c-z*s,new_center[1]+x*s+z*c]
    return full,{'x':anchor[0],'z':anchor[1],'y':float(lm['y'])},point


def ground_footprints(lm,spec,scale=.6):
    """Same 2,636 original Fuxing solid envelopes, rigidly transformed only."""
    full,old_lm,point=_transform(lm,spec,scale);module,collision=_dependencies()
    result=[]
    for volume in collision.ground_footprints(old_lm,full,scale):
        if volume['bridgeId']!='fuxing-bridge':continue
        volume['id']='fuxing-alignment:'+volume['id'];volume['polygonGame']=[point(p) for p in volume['polygonGame']]
        volume['verticesGameENU']=[point(p)+[p[2]] for p in volume['verticesGameENU']];volume['originalSourceFaceRange']=volume.pop('sourceFaceRange')
        volume['axisCorrectionOnly']=True;volume['navigationAccepted']=False;result.append(volume)
    return result


def walk_surfaces(lm,spec,scale=.6):
    full,old_lm,point=_transform(lm,spec,scale);module,collision=_dependencies();result=[]
    for region in collision.walk_surfaces(old_lm,full,scale):
        if region['bridgeId']!='fuxing-bridge':continue
        region['id']='fuxing-alignment:'+region['id'];region['polygonGame']=[point(p) for p in region['polygonGame']];region['originalSourceFaceRange']=region.pop('sourceFaceRange');result.append(region)
    return result


def source_road_profiles(lm,spec,scale=.6,endpoint_heights_game=None,allow_estimated=False):
    """Seven original source way/node profiles; actual WGS/game points unchanged."""
    full,old,bridge,city=_context(spec)
    if not math.isclose(scale,city['geography']['scale'],abs_tol=1e-12):raise ValueError('Road source coordinates require canonical city scale; no road relocation to fit a rescaled model')
    if 'y' not in lm:raise ValueError('Explicit original water-display datum required')
    module,collision=_dependencies();regions=walk_surfaces(lm,spec,scale);result=[]
    for row in module.source_road_profiles(full,float(lm['y']),endpoint_heights_game,scale,allow_estimated,True):
        if row['bridgeId']!='fuxing-bridge':continue
        # Preserve the frozen source points/order exactly. Only actual candidate
        # structural regions are updated, even if an arbitrary lm pose is wrong.
        row['actualDeckRegions']=[d for d in regions if d['deck']==row['deck']];row['sourceCoordinatesModified']=False;result.append(row)
    return result


def _covers(poly,x,z):return all((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0])>=-1e-8 for a,b in zip(poly,poly[1:]+poly[:1]))


def profile_alignment_audit(lm,spec,scale=.6,allow_estimated=False,endpoint_heights_game=None):
    """All source ways, including new/remaining failures; no target-only pass."""
    full,old,bridge,city=_context(spec);module,collision=_dependencies();a=bridge['axisRadiansEastCCW'];center=project(*bridge['centerWGS84'],city);u=(math.cos(a),math.sin(a));result=[]
    for row in source_road_profiles(lm,spec,scale,endpoint_heights_game,allow_estimated):
        records=[]
        items=[{'kind':'source-node','nodeId':n,'point':p,'height':h} for n,p,h in zip(row['nodeIds'],row['points'],row['heights'])]+[{'kind':'interpolation-sample',**p} for p in row['profileSamples']]
        for item in items:
            x,z=item['point'];d=[(item['point'][j]-center[j])/scale for j in range(2)];station=d[0]*u[0]+d[1]*u[1];transverse=-d[0]*u[1]+d[1]*u[0]
            matches=[r for r in row['actualDeckRegions'] if _covers(r['polygonGame'],x,z)];delta=item['height']-matches[0]['heightGame'] if matches else None
            reason=None if matches else ('outside finite main structure interval' if abs(station)>688+1e-7 else 'remaining transverse width/alignment mismatch')
            records.append({**item,'stationM':station,'transverseM':transverse,'actualDeckRegionIds':[r['id'] for r in matches],
              'actualHeightGame':matches[0]['heightGame'] if matches else None,'heightDifferenceGame':delta,'geometryAbsenceReason':reason,
              'planDistanceToActualDeckGame':0.0 if matches else min(collision._distance(r['polygonGame'],x,z) for r in row['actualDeckRegions']),
              'surfaceAvailable':bool(matches) and abs(delta)<1e-7})
        result.append({'sourceWayId':row['id'],'deck':row['deck'],'records':records,
          'missingMainSourceNodeCount':sum(r['kind']=='source-node' and r['geometryAbsenceReason']=='remaining transverse width/alignment mismatch' for r in records),
          'missingMainSampleCount':sum(r['kind']=='interpolation-sample' and r['geometryAbsenceReason']=='remaining transverse width/alignment mismatch' for r in records),
          'outsideMainSourceNodeCount':sum(r['kind']=='source-node' and r['geometryAbsenceReason']=='outside finite main structure interval' for r in records),
          'navigationAccepted':False})
    return result
