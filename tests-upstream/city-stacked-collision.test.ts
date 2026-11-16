import test from 'node:test';
import assert from 'node:assert/strict';
import {CityCollision} from '../src/driving.ts';
import type {CityData,Road} from '../src/city-types.ts';
import {tankFootprintClear} from '../src/city-tank-simulation.ts';

const ring=(a:number,b:number,c:number,d:number):[number,number][]=>[[a,b],[c,b],[c,d],[a,d],[a,b]];
function data(roads:Road[]=[]):CityData{return {meta:{counts:{},extent:[-20,-20,20,20],horizontalScale:.6},land:[[ring(-20,-20,20,20)]],coast:[],roads,buildings:[],green:[],water:[],landmarks:[],spawn:{x:0,z:0,yaw:0,road:'test'}};}
const road=(id:string,points:[number,number][],height:number):Road=>({id,name:id,kind:'primary',width:6,oneway:false,points,heights:points.map(()=>height),grade:height>0?'1':'0'});

test('Hangzhou collision retains all effective water parts and holes while honoring source-only records',()=>{
 const c=data();c.meta.cityId='hangzhou';
 c.water=[{name:'source-only',rings:[ring(-19,-19,19,19)],renderSurface:false},
  {name:'split',rings:[ring(-18,-18,18,18)],renderRings:[[ring(-18,-18,-5,18)],[ring(5,-18,18,18),ring(8,-3,12,3)]]}];
 const collision=new CityCollision(c);
 assert.equal(collision.blocked(0,0,0),false);
 assert.equal(collision.blocked(-10,0,0),true);assert.equal(collision.blocked(6,0,0),true);
 assert.equal(collision.blocked(10,0,0),false);assert.equal(collision.blocked(30,0,0),true);
 c.meta.cityId='shenzhen';assert.equal(new CityCollision(c).blocked(0,0,0),true);
});

test('collision road selection follows each caller height at an unconnected crossing',()=>{
 const c=data([road('ground',[[-15,0],[15,0]],0),road('upper',[[0,-15],[0,15]],8)]),collision=new CityCollision(c);
 assert.equal(collision.nearest(0,0,0)?.road.id,'ground');
 assert.equal(collision.nearest(0,0,8)?.road.id,'upper');
 assert.equal(collision.nearest(0,0,0)?.road.id,'ground');
});
test('an upper road over water only supports an actor at its deck level',()=>{
 const c=data([road('bridge',[[-15,0],[15,0]],8)]);c.water=[{name:'river',rings:[ring(-20,-20,20,20)]}];
 const collision=new CityCollision(c);
 assert.equal(collision.blocked(0,0,8),false);assert.equal(collision.blocked(0,0,0),true);
 assert.equal(collision.blocked(0,0),false); // Original two-dimensional contract.
});
test('road collision and recovery use the source-owned physical floor instead of stale node elevations',()=>{
 const c=data([road('approach',[[-15,0],[15,0]],12),road('upper',[[0,-15],[0,15]],8)]);
 c.water=[{name:'river',rings:[ring(-20,-20,20,20)]}];
 const collision=new CityCollision(c,(id,x,z,raw)=>id==='approach'?2+x*.1:raw);
 assert.equal(collision.nearest(0,0,2)?.road.id,'approach');
 assert.equal(collision.nearest(0,0,2)?.height,2);
 assert.equal(collision.nearest(0,0,8)?.road.id,'upper');
 assert.equal(collision.blocked(5,0,2.5),false);
 assert.equal(collision.blocked(5,0,12),true,'raw source elevation is no longer a support plane');
 assert.equal(new CityCollision(c).blocked(5,0,12),false,'omitting the adapter preserves the existing contract');
});
test('solid piers and glazed strips leave other floor levels accessible',()=>{
 const c=data();c.buildings=[{rings:[ring(-4,-4,4,4)],style:'landmark-detail',height:4,minY:2,maxY:6}];
 const collision=new CityCollision(c);
 assert.equal(collision.blocked(0,0,0,1.6),false);
 assert.equal(collision.blocked(0,0,1,1.6),true);
 assert.equal(collision.blocked(0,0,6),false);
 assert.equal(collision.blocked(0,0),true);
});
test('the original tank footprint remains clear under an elevated arch but rejects ground piers and low headroom',()=>{
 const c=data();c.buildings=[{rings:[ring(-8,-8,8,8)],style:'landmark-detail',height:12,minY:10,maxY:22}];
 const high=new CityCollision(c);
 assert.equal(tankFootprintClear(0,0,0,(x,z)=>high.blocked(x,z)),false);
 assert.equal(tankFootprintClear(0,0,0,(x,z)=>high.blocked(x,z,4)),true);
 assert.equal(tankFootprintClear(0,0,0,(x,z)=>high.blocked(x,z,9)),false);
 c.buildings.push({rings:[ring(-1,1,1,2)],style:'landmark-detail',height:18,minY:4,maxY:22});
 const pier=new CityCollision(c);
 assert.equal(tankFootprintClear(0,0,0,(x,z)=>pier.blocked(x,z,4)),false);
});
test('invalid provided physical heights cannot silently become a flat surface',()=>{
 const c=data([road('broken',[[0,0],[10,0]],0)]);c.roads[0].heights=[0];assert.throws(()=>new CityCollision(c),/Invalid road/);
 c.roads=[];c.buildings=[{rings:[ring(-4,-4,4,4)],style:'detail',height:4,minY:6,maxY:2}];assert.throws(()=>new CityCollision(c),/Invalid building/);
});
test('explicit structural barriers retain height clearance even on a road or supported public floor',()=>{
 const c=data([road('street',[[-15,0],[15,0]],0)]);
 c.buildings=[{rings:[ring(-1,-1,1,1)],style:'landmark-detail',height:3,minY:0,maxY:3}];
 assert.equal(new CityCollision(c).blocked(0,0,0),false,'legacy road exemption remains');
 c.buildings[0].blocksRoad=true;const barrier=new CityCollision(c);
 assert.equal(barrier.blocked(0,0,0),true);assert.equal(barrier.blocked(0,0,0,1.6,true),true);
 assert.equal(barrier.blocked(0,0,3),false);assert.equal(barrier.blocked(5,0,0),false);
 c.buildings[0].minY=5;c.buildings[0].maxY=8;
 assert.equal(new CityCollision(c).blocked(0,0,0),false,'upper ceiling stays clear of a ground actor');
});
