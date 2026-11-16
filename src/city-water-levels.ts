import {closest,inRing} from './driving.ts';
import type {V2} from './city-types.ts';
export type WaterBodyLevel={id?:string;rings:V2[][];height:number;renderSurface?:boolean;renderRings?:V2[][][]};
/** One existing reflection target follows the nearby water body's plane.
 * Preserve per-body mesh heights; lighting changes never rebuild materials.
 */
export class CityWaterLevels {
 private bodies:{body:WaterBodyLevel;bounds:number[]}[];
 constructor(bodies:WaterBodyLevel[]){this.bodies=bodies.filter(b=>b.renderSurface!==false).flatMap(b=>(b.renderRings??[b.rings]).map(rings=>({...b,rings}))).map(body=>{
  if(!Number.isFinite(body.height)||!body.rings[0]?.length||body.rings.some(r=>r.length<3||r.some(p=>!Number.isFinite(p[0]+p[1]))))throw new Error('Invalid water body level');
  const ring=body.rings[0];return {body,bounds:[Math.min(...ring.map(p=>p[0])),Math.min(...ring.map(p=>p[1])),Math.max(...ring.map(p=>p[0])),Math.max(...ring.map(p=>p[1]))]};
 });}
 nearest(x:number,z:number){
  if(!Number.isFinite(x+z))throw new Error('Invalid water focus');
  let best:WaterBodyLevel|null=null,distance=Infinity;
  for(const {body,bounds:b} of this.bodies){
   const lower=Math.hypot(Math.max(b[0]-x,0,x-b[2]),Math.max(b[1]-z,0,z-b[3]));if(lower>distance)continue;
   const inside=inRing(x,z,body.rings[0])&&!body.rings.slice(1).some(r=>inRing(x,z,r));
   let d=inside?0:Infinity;
   if(!inside)for(const ring of body.rings)for(let i=0;i<ring.length;i++)d=Math.min(d,closest(x,z,ring[i],ring[(i+1)%ring.length]).d);
   if(d<distance){best=body;distance=d;}
  }
  return best?{height:best.height,id:best.id??null,distance}:null;
 }
}
