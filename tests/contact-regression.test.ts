import test from 'node:test';
import assert from 'node:assert/strict';
import {CpuWorld as DrivingWorld} from './cpu-world.ts';
const make=(other={x:0,z:5.8,yaw:0,speed:0,height:0})=>{
 const impacts:number[]=[],received:any[]=[];const world=Object.create(DrivingWorld.prototype);
 Object.assign(world,{time:1,nextVehicleImpact:0,vehicleImpactPulse:0,geography:null,carRoadHint:undefined,tank:null,groundHeight:()=>0,carSurfaceHeight:()=>0,actorCollision:()=>false,propBlocked:()=>false,
  traffic:{cars:[other],surfaceHeight:(c:any)=>c.height,applyImpact:(...args:any[])=>received.push(args)},
  audio:{impact:(s:number)=>impacts.push(s)},state:{x:0,z:1,yaw:0,speed:20,steer:0,distance:1}});
 return {world,impacts,received,before:{x:0,z:0,yaw:0,speed:20,steer:0,distance:0}};
};
test('actual world resolution stops at touching bumpers instead of penetrating the NPC body',()=>{
 const {world,before}=make();world.resolveVehicleMotion(before,.05);
 assert.ok(world.state.z<=.8+1e-6,`body overlap: player z=${world.state.z}, NPC rear=3.3`);
 assert.ok(world.state.speed<20,'contact dissipates forward speed');
});
test('side-by-side traffic with a positive body gap does not create a circular invisible wall',()=>{
 const {world,before}=make({x:2.6,z:1,yaw:0,speed:20,height:0});world.resolveVehicleMotion(before,.05);
 assert.equal(world.state.z,1);assert.equal(world.state.speed,20);
});
test('vehicle contact produces an audio event and a response in the struck NPC',()=>{
 const {world,before,impacts,received}=make({x:0,z:5.5,yaw:0,speed:0,height:0});world.resolveVehicleMotion(before,.05);
 assert.ok(impacts.length>0,'vehicle contact should reach the existing impact audio bus');
 assert.ok(received.length>0,'struck NPC must react rather than keep its previous motion');
});
test('traffic on another bridge level never creates a contact',()=>{
 const {world,before,impacts}=make({x:0,z:3,yaw:0,speed:0,height:8});world.geography={};world.resolveVehicleMotion(before,.05);
 assert.equal(world.state.z,1);assert.deepEqual(impacts,[]);
});

test('walking does not collide with an upper-level parked car but does stop at a same-level NPC',()=>{
 const {world}=make({x:5,z:0,yaw:0,speed:0,height:0});world.state={x:0,z:0,yaw:0};world.walkingSurfaceHeight=()=>0;world.carSurfaceHeight=()=>8;
 assert.equal(world.parkedVehicleBlocks(0,0),false);assert.equal(world.parkedVehicleBlocks(5,0),true);
 world.traffic.cars[0].height=8;assert.equal(world.parkedVehicleBlocks(5,0),false);
});
test('holding against the same contact does not trigger audio every frame',()=>{
 const {world,before,impacts}=make({x:0,z:5.5,yaw:0,speed:0,height:0});
 for(let i=0;i<5;i++){world.state={...before,z:1,distance:1};world.time=1+i*.02;world.resolveVehicleMotion(before,.05);}
 assert.equal(impacts.length,1);assert.ok(world.vehicleImpactPulse>0);
});
