"""Export baked Hangzhou surfaces with the original GLB axis/material pipeline.

Run in a separate factory-startup Blender process. Public and live scenes are
untouched. This exports base terrain/roads/buildings, not landmark acceptance.
"""
from __future__ import annotations
import argparse,json,math,sys,time
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from hangzhou_surface import digest,Surface
def main(argv):
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--city-root',required=True);p.add_argument('--output',required=True);p.add_argument('--frames',required=True);a=p.parse_args(argv)
    source,city_root,output=map(lambda p:(ROOT/p).resolve(),[a.input,a.city_root,a.output]);manifest=json.loads((source/'manifest.json').read_text());began=time.monotonic()
    if ROOT/'artifacts' not in output.parents or (output.exists() and any(output.iterdir())):raise ValueError('Fresh candidate required')
    frame_path=(ROOT/a.frames).resolve();frame_report=json.loads(frame_path.read_text())
    if frame_report['sourceManifestSha256']!=digest(source/'manifest.json') or frame_report['summary']['cpuPassedMeshes']!=frame_report['summary']['affectedMeshes']:raise ValueError('Frame audit does not bind source')
    patches={r['mesh']:r for r in frame_report['rows']};used_patches=[];mesh_contracts=[]
    if manifest['cityId']!='hangzhou' or manifest['units']!='game metres; never scale again':raise ValueError('Wrong frame or units')
    for name,sha in manifest['inputs'].items():
        if digest(ROOT/name)!=sha:raise ValueError('Changed prepared source '+name)
    if digest(source/manifest['buildingsFile'])!=manifest['buildingsSha256']:raise ValueError('Changed buildings')
    import numpy as np
    import city_mesh as cm
    output.mkdir(parents=True,exist_ok=True);cm.O=output;assets=[]
    def remove(obs):
        for ob in obs:
            mesh=ob.data;cm.bpy.data.objects.remove(ob,do_unlink=True)
            if mesh.users==0:cm.bpy.data.meshes.remove(mesh)
    def mesh(name,material,vertices,origin,angle=0):
        # Exact coordinate deduplication, no decimation or geographic snapping.
        # Bulk arrays avoid millions of temporary Python vertex/face lists.
        basis=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]],dtype='f8')
        local=((vertices-origin)@basis).astype('f4');flat=local.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
        crosses=np.cross(local[:,1].astype('f8')-local[:,0],local[:,2].astype('f8')-local[:,0])
        if np.any(np.linalg.norm(crosses,axis=1)==0):raise ValueError('Zero-area exported source face '+name+' '+material)
        if material in ('land','park','water','asphalt','pavement','roadline') and np.any(crosses[:,2]<=0):raise ValueError('Nonpositive local source face '+name+' '+material)
        data=cm.bpy.data.meshes.new(name+'_'+material);data.vertices.add(len(unique));data.vertices.foreach_set('co',unique.ravel())
        data.loops.add(len(flat));data.loops.foreach_set('vertex_index',indices.astype(np.int32))
        data.polygons.add(len(vertices));data.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype=np.int32));data.polygons.foreach_set('loop_total',np.full(len(vertices),3,dtype=np.int32))
        data.update();ob=cm.bpy.data.objects.new(name+'_'+material,data);cm.bpy.context.collection.objects.link(ob);data.materials.append(cm.M[material]);ob.location=origin;ob.rotation_euler[2]=angle;uv=data.uv_layers.new();period=14 if material=='asphalt' else 8;uv.data.foreach_set('uv',(vertices.reshape(-1,3)[:,:2]/period).astype(np.float32).ravel())
        actual_matrix=np.array(ob.matrix_basis,dtype='f8');cm.bpy.context.view_layer.update();actual_matrix=np.array(ob.matrix_world,dtype='f8');world=local.astype('f8')@actual_matrix[:3,:3].T+actual_matrix[:3,3];error=float(np.linalg.norm(world-vertices,axis=2).max())
        if error>.001:raise ValueError('Local frame serialization exceeds .001 game '+name)
        mesh_contracts.append({'name':ob.name,'triangles':len(vertices),'originENU':list(map(float,ob.location)),'angleRadians':float(ob.rotation_euler[2]),'worldMaxVertexErrorGame':error,'localFloat32ZeroArea':0,'positiveHorizontalSurface':material!='concrete'})
        return ob
    field=Surface(city_root)
    for asset in ['terrain','roads']:
        obs=[]
        for record in manifest['meshRecords']:
            if not record['name'].startswith(asset+'_'):continue
            path=source/record['file']
            if digest(path)!=record['sha256']:raise ValueError('Changed mesh data')
            with np.load(path) as arrays:
                for material in arrays.files:
                    vertices=arrays[material];name=record['name'];xy=name.rsplit('_',2)[-2:];origin=np.array([int(xy[0])*640,int(xy[1])*640,0.]);patch=patches.get(name+'_'+material)
                    if patch:
                        if patch['sourceSha256']!=record['sha256']:raise ValueError('Frame source changed')
                        pp=frame_path.parent/patch['candidatePath']
                        if digest(pp)!=patch['candidateSha256']:raise ValueError('Frame proposal changed')
                        with np.load(pp) as plan:ids=plan['sourceIndices'];expected=plan['localTriangles']
                        chosen=patch['chosen'];po=np.array(chosen['originENU']);pa=chosen['angleRadians'];basis=np.array([[math.cos(pa),-math.sin(pa),0],[math.sin(pa),math.cos(pa),0],[0,0,1]])
                        if not np.array_equal(((vertices[ids]-po)@basis).astype('f4'),expected):raise ValueError('Frame does not preserve original triangles')
                        obs.append(mesh(name+'_patch',material,vertices[ids],po,pa));mask=np.ones(len(vertices),dtype=bool);mask[ids]=False;vertices=vertices[mask];used_patches.append(name+'_'+material)
                    if len(vertices):obs.append(mesh(name,material,vertices,origin))
        if asset=='roads':
            # Retain original game-unit lamp dimensions and eight-sided poles.
            # Only the source positions/estimated ground ordinate change.
            chunks={}
            for x,z,nx,nz in json.loads((city_root/'lamps.json').read_text()):
                y=field.ground(x,z);b=chunks.setdefault((math.floor(x/640),math.floor(z/640)),cm.B());b.tube('steel',(x,z,y+.1),(x,z,y+8),.075,8);b.tube('steel',(x,z,y+8),(x-nx*1.5,z-nz*1.5,y+8.3),.055,8);b.box('lamp',(x-nx*1.5,z-nz*1.5,y+8.27),(1,.38,.1))
            for key,b in chunks.items():obs.extend(b.finish('roads_'+str(key[0])+'_'+str(key[1])+'_fixtures'))
            del chunks
        before=sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in obs);result=cm.export(asset,obs)
        if result['triangles']!=before:raise ValueError('Blender changed prepared triangle count '+asset)
        assets.append({**result,'sha256':digest(output/result['file'])});remove(obs);del obs
        print('exported',asset,result['triangles'],flush=True)
    buildings=json.loads((source/manifest['buildingsFile']).read_text());chunks={}
    for building in buildings:
        shape=building['rings'][0];key=(math.floor(sum(p[0] for p in shape)/len(shape)/640),math.floor(sum(p[1] for p in shape)/len(shape)/640));b=chunks.setdefault(key,cm.B());roof=building['maxY']
        for index,(ring,bottoms) in enumerate(zip(building['rings'],building['wallBottomHeights'])):
            pairs=list(zip(ring,bottoms))
            if ring[0]==ring[-1]:pairs=pairs[:-1]
            signed=sum(p[0][0]*q[0][1]-q[0][0]*p[0][1] for p,q in zip(pairs,pairs[1:]+pairs[:1]))
            if (index==0 and signed<0) or (index>0 and signed>0):pairs=list(reversed(pairs))
            for ((x,z),y),((xx,zz),yy) in zip(pairs,pairs[1:]+pairs[:1]):
                width=math.hypot(xx-x,zz-z);b.face(building['style'],[(x,z,y),(xx,zz,yy),(xx,zz,roof),(x,z,roof)],[(0,0),(width/24,0),(width/24,(roof-yy)/24),(0,(roof-y)/24)])
        for tri in building['roofTriangles']:
            a,bp,c=tri
            if (bp[0]-a[0])*(c[1]-a[1])-(bp[1]-a[1])*(c[0]-a[0])<0:tri=list(reversed(tri))
            b.face('roof',[(x,z,roof) for x,z in tri])
    obs=[]
    for key,b in chunks.items():obs.extend(b.finish('block_'+str(key[0])+'_'+str(key[1])))
    del chunks;result=cm.export('buildings',obs);assets.append({**result,'sha256':digest(output/result['file'])});remove(obs)
    if set(used_patches)!=set(patches):raise ValueError('Unused frame patches')
    report={'frameAudit':str(frame_path.relative_to(ROOT)),'frameAuditSha256':digest(frame_path),'patches':used_patches,'meshContracts':mesh_contracts,'schemaVersion':1,'cityId':'hangzhou','kind':'actual-nonflat-base-glb-export','assets':assets,'sourceManifest':str((source/'manifest.json').relative_to(ROOT)),'sourceManifestSha256':digest(source/'manifest.json'),'sourceLampSha256':digest(city_root/'lamps.json'),'exporterSha256':digest(Path(__file__)),'elapsedSeconds':time.monotonic()-began,'status':'exported base only; not playable or visually accepted','orientation':'Blender east/north/up -> GLB Y-up; original Babylon root identity retained','pending':manifest['pending']+['source-aware ordinary roof/collision integration','all regional runtime layers and gameplay','current three-view/night/browser/performance']}
    (output/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
