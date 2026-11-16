import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {terrainHeight,loadLandmarkDetails,mergeDetailCollisions,type DetailCollisionFootprint} from '../src/landmark-details.ts';
import type {CityData} from '../src/city-types.ts';
import {CityCollision,inRing} from '../src/driving.ts';

test('terrain north direction and world offset agree with exported SW-NE triangles',()=>{
 const grid={x0:100,z0:200,dx:10,dz:20,columns:2,rows:2,heights:[0,10,20,40]};
 assert.equal(terrainHeight(grid,100,200),0);
 assert.equal(terrainHeight(grid,110,200),10);
 assert.equal(terrainHeight(grid,100,220),20);
 assert.equal(terrainHeight(grid,110,220),40);
 // Plane interpolation gives 20 at diagonal midpoint, rather than bilinear 17.5.
 assert.equal(terrainHeight(grid,105,210),20);
 assert.equal(terrainHeight(grid,107.5,205),15);
 assert.equal(terrainHeight(grid,102.5,215),20);
 assert.equal(terrainHeight(grid,99.9,210),0);
 assert.equal(terrainHeight(grid,105,221),0);
});

test('reapplying detail colliders is idempotent and keeps distinct deck heights',()=>{
 const rings:DetailCollisionFootprint['rings']=[[[0,0],[2,0],[2,2],[0,2]]];
 const data={buildings:[{id:'old',rings,height:4,style:'ordinary'},{id:'other',rings,height:3,style:'ordinary'}]} as unknown as CityData;
 const solids=[{id:'lower',rings,minY:0,maxY:1},{id:'upper',rings,minY:8,maxY:9}];
 mergeDetailCollisions(data,['old'],solids);
 const once=structuredClone(data.buildings);
 mergeDetailCollisions(data,['old'],solids);
 assert.deepEqual(data.buildings,once);assert.equal(data.buildings.length,3);
 assert.deepEqual(data.buildings.filter(b=>b.style==='landmark-detail').map(b=>[b.minY,b.maxY]),[[0,1],[8,9]]);
 assert.throws(()=>mergeDetailCollisions(data,[],[solids[0],solids[0]]));
 assert.throws(()=>mergeDetailCollisions(data,[],[{...solids[0],maxY:-1}]));
 assert.deepEqual(data.buildings,once,'invalid manifest must not partially remove collisions');
});
test('an object can retire obsolete collider IDs without retaining its previous envelope or deleting unrelated buildings',()=>{
 const rings:DetailCollisionFootprint['rings']=[[[0,0],[2,0],[2,2],[0,2]]];
 const data={buildings:[{id:'city-balcony:0',rings,height:4,style:'landmark-detail'},
  {id:'other:0',rings,height:4,style:'landmark-detail'},{id:'ordinary',rings,height:8,style:'ordinary'}]} as unknown as CityData;
 const solids=[{id:'city-balcony:body:column',rings,minY:1,maxY:5}];
 mergeDetailCollisions(data,[],solids,['city-balcony:0','ordinary']);
 assert.deepEqual(data.buildings.map(b=>(b as typeof b&{id:string}).id),['other:0','ordinary','city-balcony:body:column']);
 const once=structuredClone(data.buildings);mergeDetailCollisions(data,[],solids,['city-balcony:0']);
 assert.deepEqual(data.buildings,once);
 assert.throws(()=>mergeDetailCollisions(data,[],[],['city-balcony:0','city-balcony:0']));
 assert.deepEqual(data.buildings,once);
});

test('Hangzhou detail layer reuses the hash-bound city terrain and rejects a mismatched floor source before merging',async t=>{
 const makeData=()=>({meta:{cityId:'hangzhou',counts:{}},buildings:[],landmarks:[]} as unknown as CityData);
 const hash='b'.repeat(64),heightAt=(x:number,z:number)=>37+x*.03-z*.01;
 let terrain:unknown={kind:'city-geography',cityId:'hangzhou',manifestSha256:hash};
 const requested:string[]=[];
 t.mock.method(globalThis,'fetch',async (url:string)=>{
  requested.push(url);assert.ok(url.endsWith('landmark-detail.json'),'No synthetic local DEM fetch');
  return new Response(JSON.stringify({schemaVersion:1,asset:'/cities/hangzhou/landmark-detail.glb',landmarks:[],baseBuildingIds:[],collisionFootprints:[],terrain}));
 });
 const data=makeData(),shared={cityId:'hangzhou' as const,manifestSha256:hash,heightAt};
 const loaded=await loadLandmarkDetails(data,shared);
 assert.ok(loaded);assert.equal(loaded.terrain,null);assert.equal(loaded.heightAt,heightAt);assert.equal(loaded.heightAt(100,50),39.5);assert.equal(requested.length,1);
 const unchanged=makeData();
 await assert.rejects(loadLandmarkDetails(unchanged,{...shared,manifestSha256:'c'.repeat(64)}),/绑定不一致/);
 assert.deepEqual(unchanged,makeData());
 await assert.rejects(loadLandmarkDetails(makeData()),/绑定不一致/);
 terrain={url:'/city/terrain-detail.json'};
 await assert.rejects(loadLandmarkDetails(makeData(),shared),/明确的城市高程来源/);
});

test('live detail merge replaces old collisions, blocks real footprints and leaves arrivals drivable',async t=>{
 const json=async (path:string)=>JSON.parse(await readFile(new URL('../public'+path,import.meta.url),'utf8'));
 const data=await json('/city/city.json');
 t.mock.method(globalThis,'fetch',async (path:string)=>new Response(JSON.stringify(await json(path)),{headers:{'content-type':'application/json'}}));
 const loaded=await loadLandmarkDetails(data);
 assert.ok(loaded);
 const collision=new CityCollision(data);
 for(const oldId of loaded.manifest.baseBuildingIds)assert.ok(!data.buildings.some((b:{id:string})=>b.id===oldId),'Old footprint remains: '+oldId);
 for(const mark of loaded.manifest.landmarks){
  assert.equal(collision.blocked(...mark.arrival),false,'Arrival blocked: '+mark.id);
  const live=data.landmarks.find((m:{id:string})=>m.id===mark.id);
  assert.ok(live?.detailCollision||live?.height===0,'Old circular exclusion remains: '+mark.id);
 }
 for(const f of loaded.manifest.collisionFootprints){
  const ring=f.rings[0],xs=ring.map(p=>p[0]),zs=ring.map(p=>p[1]);let checked=0;
  for(let x=Math.min(...xs)+2;x<Math.max(...xs);x+=2)for(let z=Math.min(...zs)+2;z<Math.max(...zs);z+=2){
   if(!inRing(x,z,ring)||f.rings.slice(1).some(hole=>inRing(x,z,hole)))continue;
   const road=collision.nearest(x,z);if(road&&road.d<road.road.width/2-.65)continue;
   assert.equal(collision.blocked(x,z),true,'Unblocked building interior: '+f.id);checked++;
  }
  assert.ok(checked>0,'No interior collision samples: '+f.id);
 }
});
