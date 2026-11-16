"""Export an isolated, source-owned cut terrain candidate in factory Blender.

The local crop remains open at its original world/shore boundaries. It must
replace that domain in the base terrain before activation; never overlay it.
"""
import argparse,json,math,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
    source=(ROOT/a.input).resolve();out=(ROOT/a.output).resolve();contract_path=source/'candidate-contract.json';contract=json.loads(contract_path.read_text())
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh artifact candidate required')
    if contract['cityId']!='hangzhou' or contract['units']!='game east/north/up; scale applied once' or not contract['cpuChecksPassed']:raise ValueError('Invalid prepared contract')
    mesh_path=ROOT/contract['mesh'];provenance_path=source/'top-provenance.json'
    if sha(mesh_path)!=contract['meshSha256'] or sha(ROOT/contract['inputRoot']/'geography/site-surfaces.json')!=contract['inputSitesSha256']:raise ValueError('Prepared source drift')
    if contract.get('physicsSitesFile'):
        if sha(ROOT/contract['physicsSitesFile'])!=contract['physicsSitesSha256']:raise ValueError('Repaired physical site source drift')
    import numpy as np
    import city_mesh as cm
    with np.load(mesh_path) as arrays:top=arrays['top'];walls=arrays['walls']
    provenance=json.loads(provenance_path.read_text());assert len(provenance)==len(top)
    if any(p['material'] not in ('land','park') for p in provenance):raise ValueError('Unsupported source terrain material')
    source_faces=np.concatenate([top,walls]);origin=np.asarray(contract['float32SimulatedLocalOrigin'],dtype='f4').astype('f8');chosen=None
    for degree in range(360):
        angle=degree*math.pi/180;basis=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
        local=((source_faces-origin)@basis).astype('f4');wide=local.astype('f8');normal=np.cross(wide[:,1]-wide[:,0],wide[:,2]-wide[:,0])
        if np.all(np.linalg.norm(normal,axis=1)>0) and np.all(normal[:len(top),2]>0):chosen=(angle,local);break
    if chosen is None:raise ValueError('No single local frame preserves prepared topology')
    angle,local=chosen;out.mkdir(parents=True);cm.O=out;objects=[];records=[]
    for material in ['land','park']:
        ids=[i for i,p in enumerate(provenance) if p['material']==material]
        if material=='land':ids+=list(range(len(top),len(source_faces)))
        if not ids:continue
        v=local[ids];flat=v.reshape(-1,3);unique,indices=np.unique(flat,axis=0,return_inverse=True)
        name='terrain_balcony_local_'+material;mesh=cm.bpy.data.meshes.new(name)
        mesh.vertices.add(len(unique));mesh.vertices.foreach_set('co',unique.ravel());mesh.loops.add(len(flat));mesh.loops.foreach_set('vertex_index',indices.astype('i4'))
        mesh.polygons.add(len(v));mesh.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4'));mesh.polygons.foreach_set('loop_total',np.full(len(v),3,dtype='i4'));mesh.update()
        ob=cm.bpy.data.objects.new(name,mesh);cm.bpy.context.collection.objects.link(ob);mesh.materials.append(cm.M[material]);ob.location=origin;ob.rotation_euler[2]=angle
        # Use original world-projected terrain UVs. Vertical faces project on
        # their dominant wall plane so a cliff does not get a collapsed UV.
        uv=[]
        for index in ids:
            t=source_faces[index];axes=[0,1]
            if index>=len(top):
                n=np.cross(t[1]-t[0],t[2]-t[0]);axes=[1,2] if abs(n[0])>=abs(n[1]) else [0,2]
            # Integer-period translation preserves repeat texture phase and
            # density while avoiding world-sized float32 UV cancellation.
            uv.extend(t[:,axes]/8-np.floor(origin[axes]/8))
        mesh.uv_layers.new().data.foreach_set('uv',np.asarray(uv,dtype='f4').ravel());cm.bpy.context.view_layer.update()
        matrix=np.asarray(ob.matrix_world,dtype='f8');world=v.astype('f8')@matrix[:3,:3].T+matrix[:3,3];error=float(np.linalg.norm(world-source_faces[ids],axis=2).max())
        if error>.001:raise ValueError('Serialized local frame exceeds previous position budget')
        objects.append(ob);records.append({'mesh':name,'material':material,'sourceIndices':ids,'triangles':len(ids),'actualMatrixENU':matrix.tolist(),'maxVertexErrorGame':error})
    asset=cm.export('city-balcony-terrain',[*objects])
    if asset['triangles']!=len(source_faces):raise ValueError('Exporter changed prepared topology')
    report={'schemaVersion':1,'cityId':'hangzhou','kind':'actual local cut-terrain candidate GLB','sourceContract':str(contract_path.relative_to(ROOT)),'sourceContractSha256':sha(contract_path),'sourceMeshSha256':sha(mesh_path),'sourceProvenanceSha256':sha(provenance_path),'exporterSha256':sha(Path(__file__)),'assets':[{**asset,'sha256':sha(out/asset['file'])}],'frame':{'originENU':origin.tolist(),'angleRadians':angle},'uv':{'periodGame':8,'integerPeriodOriginENU':np.floor(origin/8).tolist(),'use':'repeating land/park projection only; lawn shader uses world position'},'topTriangles':len(top),'verticalTriangles':len(walls),'meshContracts':records,'pending':contract['pending']+['independent actual GLB topology/UV/NullEngine verification','crop must replace source base geometry; do not overlay','browser visual/day-night/performance']}
    (out/'asset-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='meshContracts'},indent=2))
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
