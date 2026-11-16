"""Isolated Blender export of prepared source shoreline solids, no city rebuild."""
from pathlib import Path
import argparse,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import digest
from build_hangzhou_foundations import triangle_hash
def main(argv):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--ownership',required=True);args=ap.parse_args(argv)
    source=(ROOT/args.input).resolve();out=(ROOT/args.output).resolve();manifest=json.loads((source/'manifest.json').read_text())
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    if manifest['kind']!='four-source-shore-contact-candidate' or manifest['cityId']!='hangzhou':raise ValueError('Wrong prepared source')
    for p,sha in manifest['inputs'].items():
        if digest(ROOT/p)!=sha:raise ValueError('Changed prepared shore '+p)
    ownership_path=ROOT/args.ownership;ownership=json.loads(ownership_path.read_text())
    for dep in ownership['maskFiles']:
        if digest(Path(dep['path']))!=dep['sha256']:raise ValueError('Changed ownership mask')
    model=ROOT/'artifacts/cities/hangzhou/landmarks/city-balcony-floor-v2/city-balcony.glb'
    if digest(model)!=ownership['actualBalconyArtifactSha256']:raise ValueError('Changed balcony model')
    import numpy as np
    import city_mesh as cm
    import bmesh
    def cutter(name,ring,low,high,origin):
        ring=[tuple(p[:2]) for p in ring]
        if ring[0]==ring[-1]:ring.pop()
        signed=sum(ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))
        if signed<0:ring.reverse()
        n=len(ring);verts=[(x-origin[0],z-origin[1],y-origin[2]) for y in [low,high] for x,z in ring]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        mesh=cm.bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
        ob=cm.bpy.data.objects.new(name,mesh);cm.bpy.context.collection.objects.link(ob);ob.location=origin;return ob
    def subtract(ob,tool):
        cm.bpy.context.view_layer.objects.active=ob;ob.select_set(True)
        mod=ob.modifiers.new('source-owned-shore-cut','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
        cm.bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh=tool.data;cm.bpy.data.objects.remove(tool,do_unlink=True);cm.bpy.data.meshes.remove(mesh)
        ob.select_set(False)
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
        if record['id']==ownership['shoreSourceId']:
            high=float(triangles[:,:,2].max()+10)
            subtract(ob,cutter('balcony-upper-volume',ownership['clipEnvelopeGame']['coordinates'][0],ownership['capTopYGame'],high,origin))
            path=next(Path(d['path']) for d in ownership['maskFiles'] if d['path'].endswith('pillar34-subtraction.geojson'))
            masks=json.loads(path.read_text())
            mask=next(f for f in masks['features'] if f['id']=='pillar-34-subtract')
            subtract(ob,cutter('balcony-source-pier',mask['geometry']['coordinates'][0],ownership['originalShoreBottomYGame']-1,high,origin))
            data=ob.data;bm=bmesh.new();bm.from_mesh(data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
            local=np.array([[data.vertices[i].co[:] for i in p.vertices] for p in data.polygons],dtype='<f4')
            triangles=local.astype('f8')+origin
            if np.any(np.linalg.norm(np.cross(local[:,1].astype('f8')-local[:,0],local[:,2].astype('f8')-local[:,0]),axis=1)==0):raise ValueError('Boolean collapsed shore face')
        uv=[]
        for t in triangles:
            normal=np.cross(t[1]-t[0],t[2]-t[0]);axis=int(np.argmax(np.abs(normal)));axes=([1,2],[0,2],[0,1])[axis]
            uv.extend(t[:,axes]/8)
        data.uv_layers.new().data.foreach_set('uv',np.asarray(uv,dtype='f4').ravel())
        gltf=local[:,:,[0,2,1]].copy();gltf[:,:,2]*=-1
        records.append({'id':record['id'],'mesh':name,'triangles':len(local),'originENU':origin.tolist(),'maxSerializationErrorGame':float(np.abs(local.astype('f8')+origin-triangles).max()),'localGltfTrianglesSha256':triangle_hash(gltf)})
    before=sum(len(o.data.polygons) for o in objects);asset=cm.export('coastal-shoreline',objects)
    if asset['triangles']!=before:raise ValueError('Blender changed shore triangles')
    result={'cityId':'hangzhou','kind':'actual-four-source-shore-contact-GLB','sourceManifest':str((source/'manifest.json').relative_to(ROOT)),'sourceManifestSha256':digest(source/'manifest.json'),'exporterSha256':digest(Path(__file__)),'ownershipContractSha256':digest(ownership_path),'ownershipContract':str(ownership_path.relative_to(ROOT)),'triangleHasherSha256':digest(ROOT/'scripts/build_hangzhou_foundations.py'),'assets':[{**asset,'sha256':digest(out/asset['file'])}],'objects':records,'pending':manifest['pending']+['city balcony dry terrain cut remains separate; unchanged terrain still intersects lower space']}
    (out/'asset-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
