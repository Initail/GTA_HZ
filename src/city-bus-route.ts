import type {RoadGraph} from './navigation.ts';import type {V2} from './city-types.ts';
export type BusStopAnchor={id:string;name:string;platform:{x:number;z:number;height:number};node:number;sourcePlatformId:string;sourceStopId:string};
export type BusRouteEdge={from:number;to:number;start:number;length:number};
export type BusRoute={id:string;name:string;edges:BusRouteEdge[];length:number;stops:(BusStopAnchor&{distance:number})[];simulationHeadwaySeconds:number;simulationDwellSeconds:number};
export type BusChainStop=BusStopAnchor&{chainIndex:number};
/** Keep a transit relation's ordered source chain, including repeated junctions.
 * A shortest path between stops can silently skip the line's intermediate roads.
 * Platform heights must already be physically resolved by the service loader.
 */
export function buildBusRouteOnChain(graph:RoadGraph,id:string,name:string,chain:readonly number[],stops:readonly BusChainStop[],headway=120,dwell=12):BusRoute{
 if(!graph.nodeHeights||stops.length<2||chain.length<2||!Number.isFinite(headway+dwell)||dwell<3||headway<dwell)throw Error('Bus source chain needs prepared levels, stops and simulated timetable');
 for(let i=0;i<stops.length;i++){
  const s=stops[i];
  if(!Number.isInteger(s.chainIndex)||s.chainIndex<0||s.chainIndex>=chain.length||chain[s.chainIndex]!==s.node||!graph.nodes[s.node]||!s.sourceStopId||!s.sourcePlatformId||![s.platform.x,s.platform.z,s.platform.height].every(Number.isFinite)||i>0&&s.chainIndex<=stops[i-1].chainIndex)throw Error('Bus stop is not bound to an ordered source-chain occurrence');
 }
 const start=stops[0].chainIndex,end=stops.at(-1)!.chainIndex,edges:BusRouteEdge[]=[],distances=new Map([[start,0]]);let length=0;
 for(let i=start;i<end;i++){
  const from=chain[i],to=chain[i+1],distance=graph.edges[from]?.get(to);
  if(!Number.isInteger(from)||!Number.isInteger(to)||distance===undefined||!Number.isFinite(distance)||distance<=0||graph.allowsDirection(from,to,'bus')!==true)throw Error('Bus source chain contains a missing or unpermitted directed edge');
  edges.push({from,to,start:length,length:distance});length+=distance;distances.set(i+1,length);
 }
 return {id,name,edges,length,stops:stops.map(({chainIndex,...stop})=>({...stop,platform:{...stop.platform},distance:distances.get(chainIndex)!})),simulationHeadwaySeconds:headway,simulationDwellSeconds:dwell};
}
/** Prepared source-node graph only. Crossing lines never create a transfer. */
export function buildBusRoute(graph:RoadGraph,id:string,name:string,stops:BusStopAnchor[],headway=120,dwell=12):BusRoute{
 if(!graph.nodeHeights||stops.length<2||!Number.isFinite(headway+dwell)||headway<dwell||dwell<3)throw Error('Bus route needs prepared levels, stops and an explicit simulated timetable');
 for(const s of stops)if(!graph.nodes[s.node]||!s.sourcePlatformId||!s.sourceStopId||![s.platform.x,s.platform.z,s.platform.height].every(Number.isFinite))throw Error('Bus stop lacks independently bound platform and road source node');
 const edges:BusRouteEdge[]=[],bound:BusRoute['stops']=[{...stops[0],distance:0}];let length=0;
 for(let leg=1;leg<stops.length;leg++){
  const start=stops[leg-1].node,end=stops[leg].node,dist=new Map<number,number>([[start,0]]),prev=new Map<number,number>(),queue:[number,number][]=[[0,start]];
  // Small binary heap; each search is limited to this source graph, never a
  // proximity-generated shortcut across lake, courtyard or stacked road.
  const push=(item:[number,number])=>{let i=queue.length;queue.push(item);while(i){const p=(i-1)>>1;if(queue[p][0]<=item[0])break;queue[i]=queue[p];i=p;}queue[i]=item;};
  const pop=()=>{const first=queue[0],last=queue.pop()!;if(queue.length){let i=0;while(i*2+1<queue.length){let c=i*2+1;if(c+1<queue.length&&queue[c+1][0]<queue[c][0])c++;if(queue[c][0]>=last[0])break;queue[i]=queue[c];i=c;}queue[i]=last;}return first;};
  while(queue.length){const [d,n]=pop();if(dist.get(n)!==d)continue;if(n===end)break;for(const [next,cost] of graph.edges[n])if(graph.canTraverse(n,next,'bus')&&d+cost<(dist.get(next)??Infinity)){dist.set(next,d+cost);prev.set(next,n);push([d+cost,next]);}}
  if(!dist.has(end)||start===end)throw Error('Bus stops have no distinct permitted source-node route: '+stops[leg].id);
  const chain=[end];while(chain[chain.length-1]!==start){const n=prev.get(chain[chain.length-1]);if(n===undefined)throw Error('Incomplete source bus route');chain.push(n);}chain.reverse();
  for(let i=1;i<chain.length;i++){const from=chain[i-1],to=chain[i],d=graph.edges[from].get(to)!;if(!Number.isFinite(d)||d<=0)throw Error('Invalid bus edge');edges.push({from,to,start:length,length:d});length+=d;}
  bound.push({...stops[leg],distance:length});
 }
 return {id,name,edges,length,stops:bound,simulationHeadwaySeconds:headway,simulationDwellSeconds:dwell};
}
export function busRoutePose(graph:RoadGraph,route:BusRoute,distance:number){
 const d=Math.max(0,Math.min(route.length,distance)),edge=route.edges.find(e=>d<e.start+e.length)??route.edges.at(-1)!;
 const a=graph.nodes[edge.from],b=graph.nodes[edge.to],t=Math.max(0,Math.min(1,(d-edge.start)/edge.length)),point:V2=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
 return {x:point[0],z:point[1],height:graph.surfaceHeightOnEdge(edge.from,edge.to,t,0,point,'bus'),yaw:Math.atan2(b[0]-a[0],b[1]-a[1]),sourceEdge:[edge.from,edge.to] as [number,number]};
}
