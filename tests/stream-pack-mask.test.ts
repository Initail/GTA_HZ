import {test} from 'node:test';import assert from 'node:assert/strict';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';import {Scene} from '@babylonjs/core/scene.js';import {AssetContainer} from '@babylonjs/core/assetContainer.js';import {Mesh} from '@babylonjs/core/Meshes/mesh.js';import {VertexData} from '@babylonjs/core/Meshes/mesh.vertexData.js';
import {createPackMemberMask} from '../src/city-stream-pack-mask.ts';
function fixture(){const engine=new NullEngine(),scene=new Scene(engine),container=new AssetContainer(scene),root=new Mesh('__root__',scene);root.scaling.z=-1;container.meshes.push(root);
 for(const name of ['terrain_a','roads_a','buildings_b']){const mesh=new Mesh(name,scene),v=new VertexData();v.positions=[0,0,0,1,0,0,0,1,0];v.indices=[0,1,2];v.applyToMesh(mesh);mesh.position.set(3,4,5);mesh.parent=root;mesh.freezeWorldMatrix();container.meshes.push(mesh);}
 const bindings=[{name:'terrain_a',member:'terrain:a'},{name:'roads_a',member:'roads:a'},{name:'buildings_b',member:'buildings:b'}];return {engine,scene,container,root,bindings};}
test('per-member parents preserve actual matrices and cannot be re-enabled by ordinary per-mesh culling',()=>{
 const f=fixture();try{const before=f.container.meshes.map(m=>Array.from(m.getWorldMatrix().m)),mask=createPackMemberMask(f.container,f.bindings);assert.equal(mask.memberCount,3);mask.selectMembers(['roads:a']);
  for(const mesh of f.container.meshes)mesh.setEnabled(true); // Existing cull legitimately re-enables meshes.
  assert.equal(f.container.meshes[1].isEnabled(),false);assert.equal(f.container.meshes[2].isEnabled(),true);assert.equal(f.container.meshes[3].isEnabled(),false);
  assert.deepEqual(f.container.meshes.map(m=>Array.from(m.getWorldMatrix().m)),before);mask.selectMembers(['terrain:a','buildings:b']);assert.equal(f.container.meshes[2].isEnabled(),false);assert.equal(f.container.meshes[3].isEnabled(),true);
  f.container.dispose();assert.equal(f.scene.meshes.length,0);assert.equal(f.scene.transformNodes.length,0);
 }finally{f.scene.dispose();f.engine.dispose();}
});
test('missing/ambiguous bindings fail before allocating parents and unknown visibility cannot partially switch',()=>{
 const f=fixture();try{assert.throws(()=>createPackMemberMask(f.container,f.bindings.slice(1)),/coverage/);assert.equal(f.container.transformNodes.length,0);
  const mask=createPackMemberMask(f.container,f.bindings);mask.selectMembers(['roads:a']);assert.throws(()=>mask.selectMembers(['terrain:a','unknown']),/Unknown/);assert.equal(f.container.meshes[2].isEnabled(),true);assert.equal(f.container.meshes[1].isEnabled(),false);
 }finally{f.scene.dispose();f.engine.dispose();}
});
test('duplicate loaded names are rejected before creating any member parent',()=>{
 const f=fixture();try{
  f.container.meshes[2].name=f.container.meshes[1].name;
  assert.throws(()=>createPackMemberMask(f.container,f.bindings),/identity changed/);assert.equal(f.container.transformNodes.length,0);
  assert(f.container.meshes.slice(1).every(m=>m.parent===f.root));
 }finally{f.scene.dispose();f.engine.dispose();}
});
