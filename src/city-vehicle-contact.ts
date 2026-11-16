import {PEDESTRIAN_IMPACT} from './pedestrian-impact.ts';
export type VehicleBody={x:number;z:number;yaw:number;groundY:number;halfWidth:number;halfLength:number;height:number};
export type VehicleContact={normal:{x:number;z:number};penetration:number};
export const CAR_BODY={halfWidth:PEDESTRIAN_IMPACT.carHalfWidth,halfLength:PEDESTRIAN_IMPACT.carHalfLength,height:PEDESTRIAN_IMPACT.carHeight};
const dot=(x:number,z:number,n:{x:number;z:number})=>x*n.x+z*n.z;
const axes=(p:VehicleBody)=>[{x:Math.cos(p.yaw),z:-Math.sin(p.yaw)},{x:Math.sin(p.yaw),z:Math.cos(p.yaw)}];
/** Oriented body contact at the same physical level. No circular side wall. */
export function vehicleContact(a:VehicleBody,b:VehicleBody):VehicleContact|null{
 if(a.groundY+a.height<=b.groundY||b.groundY+b.height<=a.groundY)return null;
 if(Math.hypot(a.x-b.x,a.z-b.z)>Math.hypot(a.halfWidth,a.halfLength)+Math.hypot(b.halfWidth,b.halfLength))return null;
 const aa=axes(a),ba=axes(b);let penetration=Infinity,normal={x:0,z:0};
 for(const n of [...aa,...ba]){
  const ra=Math.abs(dot(aa[0].x,aa[0].z,n))*a.halfWidth+Math.abs(dot(aa[1].x,aa[1].z,n))*a.halfLength;
  const rb=Math.abs(dot(ba[0].x,ba[0].z,n))*b.halfWidth+Math.abs(dot(ba[1].x,ba[1].z,n))*b.halfLength;
  const separation=dot(b.x-a.x,b.z-a.z,n),overlap=ra+rb-Math.abs(separation);
  if(overlap<0)return null;
  if(overlap<penetration){penetration=overlap;const sign=separation<0?-1:1;normal={x:n.x*sign,z:n.z*sign};}
 }
 return {normal,penetration};
}
export function interpolateBody(a:VehicleBody,b:VehicleBody,t:number):VehicleBody{
 const yaw=Math.atan2(Math.sin(b.yaw-a.yaw),Math.cos(b.yaw-a.yaw));
 return {...a,x:a.x+(b.x-a.x)*t,z:a.z+(b.z-a.z)*t,groundY:a.groundY+(b.groundY-a.groundY)*t,yaw:a.yaw+yaw*t};
}
/** Bounded sweeps at <= .2 game units of edge travel. Current 53g/s, .05s
 * driving steps are well inside 128 iterations, including vehicle rotation. */
export function sweepVehicleContact(before:VehicleBody,after:VehicleBody,other:VehicleBody){
 const angle=Math.abs(Math.atan2(Math.sin(after.yaw-before.yaw),Math.cos(after.yaw-before.yaw)));
 const travel=Math.hypot(after.x-before.x,after.z-before.z)+angle*Math.hypot(before.halfWidth,before.halfLength);
 const steps=Math.max(1,Math.ceil(travel/.2));
 if(steps>128)throw Error('Vehicle sweep exceeds bounded motion contract');
 const initial=vehicleContact(before,other);
 if(initial){
  const end=vehicleContact(after,other);
  // Permit separation from legacy/spawn overlaps; never pin a reversing car.
  if(!end||end.penetration<initial.penetration-1e-8)return null;
  if(angle<1e-8&&end.penetration<=initial.penetration+1e-8&&dot(after.x-before.x,after.z-before.z,initial.normal)<=1e-8)return null;
  return {...initial,fraction:0};
 }
 for(let i=1;i<=steps;i++){
  let hit=vehicleContact(interpolateBody(before,after,i/steps),other);if(!hit)continue;
  let lo=(i-1)/steps,hi=i/steps;
  for(let k=0;k<16;k++){const mid=(lo+hi)/2,probe=vehicleContact(interpolateBody(before,after,mid),other);if(probe){hi=mid;hit=probe;}else lo=mid;}
  return {...hit,fraction:lo};
 }
 return null;
}
/** Same sports-car body as pedestrian impacts; speed controls remain unchanged.
 * The existing .15 rebound becomes restitution at the actual contact normal. */
export function vehicleImpulse(normal:{x:number;z:number},a:{x:number;z:number},b:{x:number;z:number},massA=1,massB=1){
 const closing=Math.max(0,dot(a.x-b.x,a.z-b.z,normal));
 const impulse=closing*1.15/(1/massA+1/massB);
 return {closing,a:{x:a.x-normal.x*impulse/massA,z:a.z-normal.z*impulse/massA},b:{x:b.x+normal.x*impulse/massB,z:b.z+normal.z*impulse/massB}};
}
/** Test an actor's vertical interval and point against a vehicle body. */
export function vehicleBlocksPoint(body:VehicleBody,x:number,z:number,feet:number,bodyHeight=1.6){
 if(feet>=body.groundY+body.height||feet+bodyHeight<=body.groundY)return false;
 const dx=x-body.x,dz=z-body.z,c=Math.cos(body.yaw),s=Math.sin(body.yaw);
 return Math.abs(dx*c-dz*s)<body.halfWidth&&Math.abs(dx*s+dz*c)<body.halfLength;
}
