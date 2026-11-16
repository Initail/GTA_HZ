import type {Road,V2} from './city-types.ts';
import {roadAllows,roadDirections,type TravelMode} from './road-access.ts';
export type NodedRoadGraph={nodes:V2[];edges:number[][];nodeHeights?:number[];roadNodes?:Record<string,number[]>};
export class RoadGraph{
 nodeHeights:number[]|null=null;
 private sourceDirections:Map<string,boolean>|null=null;
 private traversalOwners=new Map<TravelMode,Map<string,string>>();
 private edgeRoads=new Map<string,string>();
 private sourceSurface:((roadId:string,x:number,z:number,sourceHeight:number)=>number)|null=null;
 nodes:V2[]=[];edges:Map<number,number>[]=[];lookup=new Map<string,number>();
 constructor(roads:Road[],noded?:NodedRoadGraph){if(noded){this.nodes=noded.nodes;if(noded.nodeHeights){if(noded.nodeHeights.length!==this.nodes.length||noded.nodeHeights.some(h=>!Number.isFinite(h)))throw new Error('Invalid source road node heights');this.nodeHeights=noded.nodeHeights;}this.edges=this.nodes.map(()=>new Map());for(const [a,b] of noded.edges){const p=this.nodes[a],q=this.nodes[b],d=Math.hypot(p[0]-q[0],p[1]-q[1]);this.edges[a].set(b,d);this.edges[b].set(a,d);}if(noded.roadNodes){
   this.sourceDirections=new Map();
   const modes:TravelMode[]=['motorcar','foot','bicycle','bus'];for(const mode of modes)this.traversalOwners.set(mode,new Map());
   for(const road of roads){
    const chain:number[]|undefined=noded.roadNodes[road.id];if(!chain)throw new Error('Missing source road chain '+road.id);
    if(road.sourceAccessTags&&!road.sourceWayPointOrder)throw Error('Missing source road point order '+road.id);
    const decisions=modes.map(mode=>({mode,allowed:roadAllows(road,mode).allowed,
      direction:road.sourceAccessTags?roadDirections(road,mode,road.sourceWayPointOrder!):{forward:true,backward:!road.oneway}}));
    for(let i=1;i<chain.length;i++){
     const a=chain[i-1],b=chain[i];if(a===b)continue;if(!this.edges[a]?.has(b))throw new Error('Source road chain is not a graph edge');
     this.edgeRoads.set(a+','+b,road.id);this.edgeRoads.set(b+','+a,road.id);
     for(const {mode,allowed,direction} of decisions){const owners=this.traversalOwners.get(mode)!;
      for(const [key,enabled] of [[a+','+b,direction.forward],[b+','+a,direction.backward]] as const)if(allowed&&enabled===true&&!owners.has(key))owners.set(key,road.id);
     }
     for(const key of [a+','+b,b+','+a])this.sourceDirections.set(key,this.traversalOwners.get('motorcar')!.has(key));
    }
   }
  }return;}for(const r of roads){let prev=-1;for(const p of r.points){const key=Math.round(p[0]/3)+','+Math.round(p[1]/3);let id=this.lookup.get(key);if(id===undefined){id=this.nodes.length;this.lookup.set(key,id);this.nodes.push(p);this.edges.push(new Map());}if(prev>=0&&prev!==id){const a=this.nodes[prev],b=this.nodes[id],d=Math.hypot(a[0]-b[0],a[1]-b[1]);this.edges[prev].set(id,d);this.edges[id].set(prev,d);}prev=id;}}}
 /** OSM chain direction is available for prepared Hangzhou graphs. */
 allowsDirection(from:number,to:number,mode:TravelMode='motorcar'){return this.sourceDirections?this.traversalOwners.get(mode)!.has(from+','+to):undefined;}
 /** Prepared directions are authoritative; legacy graphs without them remain bidirectional. */
 canTraverse(from:number,to:number,mode:TravelMode='motorcar'){return this.edges[from]?.has(to)===true&&this.allowsDirection(from,to,mode)!==false;}
 canUseEdge(a:number,b:number,mode:TravelMode='motorcar'){return this.canTraverse(a,b,mode)||this.canTraverse(b,a,mode);}
 /** Fractions use the same a -> b orientation as nearestEdge; a zero-length connector needs no travel. */
 canTraverseSegment(a:number,b:number,fromT:number,toT:number){return this.canUseEdge(a,b)&&(Math.abs(toT-fromT)<=1e-9||this.canTraverse(fromT<toT?a:b,fromT<toT?b:a));}
 /** NPCs already know their source edge: do not choose a deck by x/z alone. */
 heightOnEdge(from:number,to:number,t:number,fallback:number){if(!this.nodeHeights)return fallback;if(!Number.isFinite(t)||!this.edges[from]?.has(to))throw new Error('Invalid source height edge');return this.nodeHeights[from]+(this.nodeHeights[to]-this.nodeHeights[from])*Math.max(0,Math.min(1,t));}
 bindSourceSurfaceHeight(sample:(roadId:string,x:number,z:number,sourceHeight:number)=>number){if(!this.nodeHeights||!this.sourceDirections)throw new Error('Source surface binding needs prepared node identities');this.sourceSurface=sample;}
 /** Rendered actor surface; graph routing still uses its source heights. */
 surfaceHeightOnEdge(from:number,to:number,t:number,fallback:number,position:V2,mode:TravelMode='motorcar'){
  const height=this.heightOnEdge(from,to,t,fallback);if(!this.sourceSurface)return height;
  const id=this.traversalOwners.get(mode)?.get(from+','+to)??this.edgeRoads.get(from+','+to);if(!id)throw new Error('Unbound source surface edge');
  return this.sourceSurface(id,position[0],position[1],height);
 }
 nearest(p:V2){let best=0,d=Infinity;for(let i=0;i<this.nodes.length;i++){const q=this.nodes[i],n=(p[0]-q[0])**2+(p[1]-q[1])**2;if(n<d){d=n;best=i;}}return best;}
 nearestEdge(p:V2){let best={a:0,b:0,point:this.nodes[0],t:0,d:Infinity,length:0};for(let i=0;i<this.nodes.length;i++){const a=this.nodes[i];for(const [j,length] of this.edges[i]){if(j<=i||!this.canUseEdge(i,j))continue;const b=this.nodes[j],dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(length*length||1))),point:V2=[a[0]+dx*t,a[1]+dz*t],d=Math.hypot(p[0]-point[0],p[1]-point[1]);if(d<best.d)best={a:i,b:j,point,t,d,length};}}return best;}
 route(a:V2,b:V2):V2[]{
  const start=this.nearestEdge(a),end=this.nearestEdge(b);if(!Number.isFinite(start.d)||!Number.isFinite(end.d))return [];
  const dense=(points:V2[])=>{const result:V2[]=[];for(const p of points){if(!result.length){result.push(p);continue;}const q=result.at(-1)!,d=Math.hypot(q[0]-p[0],q[1]-p[1]);if(d<.08)continue;const steps=Math.ceil(d/20);for(let k=1;k<=steps;k++)result.push([q[0]+(p[0]-q[0])*k/steps,q[1]+(p[1]-q[1])*k/steps]);}return result;};
  if(start.a===end.a&&start.b===end.b&&this.canTraverseSegment(start.a,start.b,start.t,end.t))return dense([a,start.point,end.point,b]);
  const dist=new Float64Array(this.nodes.length).fill(Infinity),parent=new Int32Array(this.nodes.length).fill(-1);
  const heap:[number,number][]=[];const push=(item:[number,number])=>{let i=heap.length;heap.push(item);while(i>0){const p=(i-1)>>1;if(heap[p][0]<=item[0])break;heap[i]=heap[p];i=p;}heap[i]=item;};
  const pop=()=>{const result=heap[0],last=heap.pop()!;if(heap.length){let i=0;while(i*2+1<heap.length){let c=i*2+1;if(c+1<heap.length&&heap[c+1][0]<heap[c][0])c++;if(heap[c][0]>=last[0])break;heap[i]=heap[c];i=c;}heap[i]=last;}return result;};
  for(const [id,d,t] of [[start.a,start.t*start.length,0],[start.b,(1-start.t)*start.length,1]])if(this.canTraverseSegment(start.a,start.b,start.t,t)){dist[id]=d;push([d,id]);}
  while(heap.length){const [d,id]=pop();if(d!==dist[id])continue;for(const [next,len] of this.edges[id])if(this.canTraverse(id,next)&&d+len<dist[next]){dist[next]=d+len;parent[next]=id;push([dist[next],next]);}}
  const costA=this.canTraverseSegment(end.a,end.b,0,end.t)?dist[end.a]+end.t*end.length:Infinity,costB=this.canTraverseSegment(end.a,end.b,1,end.t)?dist[end.b]+(1-end.t)*end.length:Infinity;const last=costA<=costB?end.a:end.b;if(!Number.isFinite(Math.min(costA,costB)))return [];
  const route:V2[]=[];for(let v=last;v>=0;v=parent[v])route.push(this.nodes[v]);return dense([a,start.point,...route.reverse(),end.point,b]);
 }
}
