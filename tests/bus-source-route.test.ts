import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RoadGraph} from '../src/navigation.ts';
import type {Road} from '../src/city-types.ts';
import {buildBusRouteOnChain,type BusChainStop} from '../src/city-bus-route.ts';

function fixture(){
 const nodes:[number,number][]=[[0,0],[0,10],[10,10],[10,0],[20,0]];
 const road=(id:string,chain:number[],tags:Record<string,string>):Road=>({id,sourceId:'way/'+id,name:id,kind:'service',width:6,oneway:false,points:chain.map(i=>nodes[i]),nodeIds:chain.map(String),sourceWayPointOrder:'osm-forward',sourceAccessTags:{highway:'service',...tags}});
 const graph=new RoadGraph([road('line',[0,1,2,3,4],{access:'private',bus:'yes',oneway:'yes'}),road('shortcut',[0,3],{})],{nodes,nodeHeights:[4,4,4,4,4],edges:[[0,1],[1,2],[2,3],[3,4],[0,3]],roadNodes:{line:[0,1,2,3,4],shortcut:[0,3]}});
 const stops:BusChainStop[]=[0,4].map(i=>({id:'stop'+i,name:'站'+i,sourcePlatformId:'node/platform'+i,sourceStopId:'node/'+i,node:i,chainIndex:i,platform:{x:nodes[i][0]+2,z:nodes[i][1],height:4}}));
 return {graph,stops,chain:[0,1,2,3,4]};
}
test('scheduled bus retains the line detour while cars remain barred from the depot',()=>{
 const {graph,stops,chain}=fixture(),route=buildBusRouteOnChain(graph,'line','游戏班次',chain,stops);
 assert.deepEqual(route.edges.map(e=>[e.from,e.to]),[[0,1],[1,2],[2,3],[3,4]]);assert.equal(route.length,40);
 assert.equal(graph.canTraverse(0,1,'motorcar'),false);assert.equal(graph.canTraverse(0,1,'foot'),false);
 assert.equal(route.stops[1].distance,40);assert.equal(route.simulationDwellSeconds,12);
});
test('wrong direction and a geometric crossing with no source edge are rejected',()=>{
 const {graph,stops}=fixture();
 assert.throws(()=>buildBusRouteOnChain(graph,'x','x',[4,3,2,1,0],[{...stops[1],chainIndex:0},{...stops[0],chainIndex:4}]),/unpermitted/);
 assert.throws(()=>buildBusRouteOnChain(graph,'x','x',[0,2,4],[stops[0],{...stops[1],chainIndex:2}]),/missing/);
});
test('unbound platform height or a misordered stop never becomes a usable route',()=>{
 const {graph,stops,chain}=fixture();
 assert.throws(()=>buildBusRouteOnChain(graph,'x','x',chain,[stops[0],{...stops[1],platform:{...stops[1].platform,height:NaN}}]),/stop/);
 assert.throws(()=>buildBusRouteOnChain(graph,'x','x',chain,[stops[1],stops[0]]),/stop/);
 assert.throws(()=>buildBusRouteOnChain(graph,'x','x',chain,[stops[0],{...stops[1],chainIndex:2}]),/stop/);
 const route=buildBusRouteOnChain(graph,'x','x',chain,stops);stops[0].platform.x=900;assert.notEqual(route.stops[0].platform.x,900);
});
test('revisited junction is bound to its exact occurrence rather than the first matching node',()=>{
 const nodes:[number,number][]=[[0,0],[0,10],[10,10],[10,0]],chain=[0,1,2,3,0,1];
 const road={id:'loop',name:'loop',kind:'service',width:6,oneway:true,points:[...nodes,nodes[0]],sourceAccessTags:{highway:'service',oneway:'yes'},sourceWayPointOrder:'osm-forward'} as Road;
 const graph=new RoadGraph([road],{nodes,nodeHeights:[1,1,1,1],edges:[[0,1],[1,2],[2,3],[3,0]],roadNodes:{loop:[0,1,2,3,0]}});
 const stops:BusChainStop[]=[0,4,5].map((i,j)=>({id:'s'+j,name:'s'+j,node:chain[i],chainIndex:i,sourceStopId:'node/'+chain[i],sourcePlatformId:'node/p'+j,platform:{x:2,z:0,height:1}}));
 const route=buildBusRouteOnChain(graph,'loop','loop',chain,stops);assert.deepEqual(route.stops.map(s=>s.distance),[0,40,50]);
});
