import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {stripTypeScriptTypes} from 'node:module';
import {Vector3} from '@babylonjs/core/Maths/math.vector.js';
const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8'),begin=source.indexOf(' private placeInitialDrivingView(){'),end=source.indexOf('\n private attachBaseTile(',begin);assert(begin>=0&&end>begin);
const Harness=new Function('Vector3',stripTypeScriptTypes('class Harness{'+source.slice(begin,end)+'}')+';return Harness;')(Vector3);
test('initial car and camera follow the actual road level at nonzero and below-datum spawn heights',()=>{
 for(const road of [-3,0,7.1,63]){
  const world=new Harness();let target:Vector3|undefined;
  Object.assign(world,{state:{x:251,z:-41,yaw:1.2,speed:0,distance:73},carSurfaceHeight:(x:number,z:number)=>{assert.equal(x,251);assert.equal(z,-41);return road;},groundHeight:()=>road-20,car:{position:new Vector3(),rotation:{y:0}},camera:{position:new Vector3(),setTarget:(t:Vector3)=>target=t}});
  world.placeInitialDrivingView();assert.equal(world.car.position.y,road+.12);assert.equal(world.camera.position.y,road+3.7);assert.equal(target!.y,road+1.1);
  assert(Math.abs(Vector3.Distance(new Vector3(251,world.camera.position.y,-41),world.camera.position)-8)<1e-10);assert.equal(world.cameraYaw,1.2);assert.equal(world.state.distance,73);
 }
});
test('initial admission and completed loading use the same road-relative camera placement',()=>{
 const init=source.slice(source.indexOf(' async init(progress:'),source.indexOf('\n private configureTrafficContact('));
 assert.equal(init.split('this.placeInitialDrivingView();').length-1,2);
 assert(init.indexOf('this.placeInitialDrivingView();')<init.indexOf('await this.baseStream.init(this.baseView());'));
 assert(init.lastIndexOf('this.placeInitialDrivingView();')>init.indexOf('this.ready=true'));
});
