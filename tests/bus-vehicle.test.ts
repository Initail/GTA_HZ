import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {busEnvelope,busBoardingPoint,busWalkerClear,busLocalToWorld,prepareBusPassengerCamera,busPassengerCameraPose,busSolidDistance,type BusFrame,type BusModelGeometry} from '../src/city-bus-vehicle.ts';
const model:BusModelGeometry=JSON.parse(readFileSync(new URL('./fixtures/bus/generated-bus-mesh-v4.json',import.meta.url),'utf8'));
const flat:BusFrame={origin:[10,5,20],right:[1,0,0],up:[0,1,0],forward:[0,0,1]};
test('actual generated bus envelope contains mirrors and uses one .60 geographic scale',()=>{
 const b=busEnvelope(model);assert.ok(b.halfWidth>2.55*.6/2);assert.ok(b.frontExtent>=8.545*.6/2&&b.frontExtent<2.6);assert.ok(b.frontExtent!==5.1);
 for(const s of model.solids){assert.ok(Math.abs(s.center[0])+s.size[0]/2<=b.halfWidth+1e-9);assert.ok(s.center[2]+s.size[2]/2<=b.frontExtent+1e-9);}
});
test('boarding anchor protects the unchanged .23g walker capsule and rejects missing/wrong floor',()=>{
 const p=busBoardingPoint(model,flat,()=>5)!;assert.ok(p);assert.ok(p.x-.23>10+busEnvelope(model).halfWidth);
 assert.equal(busBoardingPoint(model,flat,()=>null),null);assert.equal(busBoardingPoint(model,flat,()=>6),null);
 assert.equal(busBoardingPoint(model,flat,()=>5,'missing-door'),null);
 const front=model.doors.find(d=>d.id==='front')!;assert.equal(p.z,20+front.localGroundPortal[2]);
});
test('actual seated camera clears every physical interior solid, including near-plane corners',()=>{
 const camera=prepareBusPassengerCamera(model);assert.ok(camera.clearance>camera.radius+.005);assert.equal(camera.standingAvatarVisible,false);
 for(const s of model.solids)assert.ok(busSolidDistance(camera.eye,s)>camera.radius+.005,s.name);
 for(const aspect of [.4,1,16/9,2.5,4,10])for(const yaw of [-10,0,10])for(const pitch of [-10,0,10]){
  const view=busPassengerCameraPose(camera,flat,yaw,pitch,aspect),r=view.near*Math.sqrt(1+Math.tan(view.fov/2)**2*(1+aspect**2));
  assert.ok(r<=camera.radius+1e-9);assert.deepEqual(view.eye,busLocalToWorld(flat,camera.eye));assert.deepEqual(view.up,[0,1,0]);
 }
});
test('supported pitch and roll rotate seat eye and direction together',()=>{
 const a=.2,c=Math.cos(a),s=Math.sin(a),frame:BusFrame={origin:[10,5,20],right:[1,0,0],up:[0,c,-s],forward:[0,s,c]};
 const camera=prepareBusPassengerCamera(model),view=busPassengerCameraPose(camera,frame);
 assert.deepEqual(view.eye,busLocalToWorld(frame,camera.eye));assert.ok(Math.abs(view.target[1]-view.eye[1]-s)<1e-10);
});
test('camera refuses blocked seat, nonfinite view and model dimensions missing mirrors',()=>{
 const changed=structuredClone(model),eye=prepareBusPassengerCamera(model).eye;
 changed.solids.push({name:'regression-obstruction',motion:'static',shape:'box',center:eye,size:[.02,.02,.02]});
 assert.throws(()=>prepareBusPassengerCamera(changed));assert.throws(()=>busPassengerCameraPose(prepareBusPassengerCamera(model),flat,0,0,NaN));
 const narrow=structuredClone(model);narrow.runtimeBody.halfWidth=.1;assert.throws(()=>busEnvelope(narrow));
});

test('a roll into the player cannot accept a flat-width-only boarding point',()=>{
 const angle=-.35,c=Math.cos(angle),s=Math.sin(angle),frame:BusFrame={origin:[0,5,0],right:[c,s,0],up:[-s,c,0],forward:[0,0,1]};
 const z=model.doors.find(d=>d.id==='front')!.localGroundPortal[2];
 assert.equal(busWalkerClear(model,frame,{x:.95,z,height:5,yaw:0}),false);
 assert.equal(busWalkerClear(model,flat,{x:30,z:20,height:5,yaw:0}),true);
});

test('invalid or reflected support frames are rejected before camera or boarding changes',()=>{
 const camera=prepareBusPassengerCamera(model);
 for(const right of [[2,0,0],[-1,0,0],[NaN,0,0]] as [number,number,number][]){
  const frame={...flat,right};assert.throws(()=>busPassengerCameraPose(camera,frame));assert.throws(()=>busBoardingPoint(model,frame,()=>5));
 }
 assert.equal(busWalkerClear(model,flat,{x:NaN,z:0,height:5,yaw:0}),false);
});

test('diagonal stops retain a safe boarding anchor for the same full player body',()=>{
 for(const yaw of [-.7228359610279572,Math.PI/4,Math.PI/3,-Math.PI/4]){
  const c=Math.cos(yaw),s=Math.sin(yaw),frame:BusFrame={origin:[0,5,0],right:[c,0,-s],up:[0,1,0],forward:[s,0,c]};
  const p=busBoardingPoint(model,frame,()=>5);
  assert.ok(p,`clear level ground at heading ${yaw} must have a safe outside anchor`);
  assert.equal(busWalkerClear(model,frame,p),true);
 }
});

test('front and middle portals remain clear through headings and supported pitch/roll',()=>{
 for(const yaw of [-2.9,-1.5,-.72,0,.4,1.2,2.4])for(const roll of [-.12,0,.12]){
  const pitch=.08,c=Math.cos(yaw),s=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch),cr=Math.cos(roll),sr=Math.sin(roll);
  const baseRight=[c,0,-s],baseUp=[-s*sp,cp,-c*sp];
  const frame:BusFrame={origin:[10,5,20],right:baseRight.map((v,i)=>v*cr+baseUp[i]*sr) as [number,number,number],up:baseUp.map((v,i)=>v*cr-baseRight[i]*sr) as [number,number,number],forward:[s*cp,sp,c*cp]};
  const ground=(x:number,z:number)=>5-(frame.up[0]*(x-10)+frame.up[2]*(z-20))/frame.up[1];
  for(const id of ['front','middle']){const p=busBoardingPoint(model,frame,ground,id);assert.ok(p,`${yaw}/${roll}/${id}`);assert.equal(busWalkerClear(model,frame,p),true);}
 }
});
