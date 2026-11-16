"""Serial Blender exporter for evidence-ready Hangzhou modules, into candidates.

Run in a separate --background --factory-startup process. The live Blender
scene and current public assets are not touched. No city_mesh import in host.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv):
    parser=argparse.ArgumentParser(); parser.add_argument('--job',required=True); parser.add_argument('--spec',required=True)
    parser.add_argument('--module',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--palette',default=None)
    parser.add_argument('--base-y',type=float,default=0)
    parser.add_argument('--placement',default=None)
    args=parser.parse_args(argv)
    output=(ROOT/args.output).resolve()
    if ROOT/'artifacts' not in output.parents or 'public' in output.parts: raise ValueError('Candidate output under artifacts required')
    if output.exists() and any(output.iterdir()): raise ValueError('Fresh candidate output required')
    from landmark_tasks import assess
    job_path=(ROOT/args.job).resolve(); job,status=assess(job_path)
    if status['currentStage'] not in ('evidence-ready','modelled','verified'): raise ValueError('Evidence gate not passed: '+json.dumps(status['errors']['evidence-ready'],ensure_ascii=False))
    if job['coordinatePolicy']['cityId']!='hangzhou': raise ValueError('Hangzhou job required')
    source=(ROOT/args.module).resolve(); spec_path=(ROOT/args.spec).resolve(); spec=json.loads(spec_path.read_text())
    from hangzhou_exclusions import normalized_exclusion_ids
    excluded_ids=normalized_exclusion_ids(spec.get('baseBuildingIdsToExclude',[]),spec)
    if spec['id']!=job['place']['id'] or spec['cityId']!='hangzhou': raise ValueError('Spec identity mismatch')
    from city_config import load_city,project
    city=load_city('hangzhou'); x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city)
    # This is intentionally the only Blender-scene initialization in the process.
    import city_mesh
    output.mkdir(parents=True,exist_ok=True); city_mesh.O=output
    module_spec=importlib.util.spec_from_file_location('hangzhou_candidate_module',source)
    module=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
    builder=city_mesh.B(); identifier=spec['id']; prefix='detail_'+identifier+'_'
    source_inputs=[]
    if args.palette:
        palette_path=(ROOT/args.palette).resolve();palette=json.loads(palette_path.read_text())
        if palette['cityId']!='hangzhou':raise ValueError('Wrong material palette city')
        for token,values in palette['objects'].get(identifier,{}).items():
            if token not in city_mesh.M:raise ValueError('Unknown shared material token '+token)
            color=values['color'];rough=values['roughness'];metal=values['metallic']
            if len(color)!=3 or any(not 0<=v<=1 for v in [*color,rough,metal]):raise ValueError('Invalid authored material values')
            replacement=city_mesh.material('hz-'+identifier+'-'+token,color,rough,metal)
            city_mesh.M[token]=replacement
        source_inputs.append({'path':str(palette_path.relative_to(ROOT)),'sha256':digest(palette_path),'basis':palette['basis'],'role':'material-palette'})
    if not math.isfinite(args.base_y):raise ValueError('Finite game-unit base height required')
    lm={'id':identifier,'x':x,'z':z,'y':args.base_y}
    if args.placement:
        pp=(ROOT/args.placement).resolve();placement=json.loads(pp.read_text())
        if args.base_y!=0 or placement['id']!=identifier or placement['cityId']!='hangzhou' or placement['units']!='absolute game metres; never multiply input y by .60':raise ValueError('One matching explicit game-unit placement required')
        supplied=placement['landmark']
        if math.hypot(supplied['x']-x,supplied['z']-z)>.001:raise ValueError('Placement anchor does not match source footprint')
        for dependency in placement['sourceInputs']:
            if digest(ROOT/dependency['path'])!=dependency['sha256']:raise ValueError('Changed placement source')
        lm.update(supplied);source_inputs.append({'path':str(pp.relative_to(ROOT)),'sha256':digest(pp),'role':'placement','basis':placement['heightBasis']})
    report=module.build(builder,lm,spec,city['geography']['scale'])
    objects=builder.finish('detail_'+identifier)
    export=city_mesh.export(identifier,objects)
    artifact=output/(identifier+'.glb')
    from landmark_tasks import glb_stats
    stats=glb_stats(artifact,prefix)
    delivery={'id':identifier,'status':'model-exported-not-verified','scope':spec.get('scope'),
              'cityId':'hangzhou','sourceModule':str(source.relative_to(ROOT)),'sourceModuleSha256':digest(source),
              'spec':str(spec_path.relative_to(ROOT)),'specSha256':digest(spec_path),
              'artifact':str(artifact.relative_to(ROOT)),'artifactSha256':digest(artifact),
              'coordinateConfigSha256':digest(ROOT/'config/cities/hangzhou.json'),
              'sourceSnapshotSha256':spec.get('sourceSnapshotSha256'),'anchorGame':[x,z],'baseYGame':lm['y'],'hallBaseYGame':lm.get('hallBaseYGame'),'scale':city['geography']['scale'],
              'gltfOrientation':'Blender east/north/up -> glTF Y-up; existing Babylon root identity fix required',
              'baseBuildingIdsToExclude':excluded_ids,'sourceSpecExclusionIds':spec.get('baseBuildingIdsToExclude',[]),'modelReport':report,'export':export,'glbStats':stats,'sourceInputs':source_inputs,
              'pending':['base and facade exclusion','ground datum','connected arrival','collision and passage','three in-game views','day/night','performance']}
    (output/'model-delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(delivery,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
