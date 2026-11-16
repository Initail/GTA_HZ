"""Bind a checked source-node join and real structure to fresh city inputs.
No public installation; the base roads/terrain still require explicit rebuild.
"""
import argparse,json,shutil
from pathlib import Path
from hangzhou_surface import digest
from hangzhou_site_surfaces import SiteSurfaces
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    for name in ['source','join','structure','collisions','output']:p.add_argument('--'+name,required=True)
    a=p.parse_args();source=ROOT/a.source;join=ROOT/a.join;structure=ROOT/a.structure;out=(ROOT/a.output).resolve();inputs={}
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    def read(path):
        path=Path(path);inputs[str(path.relative_to(ROOT))]=digest(path);return json.loads(path.read_text())
    m=read(source/'geography/manifest.json');sites=read(source/'geography'/m['siteSurfacesFile'])
    if digest(source/'geography'/m['siteSurfacesFile'])!=m['siteSurfacesSha256']:raise ValueError('Changed current site data')
    tin=read(join/'floor-tin-v2.json');bodies=read(join/'collision-proposal.json');owner=read(join/'renderer-ownership.json')
    asset=read(structure/'asset-manifest.json');details=read(ROOT/a.collisions)
    if any(d['cityId']!='hangzhou' for d in [m,sites,tin,bodies,owner,asset,details]):raise ValueError('Wrong city')
    for name,expected in asset['inputs'].items():
        if digest(ROOT/name)!=expected:raise ValueError('Changed structural source '+name)
        inputs[name]=expected
    for f in asset['assets']:
        file=structure/f['file']
        if digest(file)!=f['sha256']:raise ValueError('Changed actual structure')
        inputs[str(file.relative_to(ROOT))]=f['sha256']
    faces=[[tin['verticesENU'][i] for i in face] for face in tin['triangles']]
    previous=next(g for g in sites['terrainPatches'] if g['id']=='xianfu-low-passage')['triangles']
    if faces[:len(previous)]!=previous or len(faces)<=len(previous):raise ValueError('Join must preserve every old TIN face')
    for kind in ['terrainPatches','roadSurfaces']:
        group=next(g for g in sites[kind] if g['id']=='xianfu-low-passage')
        if kind=='roadSurfaces' and group['roadIds']!=tin['sourceRoadGroupIds']:raise ValueError('Join changed source road ownership')
        group['triangles']=faces
    if any(g['id'].startswith('xianfu:') for g in sites['solidSlabs']):raise ValueError('Underpass slabs already integrated')
    sites['solidSlabs'].extend(bodies['solidSlabs']);SiteSurfaces(sites)
    ids={s['id'] for s in details['collisionFootprints']}
    if any(s['id'] in ids or not s['id'].startswith('xianfu:') for s in bodies['collisionFootprints']):raise ValueError('Repeated/foreign structure collision')
    details['collisionFootprints'].extend(bodies['collisionFootprints'])
    details['structuralCollisionIds']=[s['id'] for s in bodies['collisionFootprints']]
    details['requiredStructuralAssets']=[{'role':'roads','sourceFile':str((structure/f['file']).relative_to(ROOT)),'sha256':f['sha256']} for f in asset['assets']]
    details['status']='landmark floors plus source-owned underpass collision; corresponding terrain/roads assembly mandatory'
    shutil.copytree(source,out)
    def write(relative,value):(out/relative).write_text(json.dumps(value,separators=(',',':'))+'\n')
    write('geography/'+m['siteSurfacesFile'],sites);m['siteSurfacesSha256']=digest(out/'geography'/m['siteSurfacesFile']);write('geography/manifest.json',m)
    write('detail-collision-candidate.json',details)
    assert digest(source/'city.json')==digest(out/'city.json')
    assert digest(source/'navigation.json')==digest(out/'navigation.json')
    report={'cityId':'hangzhou','kind':'isolated underpass source join and collision input',
            'inputs':inputs,'integratorSha256':digest(Path(__file__)),'oldFloorFaces':len(previous),'newFloorFaces':len(faces),
            'structuralWalls':len(bodies['collisionFootprints']),'roofSlabGroups':len(bodies['solidSlabs']),
            'sourceCityAndNavigationBytesUnchanged':True,
            'files':{f:digest(out/f) for f in ['city.json','navigation.json','geography/manifest.json','geography/'+m['siteSurfacesFile'],'detail-collision-candidate.json']},
            'pending':['render clipped source floor/outer F1 and soil curtain','replace old upper deck within declared source ownership','terrain/roads must contain actual structure exactly once','narrow tank turn remains blocked','balcony road profiles and terrain joins','runtime/browser acceptance']}
    write('underpass-input-manifest.json',report);print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))
if __name__=='__main__':main()
