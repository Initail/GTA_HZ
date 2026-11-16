import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {stepCar} from '../src/driving.ts';
import {CityRoadLevels,type RoadLevel} from '../src/city-road-levels.ts';
const lower:RoadLevel={id:'underpass',points:[[-100,0],[100,0]],heights:[0,0],width:10,tier:0,nodeIds:[1,2]};
const upper:RoadLevel={id:'bridge',points:[[0,-100],[0,100]],heights:[8,8],width:10,tier:1,nodeIds:[3,4]};
test('prepared arrivals retain the source deck and reject obsolete, outside and underground positions',()=>{
 const tunnel={...lower,id:'tunnel',heights:[-4,-4],tier:-1};
 const levels=new CityRoadLevels([lower,upper,tunnel],()=>0);
 assert.equal(levels.sourceArrival('bridge',0,0)?.height,8);
 assert.equal(levels.sourceArrival('underpass',0,0)?.height,0);
 for(const [id,x,z] of [['missing',0,0],['bridge',6,0],['bridge',0,120],['tunnel',0,0],['bridge',NaN,0]] as const)
  assert.equal(levels.sourceArrival(id,x,z),null);
});
test('one x/z crossing has independent lower and upper actor surfaces',()=>{
 const levels=new CityRoadLevels([lower,upper],()=>0);
 assert.equal(levels.sample(0,0,{height:0,roadId:'underpass'}).height,0);
 assert.equal(levels.sample(0,0,{height:8,roadId:'bridge'}).height,8);
 assert.equal(levels.sample(0,0).roadId,'underpass');assert.equal(levels.sample(150,150).roadId,null);
});
test('source-connected ramp endpoint joins its shared road at the same height',()=>{
 const ramp:RoadLevel={id:'ramp',points:[[100,0],[100,100]],heights:[0,8],width:10,tier:1,nodeIds:[2,5]};
 const levels=new CityRoadLevels([lower,ramp],()=>0);
 assert.equal(levels.sample(100,0,{height:0,roadId:'ramp'}).height,0);
 assert.equal(levels.sample(100,50,{height:4,roadId:'ramp'}).height,4);
});
test('buried surface requires actor context and malformed heights are rejected',()=>{
 const tunnel={...lower,id:'tunnel',heights:[-4,-4],tier:-1,nodeIds:[6,7]};
 const levels=new CityRoadLevels([lower,tunnel],()=>0);
 assert.equal(levels.sample(0,0).height,0);assert.equal(levels.sample(0,0,{height:-4,roadId:'tunnel'}).height,-4);
 assert.throws(()=>new CityRoadLevels([{...lower,heights:[0]}],()=>0));assert.throws(()=>levels.sample(NaN,0));
});
test('ground roads blend into terrain without lifting ground under an elevated deck',()=>{
 const street={...lower,heights:[4,4]},levels=new CityRoadLevels([street,upper],()=>10,20);
 assert.equal(levels.sample(30,0).height,4);
 assert.equal(levels.sample(30,15).height,7);
 assert.equal(levels.sample(30,30).height,10);
 const bridgeOnly=new CityRoadLevels([upper],()=>0,20);
 assert.equal(bridgeOnly.sample(10,0).height,0);
 assert.equal(bridgeOnly.sample(0,0,{height:8}).height,8);
 assert.equal(bridgeOnly.groundAt(0,0),0);
 assert.equal(levels.groundAt(30,15),7);
});
test('neighbouring ground road influence stays continuous across nearest-road and width boundaries',()=>{
 const a={...lower,id:'a',heights:[4,4],width:6};
 const b={...lower,id:'b',points:[[-100,20],[100,20]] as [number,number][],heights:[12,12],width:18};
 const field=new CityRoadLevels([a,b],()=>18,20),reversed=new CityRoadLevels([b,a],()=>18,20);
 for(let z=-23;z<=49;z+=.25){
  assert.ok(Math.abs(field.groundAt(0,z-1e-5)-field.groundAt(0,z+1e-5))<.0001,'discontinuous ground at '+z);
  assert.ok(Math.abs(field.groundAt(0,z)-reversed.groundAt(0,z))<1e-12);
 }
 // At-grade actors use the rendered earthworks; source IDs stay distinct.
 assert.equal(field.sample(0,0,{height:4,roadId:'a'}).height,field.groundAt(0,0));
 assert.equal(field.sample(0,20,{height:12,roadId:'b'}).roadId,'b');
 assert.equal(field.heightForSourceRoad('b',0,20,12),field.groundAt(0,20));
});
test('mixed ground feedback cannot switch a stationary actor to a disconnected deck',()=>{
 const ground={...lower,id:'ground',heights:[0,0],width:6};
 const neighbour={...ground,id:'neighbour',points:[[-100,10],[100,10]] as [number,number][],heights:[20,20],nodeIds:[5,6]};
 const deck={...ground,id:'deck',tier:1,heights:[8,8],nodeIds:[7,8]};
 const levels=new CityRoadLevels([ground,neighbour,deck],()=>0);
 let sample=levels.sample(0,0,{height:0,roadId:'ground'});
 for(let i=0;i<20;i++){
  assert.equal(sample.roadId,'ground');
  sample=levels.sample(0,0,{height:sample.height,roadId:sample.roadId!});
 }
 assert.equal(levels.sample(0,0,{height:8,roadId:'deck'}).roadId,'deck');
});
test('deck transitions require a nearby shared source node, not a distant connection',()=>{
 const a:RoadLevel={id:'a',points:[[-20,0],[20,0]],heights:[8,8],width:6,tier:1,nodeIds:[10,11]};
 const b:RoadLevel={id:'b',points:[[0,-20],[0,20],[20,0]],heights:[8,8,8],width:6,tier:1,nodeIds:[12,13,11]};
 const levels=new CityRoadLevels([a,b],()=>0);
 assert.equal(levels.sample(0,0,{height:8,roadId:'a'}).roadId,'a');
 assert.equal(levels.sample(0,5,{height:8,roadId:'a'}).roadId,null);
 const off=levels.sample(0,5,{height:8,roadId:'a'});
 assert.equal(levels.sample(0,5,{height:off.height,groundOnly:off.roadId===null}).roadId,null);
 assert.equal(levels.sample(18,4,{height:8,roadId:'a'}).roadId,'b');
 assert.equal(levels.sample(18,3.4,{height:8,roadId:'a'}).roadId,'a');
 const joined=levels.sample(20,4,{height:8,roadId:'a'});
 assert.equal(joined.roadId,'b');
});
test('the real Wanzhangshan exit follows its connected grade before the old endpoint cap creates a false car stop',()=>{
 const fixture=JSON.parse(readFileSync(new URL('./fixtures/xianfu-upper-source-seam.json',import.meta.url),'utf8'));
 const roads=fixture.roads as RoadLevel[],levels=new CityRoadLevels(roads,()=>0);
 const next=roads.find(r=>r.id==='way/697096309#0')!,old=roads.find(r=>r.id==='way/697096310#0')!;
 const [a,b]=next.points,dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz),yaw=Math.atan2(dx,dz);
 let hint={height:old.heights.at(-1)!,roadId:old.id};
 // Reach the formerly held 3.2g position through actual source queries.
 for(let s=.4;s<=3.200001;s+=.4){
  const sample=levels.sample(a[0]+dx*s/length,a[1]+dz*s/length,hint);
  assert.equal(sample.roadId,next.id);assert.ok(Math.abs(sample.height-hint.height)<.7);
  hint={height:sample.height,roadId:sample.roadId!};
 }
 const car={x:a[0]+dx*3.2/length,z:a[1]+dz*3.2/length,yaw,speed:53,steer:0,distance:0},before={...car};
 stepCar(car,{throttle:1,steer:0,handbrake:false},.05);
 for(let i=1;i<=4;i++){
  const sample=levels.sample(before.x+(car.x-before.x)*i/4,before.z+(car.z-before.z)*i/4,hint);
  assert.equal(sample.roadId,next.id);assert.ok(Math.abs(sample.height-hint.height)<.7);
 }
 assert.ok(Math.abs(levels.sample(car.x,car.z,hint).height-hint.height)<.319);
});
