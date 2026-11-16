import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {RoadGraph} from '../src/navigation.ts';import type {Road} from '../src/city-types.ts';
import {buildBusRoute} from '../src/city-bus-route.ts';import {CityBus} from '../src/city-bus.ts';import {CityBusSession} from '../src/city-bus-session.ts';
import {busEnvelope,busBoardingPoint,prepareBusPassengerCamera,type BusFrame,type BusModelGeometry} from '../src/city-bus-vehicle.ts';
const model:BusModelGeometry=JSON.parse(readFileSync(new URL('./fixtures/bus/generated-bus-mesh-v4.json',import.meta.url),'utf8'));
function setup(){
 const road={id:'test-service',sourceId:'test-only-source',points:[[0,0],[0,30]],width:6,kind:'service',name:'test',nodeIds:['a','b'],sourceWayPointOrder:'osm-forward',sourceAccessTags:{bus:'yes'}} as Road;
 const graph=new RoadGraph([road],{nodes:road.points,edges:[[0,1]],nodeHeights:[5,5],roadNodes:{[road.id]:[0,1]}});
 const frameFor=(z:number):BusFrame=>({origin:[0,5,z],right:[1,0,0],up:[0,1,0],forward:[0,0,1]});
 const stops=[0,1].map(node=>({id:'stop'+node,name:'站'+node,node,sourcePlatformId:'test-platform'+node,sourceStopId:'test-stop'+node,platform:busBoardingPoint(model,frameFor(node*30),()=>5)!}));
 const route=buildBusRoute(graph,'test','测试班次',stops,120,3);
 let platformClear=true,surface=true,paused=false,busy=false,walking=true,boarding=0,landing=0,pose={...stops[0].platform},messages:string[]=[];
 const bus=new CityBus(graph,route,{geometry:busEnvelope(model),boardingPoint:p=>surface?busBoardingPoint(model,frameFor(p.z),()=>5):null,clear:()=>true,holdDistance:()=>null,platformClear:()=>platformClear,walkingPath:()=>platformClear});
 const session=new CityBusSession(bus,prepareBusPassengerCamera(model),{pose:()=>pose,walking:()=>walking,paused:()=>paused,busy:()=>busy,frame:()=>surface?frameFor(bus.pose.z):null,board:()=>{walking=false;boarding++;},land:p=>{walking=true;pose=p;landing++;},message:s=>messages.push(s)});
 return {bus,session,messages,get boarding(){return boarding;},get landing(){return landing;},get walking(){return walking;},set busy(v:boolean){busy=v;},set paused(v:boolean){paused=v;},set surface(v:boolean){surface=v;},set clear(v:boolean){platformClear=v;}};
}
test('active task and missing contact surface refuse boarding without changing walking state',()=>{
 const h=setup();h.busy=true;assert.equal(h.session.interact(),true);assert.equal(h.boarding,0);assert.equal(h.walking,true);
 h.busy=false;h.surface=false;h.session.interact();assert.equal(h.boarding,0);h.surface=true;h.session.interact();assert.equal(h.boarding,1);assert.equal(h.session.active,true);
});
test('moving passenger can request exit but cannot teleport out before safe stop',()=>{
 const h=setup();h.session.interact();for(let i=0;i<100;i++)h.session.step(.05);
 assert.ok(h.bus.distance>0);h.session.interact();assert.equal(h.bus.requestedExit,true);assert.equal(h.landing,0);assert.match(h.session.prompt()!,/已预约/);
 for(let i=0;i<1000&&h.bus.phase!=='complete';i++)h.session.step(.05);
 assert.equal(h.bus.phase,'complete');h.clear=false;h.session.interact();assert.equal(h.landing,0);assert.equal(h.session.active,true);
 h.clear=true;h.session.interact();assert.equal(h.landing,1);assert.equal(h.session.active,false);h.session.interact();assert.equal(h.landing,1);
});
test('pause and unavailable streamed surface freeze bus and retain seated position',()=>{
 const h=setup();h.session.interact();h.paused=true;for(let i=0;i<100;i++)h.session.step(.05);assert.equal(h.bus.clock,0);assert.equal(h.session.interact(),false);
 h.paused=false;h.surface=false;for(let i=0;i<100;i++)h.session.step(.05);assert.equal(h.bus.clock,0);assert.equal(h.session.active,true);assert.equal(h.session.view(1.8),null);
 h.surface=true;h.session.step(.05);assert.ok(h.bus.clock>0);assert.ok(h.session.view(1.8));
});
test('passenger look clamps without changing vehicle position or progress',()=>{
 const h=setup();h.session.interact();h.session.look(10,10);const view=h.session.view(4)!;
 assert.ok(view);assert.equal(h.session.lookYaw,1.35);assert.equal(h.session.lookPitch,.55);assert.equal(h.bus.distance,0);
 h.session.look(NaN,0);assert.equal(h.session.lookYaw,1.35);
});
test('model front extent, rather than obsolete proxy length, controls signal stopping',()=>{
 const h=setup(),geometry=busEnvelope(model),bus=new CityBus(h.bus.graph,h.bus.route,{geometry,boardingPoint:()=>null,clear:()=>true,holdDistance:p=>10-p.z,platformClear:()=>true,walkingPath:()=>true});
 for(let i=0;i<1000;i++)bus.step(.05,false);
 assert.ok(bus.distance>6);assert.ok(bus.distance+geometry.frontExtent+1<=10+1e-9);
});
