"""Serial binding of independently exported floors and bounded foundations.

Fresh candidates only. Original body footprints shift vertically; the supplied
foundation footprints are added once. This does not certify entrances.
"""
import argparse,json,shutil,subprocess
from pathlib import Path
from hangzhou_surface import digest
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    for name in ['delivery','inventory','collisions','foundations','output']:p.add_argument('--'+name,required=True)
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    inputs={}
    def read(relative):
        path=ROOT/relative;inputs[str(path.relative_to(ROOT))]=digest(path);return json.loads(path.read_text())
    delivery=read(a.delivery);old=read(a.inventory);collision=read(a.collisions);foundation=read(Path(a.foundations)/'asset-manifest.json')
    if any(d['cityId']!='hangzhou' for d in [delivery,old,collision,foundation]):raise ValueError('Wrong city')
    selected={o['id']:o for o in old['objects']};updates=[];assets=[]
    # Validate every dependency before creating the new output directory.
    for entry in delivery['objects']:
        identifier=entry['id'];previous=selected[identifier]
        for key,hashkey in [('modelDelivery','modelDeliverySha256'),('foundationAsset','foundationSha256'),
                            ('foundationAssetManifest','foundationAssetManifestSha256'),('collisionAdditions','collisionAdditionsSha256')]:
            path=ROOT/entry[key]
            if digest(path)!=entry[hashkey]:raise ValueError('Changed selected floor '+entry[key])
            inputs[entry[key]]=entry[hashkey]
        model=read(entry['modelDelivery']);addition=read(entry['collisionAdditions'])
        for key,hashkey in [('artifact','artifactSha256'),('sourceModule','sourceModuleSha256'),('spec','specSha256')]:
            if digest(ROOT/model[key])!=model[hashkey]:raise ValueError('Changed model dependency')
            inputs[model[key]]=model[hashkey]
        mark=next(m for m in collision['landmarks'] if m['id']==identifier)
        if mark['artifactSha256']!=previous['artifactSha256']:raise ValueError('Input collision belongs to another model')
        delta=model['baseYGame']-mark['baseYGame']
        if abs(delta-entry['sourceBodyDeltaYGame'])>1e-12:raise ValueError('Unexpected/repeated floor delta')
        body=[s for s in collision['collisionFootprints'] if s['id'].startswith(identifier+':')]
        if len(body)!=entry['sourceOriginalCollisionCountToOffset']:raise ValueError('Body ownership/count mismatch')
        for solid in body:solid['minY']+=delta;solid['maxY']+=delta
        extras=addition['collisionFootprints']
        if len(extras)!=entry['collisionCount'] or any(not s['id'].startswith(identifier+':') for s in extras):raise ValueError('Foreign foundation collision')
        collision['collisionFootprints'].extend(extras)
        mark.update(baseYGame=model['baseYGame'],artifactSha256=model['artifactSha256'],sourceModuleSha256=model['sourceModuleSha256'],specSha256=model['specSha256'],collisionStatus='actual rigid floor and bounded foundation candidate; entry/actor/visual pending')
        selected[identifier]={**previous,'deliveryFile':entry['modelDelivery']}
        updates.append({'id':identifier,'deltaYGame':delta,'bodyFootprintsShifted':len(body),'foundationFootprintsAdded':len(extras)})
        manifest=read(entry['foundationAssetManifest']);record=next(r for r in manifest['assets'] if r['sha256']==entry['foundationSha256'])
        assets.append((ROOT/entry['foundationAsset'],{**record,'file':identifier+'-foundations.glb'}))
    ids=[s['id'] for s in collision['collisionFootprints']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate collision ID')
    for record in foundation['assets']:
        path=ROOT/a.foundations/record['file']
        if digest(path)!=record['sha256']:raise ValueError('Changed original foundations')
        inputs[str(path.relative_to(ROOT))]=record['sha256'];assets.append((path,{**record,'file':'core-'+record['file']}))
    out.mkdir(parents=True);fdir=out/'foundations';fdir.mkdir()
    for path,record in assets:shutil.copy2(path,fdir/record['file'])
    (fdir/'asset-manifest.json').write_text(json.dumps({'cityId':'hangzhou','kind':'source-preserving six-object foundation set','inputs':inputs,'assets':[r for p,r in assets],'active':False},indent=2)+'\n')
    collision['status']='six rigid floor/foundation candidates; independent entrance/actor/visual gates remain'
    (out/'detail-collision-candidate.json').write_text(json.dumps(collision,separators=(',',':'))+'\n')
    subprocess.run(['node','scripts/hangzhou_candidate_inventory.mjs',str(out/'model-inventory.json'),*[selected[o['id']]['deliveryFile'] for o in old['objects']]],cwd=ROOT,check=True)
    report={'cityId':'hangzhou','kind':'serial floor candidate integration; not installed','inputs':inputs,'updates':updates,
            'integrationScriptSha256':digest(Path(__file__)),'files':{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()},
            'pending':['entry/road/step/body traces','Theatre top stair/plinth discontinuity','remaining landmark floors','full rendering and runtime acceptance']}
    (out/'integration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(updates,indent=2))
if __name__=='__main__':main()
