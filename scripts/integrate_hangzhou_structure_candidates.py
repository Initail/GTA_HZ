"""Bind actual bridge structures and the checked exterior theatre access.
Keeps original object models, road topology and the other collision bodies.
Produces a fresh input candidate; runtime asset assembly remains mandatory.
"""
import argparse,json,shutil,math
from pathlib import Path
from shapely.geometry import Polygon
from hangzhou_surface import digest
from hangzhou_site_surfaces import SiteSurfaces
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    for key in ['source','bridge','entry','output']:p.add_argument('--'+key,required=True)
    a=p.parse_args();source=ROOT/a.source;bridge=ROOT/a.bridge;entry=ROOT/a.entry;out=(ROOT/a.output).resolve();inputs={}
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh output required')
    def read(p):
        p=Path(p);inputs[str(p.relative_to(ROOT))]=digest(p);return json.loads(p.read_text())
    def verify(files):
        for name,value in files.items():
            expected=value['sha256'] if isinstance(value,dict) else value
            if digest(ROOT/name)!=expected:raise ValueError('Candidate drift '+name)
            inputs[name]=expected
    bp=read(bridge/'package-manifest.json');verify(bp['files'])
    if bp['actualGlbChecks']['failed'] or bp['nullEngineChecks']['failed']:raise ValueError('Bridge actual GLB failed')
    if digest(bridge.parent/'package-manifest.json')!=bp['sourcePackageSha256']:raise ValueError('Wrong bridge source proposal')
    ep=read(entry/'delivery.json');verify(ep['artifacts']);contract=read(entry/'integration-contract.json');walk=read(ROOT/contract['appendSiteData'])
    pose=read(ROOT/contract['optionalICCSourcePose']);bodies=read(bridge.parent/'collision-candidate.json')['rows']
    city=read(source/'city.json');detail=read(source/'detail-collision-candidate.json');g=read(source/'geography/manifest.json');sites=read(source/'geography'/g['siteSurfacesFile']);nav=read(source/'navigation.json')
    if city['meta']['cityId']!='hangzhou' or detail['cityId']!='hangzhou' or sites['cityId']!='hangzhou':raise ValueError('Wrong city')
    if digest(source/'geography'/g['siteSurfacesFile'])!=g['siteSurfacesSha256']:raise ValueError('Current site drift')
    retirement=set(contract['deleteOnlyExplicitCollisionIds']);existing={r['id'] for r in detail['collisionFootprints']}
    if not retirement.issubset(existing) or not set(contract['preserveCollisionIds']).issubset(existing):raise ValueError('Theatre body identity drift')
    if len(retirement)!=32 or any(not i.startswith('grand-theatre:stair-underbody:') for i in retirement):raise ValueError('Unexpected body retirement scope')
    detail['collisionFootprints']=[r for r in detail['collisionFootprints'] if r['id'] not in retirement]
    for kind,number in [('walkFloors',contract['appendWalkFloorCount']),('solidSlabs',contract['appendSolidSlabCount'])]:
        if len(walk[kind])!=number or any(gp['id'] in {r['id'] for r in sites[kind]} for gp in walk[kind]):raise ValueError('Duplicate/missing theatre surface')
        sites[kind].extend(walk[kind])
    SiteSurfaces(sites)
    for row in bodies:
        ring=row['polygonGame'];poly=Polygon(ring)
        if not poly.is_valid or poly.area<=0 or not math.isfinite(row['minYGame']+row['maxYGame']) or row['maxYGame']<=row['minYGame']:raise ValueError('Invalid retained bridge structure')
        identifier='qiantang-bridges:'+row['id']
        if identifier in existing:raise ValueError('Repeated bridge collision')
        detail['collisionFootprints'].append({'id':identifier,'rings':[ring],'minY':row['minYGame'],'maxY':row['maxYGame'],'blocksRoad':True,'sourcePrimitiveId':row['id']})
        detail['structuralCollisionIds'].append(identifier);existing.add(identifier)
    for role,filename,expected in [('coastal-bridges',str((bridge/'coastal-bridges.glb').relative_to(ROOT)),bp['artifactSha256']),('landmarks',contract['newAsset'],contract['newAssetSha256'])]:
        if digest(ROOT/filename)!=expected:raise ValueError('Changed actual geometry asset')
        inputs[filename]=expected;detail['requiredStructuralAssets'].append({'role':role,'sourceFile':filename,'sha256':expected})
    # Copy only the verified source pose; the peer report also contains stale
    # historical model/coordinate fields which must not replace current data.
    mark=next(m for m in city['landmarks'] if m['id']==pose['id']);arrival=pose['arrival'];road=next(r for r in city['roads'] if r['id']==arrival['arrivalRoadId'])
    if not road['id'].startswith(pose['unchangedSourceWayId']+'#'):raise ValueError('Arrival segment does not belong to original source way')
    node_index=list(map(str,road['nodeIds'])).index(str(pose['arrivalSourceNodeId']))
    if math.dist(road['points'][node_index],arrival['arrival'])>1e-8:raise ValueError('ICC arrival is not its declared original source node')
    mark['previousSourceArrival']=mark['arrival'];mark['arrival']=arrival['arrival'];mark['yaw']=arrival['yaw'];mark['arrivalRoadId']=road['id'];mark['arrivalSourceNodeId']=pose['arrivalSourceNodeId']
    detail['status']='actual bridge structures plus checked exterior walk candidates; actor/visual blockers retained'
    shutil.copytree(source,out)
    def write(relative,obj):(out/relative).write_text(json.dumps(obj,separators=(',',':'))+'\n')
    write('city.json',city);write('detail-collision-candidate.json',detail);write('geography/'+g['siteSurfacesFile'],sites);g['siteSurfacesSha256']=digest(out/'geography'/g['siteSurfacesFile']);write('geography/manifest.json',g)
    if digest(out/'navigation.json')!=digest(source/'navigation.json'):raise ValueError('Structure integration altered navigation')
    report={'cityId':'hangzhou','inputs':inputs,'integratorSha256':digest(Path(__file__)),'bridgeColliders':len(bodies),'retiredTheatreBodies':sorted(retirement),'addedWalkGroups':len(walk['walkFloors']),'addedSlabGroups':len(walk['solidSlabs']),'requiredStructuralAssets':detail['requiredStructuralAssets'],'iccSourceNodeArrival':{'node':pose['arrivalSourceNodeId'],'road':road['id'],'arrival':mark['arrival']},'navigationBytesUnchanged':True,'files':{name:digest(out/name) for name in ['city.json','detail-collision-candidate.json','geography/manifest.json','geography/'+g['siteSurfacesFile']]},'pending':['actual assets must be assembled into their original runtime roles','new actor/walk surfaces need terrain/props exclusions and camera verification','Fuxing source cross-sections and original tank width blockers','theatre full curved terrace/architectural door not reconstructed','source tunnel/service profiles and full base mesh rebuild','browser visuals/gameplay/performance'],'status':'isolated candidate, not activation'}
    write('structure-integration.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','retiredTheatreBodies']},indent=2))
if __name__=='__main__':main()
