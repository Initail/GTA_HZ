"""Pure CPU geometry/source/failure audit; no Blender, export or browser."""
from pathlib import Path
import ast,collections,hashlib,importlib.util,json,math,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
from shapely.geometry import Polygon,Point
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):(HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
class FakeB:
    def __init__(self,fail_at=None):self.frame=(73,-19,.67);self.faces=[];self.fail_at=fail_at
    def face(self,material,points,uv=None):
        if self.fail_at is not None and len(self.faces)>=self.fail_at:raise RuntimeError('deliberate FakeB failure')
        x,z,a=self.frame;c,s=math.cos(a),math.sin(a);self.faces.append((material,[(x+u*c-v*s,z+u*s+v*c,h) for u,v,h in points]))
def area3(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];return math.sqrt(sum(w*w for w in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))
def bounds(faces):
    p=[v for mat,face in faces for v in face];return {'min':[min(q[j] for q in p) for j in range(3)],'max':[max(q[j] for q in p) for j in range(3)]}


def main():
    path=ROOT/'scripts/landmarks/fuxing_alignment.py';loader=importlib.util.spec_from_file_location('fuxing_alignment_cpu',path);m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
    spec=json.loads((HERE/'spec.json').read_text());full,old,new,city=m._context(spec);x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city);lm={'x':x,'z':z,'y':.9}
    source_module,collision=m._dependencies();source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [m.ORIGINAL_MODULE,m.ORIGINAL_SPEC,m.COLLISION_MODULE]}
    b=FakeB();before=b.frame;report=m.build(b,lm,spec);assert b.frame==before
    assert report['triangleCountBeforeExport']==14592 and report['faceCountBeforeExport']==7252 and report['materials']==['carpaint','concrete','silver']
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles'] and len(report['materials'])<=spec['budget']['maxMaterials']
    assert report['candidateWaterPlanes']==0 and report['candidateRoadTopPlanes']==0 and not report['sourceRoadsRelocated'] and report['baseBuildingIdsToExclude']==[]
    for mat,face in b.faces:
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):assert area3(face[0],face[i],face[i+1])>1e-9
    fail=FakeB(8);before=fail.frame
    try:m.build(fail,lm,spec)
    except RuntimeError:pass
    else:raise AssertionError('Expected deliberate FakeB failure')
    assert fail.frame==before
    small=FakeB();m.build(small,lm,spec,.3)
    for (_,a),(_,c) in zip(b.faces,small.faces):
        for p,q in zip(a,c):
            for j,base in enumerate([x,z,.9]):assert math.isclose(p[j]-base,2*(q[j]-base),abs_tol=1e-7)
    shifted=dict(lm,lon=spec['anchor']['lon']+.001,lat=spec['anchor']['lat']-.001);shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city);shift=FakeB();m.build(shift,shifted,spec)
    for (_,a),(_,c) in zip(b.faces,shift.faces):
        for p,q in zip(a,c):assert all(math.isclose(u,v,abs_tol=1e-7) for u,v in zip(p,q))
    # Baseline is exact original Fuxing subset: same reported widths, all members
    # and Y values, with a rigid rotation/translation and no mesh simplification.
    subset=json.loads(json.dumps(full));subset['bridges']=[old];source_anchor=project(full['anchor']['lon'],full['anchor']['lat'],city);source_lm={'x':source_anchor[0],'z':source_anchor[1],'y':.9};baseline=FakeB();old_report=source_module.build(baseline,source_lm,subset)
    assert old_report['triangleCountBeforeExport']==14592
    old_center=project(*old['centerWGS84'],city);angle=new['axisRadiansEastCCW']-old['axisRadiansEastCCW'];c,s=math.cos(angle),math.sin(angle)
    def mapped(p):
        u,v=p[0]-old_center[0],p[1]-old_center[1];return [x+u*c-v*s,z+u*s+v*c,p[2]]
    maximum_vertex_difference=0
    for (mat,a),(mat2,candidate) in zip(baseline.faces,b.faces):
        assert mat==mat2 and len(a)==len(candidate)
        for p,q in zip(a,candidate):maximum_vertex_difference=max(maximum_vertex_difference,max(abs(u-v) for u,v in zip(mapped(p),q)))
    assert maximum_vertex_difference<1e-7
    changed_fields={k for k in new if new[k]!=old[k]};assert changed_fields=={'centerWGS84','axisRadiansEastCCW','centerGameEN','bearingDegreesFromNorth'}
    assert old['reported']==new['reported'] and old['widthM']==new['widthM']==26.4 and old['profile']==new['profile'] and old['roads']==new['roads']
    # Derivative collision envelopes are exactly the same rigid transform. Check
    # their vertices against actual newly emitted primitive faces, not only count.
    volumes=m.ground_footprints(lm,spec);surfaces=m.walk_surfaces(lm,spec);assert len(volumes)==2636 and len(surfaces)==46
    original_surfaces=[d for d in collision.walk_surfaces(source_lm,full) if d['bridgeId']=='fuxing-bridge'];offset=min(r['sourceFaceRange'][0] for r in original_surfaces)
    for v in volumes:
        poly=Polygon(v['polygonGame']);assert poly.is_valid and poly.area>1e-12 and v['maxYGame']>v['minYGame']
        start,end=v['originalSourceFaceRange'];faces=b.faces[start-offset:end-offset];n=len(v['verticesGameENU'])//2;first=[f[1][0] for f in faces[:n]];second=[f[1][3] for f in faces[:n]];j,parts=v['sourcePrimitiveSubdivision']
        expected=[[(1-f)*a[k]+f*c[k] for k in range(3)] for f in [j/parts,(j+1)/parts] for a,c in zip(first,second)]
        assert len(expected)==len(v['verticesGameENU'])
        for p,q in zip(expected,v['verticesGameENU']):
            assert all(math.isclose(a,c,abs_tol=1e-7) for a,c in zip(p,q))
            assert poly.buffer(1e-8).covers(Point(q[:2])) and v['minYGame']-1e-8<=q[2]<=v['maxYGame']+1e-8
    for region in surfaces:
        start,end=region['originalSourceFaceRange'];points=[p for mat,face in b.faces[start-offset:end-offset] for p in face];poly=Polygon(region['polygonGame'])
        assert all(poly.buffer(1e-8).covers(Point(p[:2])) for p in points)
        assert math.isclose(max(p[2] for p in points),region['heightGame'],abs_tol=1e-8) and math.isclose(min(p[2] for p in points),region['undersideYGame'],abs_tol=1e-8)
    profiles=m.source_road_profiles(lm,spec,allow_estimated=True);assert len(profiles)==7
    frozen_profiles=[r for r in source_module.source_road_profiles(full,.9,allow_estimated=True) if r['bridgeId']=='fuxing-bridge'];fixed={f['id']:f for f in json.loads((m.ORIGINAL_SPEC.parent/'fixed-bridge-features.geojson').read_text())['features']}
    for row in profiles:
        original=next(r for r in frozen_profiles if r['id']==row['id']);raw=fixed[row['id']]
        for key in ['nodeIds','coordinatesWGS84','points','heights','profileSamples']:assert row[key]==original[key]
        assert row['coordinatesWGS84']==raw['geometry']['coordinates'] and row['nodeIds']==raw['properties']['nodeIds']
        for wgs,point in zip(row['coordinatesWGS84'],row['points']):assert all(math.isclose(a,c,abs_tol=1e-8) for a,c in zip(point,project(*wgs,city)))
    try:m.source_road_profiles(lm,spec)
    except ValueError:pass
    else:raise AssertionError('Estimated datum must require opt-in')
    try:m.source_road_profiles(lm,spec,.3,allow_estimated=True)
    except ValueError:pass
    else:raise AssertionError('No source rescaling allowed')
    audit=m.profile_alignment_audit(lm,spec,allow_estimated=True);old_audit=[r for r in collision.profile_geometry_audit(source_lm,full,allow_estimated=True) if r['bridgeId']=='fuxing-bridge'];comparison=[]
    for row in audit:
        original=next(r for r in old_audit if r['sourceWayId']==row['sourceWayId']);main_bad=lambda r:r['geometryAbsenceReason']=='source point laterally outside actual deck width/alignment'
        comparison.append({'sourceWayId':row['sourceWayId'],'deck':row['deck'],'oldMainMismatchSourceNodes':sum(main_bad(r) for r in original['sourceNodes']),
          'oldMainMismatchSamples':sum(main_bad(r) for r in original['profileSamples']),'newMainMismatchSourceNodes':row['missingMainSourceNodeCount'],'newMainMismatchSamples':row['missingMainSampleCount'],
          'remainingOutsideMainSourceNodes':row['outsideMainSourceNodeCount'],'navigationAccepted':False})
    targets=['way/154135290','way/589429905']
    for ident in targets:
        row=next(r for r in comparison if r['sourceWayId']==ident);assert row['oldMainMismatchSourceNodes']>0 and row['oldMainMismatchSamples']>0 and row['newMainMismatchSourceNodes']==row['newMainMismatchSamples']==0
    remaining_nodes=[r for row in audit for r in row['records'] if r['kind']=='source-node' and r['geometryAbsenceReason']=='remaining transverse width/alignment mismatch'];remaining_samples=[r for row in audit for r in row['records'] if r['kind']=='interpolation-sample' and r['geometryAbsenceReason']=='remaining transverse width/alignment mismatch']
    assert len(remaining_nodes)==3 and len(remaining_samples)==23 and next(row for row in audit if row['sourceWayId']=='way/336983476')['missingMainSourceNodeCount']==3
    core_half=416.9;central=[r for row in audit for r in row['records'] if abs(r['stationM'])<=core_half];assert central and all(r['surfaceAvailable'] for r in central)
    # Negative controls: arbitrary model displacement cannot move real roads;
    # explicit game-unit node height changes cannot silently move the solid deck.
    wrong_pose=dict(lm,x=lm['x']+100);wrong=m.source_road_profiles(wrong_pose,spec,allow_estimated=True)
    for row in wrong:assert row['points']==next(r for r in profiles if r['id']==row['id'])['points']
    displaced_audit=m.profile_alignment_audit(wrong_pose,spec,allow_estimated=True);assert sum(r['missingMainSourceNodeCount'] for r in displaced_audit)>3
    changed=m.profile_alignment_audit(lm,spec,allow_estimated=True,endpoint_heights_game={'1667217046':13.7});mismatch=[r for row in changed for r in row['records'] if r.get('nodeId')=='1667217046']
    assert len(mismatch)==2 and all(r['height']==13.7 and math.isclose(r['actualHeightGame'],14.1,abs_tol=1e-8) and not r['surfaceAvailable'] for r in mismatch)
    for row in audit:assert not row['navigationAccepted']
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n,ast.Import):assert all(v.name.split('.')[0] not in ['bpy','city_mesh'] for v in n.names)
        if isinstance(n,ast.ImportFrom):assert (n.module or '').split('.')[-1] not in ['bpy','city_mesh']
    assert 'bpy' not in sys.modules and 'city_mesh' not in sys.modules
    assert all(sha(ROOT/p)==expected for p,expected in source_hashes.items())
    report.update(sourceModuleSha256=sha(path),specSha256=sha(HERE/'spec.json'),frozenInputSha256=source_hashes,coordinateConfigSha256=sha(ROOT/'config/cities/hangzhou.json'),
      checks={'finiteNondegenerateCandidate':True,'triangleMaterialBudget':True,'rigidCorrectionOnlyNoWidthOrHeightChange':True,'exactRigidTransformOfOriginalAllVertices':True,
        'frameRestoredSuccessAndFailure':True,'scaleOnceAndGameDatum':True,'sourceAnchorShiftCompensation':True,'collisionVerticesMatchActualCandidateFaces':True,
        'solidEnvelopesNonemptyAndHeightBounded':True,'sourceWayCoordinatesNodeOrderAndHeightUnchanged':True,'allSevenWaysAuditedIncludingNewFailures':True,
        'specifiedWayMainTransverseGapsResolved':True,'sourceRoadsDoNotFollowWrongModelPose':True,'overrideHeightDoesNotWarpSolidDeck':True,'frozenInputsUnchanged':True,'noSceneImports':True},
      geometryBoundsGameENU=bounds(b.faces),waterDisplayBaseYGame=.9,waterDatumMeasured=False,solidEnvelopeCount=len(volumes),roadDeckRegionCount=len(surfaces),
      maxRigidTransformVertexDifferenceGame=maximum_vertex_difference,remainingMainMismatchNodeOccurrences=len(remaining_nodes),remainingMainMismatchSamples=len(remaining_samples),
      remainingMismatchWayId='way/336983476',minimumIdentifiablePlanarAlignmentBoundary={'intervalM':[-core_half,core_half],'lengthM':2*core_half,
        'basis':'original estimated stations covering2large190m and5central85m arches; dimensions come from original primary paper span sequence, not a fabricated field extent',
        'sourceNodeAndSampleRecordsCompared':len(central),'allSourceCenterPointsInsideCandidateDeck':True,'actorClearanceAccepted':False,'fullBridgeAccepted':False},
      inputVsModelConclusion='original bridge axis is biased toward one carriageway in fixed data; paired upper midpoint and lower outer midpoint agree near+7.89m; width widening unsupported. Remaining near-end issue cannot be assigned to map error, curve, missing cantilever/ramp or extent without independent boundary survey.',
      validationScope='CPU source-relative structural-axis candidate only; no GLB, Blender, browser, measured positioning/height, actor clearance or navigation acceptance.')
    write('cpu-validation.json',report);write('source-alignment-audit.json',{'sourceCoordinatesModified':False,'navigationAccepted':False,'rows':audit});write('all-way-comparison.json',{'sourceRoadCount':7,'rows':comparison,'remainingMismatchNodes':remaining_nodes,'remainingMismatchSamples':remaining_samples,'fullBridgeAccepted':False})
    write('negative-controls.json',{'wrongPoseModelShiftGame':100,'fixedSourcePointsRemainUnchanged':True,'displacedModelMissingMainNodeCount':sum(r['missingMainSourceNodeCount'] for r in displaced_audit),
      'sourceNodeGameHeightOverride':mismatch,'explicitOverrideGameHeightNotRescaled':True,'sourceRescalingRejected':True,'completeBridgeAccepted':False})
    print(json.dumps({'triangles':14592,'materials':3,'solidEnvelopes':len(volumes),'roadDeckRegions':len(surfaces),'sourceRoadsUnchanged':True,'targetWayMainMismatches':0,
      'remainingOtherWayNodes':3,'remainingOtherWaySamples':23,'centralRecognizableLengthM':833.8,'navigationAccepted':False},ensure_ascii=False))


if __name__=='__main__':main()
