import type {RoadGraph} from './navigation.ts';import {busRoutePose,type BusRoute} from './city-bus-route.ts';import type {LeisurePose} from './city-leisure.ts';
import type {BusEnvelope} from './city-bus-vehicle.ts';
export type BusEnvironment={
 geometry:BusEnvelope;
 /** Actual generated door, transformed by the supported body frame, with a safe outside capsule anchor. */
 boardingPoint:(pose:LeisurePose)=>LeisurePose|null;
 clear:(pose:LeisurePose)=>boolean;
 /** Distance to a stop line or preceding vehicle on the same physical level. */
 holdDistance:(pose:LeisurePose)=>number|null;
 platformClear:(pose:LeisurePose)=>boolean;
 walkingPath:(from:LeisurePose,to:LeisurePose)=>boolean;
};
/** Timetable is intentionally game time. No real-time arrival or fare claims. */
export class CityBus {
 distance=0;speed=0;clock=0;stopIndex=0;passenger=false;requestedExit=false;
 phase:'dwelling'|'driving'|'blocked'|'complete'='dwelling';private departAt:number;
 constructor(readonly graph:RoadGraph,readonly route:BusRoute,private env:BusEnvironment,firstDeparture=0){if(!Number.isFinite(firstDeparture)||firstDeparture<0)throw Error('Invalid bus departure');if(!Object.values(env.geometry).every(v=>Number.isFinite(v)&&v>0))throw Error('Bus model geometry is required');this.departAt=Math.max(firstDeparture,route.simulationDwellSeconds);}
 get pose(){return busRoutePose(this.graph,this.route,this.distance);}
 get currentStop(){return this.phase==='dwelling'||this.phase==='complete'?this.route.stops[this.stopIndex]:null;}
 get nextStop(){return this.route.stops[this.stopIndex+1]??null;}
 get departureIn(){return Math.max(0,this.departAt-this.clock);}
 get door(){return this.env.boardingPoint(this.pose);}
 board(walker:LeisurePose,walking:boolean,busy:boolean){
  const stop=this.currentStop;if(this.passenger||!walking||busy||!stop||this.phase!=='dwelling'||Math.abs(this.speed)>.05)return false;
  const p={...stop.platform,yaw:this.pose.yaw},door=this.door;if(!door||Math.hypot(walker.x-p.x,walker.z-p.z)>1.8||Math.abs(walker.height-p.height)>.5||Math.hypot(door.x-p.x,door.z-p.z)>4||Math.abs(door.height-p.height)>.65||!this.env.clear(this.pose)||!this.env.platformClear(p)||!this.env.platformClear(door)||!this.env.walkingPath(walker,p)||!this.env.walkingPath(p,door))return false;
  this.passenger=true;this.requestedExit=false;return true;
 }
 requestExit(){if(this.passenger)this.requestedExit=true;}
 disembark(){const stop=this.currentStop;if(!this.passenger||!stop||Math.abs(this.speed)>.05)return null;const p={...stop.platform,yaw:this.pose.yaw},door=this.door;if(!door||Math.hypot(door.x-p.x,door.z-p.z)>4||Math.abs(door.height-p.height)>.65||!this.env.clear(this.pose)||!this.env.platformClear(p)||!this.env.platformClear(door)||!this.env.walkingPath(door,p))return null;this.passenger=false;this.requestedExit=false;return p;}
 step(seconds:number,paused:boolean){
  if(paused||!Number.isFinite(seconds)||seconds<=0||this.phase==='complete')return;const dt=Math.min(.05,seconds);this.clock+=dt;
  if(this.phase==='dwelling'){if(this.clock<this.departAt||this.passenger&&this.requestedExit)return;this.phase='driving';}
  const next=this.nextStop;if(!next){this.speed=0;this.phase='complete';return;}
  const remaining=next.distance-this.distance,hold=this.env.holdDistance(this.pose),available=Math.max(0,Math.min(remaining,hold===null?Infinity:hold-this.env.geometry.frontExtent-1));
  const target=Math.min(8,Math.sqrt(2*1.8*available)),delta=target-this.speed;this.speed+=Math.sign(delta)*Math.min(Math.abs(delta),(delta>0?1:2.5)*dt);
  const move=Math.min(available,this.speed*dt),steps=Math.max(1,Math.ceil(move/.15));
  for(let i=0;i<steps;i++){
   const d=this.distance+move/steps,p=busRoutePose(this.graph,this.route,d),before=this.pose;
   // Full environment footprint checks at interpolated headings prevent an
   // abrupt source corner from rotating the bus through walls or traffic.
   const turn=Math.atan2(Math.sin(p.yaw-before.yaw),Math.cos(p.yaw-before.yaw)),n=Math.max(1,Math.ceil(Math.abs(turn)*this.env.geometry.turnRadius/.15));let clear=true;
   for(let j=1;j<=n;j++)if(!this.env.clear({...p,x:before.x+(p.x-before.x)*j/n,z:before.z+(p.z-before.z)*j/n,height:before.height+(p.height-before.height)*j/n,yaw:before.yaw+turn*j/n})){clear=false;break;}
   if(!clear){this.speed=0;this.phase='blocked';return;}this.distance=d;
  }
  this.phase='driving';if(next.distance-this.distance<.015&&this.speed<.3){this.distance=next.distance;this.speed=0;this.stopIndex++;this.phase=this.stopIndex===this.route.stops.length-1?'complete':'dwelling';this.departAt=this.clock+this.route.simulationDwellSeconds;}
 }
}
