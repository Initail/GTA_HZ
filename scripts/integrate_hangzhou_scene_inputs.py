"""Serial source-node bridge heights and reviewed local terrain cut migration.

Fresh isolated data only. Original graph coordinates/edges, controls and source
estimates remain auditable. All dependent rendered/placed assets need rebuilding.
"""
import argparse,copy,json,math,shutil
from pathlib import Path
from hangzhou_surface import digest
from hangzhou_site_surfaces import SiteSurfaces
ROOT=Path(__file__).resolve().parents[1]

def apply_profile(city,levels,navigation,proposal):
    rows=proposal['rows'];city_by={r['id']:r for r in city['roads']};by={r['id']:r for r in levels['roads']}
    if len(rows)!=proposal['affectedRoadCount'] or len({r['sourceRoadId'] for r in rows})!=len(rows):raise ValueError('Incomplete height proposal')
    nodes={};originals={};changed=set()
    for row in rows:
        rid=row['sourceRoadId'];r=by[rid];c=city_by[rid]
        for current in [r,c]:
            if current['points']!=row['points'] or list(map(str,current['nodeIds']))!=row['nodeIds'] or current['heights']!=row['originalHeights'] or current['width']!=row['widthUnchangedGame']:raise ValueError('Changed original source road '+rid)
        if len(row['nodeIds'])!=len(row['resultHeights']) or not all(math.isfinite(v) for v in row['resultHeights']):raise ValueError('Invalid proposed source elevations')
        for node,old,new in zip(row['nodeIds'],row['originalHeights'],row['resultHeights']):
            if node in nodes and (abs(nodes[node]-new)>1e-9 or abs(originals[node]-old)>1e-9):raise ValueError('Shared source node disagrees')
            nodes[node]=new;originals[node]=old
            if abs(old-new)>1e-9:changed.add(node)
    # Every adjacent way carrying a changed node must be part of the atomic
    # proposal, even if it is not itself one of the named bridge main spans.
    declared={r['sourceRoadId'] for r in rows}
    for r in levels['roads']:
        if any(str(n) in changed for n in r['nodeIds']) and r['id'] not in declared:raise ValueError('Unchanged adjacent road at modified node '+r['id'])
    for row in rows:
        for current in [by[row['sourceRoadId']],city_by[row['sourceRoadId']]]:
            current['previousEstimatedHeights']=list(current['heights'])
            current['heights']=list(row['resultHeights'])
            current['heightBasis']=row['basis']
    original_graph=copy.deepcopy(navigation)
    for i,node in enumerate(navigation['sourceNodeIds']):
        key=str(node)
        if key in nodes:
            if abs(navigation['nodeHeights'][i]-originals[key])>1e-9:raise ValueError('Navigation original height disagrees')
            navigation['nodeHeights'][i]=nodes[key]
    for key in ['nodes','edges','sourceNodeIds','componentIds','roadNodes']:
        if navigation[key]!=original_graph[key]:raise ValueError('Changed source topology '+key)
    # Recheck every source road chain, including untouched boundary ways.
    max_error=0
    for r in levels['roads']:
        chain=navigation['roadNodes'][r['id']]
        if len(chain)!=len(r['heights']):raise ValueError('Mismatched source chain')
        max_error=max(max_error,max(abs(navigation['nodeHeights'][i]-h) for i,h in zip(chain,r['heights'])))
    if max_error>1e-9:raise ValueError('Source road/graph heights diverge')
    return {'roads':len(rows),'changedSourceNodes':len(changed),'allRoadGraphHeightMaximumErrorGame':max_error,'sourceGraphCoordinatesAndEdgesUnchanged':True}

def main():
    p=argparse.ArgumentParser()
    for key in ['source','bridges','balcony','output']:p.add_argument('--'+key,required=True)
    a=p.parse_args();source=(ROOT/a.source).resolve();bridge=(ROOT/a.bridges).resolve();balcony=(ROOT/a.balcony).resolve();out=(ROOT/a.output).resolve();inputs={}
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact candidate required')
    def read(path):
        path=Path(path);inputs[str(path.relative_to(ROOT))]=digest(path);return json.loads(path.read_text())
    package=read(bridge/'package-manifest.json')
    for name,expected in package['files'].items():
        if digest(ROOT/name)!=expected:raise ValueError('Bridge package drift '+name)
        inputs[name]=expected
    proposal=read(bridge/'source-height-proposal.json');contract=read(balcony/'candidate-contract.json')
    city=read(source/'city.json');g=read(source/'geography/manifest.json');levels=read(source/'geography'/g['roadLevelsFile']);navigation=read(source/'navigation.json');sites=read(source/'geography'/g['siteSurfacesFile']);detail=read(source/'detail-collision-candidate.json')
    if any(d.get('cityId')!='hangzhou' for d in [g,levels,sites,detail,contract]) or city['meta']['cityId']!='hangzhou':raise ValueError('Wrong city')
    if digest(source/'geography'/g['roadLevelsFile'])!=proposal['sourceRoadLevelsSha256'] or g['roadLevelsSha256']!=proposal['sourceRoadLevelsSha256']:raise ValueError('Bridge profile source drift')
    if digest(ROOT/contract['physicsSitesFile'])!=contract['physicsSitesSha256']:raise ValueError('Repaired site drift')
    old=read(ROOT/contract['inputRoot']/'geography/site-surfaces.json');repair=read(ROOT/contract['physicsSitesFile'])
    if digest(ROOT/contract['inputRoot']/'geography/site-surfaces.json')!=contract['inputSitesSha256']:raise ValueError('Old cut source drift')
    if {k:v for k,v in old.items() if k!='terrainCuts'}!={k:v for k,v in repair.items() if k!='terrainCuts'}:raise ValueError('Balcony repair altered unrelated physics')
    if sites['terrainCuts']!=old['terrainCuts']:raise ValueError('Current cuts differ from reviewed original')
    sites['terrainCuts']=repair['terrainCuts'];SiteSurfaces(sites)
    changes=apply_profile(city,levels,navigation,proposal)
    for asset in detail.get('requiredStructuralAssets',[]):
        if not asset['sourceFile'].startswith('artifacts/cities/hangzhou/xianfu-structure-glb-v2/'):raise ValueError('Unrecognized structural role migration')
        if digest(ROOT/asset['sourceFile'])!=asset['sha256']:raise ValueError('Changed actual structure')
        asset['role']='landmarks';inputs[asset['sourceFile']]=asset['sha256']
    shutil.copytree(source,out)
    def write(relative,value):(out/relative).write_text(json.dumps(value,separators=(',',':'))+'\n')
    write('city.json',city);write('geography/'+g['roadLevelsFile'],levels);write('geography/'+g['siteSurfacesFile'],sites)
    g['roadLevelsSha256']=digest(out/'geography'/g['roadLevelsFile']);g['siteSurfacesSha256']=digest(out/'geography'/g['siteSurfacesFile']);write('geography/manifest.json',g)
    navigation['meta']['roadLevelsSha256']=g['roadLevelsSha256'];navigation['meta']['heightStatus']='source-node estimated bridge reconstruction plus original DSM estimates; not measured; actual driving pending';write('navigation.json',navigation);write('detail-collision-candidate.json',detail)
    files=['city.json','navigation.json','geography/manifest.json','geography/'+g['roadLevelsFile'],'geography/'+g['siteSurfacesFile'],'detail-collision-candidate.json']
    report={'cityId':'hangzhou','kind':'isolated atomic source-height and local-cut input integration','inputs':inputs,'integratorSha256':digest(Path(__file__)),'changes':changes,'physicsCutGroups':len(sites['terrainCuts']),'structuralAssetRole':'actual Xianfu structure -> landmarks; original projectile/flight mesh ownership','files':{f:digest(out/f) for f in files},'pending':['actual bridge structural asset/collision binding','full source decks and terrain render rebuild','dependent layers carrying old coordinates/heights require rebuild or explicit unchanged-region proof','Fuxing lower road/guardrail conflict and original narrow tank corridors','Balcony tunnel/service source height conflicts','browser/gameplay/visual/performance acceptance'],'status':'candidate inputs only; not activated'}
    write('scene-input-integration.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','files']},indent=2))

if __name__=='__main__':main()
