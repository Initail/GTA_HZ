import test from 'node:test';
import assert from 'node:assert/strict';
import {NullEngine,Scene} from '@babylonjs/core';
import {RoadGraph} from '../src/navigation.ts';
import {CityTraffic} from '../src/traffic.ts';
import {CityEbikes} from '../src/city-ebikes.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import type {Road} from '../src/city-types.ts';

const road=(id:string):Road=>({id,name:id,kind:'primary',width:6,oneway:true,points:[[0,-20],[0,20]],grade:id==='upper'?'1':'0'});
const make=()=>new RoadGraph([road('lower'),road('upper')],{nodes:[[0,-20],[0,20],[0,-20],[0,20]],edges:[[0,1],[2,3]],nodeHeights:[0,0,8,8],roadNodes:{lower:[0,1],upper:[2,3]}});

test('source edges keep independent heights and traffic directions at the same x/z',()=>{
 const graph=make();assert.equal(graph.heightOnEdge(0,1,.5,99),0);assert.equal(graph.heightOnEdge(2,3,.5,99),8);
 assert.equal(graph.allowsDirection(0,1),true);assert.equal(graph.allowsDirection(1,0),false);
 assert.equal(graph.allowsDirection(2,3),true);assert.equal(graph.edges[0].has(2),false);
 assert.throws(()=>graph.heightOnEdge(0,2,.5,99),/Invalid source height edge/);
 const flat=new RoadGraph([],{nodes:[[0,0],[10,0]],edges:[[0,1]]});assert.equal(flat.heightOnEdge(0,1,.5,3),3);assert.equal(flat.allowsDirection(0,1),undefined);
});
test('NPC cars do not queue behind a different road deck and report their own signal height',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),traffic=new CityTraffic(make(),[],scene,()=>{throw Error('Cannot use a global x/z sampler for these source edges');});
 traffic.cars=[{from:0,to:1,t:.5,speed:7,x:1.15,z:0,yaw:0,group:0},{from:2,to:3,t:.53,speed:7,x:1.15,z:1.2,yaw:0,group:1}];
 const heights:number[]=[];traffic.signalHold=(_x,_z,_yaw,y)=>{heights.push(y!);return null;};
 traffic.update(.1,0,0);assert.ok(traffic.cars[0].t>.5);assert.deepEqual(heights,[0,8]);
 scene.dispose();engine.dispose();
});
test('riding electric bikes use source deck heights and avoid cross-deck queues',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),bikes=new CityEbikes(scene,()=>{throw Error('Cannot use a global x/z sampler for these source edges');});
 const graph=make();bikes.attachGraph(graph,()=>true);bikes.place(0,0);
 bikes.palette=[[1,1,1]];bikes.riderPalette=[[1,1,1]];bikes.helmetPalette=[[1,1,1]];
 bikes.riders=[{from:0,to:1,t:.5,speed:7,x:2.15,z:0,yaw:0,type:0,paint:0,cloth:0,helmet:0},{from:2,to:3,t:.53,speed:7,x:2.15,z:1.2,yaw:0,type:0,paint:0,cloth:0,helmet:0}];
 const heights:number[]=[];bikes.signalHold=(_x,_z,_yaw,y)=>{heights.push(y!);return null;};
 bikes.update(.1,0,0);assert.ok(bikes.riders[0].t>.5);assert.deepEqual(heights,[0,8]);
 bikes.dispose();scene.dispose();engine.dispose();
});
test('malformed source height and direction mappings fail before use',()=>{
 assert.throws(()=>new RoadGraph([],{nodes:[[0,0]],edges:[],nodeHeights:[NaN]}),/Invalid source road node heights/);
 assert.throws(()=>new RoadGraph([road('missing')],{nodes:[[0,0]],edges:[],roadNodes:{}}),/Missing source road chain/);
});
test('ground traffic samples its actual lane position while an overlapping bridge keeps its deck',()=>{
 const graph=make(),levels=new CityRoadLevels([
  {id:'lower',points:[[0,-20],[0,20]],heights:[0,0],width:6,tier:0,nodeIds:[1,2]},
  {id:'adjacent',points:[[10,-20],[10,20]],heights:[2,2],width:6,tier:0,nodeIds:[5,6]},
  {id:'upper',points:[[0,-20],[0,20]],heights:[8,8],width:6,tier:1,nodeIds:[3,4]},
 ],()=>0);
 graph.bindSourceSurfaceHeight((id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));
 const engine=new NullEngine(),scene=new Scene(engine),traffic=new CityTraffic(graph,[],scene,()=>99);
 const car={from:0,to:1,t:.5,speed:7,x:1.15,z:0,yaw:0,group:0};
 assert.equal(traffic.surfaceHeight(car),levels.groundAt(1.15,0));
 assert.notEqual(traffic.surfaceHeight(car),graph.heightOnEdge(0,1,.5,0));
 assert.equal(traffic.surfaceHeight({...car,from:2,to:3}),8);
 assert.equal(graph.edges[0].has(2),false);assert.equal(graph.allowsDirection(1,0),false);
 assert.throws(()=>graph.surfaceHeightOnEdge(0,2,.5,0,[0,0]),/Invalid source height edge/);
 scene.dispose();engine.dispose();
});
