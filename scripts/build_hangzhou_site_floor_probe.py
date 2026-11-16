"""Export one frozen source floor TIN without dropping float32 residual faces.

Run in factory-startup Blender. This is a local render probe, not a complete
tunnel: walls, ceiling, surrounding earth and integration remain separate.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    ap=argparse.ArgumentParser();ap.add_argument('--tin',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
    source=(ROOT/a.tin).resolve();out=(ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact candidate required')
    d=json.loads(source.read_text());contract=source.parent.parent/'candidate/contract.json'
    if sha(contract)!=d['sourceContractSha256']:raise ValueError('Changed source contract')
    import numpy as np
    import city_mesh as cm
    triangles=np.array(d['verticesENU'],dtype='f8')[np.array(d['triangles'])]
    # Match the existing road renderer: asphalt is .1 game above the sampled
    # road ordinate. This is a rendering offset, never a second city scale.
    triangles[:,:,2]+=.1
    origin=np.floor(triangles.mean((0,1)));chosen=None
    for degree in range(360):
        angle=degree*math.pi/180
        basis=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
        local=((triangles-origin)@basis).astype('f4')
        c=np.cross(local[:,1].astype('f8')-local[:,0],local[:,2].astype('f8')-local[:,0])
        if np.all(c[:,2]>0):chosen=(angle,local);break
    if chosen is None:raise ValueError('No lossless local frame found')
    angle,local=chosen;flat=local.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
    mesh=cm.bpy.data.meshes.new('roads_xianfu_floor_probe');mesh.vertices.add(len(unique));mesh.vertices.foreach_set('co',unique.ravel())
    mesh.loops.add(len(flat));mesh.loops.foreach_set('vertex_index',indices.astype(np.int32))
    mesh.polygons.add(len(local));mesh.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype=np.int32));mesh.polygons.foreach_set('loop_total',np.full(len(local),3,dtype=np.int32));mesh.update()
    ob=cm.bpy.data.objects.new(mesh.name,mesh);cm.bpy.context.collection.objects.link(ob);mesh.materials.append(cm.M['asphalt']);ob.location=origin;ob.rotation_euler[2]=angle
    uv=mesh.uv_layers.new();uv.data.foreach_set('uv',(triangles.reshape(-1,3)[:,:2]/14).astype('f4').ravel());cm.bpy.context.view_layer.update()
    matrix=np.array(ob.matrix_world,dtype='f8');world=local.astype('f8')@matrix[:3,:3].T+matrix[:3,3]
    c=np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0]);error=float(np.linalg.norm(world-triangles,axis=2).max())
    if np.any(c[:,2]<=0) or error>.001:raise ValueError('Serialized frame loses source topology or position')
    out.mkdir(parents=True);cm.O=out;asset=cm.export('xianfu-floor-probe',[ob])
    if asset['triangles']!=len(triangles):raise ValueError('Exporter dropped source faces')
    np.savez_compressed(out/'source-triangles.npz',triangles=triangles,localTriangles=local)
    report={'kind':'local source TIN render probe','sourceTin':str(source.relative_to(ROOT)),'sourceTinSha256':sha(source),'sourceContractSha256':sha(contract),'builderSha256':sha(Path(__file__)),'sourceFaces':len(triangles),'asset':asset,'artifactSha256':sha(out/asset['file']),'frame':{'originENU':origin.tolist(),'angleRadians':angle,'actualMatrixENU':matrix.tolist()},'asphaltOffsetGame':.1,'localPositiveFaces':len(triangles),'actualMatrixNonpositiveFaces':int((c[:,2]<=0).sum()),'actualMatrixMaxVertexErrorGame':error,'sourceTrianglesSha256':sha(out/'source-triangles.npz'),'pending':['independent actual GLB triangle/UV/world-matrix verification','closed structural walls and ceiling; terrain partition integration','all source roads and upper endpoint transitions','browser and visual/performance acceptance']}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
