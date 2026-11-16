"""Export closed foundation candidates using local float32 mesh coordinates.

Run in a factory-startup Blender process. No scale or axis rebaking is applied.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from hangzhou_surface import digest

def triangle_hash(triangles):
    # GLB local coordinates, cyclic order preserved (normal direction matters).
    keys = []
    for t in triangles:
        pts = [tuple(float(x) if x else 0.0 for x in p) for p in t]
        ordered = min(tuple(pts[i:]+pts[:i]) for i in range(3))
        keys.append(b''.join(__import__('struct').pack('<fff', *p) for p in ordered).hex())
    return hashlib.sha256('\n'.join(sorted(keys)).encode()).hexdigest()

def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); args=ap.parse_args(argv)
    source=(ROOT/args.input).resolve(); output=(ROOT/args.output).resolve()
    if ROOT/'artifacts' not in output.parents or output.exists(): raise ValueError('Fresh isolated output required')
    manifest=json.loads((source/'manifest.json').read_text())
    if manifest['kind']!='landmark-foundation-and-collision-candidate': raise ValueError('Wrong source')
    for p,sha in manifest['inputs'].items():
        if digest(ROOT/p)!=sha: raise ValueError('Changed source '+p)
    import numpy as np
    import city_mesh as cm
    output.mkdir(parents=True); cm.O=output; records=[]; objects=[]
    for record in manifest['objects']:
        if digest(source/record['file'])!=record['sha256']: raise ValueError('Changed foundation')
        delivery=json.loads((ROOT/record['sourceDelivery']).read_text())
        if digest(ROOT/delivery['artifact'])!=delivery['artifactSha256']: raise ValueError('Changed placed model')
        with np.load(source/record['file']) as arrays:
            triangles=arrays['concrete']
        origin=np.array([math.floor(triangles[:,:,0].min()/640)*640, math.floor(triangles[:,:,1].min()/640)*640,0.])
        local=(triangles-origin).astype('<f4')
        cross=np.cross(local[:,1].astype('f8')-local[:,0],local[:,2].astype('f8')-local[:,0])
        if np.any(np.linalg.norm(cross,axis=1)==0): raise ValueError('Local float32 collapsed a foundation face')
        flat=local.reshape(-1,3); unique,indices=np.unique(flat,axis=0,return_inverse=True)
        name='hangzhou_foundation_'+record['id']+'_concrete'
        data=cm.bpy.data.meshes.new(name); data.vertices.add(len(unique)); data.vertices.foreach_set('co',unique.ravel())
        data.loops.add(len(flat)); data.loops.foreach_set('vertex_index',indices.astype('i4'))
        data.polygons.add(len(local)); data.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4')); data.polygons.foreach_set('loop_total',np.full(len(local),3,dtype='i4')); data.update()
        ob=cm.bpy.data.objects.new(name,data); cm.bpy.context.collection.objects.link(ob); ob.location=origin; data.materials.append(cm.M['concrete']); objects.append(ob)
        uv=data.uv_layers.new(); uv.data.foreach_set('uv',(triangles.reshape(-1,3)[:,:2]/8).astype('f4').ravel())
        gltf=local[:,:,[0,2,1]].copy(); gltf[:,:,2]*=-1
        records.append({'id':record['id'],'mesh':name,'triangles':len(local),'originENU':origin.tolist(),'maxSerializationErrorGame':float(np.abs(local.astype('f8')+origin-triangles).max()),'localGltfTrianglesSha256':triangle_hash(gltf)})
    before=sum(len(o.data.polygons) for o in objects)
    asset=cm.export('landmark-foundations',objects)
    if asset['triangles']!=before: raise ValueError('Blender export changed foundation triangle count')
    report={'cityId':'hangzhou','kind':'actual-foundation-GLB-candidate','sourceManifest':str((source/'manifest.json').relative_to(ROOT)),'sourceManifestSha256':digest(source/'manifest.json'),'exporterSha256':digest(Path(__file__)),'assets':[{**asset,'sha256':digest(output/asset['file'])}],'objects':records,'pending':['actual exported geometry parity','collision and entrance integration','browser visual and performance']}
    (output/'asset-manifest.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__': main(sys.argv[sys.argv.index('--')+1:])
