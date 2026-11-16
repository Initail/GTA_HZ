"""Serial isolated export of the frozen Hangzhou tree family (24 prototypes)."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(argv);out=(ROOT/a.output).resolve()
 if ROOT/'artifacts' not in out.parents or (out.exists() and any(out.iterdir())):raise ValueError('Fresh candidate required')
 source=ROOT/'docs/hangzhou/research/vegetation';palette=json.loads((source/'palette-spec.json').read_text())
 from city_config import load_city
 from landmarks import hangzhou_tree_palette as trees
 profile=load_city('hangzhou');scale=profile['geography']['scale']
 import city_mesh as cm
 from landmark_tasks import glb_stats
 cm.O=out/'landscape/canopy';cm.O.mkdir(parents=True)
 definitions=trees.material_definitions()
 for definition in definitions.values():cm.material(definition['name'],definition['color'],definition['roughness'],definition['metallic'])
 models=[];reports=[];inputs=[ROOT/'scripts/landmarks/hangzhou_tree_palette.py',source/'palette-spec.json',ROOT/'config/cities/hangzhou.json']
 for species in palette['species']:
  for lod in range(3):
   spec_path=source/'prototype-specs'/f"{species['id']}-lod{lod}.json";spec=json.loads(spec_path.read_text());inputs.append(spec_path)
   spec['materialMap']={slot:d['name'] for slot,d in definitions.items()}
   b=cm.B();report=trees.build(b,{'x':0,'z':0,'y':0},spec,scale)
   identifier=species['id']+(['','-mid','-far'][lod]);objects=b.finish(identifier,smooth=True)
   exported=cm.export(identifier,objects);path=cm.O/(identifier+'.glb');stats=glb_stats(path,identifier+'_')
   if stats['triangles']!=report['triangles']:raise ValueError('Exported tree triangle mismatch '+identifier)
   models.append({'id':identifier,'species':species['id'],'lod':lod,'file':'canopy/'+path.name,'triangles':stats['triangles'],
    'meshes':exported['meshes'],'bytes':path.stat().st_size,'height':report['heightGame'],'crownRadius':report['crownRadiusGame'],'sha256':digest(path)})
   reports.append(report)
 manifest={'version':1,'cityId':'hangzhou','species':[{'id':s['id'],'name':s['name'],'height':s['prototypeHeightM']*scale,'crown':s['prototypeCrownRadiusM']*2*scale} for s in palette['species']],
  'models':models,'units':'game units; geographic scale applied once inside prototype build; instances apply variation only',
  'dimensionStatus':'estimated archetypes; not a local tree census','sourceInputs':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in inputs]}
 (cm.O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 delivery={'cityId':'hangzhou','kind':'actual-exported-regional-tree-family','manifestSha256':digest(cm.O/'manifest.json'),'models':len(models),
  'triangles':sum(m['triangles'] for m in models),'bytes':sum(m['bytes'] for m in models),'cpuReports':reports,
  'pending':['actual source-bound placements','leaf and flower fine detail','Blender shape review','runtime LOD and clearance','day/night/rain/performance/browser']}
 (out/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:delivery[k] for k in ['kind','models','triangles','bytes','pending']},ensure_ascii=False,indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
