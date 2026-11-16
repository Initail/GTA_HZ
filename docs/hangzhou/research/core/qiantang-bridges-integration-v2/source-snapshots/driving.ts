import type {CityData,CityBuilding,V2,Road} from './city-types.ts';
export type CarState={x:number;z:number;yaw:number;speed:number;steer:number;distance:number};
export const clamp=(n:number,a:number,b:number)=>Math.max(a,Math.min(b,n));
/** Keyboard driving gets a gentler speed-dependent wheel command; autopilot keeps its calibrated controls. */
export function manualSteeringInput(direction:number,speed:number){return clamp(direction,-1,1)*(.76-.22*Math.min(1,Math.abs(speed)/26));}
export function stepCar(s:CarState,input:{throttle:number;steer:number;handbrake:boolean},dt:number,grip=1){
 dt=clamp(dt,0,.05);const v=s.speed,desired=input.steer*.48/(1+Math.abs(v)*.026);s.steer+=(desired-s.steer)*Math.min(1,dt*7);
 let force=input.throttle>=0?input.throttle*9: v>1?input.throttle*18:input.throttle*5;
 if(input.throttle>0&&v<-.5)force=18;
 force-=v*.038+v*Math.abs(v)*.0022;
 if(input.throttle===0)force-=Math.sign(v)*Math.min(Math.abs(v)/Math.max(.001,dt),.8);
 if(input.handbrake)force-=Math.sign(v)*Math.min(Math.abs(v)/Math.max(.001,dt),10);
 s.speed=clamp(v+force*dt,-10,53*grip);
 s.yaw+=s.speed/3.2*Math.tan(s.steer)*dt*(input.handbrake?1.3:1);
 const moved=s.speed*dt;s.x+=Math.sin(s.yaw)*moved;s.z+=Math.cos(s.yaw)*moved;s.distance+=Math.abs(moved);
}
export function closest(x:number,z:number,a:V2,b:V2){const dx=b[0]-a[0],dz=b[1]-a[1];const t=clamp(((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1),0,1);const px=a[0]+dx*t,pz=a[1]+dz*t;return {x:px,z:pz,d:Math.hypot(x-px,z-pz),t};}
export function inRing(x:number,z:number,ring:V2[]){let yes=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;}
type Segment={a:V2;b:V2;road:Road;ya?:number;yb?:number};
export class CityCollision{
 cells=new Map<string,Segment[]>();bCells=new Map<string,CityBuilding[]>();size=90;
 private effectiveWater?:V2[][][];
 private roadBarrierCells=new Map<string,CityBuilding[]>();
 constructor(public data:CityData,private sourceSurfaceHeight?:(roadId:string,x:number,z:number,sourceHeight:number)=>number){
  if(data.meta.cityId==='hangzhou')this.effectiveWater=data.water.filter(w=>w.renderSurface!==false).flatMap(w=>w.renderRings??[w.rings]);
  for(const road of data.roads)if(road.heights&&(road.heights.length!==road.points.length||road.heights.some(h=>!Number.isFinite(h))))throw new Error('Invalid road collision heights '+road.id);
  for(const b of data.buildings)if((b.minY===undefined)!==(b.maxY===undefined)||b.minY!==undefined&&b.maxY!==undefined&&(!Number.isFinite(b.minY+b.maxY)||b.maxY<=b.minY))throw new Error('Invalid building collision height range');
  for(const road of data.roads)for(let i=1;i<road.points.length;i++){
   const a=road.points[i-1],b=road.points[i];const seg={a,b,road,ya:road.heights?.[i-1],yb:road.heights?.[i]};
   for(let x=Math.floor(Math.min(a[0],b[0])/this.size)-1;x<=Math.floor(Math.max(a[0],b[0])/this.size)+1;x++)for(let z=Math.floor(Math.min(a[1],b[1])/this.size)-1;z<=Math.floor(Math.max(a[1],b[1])/this.size)+1;z++){const key=x+','+z;const q=this.cells.get(key)??[];q.push(seg);this.cells.set(key,q);}
  }
  for(const b of data.buildings){const ring=b.rings[0];if(!ring?.length)continue;const xs=ring.map(p=>p[0]),zs=ring.map(p=>p[1]);for(let x=Math.floor((Math.min(...xs)-1.15)/this.size);x<=Math.floor((Math.max(...xs)+1.15)/this.size);x++)for(let z=Math.floor((Math.min(...zs)-1.15)/this.size);z<=Math.floor((Math.max(...zs)+1.15)/this.size);z++){const key=x+','+z;const q=this.bCells.get(key)??[];q.push(b);this.bCells.set(key,q);if(b.blocksRoad===true){const barriers=this.roadBarrierCells.get(key)??[];barriers.push(b);this.roadBarrierCells.set(key,barriers);}}}
 }
 nearest(x:number,z:number,height?:number){let best:{x:number;z:number;d:number;yaw:number;road:Road;height?:number}|null=null;let score=Infinity;for(const s of this.cells.get(Math.floor(x/this.size)+','+Math.floor(z/this.size))??[]){const p=closest(x,z,s.a,s.b),raw=s.ya===undefined||s.yb===undefined?undefined:s.ya+(s.yb-s.ya)*p.t,y=raw===undefined?undefined:this.sourceSurfaceHeight?.(s.road.id,p.x,p.z,raw)??raw,n=p.d+(height===undefined||y===undefined?0:Math.abs(height-y)*10);if(n<score){score=n;best={...p,yaw:Math.atan2(s.b[0]-s.a[0],s.b[1]-s.a[1]),road:s.road,height:y};}}return best;}
 blocked(x:number,z:number,height?:number,bodyHeight=1.6,supportedFloor=false){
  const near=this.nearest(x,z,height),roadClear=!!near&&near.d<near.road.width/2-.65&&(height===undefined||near.height===undefined||Math.abs(near.height-height)<1.5);
  if(roadClear&&!this.roadBarrierCells.size)return false;
  for(const building of (roadClear?this.roadBarrierCells:this.bCells).get(Math.floor(x/this.size)+','+Math.floor(z/this.size))??[]){
   if(height!==undefined&&building.minY!==undefined&&building.maxY!==undefined&&(height>=building.maxY||height+bodyHeight<=building.minY))continue;
   const rings=building.rings;
   // Inner rings are open courtyards. Keep the existing clearance on both
   // sides of every wall, including an unclosed source ring's final edge.
   if(inRing(x,z,rings[0])&&!rings.slice(1).some(r=>inRing(x,z,r)))return true;
   for(const r of rings)for(let i=0;i<r.length;i++)if(closest(x,z,r[i],r[(i+1)%r.length]).d<1.15)return true;
  }
  if(roadClear)return false;
  for(const m of this.data.landmarks)if(!m.detailCollision&&m.height>0&&Math.hypot(x-m.x,z-m.z)<(m.id==='civic'?65:m.id==='tencent'?46:24))return true;
  // A verified public floor can span water; walls and columns above it remain
  // solid. The caller proves floor support independently at each body sample.
  if(supportedFloor)return false;
  return !this.data.land.some(p=>inRing(x,z,p[0])&&!p.slice(1).some(r=>inRing(x,z,r)))||(this.effectiveWater?this.effectiveWater.some(p=>inRing(x,z,p[0])&&!p.slice(1).some(r=>inRing(x,z,r))):this.data.water.some(p=>inRing(x,z,p.rings[0])&&!p.rings.slice(1).some(r=>inRing(x,z,r))));
 }
}
