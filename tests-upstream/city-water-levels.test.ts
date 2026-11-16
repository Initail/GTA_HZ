import test from 'node:test';
import assert from 'node:assert/strict';
import {NullEngine,Scene,MirrorTexture,MeshBuilder,VertexBuffer} from '@babylonjs/core';
import {CityWaterLevels,type WaterBodyLevel} from '../src/city-water-levels.ts';
import {createBayWater} from '../src/city-bay-water.ts';
import type {V2} from '../src/city-types.ts';
const ring=(a:number,b:number,c:number,d:number):V2[]=>[[a,b],[c,b],[c,d],[a,d],[a,b]];
const bodies:WaterBodyLevel[]=[{id:'lake',height:4.5,rings:[ring(-50,-50,50,50),ring(-10,-10,10,10)]},{id:'river',height:.9,rings:[ring(150,-50,250,50)]}];
test('lake, island holes and river retain separate source planes',()=>{
 const levels=new CityWaterLevels(bodies);assert.deepEqual(levels.nearest(30,0),{id:'lake',height:4.5,distance:0});
 assert.equal(levels.nearest(0,0)?.distance,10);assert.deepEqual(levels.nearest(200,0),{id:'river',height:.9,distance:0});
 assert.throws(()=>new CityWaterLevels([{height:NaN,rings:[ring(0,0,1,1)]}]),/Invalid water/);
});
test('semantic lotus regions do not add a plane and a partitioned river leaves the lock independent',()=>{
 const levels=new CityWaterLevels([
  {id:'lotus',height:5.4,rings:[ring(0,0,10,10)],renderSurface:false},
  {id:'lake',height:4.5,rings:[ring(-20,-20,20,20)]},
  {id:'river',height:6.3,rings:[ring(100,0,200,20)],renderRings:[[ring(100,0,140,20)],[ring(160,0,200,20)]]},
  {id:'lock',height:5.6,rings:[ring(140,0,160,20)]},
 ]);
 assert.equal(levels.nearest(5,5)?.id,'lake');
 assert.equal(levels.nearest(150,10)?.id,'lock');
 assert.equal(levels.nearest(180,10)?.id,'river');
});
test('Hangzhou keeps mesh elevations and reuses the reflection target across planes',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),mirror=new MirrorTexture('water-reflection',128,scene,true);mirror.refreshRate=3;
 const lake=MeshBuilder.CreateGround('terrain_water',{width:100,height:100},scene);lake.position.y=4.5;lake.computeWorldMatrix(true);
 const original=lake.getVerticesData(VertexBuffer.PositionKind)!.slice(),targets=scene.textures.filter(t=>t.isRenderTarget).length;
 const bay=createBayWater(scene,mirror,[lake],{schemaVersion:1,waterHeight:.9,crossings:[],parkLights:[],shoreDistance:{url:'',extent:[-50,-50,250,50],maxDistance:120}},{flattenWater:false,extendHorizon:false,waterBodies:bodies});
 try{
  const material=bay.material;bay.update(1,30,0);assert.equal(mirror.mirrorPlane.d,4.5);bay.setMode('night');bay.update(2,200,0);assert.equal(mirror.mirrorPlane.d,.9);
  assert.equal(bay.material,material);assert.equal(mirror.refreshRate,3);assert.equal(scene.textures.filter(t=>t.isRenderTarget).length,targets);
  assert.equal(scene.getMeshByName('bay-horizon-water'),null);assert.equal(lake.position.y,4.5);assert.deepEqual(lake.getVerticesData(VertexBuffer.PositionKind),original);
 }finally{scene.dispose();engine.dispose();}
});
