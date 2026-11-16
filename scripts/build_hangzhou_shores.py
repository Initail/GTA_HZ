"""Isolated Blender export of prepared source shoreline solids, no city rebuild."""
from pathlib import Path
import argparse,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import digest
from build_hangzhou_foundations import triangle_hash
def main(argv):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);args=ap.parse_args(argv)
    source=(ROOT/args.input).resolve();out=(ROOT/args.output).resolve();manifest=json.loads((source/'manifest.json').read_text())
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    if manifest['kind']!='four-source-shore-contact-candidate' or manifest['cityId']!='hangzhou':raise ValueError('Wrong prepared source')
    for p,sha in manifest['inputs'].items():
        if digest(ROOT/p)!=sha:raise ValueError('Changed prepared shore '+p)
    import numpy as np
    import city_mesh as cm
    cm.material('seawall',(.29,.33,.32),.88);out.mkdir(parents=True);cm.O=out;objects=[];records=[]
    for record in manifest['objects']:
        p=source/record['file']
        if digest(p)!=record['sha256']:raise ValueError('Changed shore mesh')
        with np.load(p) as arrays:triangles=arrays[record['material']]
        origin=np.array([math.floor(triangles[:,:,0].min()/640)*640,math.floor(triangles[:,:,1].min()/640)*640,0.])
        local=(triangles-origin).astype('<f4');flat=local.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
        if np.any(np.linalg.norm(np.cross(local[:,1].astype('f8')-local[:,0],local[:,2].astype('f8')-local[:,0]),axis=1)==0):raise ValueError('Shore face collapsed in float32')
        name=record['name']+'_'+record['material']
        if name in cm.bpy.data.objects:raise ValueError('Duplicate shore mesh name')
        data=cm.bpy.data.meshes.new(name);data.vertices.add(len(unique));data.vertices.foreach_set('co',unique.ravel());data.loops.add(len(flat));data.loops.foreach_set('vertex_index',indices.astype('i4'));data.polygons.add(len(local));data.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4'));data.polygons.foreach_set('loop_total',np.full(len(local),3,dtype='i4'));data.update()
        ob=cm.bpy.data.objects.new(name,data);cm.bpy.context.collection.objects.link(ob);ob.location=origin;data.materials.append(cm.M[record['material']]);objects.append(ob)
        uv=[]
        for t in triangles:
            normal=np.cross(t[1]-t[0],t[2]-t[0]);axis=int(np.argmax(np.abs(normal)));axes=([1,2],[0,2],[0,1])[axis]
            uv.extend(t[:,axes]/8)
        data.uv_layers.new().data.foreach_set('uv',np.asarray(uv,dtype='f4').ravel())
        gltf=local[:,:,[0,2,1]].copy();gltf[:,:,2]*=-1
        records.append({'id':record['id'],'mesh':name,'triangles':len(local),'originENU':origin.tolist(),'maxSerializationErrorGame':float(np.abs(local.astype('f8')+origin-triangles).max()),'localGltfTrianglesSha256':triangle_hash(gltf)})
    before=sum(len(o.data.polygons) for o in objects);asset=cm.export('coastal-shoreline',objects)
    if asset['triangles']!=before:raise ValueError('Blender changed shore triangles')
    result={'cityId':'hangzhou','kind':'actual-four-source-shore-contact-GLB','sourceManifest':str((source/'manifest.json').relative_to(ROOT)),'sourceManifestSha256':digest(source/'manifest.json'),'exporterSha256':digest(Path(__file__)),'triangleHasherSha256':digest(ROOT/'scripts/build_hangzhou_foundations.py'),'assets':[{**asset,'sha256':digest(out/asset['file'])}],'objects':records,'pending':manifest['pending']}
    (out/'asset-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
