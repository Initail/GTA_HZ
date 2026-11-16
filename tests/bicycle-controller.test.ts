import assert from 'node:assert/strict';
import {test} from 'node:test';
import {CityBicycle,BICYCLE_MAX_SPEED,type BicycleSurface} from '../src/city-bicycle.ts';
const start={x:0,z:0,yaw:0,height:0};
const clear=()=>true;
const flat=():BicycleSurface=>({height:0,blocked:null});
function ride(b:CityBicycle,seconds:number,keys=['KeyW']){for(let i=0;i<seconds*60;i++)b.step(new Set(keys),1/60);}
test('mount, pedal, brake, dismount and return to the same parked bike',()=>{
 const b=new CityBicycle(flat);assert.equal(b.mount(start,clear),'ok');ride(b,2);assert(b.z>3&&b.speed>3);
 assert.equal(b.dismount(clear),null);ride(b,1,['Space']);assert.equal(b.speed,0);
 const p=b.dismount(clear)!;assert(p);assert.equal(b.active,false);assert.equal(b.deployed,true);
 assert.equal(b.mount(p,clear),'ok');assert.equal(b.active,true);
});
test('does not move until mounted, and does not overwrite a parked bike from far away',()=>{
 const b=new CityBicycle(flat);ride(b,1);assert.equal(b.distance,0);b.mount(start,clear);const p=b.dismount(clear)!;
 assert.equal(b.mount({...p,x:10},clear),'far');assert.equal(b.x,0);assert.equal(b.active,false);
 assert.equal(b.stow({...p,x:10}),false);assert.equal(b.stow(p),true);assert.equal(b.deployed,false);
});
test('bike mileage is independent and debug travel clearing retains accumulated bike mileage',()=>{
 const b=new CityBicycle(flat),walker={...start};b.mount(walker,clear);ride(b,2);
 assert.deepEqual(walker,start);const distance=b.distance;assert(distance>0);b.clearDeployment();ride(b,1);
 assert.equal(b.distance,distance);assert.equal(b.deployed,false);assert.equal(b.speed,0);
});
test('speed cap, coasting, braking precedence and no reverse pedal',()=>{
 const b=new CityBicycle(flat);b.mount(start,clear);ride(b,12);assert.equal(b.speed,BICYCLE_MAX_SPEED);
 ride(b,1,[]);assert(b.speed<BICYCLE_MAX_SPEED);ride(b,2,['KeyW','Space']);assert.equal(b.speed,0);
 ride(b,1,['KeyS']);assert.equal(b.speed,0);
});
test('steering works in motion; pressing both steering keys cancels it',()=>{
 const b=new CityBicycle(flat);b.mount(start,clear);ride(b,1,['KeyD']);assert.equal(b.yaw,0);
 ride(b,1,['KeyW','KeyD']);assert(b.yaw>0&&b.x>0);const yaw=b.yaw;
 ride(b,1,['KeyW','KeyD','KeyA']);assert.equal(b.yaw,yaw);
});
test('blocked foot path cannot mount across a wall or dismount through it',()=>{
 const b=new CityBicycle(flat);assert.equal(b.mount(start,()=>false),'obstacle');assert.equal(b.active,false);
 b.mount(start,clear);assert.equal(b.dismount(()=>false),null);assert.equal(b.active,true);
 const p=b.dismount((x)=>x<.2)!;assert(p.x<0);
 assert.equal(b.mount({...p,x:1.5},x=>x<.2||x>1),'obstacle');
});
test('whole bicycle footprint rejects a curb, overhead obstruction or unsupported wheel',()=>{
 for(const surface of [
  (x:number,z:number):BicycleSurface=>({height:z>.7?.6:0,blocked:null}),
  (x:number,z:number):BicycleSurface=>({height:0,blocked:Math.abs(x)>.3?'obstacle':null}),
  (x:number,z:number):BicycleSurface=>({height:z>.7?NaN:0,blocked:null})
 ]){const b=new CityBicycle(surface);assert.notEqual(b.mount(start,clear),'ok');assert.equal(b.active,false);}
});
for(const reason of ['restricted-road','water','obstacle'] as const)test('swept motion stops before '+reason,()=>{
 const b=new CityBicycle((x,z)=>({height:0,blocked:z>=4?reason:null}));b.mount(start,clear);ride(b,5);
 assert(b.z<3);assert(b.z>2.5);assert.equal(b.speed,0);assert.equal(b.barrier,reason);
});
test('small continuous bridge ramp works; a discontinuous bridge deck cannot be climbed',()=>{
 const ramp=new CityBicycle((x,z)=>({height:z*.08,blocked:null}));assert.equal(ramp.mount(start,clear),'ok');ride(ramp,3);assert(ramp.z>7&&ramp.height>.5);
 const broken=new CityBicycle((x,z)=>({height:z>3?2:0,blocked:null}));broken.mount(start,clear);ride(broken,4);assert(broken.z<2.1);assert.equal(broken.barrier,'step');
});
test('dismount chooses safe bank, refuses water and refuses another bridge level',()=>{
 const b=new CityBicycle((x)=>({height:x>.5?4:0,blocked:null}));b.mount(start,clear);const p=b.dismount(x=>x<.4)!;assert(p.x<0);
 const island=new CityBicycle(flat);island.mount(start,clear);assert.equal(island.dismount(x=>Math.abs(x)<.45),null);assert.equal(island.active,true);
});
test('invalid delta and invalid mount cannot poison the pose; long frames are bounded',()=>{
 const b=new CityBicycle(flat);assert.equal(b.mount({...start,x:NaN},clear),'obstacle');b.mount(start,clear);
 b.step(new Set(['KeyW']),NaN);b.step(new Set(['KeyW']),-1);assert.equal(b.distance,0);
 b.step(new Set(['KeyW']),100);assert(b.distance<.01);assert(Number.isFinite(b.speed));
});
