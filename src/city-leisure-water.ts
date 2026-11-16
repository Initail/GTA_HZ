import {closest,inRing,CityCollision} from './driving.ts';
import type {CityData,CityWater,V2} from './city-types.ts';
import type {CitySiteSurfaces} from './city-site-surfaces.ts';
/** Uses the same rendered water rings and source road levels as the active city. */
export class CityLeisureWater {
 private waters:{id:string;rings:V2[][];height:number;bounds:number[]}[];
 constructor(data:CityData,ids:ReadonlySet<string>,private collision:CityCollision,private sites:CitySiteSurfaces|undefined,private extraSolid:(x:number,z:number,feet:number,height:number)=>boolean=()=>false,private roadHeight:(id:string,x:number,z:number,h:number)=>number=(_id,_x,_z,h)=>h){
  this.waters=data.water.filter(w=>w.id&&ids.has(w.id)&&w.renderSurface!==false).flatMap((w:CityWater)=>(w.renderRings??[w.rings]).map(rings=>{
   if(!Number.isFinite(w.height)||!rings[0]?.length)throw Error('游船水域缺少有效高度或轮廓');
   return {id:w.id!,rings,height:w.height!,bounds:[Math.min(...rings[0].map(p=>p[0])),Math.min(...rings[0].map(p=>p[1])),Math.max(...rings[0].map(p=>p[0])),Math.max(...rings[0].map(p=>p[1]))]};
  }));if(!this.waters.length)throw Error('当前城市没有匹配游船来源的水域');
 }
 at(x:number,z:number){return this.waters.find(w=>x>=w.bounds[0]&&z>=w.bounds[1]&&x<=w.bounds[2]&&z<=w.bounds[3]&&inRing(x,z,w.rings[0])&&!w.rings.slice(1).some(r=>inRing(x,z,r)))??null;}
 clear(x:number,z:number,height:number){
  const water=this.at(x,z);if(!water||!Number.isFinite(height)||Math.abs(water.height-height)>.08)return false;
  return !this.volumeBlocked(x,z,height-.2,2.05);
 }
 /** Water itself does not obstruct an above-water camera; decks and solids do. */
 volumeBlocked(x:number,z:number,feet:number,body:number){
  if(!Number.isFinite(x+z+feet+body)||body<=0)return true;
  if(this.sites?.blocked(x,z,feet,body)||this.extraSolid(x,z,feet,body))return true;
  // All nearby source decks participate, not just the nearest 2D road. A high
  // bridge leaves headroom; a low deck or surface causeway cannot be sailed through.
  const cell=this.collision.cells.get(Math.floor(x/this.collision.size)+','+Math.floor(z/this.collision.size))??[];
  for(const s of cell){
   const p=closest(x,z,s.a,s.b);if(p.d>s.road.width/2+.15)continue;
   if(s.ya===undefined||s.yb===undefined)return true;
   const y=this.roadHeight(s.road.id,p.x,p.z,s.ya+(s.yb-s.ya)*p.t);
   if(y>=feet-.25&&y-.35<=feet+body)return true;
  }
  const reason=this.collision.blockReason(x,z,feet,body,false,'foot');
  return reason!=='water'&&reason!==null;
 }
}
