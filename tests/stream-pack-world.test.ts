import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';
import {Scene} from '@babylonjs/core/scene.js';
import {MeshBuilder} from '@babylonjs/core/Meshes/meshBuilder.js';
import {AssetContainer} from '@babylonjs/core/assetContainer.js';
import {PBRMaterial} from '@babylonjs/core/Materials/PBR/pbrMaterial.js';
import {CityBaseMaterialCache} from '../src/city-stream-ownership.ts';

// Execute the actual world methods without constructing its full UI, vehicle,
// texture and post-processing graph. NullEngine checks are not GPU acceptance.
const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8');
const start=source.indexOf(' private attachBaseTile('),end=source.indexOf(' private prepareBaseFrame()',start);
assert(start>=0&&end>start);
const World=new Function('PBRMaterial','GROUND_AMBIENT_MATERIALS',stripTypeScriptTypes('class Harness { '+source.slice(start,end)+' }')+';return Harness;')(PBRMaterial,new Set(['land','park','pavement','concrete','asphalt','roadline']));
function fixture(){
 const engine=new NullEngine(),scene=new Scene(engine),world=new World(),container=new AssetContainer(scene);
 const roles=['terrain','roads','buildings'] as const,names=['terrain_water_-1_-2_water','roads_-1_-2_asphalt','block_-1_-2_concrete'];
 const meshes=names.map((name,i)=>{const mesh=MeshBuilder.CreateBox(name,{size:1},scene),material=new PBRMaterial(['water','asphalt','concrete'][i],scene);(material as any)._internalMetadata={gltf:{pointers:['/materials/'+i]}};mesh.material=material;mesh.computeWorldMatrix(true);return mesh;});
 container.meshes=meshes;container.materials=meshes.map(m=>m.material as PBRMaterial);
 const calls:{architecture:string[];facade:string[];ambient:string[];water:any[]}={architecture:[],facade:[],ambient:[],water:[]};
 const renderLists=Array.from({length:4},()=>[...meshes]);
 Object.assign(world,{scene,baseMeshes:{terrain:[],roads:[],buildings:[]},blocks:[],baseMaterialCache:new CityBaseMaterialCache(scene),headlights:[{excludedMeshes:[]}],ambient:{attach:(m:PBRMaterial)=>calls.ambient.push(m.name)},architecture:{applyMeshes:(_:unknown,role:string)=>calls.architecture.push(role)},facadeDiversity:{applyMeshes:(_:unknown,role:string)=>calls.facade.push(role)},landscapeSurfaces:{attach:()=>{}},bayWater:{attachMeshes:(m:unknown[])=>calls.water.push(...m),detachMeshes:(m:unknown[])=>{calls.water=calls.water.filter(x=>!m.includes(x));}},shadows:{getShadowMap:()=>({renderList:renderLists[0]})},mirror:{renderList:renderLists[1]},waterMirror:{renderList:renderLists[2]}});
 Object.defineProperty(scene,'geometryBufferRenderer',{configurable:true,value:{renderList:renderLists[3]}});
 const pack={members:roles.map(role=>({id:role+':-1,-2',quality:'near'}))};
 const metadata={nodes:names.map((name,i)=>({name,member:pack.members[i].id,role:roles[i],quality:'near'})),materialOrigins:roles.map((role,i)=>({role,index:0,record:{name:['water','asphalt','concrete'][i]}}))};
 const close=()=>{Object.defineProperty(scene,'geometryBufferRenderer',{value:null});container.dispose();scene.dispose();engine.dispose();};
 return {world,container,meshes,pack,metadata,calls,renderLists,close};
}
test('actual pack world hook routes all original layers and detaches every live render reference',()=>{
 const f=fixture();try{
  const release=f.world.attachBasePack(f.pack,f.container,[{},{},{}],f.metadata);
  assert.deepEqual(f.calls.architecture,['terrain','roads','buildings']);assert.deepEqual(f.calls.facade,['terrain','roads','buildings']);
  assert.deepEqual(f.calls.ambient,['asphalt']);assert.deepEqual(f.calls.water,[f.meshes[0]]);assert.deepEqual(f.world.headlights[0].excludedMeshes,[f.meshes[0]]);
  assert.equal(f.world.blocks.length,3);assert.equal(f.world.blocks[0].water,true);assert.equal(f.world.blocks[1].road,true);assert.equal(f.world.blocks[1].x,-320);assert.equal(f.world.blocks[1].z,-960);
  for(const [i,role] of ['terrain','roads','buildings'].entries())assert.deepEqual(f.world.baseMeshes[role],[f.meshes[i]]);
  release();release();assert.equal(f.world.blocks.length,0);assert.deepEqual(f.calls.water,[]);assert.deepEqual(f.world.headlights[0].excludedMeshes,[]);assert(f.renderLists.every(list=>list.length===0));assert(Object.values(f.world.baseMeshes).every((a:any)=>a.length===0));
 }finally{f.close();}
});
test('a later malformed road rolls back already attached water even before mirrors exist',()=>{
 const f=fixture();try{
  f.meshes[1].name='bad-road-identity';f.metadata.nodes[1].name=f.meshes[1].name;
  f.world.mirror=undefined;f.world.waterMirror=undefined;f.world.shadows=undefined;
  assert.throws(()=>f.world.attachBasePack(f.pack,f.container,[{},{},{}],f.metadata),/original block identity/);
  assert.equal(f.world.blocks.length,0);assert.deepEqual(f.world.baseMeshes.terrain,[]);assert.deepEqual(f.calls.water,[]);assert.deepEqual(f.world.headlights[0].excludedMeshes,[]);
 }finally{f.close();}
});
test('a surface controller failure cannot retain partially attached water',()=>{
 const f=fixture();try{
  f.world.bayWater.attachMeshes=(meshes:unknown[])=>{f.calls.water.push(...meshes);throw Error('water fixture failure');};
  assert.throws(()=>f.world.attachBasePack(f.pack,f.container,[{},{},{}],f.metadata),/water fixture failure/);
  assert.equal(f.world.blocks.length,0);assert.deepEqual(f.calls.water,[]);assert.deepEqual(f.world.baseMeshes.terrain,[]);
 }finally{f.close();}
});
test('missing pack bindings are rejected before registering any world layer or material',()=>{
 const f=fixture();try{
  f.metadata.nodes.pop();assert.throws(()=>f.world.attachBasePack(f.pack,f.container,[{},{},{}],f.metadata),/bindings incomplete/);
  assert.equal(f.world.baseMaterialCache.stats.materials,0);assert.deepEqual(f.calls.architecture,[]);assert.equal(f.world.blocks.length,0);
 }finally{f.close();}
});
test('duplicate actual mesh names cannot substitute for a missing member',()=>{
 const f=fixture();try{
  f.meshes[1].name=f.meshes[0].name;
  assert.throws(()=>f.world.attachBasePack(f.pack,f.container,[{},{},{}],f.metadata),/bindings incomplete/);
  assert.equal(f.world.baseMaterialCache.stats.materials,0);assert.deepEqual(f.calls.architecture,[]);
 }finally{f.close();}
});
