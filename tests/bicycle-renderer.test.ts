import {test} from 'node:test';import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';
import {Scene} from '@babylonjs/core/scene.js';
import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {VertexData} from '@babylonjs/core/Meshes/mesh.vertexData.js';
import {CityEbikes} from '../src/city-ebikes.ts';
test('actual served GLB contains bicycle and seated rider prototypes',()=>{
 const path=new URL('../public/cities/hangzhou/ebikes/ebikes.glb',import.meta.url);
 const bytes=readFileSync(path);assert.equal(bytes.readUInt32LE(0),0x46546c67);
 const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const names=json.nodes.map((n:any)=>n.name??'');
 for(const role of ['ebike-bicycle_','ebike-rider_'])assert(names.some((name:string)=>name.startsWith(role)),role);
});
test('player uses one existing instanced bicycle and rider; dismount removes only rider',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),bikes=new CityEbikes(scene,()=>0,0);
 try{
  const proto=(name:string)=>{const mesh=new Mesh(name,scene),v=new VertexData();v.positions=[0,0,0,1,0,0,0,1,0];v.indices=[0,1,2];v.applyToMesh(mesh);return mesh;};
  const bicycle=proto('bicycle'),rider=proto('rider');
  // Inject the two loaded prototypes, without a network request or GPU context.
  const loaded=bikes as any;loaded.proto.set('bicycle',[bicycle]);loaded.proto.set('rider',[rider]);loaded.palette=[[.2,.4,.6]];loaded.riderPalette=[[.5,.4,.3]];loaded.helmetPalette=[[.8,.8,.8]];
  assert.equal(bikes.playerBicycleReady,true);const meshes=scene.meshes.length,materials=scene.materials.length;
  bikes.playerBicycle={x:14,z:23,yaw:.6,height:8,active:true};bikes.update(0,14,23,false,true);
  assert.equal(bicycle.thinInstanceCount,1);assert.equal(rider.thinInstanceCount,1);
  const transform=bicycle.thinInstanceGetWorldMatrices()[0];assert(Math.abs(transform.m[12]-14)<1e-6);assert(Math.abs(transform.m[13]-8.01)<1e-5);assert(Math.abs(transform.m[14]-23)<1e-6);
  bikes.playerBicycle.active=false;bikes.update(0,14,23,false,true);
  assert(bicycle.isEnabled());assert.equal(rider.isEnabled(),false);assert.equal(scene.meshes.length,meshes);assert.equal(scene.materials.length,materials);
  bikes.playerBicycle=null;bikes.update(0,14,23,false,true);assert.equal(bicycle.isEnabled(),false);
 }finally{scene.dispose();engine.dispose();}
});
