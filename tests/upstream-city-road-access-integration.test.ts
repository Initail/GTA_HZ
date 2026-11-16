import test from 'node:test';import assert from 'node:assert/strict';
import {RoadGraph} from '../src/navigation.ts';import {CityAutopilot} from '../src/city-autopilot.ts';
import {CityCollision} from '../src/driving.ts';import {MapRoadIndex} from '../src/city-map-geometry.ts';
import type {Road,CityData,V2} from '../src/city-types.ts';
const road=(id:string,points:V2[],tags:Record<string,string>={}):Road=>({id,points,heights:points.map(()=>0),grade:'0',name:id,kind:'unclassified',width:6,oneway:false,sourceAccessTags:{highway:'unclassified',...tags},sourceWayPointOrder:'osm-forward'});
const city=(roads:Road[]):CityData=>({meta:{cityId:'hangzhou',counts:{},extent:[-200,-200,200,200],horizontalScale:.6},land:[[[[-200,-200],[200,-200],[200,200],[-200,200]]]],coast:[],roads,buildings:[],water:[],green:[],landmarks:[],spawn:{x:0,z:0,yaw:0,road:''}});
test('Bai motorcar=no preserves physical road and walking while motor traffic routes around it',()=>{
 const nodes:V2[]=[[0,0],[100,0],[0,100],[100,100]];
 const roads=[road('way/4326974#0',[nodes[0],nodes[1]],{motorcar:'no'}),road('west',[nodes[0],nodes[2]]),road('north',[nodes[2],nodes[3]]),road('east',[nodes[3],nodes[1]])];
 const graph=new RoadGraph(roads,{nodes,edges:[[0,1],[0,2],[2,3],[3,1]],roadNodes:{'way/4326974#0':[0,1],west:[0,2],north:[2,3],east:[3,1]}});
 assert.equal(graph.edges[0].has(1),true,'source physical edge remains');
 assert.equal(graph.canTraverse(0,1),false);assert.equal(graph.canTraverse(0,1,'foot'),true);assert.equal(graph.canTraverse(0,1,'bicycle'),true);
 assert.equal(graph.route([0,10],[100,10]).some(p=>p[1]===100),true);
 const auto=new CityAutopilot(graph,new CityCollision(city(roads)));
 const search=(auto as unknown as {findRoute(a:V2,b:V2):Generator<void,V2[],void>}).findRoute([0,10],[100,10]);let next=search.next();while(!next.done)next=search.next();
 assert(next.value.some(p=>p[1]===100));
 const collision=new CityCollision(city(roads));assert.equal(collision.blocked(50,0,0),true);assert.equal(collision.blocked(50,0,0,1.6,false,'foot'),false);
 assert.equal(collision.nearest(50,0,0)?.road.id,'way/4326974#0');assert.notEqual(collision.nearest(50,0,0,'motorcar')?.road.id,'way/4326974#0');
 assert.notEqual(new MapRoadIndex(roads).nearest([50,0])?.road.id,'way/4326974#0');
});
test('a public intersecting street remains accessible beside a restricted entrance, with deck separation',()=>{
 const restricted=road('permit',[[0,-100],[0,100]],{access:'permit'}),publicRoad=road('public',[[-100,0],[100,0]]);
 assert.equal(new CityCollision(city([restricted,publicRoad])).blocked(0,0,0),false);
 assert.equal(new CityCollision(city([restricted,publicRoad])).blocked(0,20,0),true);
 publicRoad.heights=[8,8];const collision=new CityCollision(city([restricted,publicRoad]));
 assert.equal(collision.blocked(0,0,0),true);assert.equal(collision.blocked(0,0,8),false);
});
test('source direction and permission must come from the same owner; bicycle exceptions retain source order',()=>{
 const nodes:V2[]=[[0,0],[100,0]],a=road('a',nodes,{access:'private',oneway:'no'}),b=road('b',nodes,{oneway:'-1','oneway:bicycle':'no'});b.oneway=true;b.sourceWayPointOrder='osm-reversed';
 const graph=new RoadGraph([a,b],{nodes,edges:[[0,1]],roadNodes:{a:[0,1],b:[0,1]}});
 assert.equal(graph.canTraverse(0,1),true);assert.equal(graph.canTraverse(1,0),false);
 assert.equal(graph.canTraverse(0,1,'bicycle'),true);assert.equal(graph.canTraverse(1,0,'bicycle'),true);
});
test('a fully restricted graph returns no route rather than manufacturing a start connector',()=>{
 const nodes:V2[]=[[0,0],[100,0]],r=road('closed',nodes,{access:'private'});
 const graph=new RoadGraph([r],{nodes,edges:[[0,1]],roadNodes:{closed:[0,1]}});
 assert.deepEqual(graph.route([10,0],[90,0]),[]);assert.equal(graph.canTraverseSegment(0,1,0,0),false);
});
