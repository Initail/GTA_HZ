import test from 'node:test';import assert from 'node:assert/strict';
import {CAR_BODY,vehicleContact,sweepVehicleContact,vehicleImpulse,vehicleBlocksPoint} from '../src/city-vehicle-contact.ts';
const body=(x=0,z=0,yaw=0,groundY=0)=>({x,z,yaw,groundY,...CAR_BODY});
test('front, side and rotated contact are symmetric; height intervals stay independent',()=>{
 for(let i=0;i<80;i++){const yaw=i*Math.PI/40,a=body(0,0,yaw),b=body(Math.sin(yaw)*4.9,Math.cos(yaw)*4.9,yaw);
  assert.ok(vehicleContact(a,b));assert.ok(vehicleContact(b,a));assert.equal(vehicleContact(a,{...b,groundY:2}),null);
  const separated={...b,x:Math.cos(yaw)*2.1,z:-Math.sin(yaw)*2.1};assert.equal(vehicleContact(a,separated),null);
 }
});
test('the swept body catches maximum-speed forward and reverse contact at 20 and 60 Hz',()=>{
 for(const dt of [.05,1/60])for(const direction of [-1,1]){
  const distance=53*dt,other=body(0,direction*(5+distance*.5));
  const hit=sweepVehicleContact(body(),body(0,direction*distance),other);assert.ok(hit);assert.ok(Math.abs(hit.fraction-.5)<.0001);
 }
});
test('an already touching car can reverse out without being pinned or receiving another impact',()=>{
 assert.equal(sweepVehicleContact(body(),body(0,-.5),body(0,4.9)),null);
});
test('rotation catches a corner contact even without centre translation',()=>{
 const hit=sweepVehicleContact(body(),body(0,0,Math.PI/2),body(3.4,0));assert.ok(hit);assert.ok(hit.fraction>0&&hit.fraction<1);
});
test('equal-mass impulses conserve momentum, dissipate energy and ignore separation',()=>{
 for(const speed of [1,5,15,53]){
  const q=vehicleImpulse({x:0,z:1},{x:3,z:speed},{x:0,z:0});
  assert.ok(Math.abs(q.a.z+q.b.z-speed)<1e-10);assert.ok(q.a.z*q.a.z+q.b.z*q.b.z<=speed*speed);assert.equal(q.a.x,3);
 }
 const q=vehicleImpulse({x:0,z:1},{x:0,z:-3},{x:0,z:0});assert.equal(q.closing,0);assert.equal(q.a.z,-3);
});
test('walking clearance checks the parked car height and keeps the existing human footprint separate',()=>{
 assert.equal(vehicleBlocksPoint(body(),0,0,0),true);assert.equal(vehicleBlocksPoint(body(0,0,0,8),0,0,0),false);
 assert.equal(vehicleBlocksPoint(body(),0,0,1.45),false);assert.equal(vehicleBlocksPoint(body(),1.1,0,0),false);
});
test('a car touching another side can slide forward without an invisible brake',()=>{
 assert.equal(sweepVehicleContact(body(),body(0,1),body(2.06,0)),null);
});
