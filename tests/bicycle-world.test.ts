import {test} from 'node:test';import assert from 'node:assert/strict';
import {CpuWorld} from './cpu-world.ts';
import {CityBicycle} from '../src/city-bicycle.ts';
import {CityBicycleParking} from '../src/city-bicycle-parking.ts';
import {CityWalk} from '../src/city-walk.ts';
import {CityCollision} from '../src/driving.ts';
import {readFileSync} from 'node:fs';import {stripTypeScriptTypes} from 'node:module';
import {CareerGame} from '../src/city-career.ts';
function world(){
 const w=new CpuWorld();
 const roads=[{id:'public',points:[[-40,0],[40,0]],heights:[0,0],kind:'residential',width:14,name:'测试公共路',oneway:false,sourceAccessTags:{highway:'residential'}}];
 const data={meta:{extent:[-60,-60,60,60]},land:[[[[-60,-60],[60,-60],[60,60],[-60,60]]]],roads,buildings:[],water:[],landmarks:[],coast:[],green:[]};
 Object.assign(w,{geography:null,groundHeight:()=>0,collision:new CityCollision(data as any),state:{x:20,z:0,yaw:0,speed:0,steer:0,distance:123},ready:true,paused:false,observer:{active:false},flight:null,tank:null,propBlocked:()=>false,traffic:null,bambooCafe:null,ebikes:{playerBicycleReady:true},keys:new Set(),messages:[],cull:()=>{},vegetation:()=>{},cancelAutoDrive:()=>{},scene:{isDisposed:false},debugEpoch:7});
 w.onMessage=(message:string)=>w.messages.push(message);
 w.walk=new CityWalk((x,z)=>w.actorCollision(x,z,true)||w.parkedVehicleBlocks(x,z),(x,z)=>w.walkingSurfaceHeight(x,z));
 Object.assign(w.walk,{active:true,x:0,z:0,yaw:Math.PI/2});
 w.bicycle=new CityBicycle((x,z,h)=>w.bicycleSurface(x,z,h));return w;
}
test('actual world mount and F dismount keep the parked car, odometer and epoch intact',async()=>{
 const w=world(),car={...w.state};await w.toggleBicycle();assert.equal(w.controlMode,'bicycle');assert.equal(w.walk.active,false);assert.equal(w.actor,w.bicycle);
 for(let i=0;i<60;i++)w.bicycle.step(new Set(['KeyW']),1/60);
 assert(w.actor.x>0);assert.deepEqual(w.state,car);assert.equal(w.debugEpoch,7);
 await w.toggleWalking();assert.equal(w.controlMode,'bicycle','moving dismount refused');
 for(let i=0;i<30;i++)w.bicycle.step(new Set(['Space']),1/60);
 await w.toggleWalking();assert.equal(w.controlMode,'walking');assert.equal(w.bicycle.deployed,true);assert.equal(w.walk.active,true);assert.deepEqual(w.state,car);
 w.stowBicycle();assert.equal(w.bicycle.deployed,false);assert.equal(w.debugEpoch,7);
});
test('actual mount blocks menus, observer, car mode, unavailable model and walls',async()=>{
 const w=world();w.paused=true;await w.toggleBicycle();assert.equal(w.bicycle.active,false);
 w.paused=false;w.observer.active=true;await w.toggleBicycle();assert.equal(w.bicycle.active,false);
 w.observer.active=false;w.walk.active=false;await w.toggleBicycle();assert.equal(w.controlMode,'car');
 w.walk.active=true;w.ebikes.playerBicycleReady=false;await w.toggleBicycle();assert.equal(w.bicycle.active,false);
 w.ebikes.playerBicycleReady=true;w.propBlocked=()=>true;await w.toggleBicycle();assert.equal(w.bicycle.active,false);
});
test('actual bicycle surface respects same-level cars, pedestrians and cafe interiors',()=>{
 const w=world();assert.equal(w.bicycleSurface(0,0,0).blocked,null);
 assert.equal(w.bicycleSurface(20,0,0).blocked,'obstacle');
 w.pedestrians={people:[{x:0,z:0}],heightAt:()=>0};assert.equal(w.bicycleSurface(0,0,0).blocked,'obstacle');
 w.pedestrians.heightAt=()=>8;assert.equal(w.bicycleSurface(0,0,0).blocked,null);
 w.bambooCafe={layout:{floorAt:()=>0,blocked:()=>false}};assert.equal(w.bicycleSurface(0,0,0).blocked,'obstacle');
 w.bambooCafe=null;w.canopy={trunkNear:()=>true};assert.equal(w.bicycleSurface(0,0,0).blocked,'obstacle');
});
test('observer and aircraft temporarily own controls without discarding the bicycle',async()=>{
 const w=world();await w.toggleBicycle();w.observer.active=true;assert.equal(w.controlMode,'observer');
 w.flight={active:true};assert.equal(w.controlMode,'aircraft');assert.equal(w.bicycle.active,true);
 w.flight.active=false;w.observer.active=false;assert.equal(w.controlMode,'bicycle');
});
test('actual career adapter excludes bicycle distance from motor-vehicle completion',async()=>{
 const source=readFileSync(new URL('../src/city-career-experience.ts',import.meta.url),'utf8');
 const adapter=source.slice(source.indexOf(' function frame('),source.indexOf(' function persist('));
 const w=world();await w.toggleBicycle();
 const frame=new Function('world',stripTypeScriptTypes(adapter)+';return frame;')(w);
 assert.equal(frame().inVehicle,false);assert.equal(frame().odometer,123);assert.deepEqual(frame().position,[0,0]);
 const places={hub:[0,0],bay:[100,0],office:[200,0],park:[100,100],workshop:[40,0]} as const;
 const game=new CareerGame(places as any);game.selectRole('office');assert(game.accept('quiet-ten-minutes',frame()).ok);assert(game.interact(frame()).ok);
 const target=game.active!.objective.position;
 for(let i=1;i<=100;i++){w.bicycle.x=target[0]*i/100;w.bicycle.z=target[1]*i/100;w.bicycle.speed=5;game.tick(frame(.05));}
 w.bicycle.speed=0;assert.equal(game.interact(frame()).ok,false);assert.equal(game.save.cash,180);assert.equal(w.state.distance,123);
});

test('actual mount/dismount/stow checkpoints keep the parked snapshot in sync without writing the car',async()=>{
 const w=world(),car={...w.state};let raw:string|null=null;
 const storage={getItem:()=>raw,setItem:(_key:string,value:string)=>{raw=value;}};
 w.bicycleParking=new CityBicycleParking(w.bicycle,storage,{city:'hangzhou',projection:'test',key:'test-bicycle-only',extent:[-60,-60,60,60]});
 await w.toggleBicycle();assert.equal(JSON.parse(raw!).pose,null);
 await w.toggleWalking();assert.deepEqual(JSON.parse(raw!).pose,w.bicycle.pose);
 w.stowBicycle();assert.equal(JSON.parse(raw!).pose,null);assert.deepEqual(w.state,car);assert.equal(w.debugEpoch,7);
});
test('actual storage failure remains visible in the mount and parking message',async()=>{
 const w=world();w.bicycleParking={checkpoint:()=>false};
 await w.toggleBicycle();assert.match(w.messages.at(-1),/暂不能保存/);
 await w.toggleWalking();assert.match(w.messages.at(-1),/暂不能保存/);assert.equal(w.bicycle.deployed,true);
});
