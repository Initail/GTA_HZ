import test from 'node:test';
import assert from 'node:assert/strict';
import {RoadGraph,type NodedRoadGraph} from '../src/navigation.ts';
import {CityAutopilot} from '../src/city-autopilot.ts';
import type {CityCollision} from '../src/driving.ts';
import {CityTraffic} from '../src/traffic.ts';
import {CityEbikes} from '../src/city-ebikes.ts';
import type {Road,V2} from '../src/city-types.ts';
import type {Scene} from '@babylonjs/core';

// Copy this file directly to tests/. These tiny fixtures use no whole-city assets.
// Real fragments below are from the fixed Geofabrik 261011 Hangzhou extraction.
const routeLength=(points:readonly V2[])=>points.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-points[i][0],p[1]-points[i][1]),0);
const lerp=(a:V2,b:V2,t:number):V2=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
type Chain=[number,number,boolean?];
function fixture(nodes:V2[],chains:Chain[],prepared=true,grades?:string[]){
 const roads:Road[]=chains.map(([a,b,oneway=true],i)=>({id:'r'+i,name:'fixture',kind:'service',width:4.5,grade:grades?.[i]??'0',oneway,points:[nodes[a],nodes[b]],nodeIds:[String(a),String(b)]}));
 const noded:NodedRoadGraph={nodes,edges:chains.map(([a,b])=>[a,b])};
 if(prepared)noded.roadNodes=Object.fromEntries(chains.map(([a,b],i)=>['r'+i,[a,b]]));
 return new RoadGraph(roads,noded);
}
function autopilotRoute(graph:RoadGraph,start:V2,end:V2):V2[]{
 // Exercise the actual incremental planner without scene/physics or timing-driven ticks.
 // findRoute does not use collision; scene integration is covered separately.
 const pilot=new CityAutopilot(graph,{} as CityCollision);
 const iterator=(pilot as unknown as {findRoute:(a:V2,b:V2)=>Generator<void,V2[],void>}).findRoute(start,end);
 let result=iterator.next(),slices=0;
 while(!result.done){assert.ok(++slices<10000,'planner must terminate');result=iterator.next();}
 return result.value;
}
const planners={map:(g:RoadGraph,a:V2,b:V2)=>g.route(a,b),autopilot:autopilotRoute};
type Case={name:string;nodes:V2[];chains:Chain[];start:V2;end:V2;expectedLength:number;prepared?:boolean;grades?:string[]};
const cases:Case[]=[
 {name:'same edge cannot take a reverse shortcut',nodes:[[0,0],[100,0]],chains:[[0,1]],start:[80,0],end:[20,0],expectedLength:0},
 {name:'same edge remains usable forward',nodes:[[0,0],[100,0]],chains:[[0,1]],start:[20,0],end:[80,0],expectedLength:60},
 {name:'exact endpoint needs no reverse zero-length connector',nodes:[[0,0],[100,0]],chains:[[0,1]],start:[0,0],end:[80,0],expectedLength:80},
 {name:'start projection cannot escape through a forbidden endpoint',nodes:[[0,0],[100,0],[-20,0]],chains:[[0,1],[2,0,false]],start:[80,0],end:[-10,0],expectedLength:0},
 {name:'destination projection cannot be entered backwards',nodes:[[0,0],[100,0],[120,0]],chains:[[0,1],[1,2,false]],start:[110,0],end:[80,0],expectedLength:0},
 {name:'middle edge relaxation respects one way',nodes:[[0,0],[100,0],[200,0],[0,-20],[200,-20]],chains:[[0,1],[1,2],[0,3,false],[2,4,false]],start:[200,-10],end:[0,-10],expectedLength:0},
 {name:'same edge reverse request can use a legal loop',nodes:[[0,0],[100,0],[100,100],[0,100]],chains:[[0,1],[1,2],[2,3],[3,0]],start:[80,0],end:[20,0],expectedLength:340},
 {name:'legacy noded graph without roadNodes remains bidirectional',nodes:[[0,0],[100,0]],chains:[[0,1]],start:[80,0],end:[20,0],expectedLength:60,prepared:false},
 {name:'opposite one-way owners permit both directions on a shared edge',nodes:[[0,0],[100,0]],chains:[[0,1],[1,0]],start:[80,0],end:[20,0],expectedLength:60},
 {name:'geometric crossing of distinct prepared deck nodes is not a junction',nodes:[[-100,0],[100,0],[0,-100],[0,100]],chains:[[0,1,false],[2,3,false]],start:[-80,0],end:[0,80],expectedLength:0,grades:['1','0']},
];
for(const [name,plan] of Object.entries(planners))for(const scenario of cases)test(`${name}: ${scenario.name}`,()=>{
 const graph=fixture(scenario.nodes,scenario.chains,scenario.prepared??true,scenario.grades);
 const route=plan(graph,scenario.start,scenario.end);
 if(scenario.expectedLength===0)assert.deepEqual(route,[],'unreachable request must return no route');
 else {assert.ok(route.length>1);assert.ok(Math.abs(routeLength(route)-scenario.expectedLength)<1e-6,`unexpected route length ${routeLength(route)}`);}
});

// way/118180320 (绿汀路), raw tags highway=secondary, oneway=-1.
// Raw source order: 3635012653 [119.9863768,30.2762903] ->
//                   6052188834 [119.9863361,30.2751379].
// The existing preparation correctly reverses it; these are the actual prepared
// points at original demo-v3 graph nodes [9550,9549], source segment index 6.
const lvting:Road={id:'way/118180320#0',sourceId:'way/118180320',name:'绿汀路',kind:'secondary',width:6,grade:'0',oneway:true,
 nodeIds:['6052188834','3635012653'],points:[[-9737.316273030889,75.68655809668476],[-9734.966577735642,152.33757272937464]],heights:[3.080146999587515,3.412554676328946]};
function sourceGraph(road:Road){return new RoadGraph([road],{nodes:road.points,edges:[[0,1]],roadNodes:{[road.id]:[0,1]},nodeHeights:road.heights});}
for(const [name,plan] of Object.entries(planners)){
 test(`${name}: real Hangzhou oneway=-1 fragment rejects travel in raw source direction`,()=>{
  const graph=sourceGraph(lvting),start=lerp(...lvting.points as [V2,V2],.8),end=lerp(...lvting.points as [V2,V2],.2);
  assert.equal(graph.allowsDirection(0,1),true);assert.equal(graph.allowsDirection(1,0),false);
  assert.deepEqual(plan(graph,start,end),[]);
 });
 test(`${name}: real Hangzhou oneway=-1 fragment allows prepared forward direction`,()=>{
  const graph=sourceGraph(lvting),start=lerp(...lvting.points as [V2,V2],.2),end=lerp(...lvting.points as [V2,V2],.8),route=plan(graph,start,end);
  assert.ok(Math.abs(routeLength(route)-46.012212296220746)<1e-6);
 });
 test(`${name}: old Shenzhen graph without noded metadata keeps reverse routing`,()=>{
  const road:Road={id:'legacy',name:'legacy',kind:'service',width:6,grade:'0',oneway:true,points:[[0,0],[100,0]]};
  const graph=new RoadGraph([road]);assert.equal(graph.allowsDirection(1,0),undefined);
  assert.ok(Math.abs(routeLength(plan(graph,[80,0],[20,0]))-60)<1e-6);
 });
}

// Real directed sink on way/157966406, tags highway=service, lit=yes,
// oneway=yes, service=parking_aisle. Original demo-v3 graph edge [6246,11942].
const parking:Road={id:'way/157966406#0',sourceId:'way/157966406',name:'支路',kind:'service',width:4.5,grade:'0',oneway:true,
 nodeIds:['1701921798','1701921803'],points:[[-845.0820573025788,-5667.851656974098],[-849.9950565559051,-5656.510978394747]],heights:[6.398587867240387,6.071802884019553]};
function actorSeed(road:Road){const p=lerp(...road.points as [V2,V2],.999),[a,b]=road.points;return {from:0,to:1,t:.999,speed:10,x:p[0],z:p[1],yaw:Math.atan2(b[0]-a[0],b[1]-a[1])};}
for(const oneway of [true,false]){
 test(`car NPC ${oneway?'holds at a real one-way sink':'may turn back at a two-way dead end'}`,()=>{
  const road={...parking,oneway},graph=sourceGraph(road),seed=actorSeed(road),allowed=(a:number,b:number)=>graph.allowsDirection(a,b)!==false;
  // Empty prototypes make this a controller test; no engine, canvas or GPU is created.
  const traffic=new CityTraffic(graph,[],{} as Scene,()=>0,allowed);traffic.origin=[seed.x,seed.z];traffic.cars=[{...seed,group:0}];
  for(let i=0;i<5;i++)traffic.update(.1,seed.x,seed.z);
  const car=traffic.cars[0];assert.ok(allowed(car.from,car.to));
  if(oneway){assert.equal(car.from,0);assert.equal(car.to,1);assert.equal(car.t,1);}
  else {assert.equal(car.from,1);assert.equal(car.to,0);assert.ok(car.t>0&&car.t<1);}
 });
 test(`bicycle NPC ${oneway?'holds at a real one-way sink':'may turn back at a two-way dead end'}`,()=>{
  const road={...parking,oneway},graph=sourceGraph(road),seed=actorSeed(road),allowed=(a:number,b:number)=>graph.allowsDirection(a,b)!==false;
  const bikes=new CityEbikes({} as Scene,()=>0);bikes.attachGraph(graph,allowed);bikes.riders=[{...seed,type:1,paint:0,cloth:0,helmet:0}];
  for(let i=0;i<5;i++)(bikes as unknown as {step:(dt:number)=>void}).step(.1);
  const rider=bikes.riders[0];assert.ok(allowed(rider.from,rider.to));
  if(oneway){assert.equal(rider.from,0);assert.equal(rider.to,1);assert.equal(rider.t,1);}
  else {assert.equal(rider.from,1);assert.equal(rider.to,0);assert.ok(rider.t>0&&rider.t<1);}
 });
}
