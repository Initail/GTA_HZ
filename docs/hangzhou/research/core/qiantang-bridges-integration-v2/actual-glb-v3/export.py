"""Actual isolated three-bridge GLB render probe. No Skill acceptance promotion."""
from pathlib import Path
import json,hashlib,sys
P=Path(__file__).resolve().parent;SOURCE=P.parent;ROOT=SOURCE.parents[4];sys.path.insert(0,str(ROOT/'scripts'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((SOURCE/'package-manifest.json').read_text())
for rel,h in manifest['files'].items():
 if sha(ROOT/rel)!=h:raise ValueError('Frozen input drift '+rel)
if (P/'coastal-bridges.glb').exists():raise ValueError('Preserve actual candidate; choose new version')
import numpy as np
import city_mesh as cm
src=np.load(SOURCE/'candidate-mesh.npz');tri=src['trianglesENU'];uv=src['uvs'];materials=src['materials'];parts=json.loads((SOURCE/'validation-model.json').read_text())['report']['bridges'];objects=[];records=[];actual=[];uvflip=[];start=0
for part in parts:
 count=part['triangles'];ids0=np.arange(start,start+count);origin=np.floor(tri[ids0].mean((0,1)))
 for mat in sorted(set(materials[ids0])):
  ids=ids0[materials[ids0]==mat];local=(tri[ids]-origin).astype('f4');flat=local.reshape(-1,3);vertices=flat;indices=np.arange(len(flat),dtype='i4');name='coastal_'+part['id']+'_'+mat
  mesh=cm.bpy.data.meshes.new(name);mesh.vertices.add(len(vertices));mesh.vertices.foreach_set('co',vertices.ravel());mesh.loops.add(len(flat));mesh.loops.foreach_set('vertex_index',indices.astype('i4'));mesh.polygons.add(len(ids));mesh.polygons.foreach_set('loop_start',np.arange(0,len(flat),3,dtype='i4'));mesh.polygons.foreach_set('loop_total',np.full(len(ids),3,dtype='i4'));mesh.update()
  layer=mesh.uv_layers.new();layer.data.foreach_set('uv',uv[ids].astype('f4').ravel());mesh.materials.append(cm.M[str(mat)]);ob=cm.bpy.data.objects.new(name,mesh);cm.bpy.context.collection.objects.link(ob);ob.location=origin;objects.append(ob);cm.bpy.context.view_layer.update();matrix=np.array(ob.matrix_world);world=local.astype('f8')@matrix[:3,:3].T+matrix[:3,3]
  area=np.linalg.norm(np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0]),axis=1);flipped=uv[ids].astype('f4');flipped[:,:,1]=1.-flipped[:,:,1];u=flipped.astype('f8');uvarea=(u[:,1,0]-u[:,0,0])*(u[:,2,1]-u[:,0,1])-(u[:,1,1]-u[:,0,1])*(u[:,2,0]-u[:,0,0]);err=float(np.max(np.linalg.norm(world-tri[ids],axis=2)))
  if np.any(area==0) or np.any(uvarea==0) or err>.001:raise ValueError({'name':name,'zeroGeometry':int(sum(area==0)),'zeroUVAfterVflip':int(sum(uvarea==0)),'maxError':err})
  records.append({'name':name,'bridgeId':part['id'],'material':str(mat),'sourceTriangleIds':ids.tolist(),'originENU':origin.tolist(),'actualMatrixENU':matrix.tolist(),'triangles':len(ids),'maxSourceErrorGame':err,'zeroGeometry':0,'zeroUVAfterVflip':0});actual.append(world);uvflip.append(flipped)
 start+=count
assert start==len(tri)
cm.O=P;export=cm.export('coastal-bridges',objects)
assert export['triangles']==len(tri),'Exporter changed frozen source triangle count'
report={'kind':'actual isolated bridge render probe with unresolved actor/support blockers','sourceFrozenManifestSha256':sha(SOURCE/'package-manifest.json'),'sourceModuleSha256':manifest['sourceModuleSha256'],'specSha256':manifest['specSha256'],'candidateMeshSha256':sha(SOURCE/'candidate-mesh.npz'),'exporterSha256':sha(Path(__file__)),'sharedMaterialExporterSha256':sha(ROOT/'scripts/city_mesh.py'),'export':export,'artifactSha256':sha(P/'coastal-bridges.glb'),'parts':records,'coordinateContract':'local integer ENU origin, f32 local vertices, glTF Y-up; original Babylon root identity correction','pending':['independent GLB directed triangles and UV','actual Babylon root/mesh ray path','all actor/support blockers in frozen source package','browser day/night/performance/actual driving']};(P/'model-delivery.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['export','artifactSha256','sourceModuleSha256','specSha256']}))
