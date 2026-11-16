"""Render a local GLB in Blender for intermediate shape review (not in-game QA)."""
import sys
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))

def main(argv):
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--street-bearing',type=float,default=225.0)
    parser.add_argument('--views',nargs='+',choices=['front','back','left','right','top','street_three_quarter'],default=None)
    args=parser.parse_args(argv); output=(ROOT/args.output).resolve()
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())): raise ValueError('Fresh artifacts directory required')
    import bpy
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str((ROOT/args.input).resolve()))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    from landmarks.candidate_preview import render_preview
    output.mkdir(parents=True,exist_ok=True)
    options={'street_bearing_degrees':args.street_bearing}
    if args.views:options['views']=args.views
    result=render_preview(objects,output,**options)
    (output/'review-kind.json').write_text(json.dumps({'kind':'Blender shape preview; no runtime/context/collision/performance pass','input':args.input,'result':result},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__': main(sys.argv[sys.argv.index('--')+1:])
