import test from 'node:test';import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CitySiteSurfaces,type SiteSurface,type SiteSurfaceData} from '../src/city-site-surfaces.ts';
import {CityCollision} from '../src/driving.ts';
import {CityWalk} from '../src/city-walk.ts';
import type {CityData} from '../src/city-types.ts';
const floor=(id:string,y:number):SiteSurface=>({id,triangles:[[[0,0,y],[10,0,y],[0,10,y]]]});
const data=(terrainCuts:SiteSurface[]=[],walkFloors:SiteSurface[]=[]):SiteSurfaceData=>({cityId:'hangzhou',units:'game east/north/up; scale applied once',terrainCuts,walkFloors});
test('a source deck contact tolerates arithmetic roundoff but still blocks tiny real penetrations',()=>{
 const s=data();s.solidSlabs=[{...floor('deck',66.89129083879237),thicknessGame:.45}];const sites=new CitySiteSurfaces(s),top=66.89129083879237;
 assert.equal(sites.blocked(2,2,top-2.85e-14),false);
 assert.equal(sites.blocked(2,2,top-1e-8),true);
 assert.equal(sites.blocked(2,2,top-.45-1.6+2.85e-14),false);
 assert.equal(sites.blocked(2,2,top-.45-1.6+1e-8),true);
});
test('real thin TIN boundary faces use finite edge contact without extending their height planes',()=>{
 const fixture=JSON.parse(readFileSync(new URL('./fixtures/xianfu-thin-floor-boundaries.json',import.meta.url),'utf8'));
 const s=data();s.terrainPatches=[{id:'xianfu',triangles:fixture.triangles}];
 s.roadSurfaces=[{id:'xianfu',roadIds:['source-road'],triangles:fixture.triangles}];
 const sites=new CitySiteSurfaces(s);
 for(const [x,z,y] of fixture.queries){
  assert.ok(Math.abs(sites.groundAt(x,z,80)-y)<.0001);
  assert.ok(Math.abs(sites.roadAt('source-road',x,z)!-y)<.0001);
 }
});
test('bounded site cuts only lower their explicit triangle, including a shared edge',()=>{
 const sites=new CitySiteSurfaces(data([floor('site-cut',1.5)]));
 assert.equal(sites.groundAt(2,2,5),1.5);assert.equal(sites.groundAt(5,5,5),1.5);
 assert.equal(sites.groundAt(8,8,5),5);assert.equal(sites.groundAt(2,2,1),1);
});
test('two public levels preserve actor height without switching vertically at the same XY',()=>{
 const sites=new CitySiteSurfaces(data([],[floor('lower',2),floor('upper',5.6)]));
 assert.deepEqual(sites.walkAt(2,2,1.6,2),{id:'lower',height:2});
 assert.deepEqual(sites.walkAt(2,2,1.6,5.6),{id:'upper',height:5.6});
 assert.deepEqual(sites.walkAt(2,2,1.6,1.6),{id:'lower',height:2});
 assert.deepEqual(sites.walkAt(2,2,0,0),{id:null,height:0});
 assert.deepEqual(sites.walkAt(8,8,1.6,5.6),{id:null,height:1.6},'existing CityWalk step check rejects walking off the upper edge');
});
test('source deck identity prevents stationary or moving updates from climbing close stacked floors',()=>{
 const sites=new CitySiteSurfaces(data([],[floor('lower',2),floor('middle',2.4),floor('upper',2.8)]));
 assert.equal(sites.walkAt(2,2,2).id,'lower');
 let hint:{id:string|null;height:number}={id:'lower',height:2};
 for(let i=0;i<100;i++){
  hint=sites.walkAt(2+i*.01,2,1.6,hint);assert.equal(hint.id,'lower');assert.equal(hint.height,2);
 }
 const folded=floor('folded',2);folded.triangles.push(...floor('folded',2.4).triangles);
 assert.equal(new CitySiteSurfaces(data([],[folded])).walkAt(2,2,1.6,{id:'folded',height:2}).height,2);
});
test('a source approach plane interpolates its full width and does not create support outside its footprint',()=>{
 const ramp:SiteSurface={id:'approach',triangles:[[[0,0,5],[10,0,5.2],[0,4,5]],[[10,0,5.2],[10,4,5.2],[0,4,5]]]};
 const sites=new CitySiteSurfaces(data([],[ramp]));
 for(const z of [0,1,2,3,4])assert(Math.abs(sites.walkAt(5,z,4.7,5.1).height-5.1)<1e-12);
 assert.equal(sites.walkAt(5,4.01,4.7,5.1).id,null);
});
test('site data rejects inverted, degenerate, repeated and nonfinite surfaces',()=>{
 const f=floor('a',1);assert.throws(()=>new CitySiteSurfaces(data([],[f,f])));
 assert.throws(()=>new CitySiteSurfaces(data([],[{id:'bad',triangles:[[[0,0,1],[0,10,1],[10,0,1]]]}])));
 assert.throws(()=>new CitySiteSurfaces(data([],[floor('nan',NaN)])));
 assert.throws(()=>new CitySiteSurfaces(data([],[{id:'flat',triangles:[[[0,0,1],[1,0,1],[2,0,1]]]}])));
});
test('source road and earthwork consumers use one TIN while solid slabs retain space below them',()=>{
 const patch=floor('low-passage',2),d=data();d.terrainPatches=[patch];d.roadSurfaces=[{...patch,roadIds:['approach','tunnel']}];d.solidSlabs=[{...floor('upper-slab',8),thicknessGame:.4}];
 const sites=new CitySiteSurfaces(d);
 assert.equal(sites.groundAt(2,2,3),2);assert.equal(sites.groundAt(2,2,1),2,'explicit earthwork patches can include bounded fill');
 assert.equal(sites.roadAt('approach',2,2),2);assert.equal(sites.roadAt('tunnel',2,2),2);assert.equal(sites.roadAt('unrelated',2,2),undefined);
 assert.equal(sites.roadAt('approach',8,8),undefined);
 assert.equal(sites.blocked(2,2,2),false);assert.equal(sites.blocked(2,2,6.5),true);assert.equal(sites.blocked(2,2,8),false);
 const overlap=data();overlap.terrainPatches=[patch,floor('wrong',3)];assert.throws(()=>new CitySiteSurfaces(overlap).groundAt(2,2,0),/disagree/);
});
test('a real step boundary belongs to the upper face without adding a ramp or a gap',()=>{
 const low=floor('deck',2);low.openEdges=[[false,true,false]];
 low.triangles.push([[10,0,2.04],[10,10,2.04],[0,10,2.04]]);low.openEdges.push([false,false,false]);
 const sites=new CitySiteSurfaces(data([],[low]));
 assert.equal(sites.walkAt(5,5,1.6,{id:'deck',height:2}).height,2.04);
 assert.equal(sites.walkAt(4.999,5,1.6,{id:'deck',height:2}).height,2);
 assert.equal(sites.walkAt(5.001,5,1.6,{id:'deck',height:2}).height,2.04);
});
test('original walking stops at the floor edge over water and still collides with structural piers',()=>{
 const sites=new CitySiteSurfaces(data([],[floor('public-floor',5)]));let previous=5;
 const ring:[number,number][]=[[-20,-20],[20,-20],[20,20],[-20,20],[-20,-20]];
 const city:CityData={meta:{cityId:'hangzhou',counts:{},extent:[-20,-20,20,20],horizontalScale:.6},land:[[ring]],coast:[],roads:[],buildings:[],green:[],water:[{rings:[ring],name:'river'}],landmarks:[],spawn:{x:2,z:2,yaw:0,road:'none'}};
 const collision=new CityCollision(city),sample=(x:number,z:number)=>sites.walkAt(x,z,0,previous);
 const walk=new CityWalk((x,z)=>{const p=sample(x,z);return collision.blocked(x,z,p.height,1.6,p.id!==null);},(x,z)=>sample(x,z).height);
 walk.active=true;walk.x=2;walk.z=2;
 assert(walk.clear(2,2));assert(!walk.clear(8,8));
 for(let i=0;i<200;i++){walk.step(new Set(['KeyW','ShiftLeft']),.05);previous=walk.eye.y-1.53-(walk.moving?Math.sin(walk.distance*7)*.008:0);}
 assert(walk.z<8);assert(Math.abs(previous-5)<1e-10);
 city.buildings=[{rings:[[[1,1],[3,1],[3,3],[1,3],[1,1]]],style:'landmark-detail',height:4,minY:5,maxY:9}];
 assert.equal(new CityCollision(city).blocked(2,2,5,1.6,true),true,'floor support must not bypass a wall or pier');
});
