"""Real CPU/GLB/source-node validation. Never runs Blender or browser."""
from pathlib import Path
import ast,collections,hashlib,importlib.util,json,math,struct,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
from shapely.geometry import Polygon,Point


def write(name,data):(HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load_module(path,name):
    loader=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module);return module


def glb_positions(path):
    data=path.read_bytes();assert data[:4]==b'glTF';size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    gltf=json.loads(data[20:20+size]);start=20+size;binary_size,kind=struct.unpack_from('<II',data,start);assert kind==0x004e4942;binary=data[start+8:start+8+binary_size]
    # This actual candidate has no node transform, skin, compressed attributes.
    assert all(not any(k in n for k in ['matrix','translation','rotation','scale','skin']) for n in gltf['nodes'])
    result={};triangles=0
    for mesh in gltf['meshes']:
        name=mesh['name'];assert name.startswith('detail_qiantang-bridges_');material=name.removeprefix('detail_qiantang-bridges_');points=[]
        for primitive in mesh['primitives']:
            a=gltf['accessors'][primitive['attributes']['POSITION']];v=gltf['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='VEC3' and 'sparse' not in a
            offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',12)
            for j in range(a['count']):
                x,y,z=struct.unpack_from('<fff',binary,offset+j*stride);points.append((x,-z,y))
            triangles+=gltf['accessors'][primitive['indices']]['count']//3
        result[material]=points
    return result,triangles


def main():
    module_path=ROOT/'scripts/landmarks/qiantang_bridge_collision.py';m=load_module(module_path,'collision_cpu')
    spec=json.loads((HERE/'spec.json').read_text());original=json.loads(m.SOURCE_SPEC.read_text());city=load_city('hangzhou');x,z=project(original['anchor']['lon'],original['anchor']['lat'],city);lm={'x':x,'z':z,'y':.9}
    report=m.collision_report(lm,spec);volumes=m.ground_footprints(lm,spec);decks=m.walk_surfaces(lm,spec);rail=m.walk_surfaces(lm,spec,mode='rail');replay=m._replay(lm,spec,.6)
    assert len(volumes)==7457 and len(decks)==48 and len(rail)==1
    assert len([v for v in volumes if v['kind']=='bridge-pier'])==41
    assert not any(v['kind']=='deck' for v in volumes)
    assert report['actualReplayTriangles']==24148 and report['navigationAccepted'] is False
    assert all(not d['navigationAccepted'] for d in decks+rail)
    for v in volumes:
        p=Polygon(v['polygonGame']);assert p.is_valid and p.area>1e-12
        assert math.isfinite(v['minYGame']+v['maxYGame']) and v['maxYGame']>v['minYGame']
        assert all(v['minYGame']-1e-8<=q[2]<=v['maxYGame']+1e-8 and p.buffer(1e-8).covers(Point(q[:2])) for q in v['verticesGameENU'])
        assert v['sourceFaceRange'][1]<=len(replay['faces'])
        actual_faces=replay['faces'][v['sourceFaceRange'][0]:v['sourceFaceRange'][1]]
        if v['sourcePrimitiveSubdivision'] is None:
            assert set(tuple(q) for q in v['verticesGameENU'])==set(q for material,points in actual_faces for q in points)
        else:
            n=len(v['verticesGameENU'])//2;first=[face[1][0] for face in actual_faces[:n]];second=[face[1][3] for face in actual_faces[:n]];j,parts=v['sourcePrimitiveSubdivision']
            expected=[[(1-f)*a[k]+f*b[k] for k in range(3)] for f in [j/parts,(j+1)/parts] for a,b in zip(first,second)]
            assert v['verticesGameENU']==expected
    assert min(v['minYGame'] for v in volumes)<1e-8
    # All replayed faces have a deck or structural primitive association. Portal
    # end caps are contained by the first/last section, not zero-volume blockers.
    covered=set()
    for obj in volumes+decks+rail:covered.update(range(*obj['sourceFaceRange']))
    unassigned=[i for i in range(len(replay['faces'])) if i not in covered]
    assert len(unassigned)==4 and all(replay['faces'][i][0]=='civicred' for i in unassigned)
    portals=[v for v in volumes if v['kind']=='pylon-section']
    for i in unassigned:
        for q in replay['faces'][i][1]:assert any(Polygon(v['polygonGame']).buffer(1e-8).covers(Point(q[:2])) and v['minYGame']-1e-8<=q[2]<=v['maxYGame']+1e-8 for v in portals)
    # Validate against current exported geometry, independently of our counters.
    delivery_path=ROOT/'artifacts/cities/hangzhou/landmarks/qiantang-bridges-v1/model-delivery.json';delivery=json.loads(delivery_path.read_text());glb=ROOT/delivery['artifact']
    assert delivery['sourceModuleSha256']==m.SOURCE_MODULE_SHA256 and delivery['specSha256']==m.SOURCE_SPEC_SHA256 and delivery['baseYGame']==lm['y']
    assert sha(glb)==delivery['artifactSha256']
    glb_points,glb_tris=glb_positions(glb);assert glb_tris==replay['triangleCount']
    source=collections.defaultdict(set)
    def f32(q):return tuple(struct.unpack('<f',struct.pack('<f',v))[0] for v in q)
    for mat,points in replay['faces']:source[mat].update(f32(q) for q in points)
    glb_comparison=[]
    for mat,points in glb_points.items():
        actual=set(points);missing=source[mat]-actual;extra=actual-source[mat]
        assert not missing and not extra,(mat,len(missing),len(extra))
        glb_comparison.append({'material':mat,'replayedUniqueFloat32Vertices':len(source[mat]),'exportedUniqueFloat32Vertices':len(actual),'missing':0,'extra':0})
    assert set(glb_points)==set(source)
    # The datum is in game units; physical dimensions halve under .3 only once.
    small=m._replay(lm,spec,.3)
    for (_,a),(_,b) in zip(replay['faces'],small['faces']):
        for p,q in zip(a,b):
            for k,base in enumerate([x,z,.9]):assert math.isclose(p[k]-base,2*(q[k]-base),abs_tol=1e-7)
    shifted=dict(lm,y=3.4);raised=m._replay(shifted,spec,.6)
    for (_,a),(_,b) in zip(replay['faces'],raised['faces']):
        for p,q in zip(a,b):assert math.isclose(q[2]-p[2],2.5,abs_tol=1e-8) and p[:2]==q[:2]
    moved=dict(lm,lon=original['anchor']['lon']+.001,lat=original['anchor']['lat']-.001);moved['x'],moved['z']=project(moved['lon'],moved['lat'],city);moved_replay=m._replay(moved,spec,.6)
    for (_,a),(_,b) in zip(replay['faces'],moved_replay['faces']):
        for p,q in zip(a,b):assert all(math.isclose(u,v,abs_tol=1e-7) for u,v in zip(p,q))
    # Cache cannot be contaminated by integration callers changing returned data.
    volumes[0]['minYGame']=999;assert m.ground_footprints(lm,spec)[0]['minYGame']!=999;volumes=m.ground_footprints(lm,spec)
    try:m.ground_footprints({'x':x,'z':z},spec)
    except ValueError:pass
    else:raise AssertionError('Missing model water datum must fail')
    clone=json.loads(json.dumps(original));clone['bridges'][0]['widthM']=999
    try:m.ground_footprints(lm,clone)
    except ValueError:pass
    else:raise AssertionError('Changed source spec must fail')
    try:m.source_road_profiles(lm,spec)
    except ValueError:pass
    else:raise AssertionError('Estimated heights need opt-in')
    profiles=m.source_road_profiles(lm,spec,allow_estimated=True);rail_profiles=m.source_rail_profiles(lm,spec,allow_estimated=True);assert len(profiles)==15 and len(rail_profiles)==1
    features={f['id']:f for f in json.loads((m.SOURCE_SPEC.parent/'fixed-bridge-features.geojson').read_text())['features']};shared={};shared_cases=[];covered_nodes=[]
    for row in profiles+rail_profiles:
        raw=features[row['id']];assert row['nodeIds']==raw['properties']['nodeIds'] and row['coordinatesWGS84']==raw['geometry']['coordinates']
        for n,wgs,p,h in zip(row['nodeIds'],row['coordinatesWGS84'],row['points'],row['heights']):
            assert all(math.isclose(a,b,abs_tol=1e-8) for a,b in zip(p,project(*wgs,city)))
            key=(row['bridgeId'],row['mode'],row['deck'],n)
            if key in shared:assert math.isclose(shared[key],h,abs_tol=1e-8);shared_cases.append({'sourceNodeId':n,'mode':row['mode'],'deck':row['deck'],'heightGame':h})
            shared[key]=h
            surface=m.surface_at_game(row['id'],*p,lm,spec,allow_estimated=True,mode=row['mode']);assert surface['sourceProfileHeightGame']==h
            if surface['heightGame'] is not None:
                assert math.isclose(surface['heightGame'],h,abs_tol=1e-8);covered_nodes.append({'way':row['id'],'node':n,'mode':row['mode'],'heightGame':h})
        assert all(not d['navigationAccepted'] for d in row['actualDeckRegions'])
    q=next(r for r in profiles if r['id']=='way/4348186');r=rail_profiles[0];n='3351280499';index=q['nodeIds'].index(n);point=q['points'][index]
    upper=m.surface_at_game(q['id'],*point,lm,spec,allow_estimated=True);lower=m.surface_at_game(r['id'],*point,lm,spec,allow_estimated=True,mode='rail')
    assert upper['heightGame']==12.3 and math.isclose(lower['heightGame'],5.88,abs_tol=1e-8)
    assert m.surface_at_game(r['id'],*point,lm,spec,allow_estimated=True,mode='road') is None
    assert math.isclose(upper['heightGame']-lower['heightGame'],6.42,abs_tol=1e-8)
    # Actual source-node override is game units, shared by both upper source ways,
    # but it does not move the frozen structural bridge. Query fails explicitly.
    node='1667217046';overrides={node:13.7};changed=m.source_road_profiles(lm,spec,endpoint_heights_game=overrides,allow_estimated=True)
    touched=[r for r in changed if node in r['nodeIds']];assert len(touched)==2
    override_examples=[]
    for row in touched:
        j=row['nodeIds'].index(node);assert row['heights'][j]==13.7
        surface=m.surface_at_game(row['id'],*row['points'][j],lm,spec,endpoint_heights_game=overrides,allow_estimated=True)
        assert surface['heightGame'] is None and math.isclose(surface['actualDeckHeightGame'],14.1,abs_tol=1e-8) and math.isclose(surface['heightDifferenceGame'],-.4,abs_tol=1e-8)
        override_examples.append(surface)
    audit=m.profile_geometry_audit(lm,spec,allow_estimated=True)
    assert len(audit)==15 and sum(r['missingGeometryNodeCount'] for r in audit)>0 and sum(r['profileMismatchNodeCount'] for r in audit)==0
    assert any(p['geometryAbsenceReason']=='source point laterally outside actual deck width/alignment' for r in audit for p in r['sourceNodes']+r['profileSamples'])
    assert all(not r['navigationAccepted'] for r in audit)
    # Existing fixed source 4 continuations remain present and node-consistent.
    continuations={'3112466937':['way/306360719','way/589558020','way/306360721'],'3112466958':['way/306360714','way/306360716','way/589558021']}
    continuation_checks=[]
    for node,ids in continuations.items():
        values=[]
        for ident in ids:
            row=next(r for r in profiles if r['id']==ident);j=row['nodeIds'].index(node);values.append((row['points'][j],row['heights'][j]))
        assert all(v==values[0] for v in values);continuation_checks.append({'node':node,'ways':ids,'pointGame':values[0][0],'heightGame':values[0][1],'nodeAgreement':True,'physicalApproachAccepted':False})
    # Height-aware envelopes cannot make an upper-floor railing obstruct a
    # lower-floor actor. A 1.8 game-unit probe is a CPU fixture, not player sizing.
    fuxing_upper=[v for v in volumes if v['bridgeId']=='fuxing-bridge' and v['kind'].startswith('guardrail') and v['minYGame']>14]
    assert fuxing_upper and all(v['minYGame']>8.1+1.8 for v in fuxing_upper)
    def at_point(selected,point,low,high):return [v['id'] for v in selected if v['minYGame']<high and v['maxYGame']>low and Polygon(v['polygonGame']).buffer(1e-8).covers(Point(point))]
    zbridge=next(b for b in original['bridges'] if b['id']=='zhijiang-bridge');u=(math.cos(zbridge['axisRadiansEastCCW']),math.sin(zbridge['axisRadiansEastCCW']));center=project(*zbridge['centerWGS84'],city)
    portal_openings=[]
    for station in [-123,123]:
        p=[center[j]+station*.6*u[j] for j in range(2)];hits=at_point(portals,p,11.7,13.5);assert not hits
        side=[p[0]-u[1]*22.2*.6,p[1]+u[0]*22.2*.6];hits=at_point(portals,side,2,3);assert hits
        portal_openings.append({'stationM':station,'centerPointGame':p,'probeYGame':[11.7,13.5],'blockingPylonSections':[],'sideLegContactDetected':True,'trafficClearanceAccepted':False})
    # Explicit two-leg void below Fuxing's crossbeam; no merged solid pier box.
    fbridge=next(b for b in original['bridges'] if b['id']=='fuxing-bridge');u=(math.cos(fbridge['axisRadiansEastCCW']),math.sin(fbridge['axisRadiansEastCCW']));center=project(*fbridge['centerWGS84'],city);p=[center[j]-596.5*.6*u[j] for j in range(2)]
    assert not at_point([v for v in volumes if v['bridgeId']=='fuxing-bridge' and v['kind']=='bridge-pier'],p,1,3)
    frozen=load_module(m.SOURCE_MODULE,'original_not_patched');assert frozen._Mesh.__name__=='_Mesh' and frozen._deck.__name__=='_deck' and frozen._zhijiang.__name__=='_zhijiang'
    for node in ast.walk(ast.parse(module_path.read_text())):
        if isinstance(node,ast.Import):assert all(v.name.split('.')[0] not in ['bpy','city_mesh'] for v in node.names)
        if isinstance(node,ast.ImportFrom):assert (node.module or '').split('.')[-1] not in ['bpy','city_mesh']
    assert 'bpy' not in sys.modules and 'city_mesh' not in sys.modules
    summaries=[]
    for row in audit:
        s={k:v for k,v in row.items() if k not in ['sourceNodes','profileSamples','actualDeckRegionIds']}
        s['missingOutsideMainNodes']=sum(n['geometryAbsenceReason']=='outside finite model main-span longitudinal interval' for n in row['sourceNodes'])
        s['missingLateralNodes']=sum(n['geometryAbsenceReason']=='source point laterally outside actual deck width/alignment' for n in row['sourceNodes'])
        s['missingLateralSamples']=sum(n['geometryAbsenceReason']=='source point laterally outside actual deck width/alignment' for n in row['profileSamples'])
        summaries.append(s)
    report.update(adapterModuleSha256=sha(module_path),adapterSpecSha256=sha(HERE/'spec.json'),sourceDeliverySha256=sha(delivery_path),sourceArtifactSha256=sha(glb),
      checks={'actualFrozenReplayMatchesExportedFloat32Positions':True,'finitePositiveNonemptySolidVolumes':True,'envelopeVerticesDerivedFromEmittedPrimitiveFaces':True,'allPrimitiveFacesOrPortalCapsAssociated':True,
        'scaleOnceAndExplicitGameDatum':True,'sourceShiftCompensation':True,'cachedReturnedDataIsolation':True,'changedSpecAndMissingDatumRejected':True,
        'sourceWaysNodesAndSharedHeights':True,'roadRailLevelsSeparateAtRealSharedNode':True,'overriddenProfileMismatchBlocksSurfaceLookup':True,
        'upperRailingCannotBlockLowerProbe':True,'portalCentralVoidAndSideLegPreserved':True,'pairedPierVoidPreserved':True,'noSceneImportAndNoOriginalMonkeypatch':True},
      exportedVertexComparison=glb_comparison,originalFaceCount=len(replay['faces']),portalEndCapsCoveredByNeighborSections=unassigned,
      sourceProfileCount=len(profiles),railProfileCount=1,coveredSourceNodes=covered_nodes,sharedSameDeckSourceNodes=shared_cases,
      missingSourceNodes=sum(r['missingGeometryNodeCount'] for r in audit),missingSourceSamples=sum(r['missingGeometrySampleCount'] for r in audit),
      missingUniqueSourceNodeIds=sorted({n['nodeId'] for r in audit for n in r['sourceNodes'] if not n['actualDeckRegionIds']}),
      sourceNodeCountBasis='way/node occurrences; shared nodes can appear on multiple source ways',
      estimatedWaterDisplayGameY=.9,waterDatumMeasured=False,railRoadSameNode={'node':n,'roadHeightGame':12.3,'railHeightGame':5.88,'separationGame':6.42},
      validationScope='CPU float32 GLB positions / frozen B mesh envelopes / source-node consistency only; no browser, real actor clearance, bank/approach or present driving acceptance.')
    # n above is deliberately not relied on: use the actual rail/road shared ID.
    report['railRoadSameNode']['node']='3351280499'
    report['missingUniqueSourceNodeCount']=len(report['missingUniqueSourceNodeIds'])
    write('cpu-validation.json',report);write('source-profile-geometry-audit.json',{'datumGameY':.9,'navigationAccepted':False,'profiles':audit})
    write('source-profile-summary.json',{'sourceRoadProfileCount':15,'profiles':summaries,'sourceContinuations':continuation_checks,'notTrafficClosures':True})
    write('negative-controls.json',{'explicitSourceNodeHeightGame':13.7,'mismatchedFrozenDeckQueries':override_examples,'portalOpeningProbes':portal_openings,
      'roadRailSameSourceNodeSeparate':report['railRoadSameNode'],'upperGuardrailsAboveLowerProbe':True,'probeActorHeightGame':1.8,'actorDimensionsMeasured':False})
    write('representative-solid-volumes.json',{'datumGameY':.9,'status':'candidate-not-runtime-verified','byKind':{kind:next(v for v in volumes if v['kind']==kind) for kind in report['solidKinds']}})
    print(json.dumps({'actualReplayTriangles':24148,'solidEnvelopes':len(volumes),'roadDeckRegions':len(decks),'GLBVertexSetsMatch':True,'sourceProfiles':15,
      'missingGeometrySourceNodes':report['missingSourceNodes'],'missingGeometrySamples':report['missingSourceSamples'],'navigationAccepted':False},ensure_ascii=False))


if __name__=='__main__':main()


if __name__=='__main__':main()
