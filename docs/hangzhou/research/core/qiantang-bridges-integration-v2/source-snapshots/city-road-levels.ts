import {closest} from './driving.ts';
import type {V2} from './city-types.ts';

export type RoadLevel={id:string;points:V2[];heights:number[];width:number;tier:number;nodeIds:(string|number)[];surfaceGroup?:string;sourceDeclaredTier?:number};
export type RoadHeightHint={height:number;roadId?:string;groundOnly?:boolean};
type Segment={road:RoadLevel;a:V2;b:V2;ya:number;yb:number;na:string;nb:string};

/** Separate stacked surfaces by source identity and the actor's previous height.
 * Caller owns one hint per actor. A global player hint must never move NPCs.
 * Meshes and physical QA are required alongside this runtime sampler.
 */
export class CityRoadLevels {
 private cells=new Map<string,Segment[]>();private size=100;
 private byId=new Map<string,RoadLevel>();
 private sourceNodes=new Map<string,Set<string>>();
 constructor(roads:RoadLevel[],private terrain:(x:number,z:number)=>number,private terrainTransitionGame=20,private groundModifier?:(x:number,z:number,height:number)=>number,private sourceModifier?:(roadId:string,x:number,z:number)=>number|undefined){
  if(!Number.isFinite(terrainTransitionGame)||terrainTransitionGame<=0)throw new Error('Invalid road terrain transition');
  for(const road of roads){
   if(this.byId.has(road.id))throw new Error('Duplicate road surface '+road.id);this.byId.set(road.id,road);
   this.sourceNodes.set(road.id,new Set(road.nodeIds.map(String)));
   if(road.points.length!==road.heights.length||road.points.length!==road.nodeIds.length||!Number.isFinite(road.width+road.tier)||road.width<=0||road.heights.some(h=>!Number.isFinite(h)))throw new Error('Invalid road surface '+road.id);
   for(let i=1;i<road.points.length;i++){
    const a=road.points[i-1],b=road.points[i],segment={road,a,b,ya:road.heights[i-1],yb:road.heights[i],na:String(road.nodeIds[i-1]),nb:String(road.nodeIds[i])},margin=road.width/2+terrainTransitionGame;
    if(!Number.isFinite(a[0]+a[1]+b[0]+b[1]))throw new Error('Invalid road coordinate');
    for(let x=Math.floor((Math.min(a[0],b[0])-margin)/this.size);x<=Math.floor((Math.max(a[0],b[0])+margin)/this.size);x++)for(let z=Math.floor((Math.min(a[1],b[1])-margin)/this.size);z<=Math.floor((Math.max(a[1],b[1])+margin)/this.size);z++){
     const key=x+','+z,cell=this.cells.get(key)??[];cell.push(segment);this.cells.set(key,cell);
    }
   }
  }
 }
 /** Ground actors follow the same continuous earthworks as the ground mesh.
  * Elevated/tunnel actors retain their source edge, even above another road. */
 heightForSourceRoad(roadId:string,x:number,z:number,sourceHeight:number){
  const road=this.byId.get(roadId);if(!road)throw new Error('Unknown road surface '+roadId);
  if(!Number.isFinite(x+z+sourceHeight))throw new Error('Invalid source road height');
  return this.sourceModifier?.(roadId,x,z)??(road.tier===0?this.groundAt(x,z):sourceHeight);
 }
 /** Revalidate a prepared arrival by source identity; never switch layers by XY proximity. */
 sourceArrival(roadId:string,x:number,z:number){
  const road=this.byId.get(roadId);if(!road||road.tier<0||!Number.isFinite(x+z))return null;
  let best:{height:number;roadId:string;tier:number;distance:number}|null=null;
  for(let i=1;i<road.points.length;i++){
   const p=closest(x,z,road.points[i-1],road.points[i]);
   if(p.d>road.width/2-.35||best&&p.d>=best.distance)continue;
   const h=road.heights[i-1]+(road.heights[i]-road.heights[i-1])*p.t;
   best={height:this.heightForSourceRoad(road.id,x,z,h),roadId:road.id,tier:road.tier,distance:p.d};
  }
  return best;
 }
 /** Earth surface below elevated decks. Props and terrain never rise to a
  * bridge simply because it is the only road above the queried x/z. */
 groundAt(x:number,z:number){
  if(!Number.isFinite(x+z))throw new Error('Invalid ground query');
  let weightedHeight=0,totalWeight=0,influence=0;
  for(const segment of this.cells.get(Math.floor(x/this.size)+','+Math.floor(z/this.size))??[]){
   if(segment.road.tier!==0)continue;
   const q=closest(x,z,segment.a,segment.b);
   if(q.d>=segment.road.width/2+this.terrainTransitionGame)continue;
   const dx=segment.b[0]-segment.a[0],dz=segment.b[1]-segment.a[1],t=((q.x-segment.a[0])*dx+(q.z-segment.a[1])*dz)/(dx*dx+dz*dz||1);
   const edge=Math.max(0,Math.min(1,(q.d-segment.road.width/2)/this.terrainTransitionGame));
   const weight=1-edge*edge*(3-2*edge);
   weightedHeight+=(segment.ya+(segment.yb-segment.ya)*t)*weight;
   totalWeight+=weight;influence=Math.max(influence,weight);
  }
  // Every segment enters and leaves with zero weight. Selecting only the
  // nearest segment made its Voronoi borders jump between unrelated floors.
  // Ground earthworks blend; an actor's source-selected deck remains separate.
  const base=this.terrain(x,z);
  const ground=totalWeight>0?base+(weightedHeight/totalWeight-base)*influence:base;
  return this.groundModifier?this.groundModifier(x,z,ground):ground;
 }
 sample(x:number,z:number,hint?:RoadHeightHint){
  if(!Number.isFinite(x+z)||hint&&!Number.isFinite(hint.height))throw new Error('Invalid surface query');
  const candidates=[];
  const previous=hint?.roadId?this.byId.get(hint.roadId):undefined;
  const previousNodes=previous?this.sourceNodes.get(previous.id):undefined;
  let ground:number|undefined;
  for(const segment of this.cells.get(Math.floor(x/this.size)+','+Math.floor(z/this.size))??[]){
   const q=closest(x,z,segment.a,segment.b);
   const dx=segment.b[0]-segment.a[0],dz=segment.b[1]-segment.a[1],t=((q.x-segment.a[0])*dx+(q.z-segment.a[1])*dz)/(dx*dx+dz*dz||1);
   const sourceHeight=segment.ya+(segment.yb-segment.ya)*t;
   if(q.d>segment.road.width/2+.65)continue;
   if(!hint&&segment.road.tier<0)continue;
   if(hint?.groundOnly&&segment.road.tier!==0)continue;
   // A nearby overpass is not an exit. Change elevated/tunnel source only at
   // a local shared OSM node; ordinary ground remains freely traversable.
   let localConnection=false;
   if(previous&&previous.id!==segment.road.id){
    const reach=(previous.width+segment.road.width)/2+.65;
    localConnection=(previousNodes!.has(segment.na)&&Math.hypot(x-segment.a[0],z-segment.a[1])<=reach)||
       (previousNodes!.has(segment.nb)&&Math.hypot(x-segment.b[0],z-segment.b[1])<=reach);
    if((previous.tier!==0||segment.road.tier!==0)&&!localConnection)continue;
   }
   const height=this.sourceModifier?.(segment.road.id,x,z)??(segment.road.tier===0?(ground??=this.groundAt(x,z)):sourceHeight);
   const score=hint?Math.abs(height-hint.height)*10+q.d*.05-(hint.roadId===segment.road.id ? .01:0):height+q.d*.001;
   const sameGroup=!!previous?.surfaceGroup&&previous.surfaceGroup===segment.road.surfaceGroup;
   const interior=q.t>0&&q.t<1;
   // A clamped old endpoint is not an extension of its deck. At a shared
   // local source node follow the connected segment as soon as it owns the
   // actor, avoiding an accumulated height jump at the end of the road cap.
   candidates.push({height,roadId:segment.road.id,tier:segment.road.tier,distance:q.d,score,groupInterior:(sameGroup||localConnection)&&interior,previousPriority:segment.road.id===previous?.id&&interior});
  }
  candidates.sort((a,b)=>Number(b.previousPriority)-Number(a.previousPriority)||Number(b.groupInterior)-Number(a.groupInterior)||a.score-b.score||a.roadId.localeCompare(b.roadId));
  const best=candidates[0];if(best)return {height:best.height,roadId:best.roadId,tier:best.tier,distance:best.distance};
  return {height:this.groundAt(x,z),roadId:null,tier:null,distance:Infinity};
 }
}
