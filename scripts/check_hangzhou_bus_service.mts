/** Replay the complete ordered service through the current prepared RoadGraph. */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,relative} from 'node:path';
import {RoadGraph} from '../artifacts/cities/hangzhou/city-leisure-v15/src/navigation.ts';
import {buildBusRouteOnChain,busRoutePose} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-bus-route.ts';
import {CityBus} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-bus.ts';
import {busEnvelope} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-bus-vehicle.ts';
const root=resolve(import.meta.dirname,'..'),folder=resolve(root,process.argv[2]),target=resolve(folder,'graph-runtime-check.json');
if(!folder.startsWith(resolve(root,'artifacts/cities/hangzhou')+'/')||existsSync(target))throw Error('Use an existing candidate with a fresh report');
const hashes:Record<string,string>={};
function read(p:string){const path=resolve(root,p),b=readFileSync(path);hashes[relative(root,path)]=createHash('sha256').update(b).digest('hex');return JSON.parse(b.toString());}
const catalog=read(resolve(folder,'source-service-catalog.json')),input=read('artifacts/cities/hangzhou/bus-route-7-v1/prepared-inputs-v1.json');
for(const [p,hash] of Object.entries(catalog.inputs))assert.equal(createHash('sha256').update(readFileSync(resolve(root,p))).digest('hex'),hash,p);
const depot=read('artifacts/cities/hangzhou/bus-depot-way-v1/source-v1/candidate.json'),noded=read('artifacts/cities/hangzhou/bus-depot-way-v1/source-v1/graph-candidate.json');
const model=read('artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4/generated-bus-mesh-v4.json');
assert.equal(noded.nodes.length,input.graph.nodes.length+2);assert.deepEqual(noded.nodes.slice(0,input.graph.nodes.length),input.graph.nodes);
const indices=new Map<string,number>(noded.sourceNodeIds.map((id:string,i:number)=>['node/'+id,i]));
const graph=new RoadGraph([...input.roads,depot.road],noded),routes=[];
for(const source of catalog.routes){
 assert.equal(source.selectionAccepted,true);const chain=source.chain.nodes.map((id:string)=>{const i=indices.get(id);assert.notEqual(i,undefined,id);return i!;});
 for(let i=0;i<chain.length;i++)assert.ok(Math.hypot(graph.nodes[chain[i]][0]-source.pointsGame[i][0],graph.nodes[chain[i]][1]-source.pointsGame[i][1])<1e-7,'same source projection');
 const stops=source.stops.map((s:any)=>({id:s.sourcePlatformId,name:s.name,sourcePlatformId:s.sourcePlatformId,sourceStopId:s.selection.sourceStopId,node:chain[s.selection.chainIndex],chainIndex:s.selection.chainIndex,
  // Routing fixture only. The published source catalog retains platformHeight=null.
  platform:{x:s.platformGame[0],z:s.platformGame[1],height:noded.nodeHeights[chain[s.selection.chainIndex]]}}));
 const route=buildBusRouteOnChain(graph,source.id,source.name,chain,stops);
 assert.deepEqual(route.edges.map(e=>['node/'+noded.sourceNodeIds[e.from],'node/'+noded.sourceNodeIds[e.to]]),source.chain.edges.slice(stops[0].chainIndex,stops.at(-1).chainIndex).map((e:any)=>[e.from,e.to]));
 let samples=0;for(const edge of route.edges)for(const t of [0,.5,1]){const p=busRoutePose(graph,route,Math.min(route.length,edge.start+edge.length*t));assert.ok([p.x,p.z,p.yaw,p.height].every(Number.isFinite));samples++;}
 const bus=new CityBus(graph,route,{geometry:busEnvelope(model),boardingPoint:()=>null,clear:()=>false,holdDistance:()=>0,platformClear:()=>false,walkingPath:()=>false});
 assert.equal(bus.board({...stops[0].platform,yaw:0},true,false),false);assert.equal(bus.passenger,false);
 routes.push({id:source.id,stops:route.stops.length,edges:route.edges.length,lengthGame:route.length,sourceEdgeSamples:samples,allSourceEdgesPreserved:true,boardingWithoutPhysicalApproval:false});
}
const depotChain=noded.roadNodes[depot.road.id];for(let i=1;i<depotChain.length;i++){const a=depotChain[i-1],b=depotChain[i];assert.equal(graph.canTraverse(a,b,'bus'),true);assert.equal(graph.canTraverse(b,a,'bus'),false);assert.equal(graph.canTraverse(a,b,'motorcar'),false);assert.equal(graph.canTraverse(a,b,'foot'),false);}
writeFileSync(target,JSON.stringify({status:'pass',scope:'source graph replay only; provisional road heights and fixture platform heights are not physical acceptance',inputs:hashes,routes,depotPublicCarAndFootDenied:true,platformHeightsAccepted:false,mainWorldInstalled:false,browserAccepted:false},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({routes:routes.length,stops:routes.reduce((n,r)=>n+r.stops,0),edges:routes.reduce((n,r)=>n+r.edges,0),sourceEdgeSamples:routes.reduce((n,r)=>n+r.sourceEdgeSamples,0),physicalAccepted:false}));
