"""Export an already-clipped exposed soil curtain; no new terrain or road."""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--report',default='soil-exposure-report.json');a=p.parse_args(argv)
    source=(ROOT/a.source).resolve();out=(ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact directory required')
    manifest=json.loads((source/'package-manifest.json').read_text())
    meshpath=source/'soil-exposure-export.npz';reportpath=source/a.report
    # Read the frozen packet binding rather than accepting an arbitrary NPZ.
    text=json.dumps(manifest)
    if sha(meshpath) not in text or sha(reportpath) not in text:raise ValueError('Soil files absent from frozen packet hashes')
    import numpy as np
    import city_mesh as cm
    with np.load(meshpath) as data:triangles=data['trianglesENU'];origin=data['originENU'].astype('f4').astype('f8');uv=data['uvs'].astype('f4')
    local=(triangles-origin).astype('f4');flat=local.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
    wide=local.astype('f8');normal=np.cross(wide[:,1]-wide[:,0],wide[:,2]-wide[:,0])
    if np.any(np.linalg.norm(normal,axis=1)==0):raise ValueError('Soil face degenerates in local float32')
    u,v=uv[:,1].astype('f8')-uv[:,0],uv[:,2].astype('f8')-uv[:,0]
    if np.any(u[:,0]*v[:,1]-u[:,1]*v[:,0]==0):raise ValueError('Soil UV degenerates in float32')
    mesh=cm.bpy.data.meshes.new('terrain_xianfu_soil_land');mesh.vertices.add(len(unique));mesh.vertices.foreach_set('co',unique.ravel())
    mesh.loops.add(len(flat));mesh.loops.foreach_set('vertex_index',indices.astype('i4'));mesh.polygons.add(len(local))
    mesh.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4'));mesh.polygons.foreach_set('loop_total',np.full(len(local),3,dtype='i4'));mesh.update()
    ob=cm.bpy.data.objects.new(mesh.name,mesh);cm.bpy.context.collection.objects.link(ob);ob.location=origin
    mesh.materials.append(cm.M['land']);mesh.uv_layers.new().data.foreach_set('uv',uv.ravel());cm.bpy.context.view_layer.update()
    matrix=np.asarray(ob.matrix_world,dtype='f8');world=wide@matrix[:3,:3].T+matrix[:3,3];error=float(np.linalg.norm(world-triangles,axis=2).max())
    if error>.001:raise ValueError('Soil serialization exceeds position budget')
    out.mkdir(parents=True);cm.O=out;asset=cm.export('xianfu-soil-skin',[ob])
    if asset['triangles']!=len(local):raise ValueError('Exporter changed soil triangle count')
    np.savez_compressed(out/'serialized-source.npz',local=local,uv=uv)
    result={'cityId':'hangzhou','kind':'actual exposed soil curtain; not a standalone closed solid',
            'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [source/'package-manifest.json',meshpath,reportpath,Path(__file__)]},
            'assets':[{**asset,'sha256':sha(out/asset['file'])}],'originENU':origin.tolist(),'matrixENU':matrix.tolist(),
            'actualMaxVertexErrorGame':error,'serializedSourceSha256':sha(out/'serialized-source.npz'),
            'pending':['independent actual GLB source/UV verification','terrain-edge merge and portal clearance','browser visual/performance']}
    (out/'asset-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
