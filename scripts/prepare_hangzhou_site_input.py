"""Serial, isolated geographic input with explicit source-owned site surfaces.
Does not activate the city or imply the corresponding render meshes are ready.
"""
import argparse,json,shutil,hashlib
from pathlib import Path
import shapely
from shapely.geometry import shape,Polygon,LineString
from hangzhou_surface import digest
from hangzhou_site_surfaces import SiteSurfaces
ROOT=Path(__file__).resolve().parents[1]
def triangles(geometry,height):
    result=[]
    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(geometry)):
        ps=list(t.exterior.coords)[:3]
        if not Polygon(ps).exterior.is_ccw:ps.reverse()
        result.append([[x,z,height] for x,z in ps])
    return result
def main():
    ap=argparse.ArgumentParser()
    for name in ['source','xianfu','balcony','walks','occupancy','collisions','output']:ap.add_argument('--'+name,required=True)
    a=ap.parse_args();source=ROOT/a.source;out=ROOT/a.output
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    inputs={}
    def read(p):
        p=Path(p);inputs[str(p.relative_to(ROOT))]=digest(p);return json.loads(p.read_text())
    city=read(source/'city.json');m=read(source/'geography/manifest.json');levels=read(source/'geography'/m['roadLevelsFile'])
    tin_path=ROOT/a.xianfu;tin=read(tin_path);contract_path=tin_path.parent.parent/'candidate/contract.json';contract=read(contract_path)
    if digest(contract_path)!=tin['sourceContractSha256'] or digest(source/'city.json')!=contract['inputs']['citySha256'] or digest(source/'geography'/m['roadLevelsFile'])!=contract['inputs']['roadLevelsSha256']:raise ValueError('Xianfu source drift')
    if digest(source/'geography'/m['terrainFile'])!=contract['inputs']['terrainSha256']:raise ValueError('Terrain source drift')
    for filename,sha in contract['geometryFiles'].items():
        p=contract_path.parent/filename
        if digest(p)!=sha:raise ValueError('Changed local source contract '+filename)
        inputs[str(p.relative_to(ROOT))]=sha
    by_id={r['id']:r for r in levels['roads']}
    for override in tin['upperPhysicalTierOverrides']:
        r=by_id[override['sourceRoadId']]
        if r['tier']!=override['sourceDeclaredTier']:raise ValueError('Original physical tier mismatch')
        r['sourceDeclaredTier']=r['tier'];r['tier']=override['physicalSurfaceTier'];r['physicalTierBasis']='explicit Xianfu upper deck ownership; original OSM city grade retained'
    for road_id in tin['sourceRoadGroupIds']:by_id[road_id]['surfaceGroup']='xianfu-low-passage'
    faces=[[tin['verticesENU'][i] for i in t] for t in tin['triangles']]
    sites=read(ROOT/a.walks)
    if sites['cityId']!='hangzhou':raise ValueError('Wrong walk city')
    sites['terrainPatches']=[{'id':'xianfu-low-passage','triangles':faces}]
    sites['roadSurfaces']=[{'id':'xianfu-low-passage','roadIds':tin['sourceRoadGroupIds'],'triangles':faces}]
    ownership_path=ROOT/a.balcony;ownership=read(ownership_path)
    for dep in ownership['maskFiles']:
        p=Path(dep['path']);read(p)
        if digest(p)!=dep['sha256']:raise ValueError('Changed balcony ownership mask')
    main=read(ownership_path.parent/'dry-main-terrain-cut.geojson')['features'][0]
    sites['terrainCuts'].append({'id':'city-balcony:dry-main','triangles':triangles(shape(main['geometry']),ownership['capTopYGame'])})
    for side in ['west','east']:
        features=read(ownership_path.parent/(side+'-finger-terrain-cut.geojson'))['features'];faces=[]
        for f in features:
            if 'frozenUpperTriangleIndex' not in f['properties']:continue
            ps=f['geometry']['coordinates'][0][:3]
            if not Polygon([p[:2] for p in ps]).exterior.is_ccw:ps=list(reversed(ps))
            faces.append(ps)
        sites['terrainCuts'].append({'id':'city-balcony:'+side+'-finger','triangles':faces})
    # Reject invalid units/orientation/identity before creating a candidate.
    SiteSurfaces(sites)
    detail=read(ROOT/a.collisions);occ=read(ROOT/a.occupancy)
    detail['collisionFootprints']=[p for p in detail['collisionFootprints'] if not p['id'].startswith('city-balcony:')]
    for p in occ['existingFiniteHeightSolids']:
        detail['collisionFootprints'].append({'id':'city-balcony:body:'+p['id'],'rings':p['ringsXZ'],'minY':p['minYGame'],'maxY':p['maxYGame'],'blocksRoad':True})
    for p in occ['guardPanels']:
        # The authored steel frame is finite. Retain the existing runtime wall
        # clearance/body sampling; no infinite plane or new actor radius.
        ring=LineString(p['planSegmentXZ']).buffer(p['steelFrameWidthGame']/2,cap_style=2)
        detail['collisionFootprints'].append({'id':'city-balcony:guard:'+p['id'],'rings':[list(map(list,ring.exterior.coords))],'minY':p['minYGame'],'maxY':p['maxYGame'],'blocksRoad':True})
    delivery_path=ROOT/'artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/model-delivery.json';delivery=read(delivery_path)
    if digest(ROOT/delivery['artifact'])!=ownership['actualBalconyArtifactSha256']:raise ValueError('Changed balcony model')
    for mark in detail['landmarks']:
        if mark['id']=='city-balcony':mark.update(baseYGame=delivery['baseYGame'],artifactSha256=delivery['artifactSha256'],sourceModuleSha256=delivery['sourceModuleSha256'],specSha256=delivery['specSha256'],collisionStatus='source slab/guard candidate; upper-only walking; body clearance unverified')
    navigation=read(ROOT/contract['inputs']['sourceNavigationPath'])
    if inputs[contract['inputs']['sourceNavigationPath']]!=contract['inputs']['sourceNavigationSha256']:raise ValueError('Changed source navigation')
    nav_before=hashlib.sha256(json.dumps({k:v for k,v in navigation.items() if k!='meta'},sort_keys=True).encode()).hexdigest()
    shutil.copytree(source,out)
    def write(name,data):(out/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
    write('geography/site-surfaces.json',sites);write('geography/'+m['roadLevelsFile'],levels)
    m.update(roadLevelsSha256=digest(out/'geography'/m['roadLevelsFile']),siteSurfacesFile='site-surfaces.json',siteSurfacesSha256=digest(out/'geography/site-surfaces.json'))
    write('geography/manifest.json',m)
    navigation['meta']['roadLevelsSha256']=m['roadLevelsSha256'];write('navigation.json',navigation)
    assert nav_before==hashlib.sha256(json.dumps({k:v for k,v in navigation.items() if k!='meta'},sort_keys=True).encode()).hexdigest()
    write('detail-collision-candidate.json',detail)
    inputs[str(Path(__file__).relative_to(ROOT))]=digest(Path(__file__))
    report={'cityId':'hangzhou','kind':'source-owned-site-input-candidate','inputs':inputs,'citySourceUntouched':digest(source/'city.json')==digest(out/'city.json'),'sourceNodeHeightsUntouched':all(r['points']==by_id[r['id']]['points'] and r['nodeIds']==by_id[r['id']]['nodeIds'] and r['heights']==by_id[r['id']]['heights'] for r in json.loads((source/'geography'/m['roadLevelsFile']).read_text())['roads']),'navigationGraphSha256':nav_before,'files':{f:digest(out/f) for f in ['city.json','navigation.json','geography/manifest.json','geography/'+m['roadLevelsFile'],'geography/site-surfaces.json','detail-collision-candidate.json']},'pending':['partition terrain/render faces at source patch/cut boundaries and close vertical seams','upper-road endpoint joins and lower-cavity structural geometry','actual world/actor/NPC/ebike traces','three float32 TIN residual faces','city balcony upper body/guard clearance; no lower-floor entry enabled','rebuild dependent placements/material data and hashes','real browser and visual/performance acceptance']}
    write('site-input-manifest.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
