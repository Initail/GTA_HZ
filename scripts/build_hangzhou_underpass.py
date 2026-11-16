"""Export frozen underpass structure in an isolated Blender scene, once scaled."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(argv):
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--output',required=True);a=p.parse_args(argv)
    source=(ROOT/a.spec).resolve();out=(ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    spec=json.loads(source.read_text())
    import numpy as np
    from landmarks import xianfu_underpass as model
    geometry=model.load_geometry(spec)
    import city_mesh as cm
    origin=np.array(geometry['localOriginENU'],dtype='f4').astype('f8')
    out.mkdir(parents=True);cm.O=out;objects=[];records=[];expected={}
    for index,part in enumerate(geometry['parts']):
        vertices=np.asarray(part['trianglesENU'],dtype='f8')
        local=(vertices-origin).astype('f4');wide=local.astype('f8')
        if np.any(np.linalg.norm(np.cross(wide[:,1]-wide[:,0],wide[:,2]-wide[:,0]),axis=1)==0):raise ValueError('Degenerate local geometry '+part['id'])
        uv=np.asarray([model.projected_uv(t,origin) for t in vertices],dtype='f4')
        du,dv=uv[:,1].astype('f8')-uv[:,0],uv[:,2].astype('f8')-uv[:,0]
        if np.any(du[:,0]*dv[:,1]-du[:,1]*dv[:,0]==0):raise ValueError('Degenerate projected UV '+part['id'])
        name='roads_xianfu_structure_'+str(index)+'_'+part['material']
        mesh=cm.bpy.data.meshes.new(name);flat=local.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
        mesh.vertices.add(len(unique));mesh.vertices.foreach_set('co',unique.ravel())
        mesh.loops.add(len(flat));mesh.loops.foreach_set('vertex_index',indices.astype('i4'))
        mesh.polygons.add(len(local));mesh.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4'))
        mesh.polygons.foreach_set('loop_total',np.full(len(local),3,dtype='i4'));mesh.update()
        ob=cm.bpy.data.objects.new(name,mesh);cm.bpy.context.collection.objects.link(ob);ob.location=origin
        mesh.materials.append(cm.M[part['material']]);mesh.uv_layers.new().data.foreach_set('uv',uv.ravel())
        cm.bpy.context.view_layer.update();matrix=np.asarray(ob.matrix_world,dtype='f8')
        world=wide@matrix[:3,:3].T+matrix[:3,3];error=float(np.linalg.norm(world-vertices,axis=2).max())
        if error>.001:raise ValueError('Actual frame exceeds position budget')
        records.append({'mesh':name,'sourcePart':part['id'],'triangles':len(vertices),'maxVertexErrorGame':error,'matrixENU':matrix.tolist()})
        expected[str(index)+'_local']=local;expected[str(index)+'_uv']=uv;objects.append(ob)
    asset=cm.export('xianfu-underpass',objects)
    if asset['triangles']!=sum(r['triangles'] for r in records):raise ValueError('Exporter changed triangle count')
    np.savez_compressed(out/'serialized-source.npz',**expected)
    report={'schemaVersion':1,'cityId':'hangzhou','kind':'actual source-bound underpass structure candidate',
            'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [source,ROOT/spec['geometryFile'],Path(model.__file__),Path(__file__)]},
            'assets':[{**asset,'sha256':sha(out/asset['file'])}],'meshContracts':records,
            'serializedSourceSha256':sha(out/'serialized-source.npz'),
            'orientation':'original Blender ENU -> glTF Y-up -> Babylon root handling; no second scale',
            'pending':['independent actual GLB geometry/UV/closed-parts and NullEngine verification',
                       'soil closure and source road deck ownership integration','real browser actor/visual/performance checks']}
    (out/'asset-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
