import test from 'node:test';
import assert from 'node:assert/strict';
import {attachCityRoadLevels} from '../src/city-geography.ts';
import {CityWalk} from '../src/city-walk.ts';
import {CityAutopilot} from '../src/city-autopilot.ts';
import {CityCollision} from '../src/driving.ts';
import {RoadGraph} from '../src/navigation.ts';
import type {CityData,Road} from '../src/city-types.ts';
const road=(id:string,refs:string[],height:number):Road=>({id,name:id,kind:'primary',width:6,oneway:false,points:[[0,-20],[0,20]],nodeIds:refs,heights:[height,height],grade:height?'1':'0'});
function data():CityData{return {meta:{counts:{},extent:[-30,-30,30,30],horizontalScale:.6},land:[[[[-30,-30],[30,-30],[30,30],[-30,30]]]],coast:[],roads:[road('lower',['1','2'],0),road('upper',['3','4'],8)],buildings:[],green:[],water:[],landmarks:[],spawn:{x:0,z:0,yaw:0,road:'lower'}};}
test('physical roads bind by source identity before mutating city collision data',()=>{
 const city=data(),surfaces=city.roads.map(r=>({...r,heights:r.heights!,nodeIds:r.nodeIds!,tier:Number(r.grade)}));
 const levels=attachCityRoadLevels(city,surfaces,()=>0);assert.equal(levels.sample(0,0,{height:8}).roadId,'upper');
 const wrong=surfaces.map(s=>({...s}));wrong[1]={...wrong[1],nodeIds:['1','2']};
 const fresh=data();fresh.roads.forEach(r=>delete r.heights);assert.throws(()=>attachCityRoadLevels(fresh,wrong,()=>0),/源节点不一致/);assert.equal(fresh.roads[0].heights,undefined);
});
test('walker cannot enter a parked vehicle on another deck at the same horizontal position',()=>{
 const walk=new CityWalk(()=>false,()=>0);walk.active=true;walk.x=1.9;walk.z=0;
 assert.equal(walk.canEnter({x:0,z:0,yaw:0,speed:0,groundY:8}),false);
 assert.equal(walk.canEnter({x:0,z:0,yaw:0,speed:0,groundY:0}),true);
});
test('autopilot source-layer selection rejects an unreachable other deck',()=>{
 const city=data(),collision=new CityCollision(city),graph=new RoadGraph(city.roads,{nodes:[[0,-20],[0,20],[0,-20],[0,20]],edges:[[0,1],[2,3]],nodeHeights:[0,0,8,8],roadNodes:{lower:[0,1],upper:[2,3]}});
 const auto=new CityAutopilot(graph,collision,{surfaceHeight:()=>8,destinationHeight:()=>0});auto.start({id:'lower',name:'lower',arrival:[0,10]});
 const state={x:0,z:-10,yaw:0,speed:0,steer:0,distance:0};
 for(let i=0;i<20&&auto.status.phase!=='blocked';i++)auto.update(state,[],.05);
 assert.equal(auto.status.phase,'blocked');assert.equal(auto.status.reason,'no-road-route');assert.equal(state.distance,0);
});
