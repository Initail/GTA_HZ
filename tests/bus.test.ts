import {test} from 'node:test';import assert from 'node:assert/strict';import {RoadGraph} from '../src/navigation.ts';import {buildBusRoute,busRoutePose,type BusStopAnchor} from '../src/city-bus-route.ts';import {CityBus} from '../src/city-bus.ts';import type {Road} from '../src/city-types.ts';
const fixtureGeometry={halfWidth:1.25,frontExtent:5.1,rearExtent:5.1,height:3.2,turnRadius:Math.hypot(1.25,5.1)};
const fixtureDoor=(p:{x:number;z:number;height:number;yaw:number})=>({...p,x:p.x+Math.cos(p.yaw)*1.7+Math.sin(p.yaw)*3.2,z:p.z-Math.sin(p.yaw)*1.7+Math.cos(p.yaw)*3.2});
function setup(){const road={id:'source-road',sourceId:'way/real-shape-fixture',points:[[0,0],[0,40],[0,80]],width:6,name:'fixture',kind:'service',oneway:true,nodeIds:['a','b','c'],sourceWayPointOrder:'osm-forward',sourceAccessTags:{access:'no',bus:'yes',oneway:'yes'}} as Road;
 const graph=new RoadGraph([road],{nodes:road.points,edges:[[0,1],[1,2]],nodeHeights:[5,5,8],roadNodes:{[road.id]:[0,1,2]}});
 const stops:BusStopAnchor[]=[0,1,2].map((node,i)=>({id:'stop'+i,name:'Stop '+i,sourcePlatformId:'platform'+i,sourceStopId:'node'+i,node,platform:{x:1.7,z:i*40+3.2,height:i===2?8:5}}));
 const route=buildBusRoute(graph,'test','模拟班次',stops,120,3);let blocked=false,red:number|null=null,platform=true;const bus=new CityBus(graph,route,{geometry:fixtureGeometry,boardingPoint:fixtureDoor,clear:()=>!blocked,holdDistance:()=>red,platformClear:()=>platform,walkingPath:()=>platform});
 return {graph,route,bus,set blocked(v:boolean){blocked=v;},set red(v:number|null){red=v;},set platform(v:boolean){platform=v;}};
}
test('prepared route uses bus access rather than motorcar permission',()=>{const h=setup();assert.equal(h.graph.canTraverse(0,1,'motorcar'),false);assert.equal(h.graph.canTraverse(0,1,'bus'),true);assert.equal(h.route.length,80);assert.throws(()=>buildBusRoute(h.graph,'back','wrong way',[...h.route.stops].reverse()));});
test('source edge interpolation retains level and source identity',()=>{const h=setup(),p=busRoutePose(h.graph,h.route,60);assert.equal(p.height,6.5);assert.deepEqual(p.sourceEdge,[1,2]);});
test('wrong layer, active jobs and remote platform cannot board',()=>{const h=setup(),p={...h.route.stops[0].platform,yaw:0};assert.equal(h.bus.board({...p,height:20},true,false),false);assert.equal(h.bus.board(p,true,true),false);assert.equal(h.bus.board({...p,x:15},true,false),false);assert.equal(h.bus.board(p,true,false),true);});
test('boarding requires the actual platform-to-door path, not only reaching the platform',()=>{
 const h=setup(),stop=h.route.stops[0];stop.platform={...stop.platform,x:2.2};
 const p={...stop.platform,yaw:0},bus=new CityBus(h.graph,h.route,{geometry:fixtureGeometry,boardingPoint:fixtureDoor,clear:()=>true,holdDistance:()=>null,platformClear:()=>true,walkingPath:(from,to)=>Math.abs(from.x-to.x)<.01});
 assert.equal(bus.board(p,true,false),false,'a barrier between the platform and door must not be bypassed');assert.equal(bus.passenger,false);
});
test('an initially obstructed bus cannot accept a passenger before its first update',()=>{
 const h=setup(),p={...h.route.stops[0].platform,yaw:0};h.blocked=true;
 assert.equal(h.bus.board(p,true,false),false);assert.equal(h.bus.passenger,false);
});
test('pause preserves simulated departure time and vehicle position',()=>{const h=setup();for(let i=0;i<100;i++)h.bus.step(.05,true);assert.equal(h.bus.clock,0);assert.equal(h.bus.distance,0);h.bus.step(NaN,false);assert.equal(h.bus.clock,0);});
test('same-level red stop line holds the full front of the bus',()=>{const h=setup();h.red=10;for(let i=0;i<1000;i++){h.red=10-h.bus.distance;h.bus.step(.05,false);}assert.ok(h.bus.distance+5.1+1<=10+1e-9,`front bumper violated stop line: ${h.bus.distance}`);assert.equal(h.bus.stopIndex,0);h.red=null;for(let i=0;i<400;i++)h.bus.step(.05,false);assert.ok(h.bus.distance>3.9);});
test('solid obstruction cannot be crossed and can later clear',()=>{const h=setup();h.blocked=true;for(let i=0;i<100;i++)h.bus.step(.05,false);assert.equal(h.bus.distance,0);assert.equal(h.bus.phase,'blocked');h.blocked=false;for(let i=0;i<100;i++)h.bus.step(.05,false);assert.ok(h.bus.distance>0);});
test('passenger exits only at a stopped, safe platform',()=>{const h=setup(),p={...h.route.stops[0].platform,yaw:0};h.bus.board(p,true,false);for(let i=0;i<150;i++)h.bus.step(.05,false);assert.equal(h.bus.disembark(),null);h.bus.requestExit();for(let i=0;i<1000&&h.bus.stopIndex===0;i++)h.bus.step(.05,false);assert.equal(h.bus.stopIndex,1);assert.equal(h.bus.phase,'dwelling');h.platform=false;assert.equal(h.bus.disembark(),null);assert.equal(h.bus.passenger,true);h.platform=true;assert.deepEqual(h.bus.disembark(),{...h.route.stops[1].platform,yaw:0});assert.equal(h.bus.passenger,false);});
