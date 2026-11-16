import type {BaseStreamTile} from './city-stream-assets.ts';
import {BASE_STREAM_LIMITS,type StreamBudget} from './city-stream-residency.ts';
import {COMPATIBLE_CITY_RANGE} from './city-stream-profile.ts';
export type BaseStreamView={x:number;z:number;overview:boolean;rangeProfile?:'compatible';intersects?:(tile:BaseStreamTile)=>boolean};
const boundsDistance=(bounds:BaseStreamTile['bounds'],x:number,z:number)=>Math.hypot(Math.max(bounds.min[0]-x,0,x-bounds.max[0]),Math.max(bounds.min[2]-z,0,z-bounds.max[2]));
export const tileDistance=(t:BaseStreamTile,x:number,z:number)=>boundsDistance(t.bounds,x,z);
/** An audited whole-building partition can refine quality distance without
 * fragmenting the original six material meshes into 117 draws. Visibility and
 * retention still use the original parent, so this never removes source cover. */
export const tileLodDistance=(t:BaseStreamTile,x:number,z:number)=>t.lodBounds?.length?Math.min(...t.lodBounds.map(bounds=>boundsDistance(bounds,x,z))):tileDistance(t,x,z);
/** Frozen source building/road nodes are grouped by their original 640g cell
 * names. The actual world cull measures these from that cell's centre; terrain
 * uses bounds. Geometry distance remains separate for LOD and retention. */
export function tileCullDistance(t:BaseStreamTile,x:number,z:number){
 if(t.role!=='terrain'){
  const cell=(t.parentSourceId??t.id).match(/^(buildings|roads):(-?\d+),(-?\d+)$/);
  if(cell&&cell[1]===t.role){const cx=Number(cell[2]),cz=Number(cell[3]);if(Number.isSafeInteger(cx)&&Number.isSafeInteger(cz))return Math.hypot((cx+.5)*640-x,(cz+.5)*640-z);}
 }
 if(t.parentSourceId)throw Error('Invalid inherited source cull identity');
 return tileDistance(t,x,z);
}
/** Same original world ranges in game units: 2500 roads, 3300 ordinary/terrain,
 * 1400 reflections, 520 street / 1650 overview shadows. No geometry simplification.
 * An overview's unlimited source visibility can exceed the temporary budget;
 * return an explicit blocked plan instead of truncating its required set. */
export function planBaseStream(tiles:readonly BaseStreamTile[],view:BaseStreamView,budget:Readonly<StreamBudget>=BASE_STREAM_LIMITS){
 if(!Number.isFinite(view.x+view.z))throw Error('Invalid base stream focus');
 const required:BaseStreamTile[]=[],retained:BaseStreamTile[]=[];
 for(const tile of tiles){
  const compact=view.rangeProfile==='compatible',distance=tileDistance(tile,view.x,view.z),cullDistance=tileCullDistance(tile,view.x,view.z),range=compact?COMPATIBLE_CITY_RANGE.visible:tile.role==='roads'?2500:3300;
  const visual=((!compact&&view.overview)||cullDistance<range)&&(!view.intersects||view.intersects(tile));
  const auxiliary=tile.role!=='roads'&&cullDistance<(compact?Math.max(COMPATIBLE_CITY_RANGE.reflection,view.overview?COMPATIBLE_CITY_RANGE.overviewShadow:COMPATIBLE_CITY_RANGE.streetShadow):view.overview?1650:1400);
  if(visual||auxiliary)required.push(tile);
  if(visual||auxiliary||distance<range+(compact?COMPATIBLE_CITY_RANGE.retentionMargin:640))retained.push(tile);
 }
 const cost={bytes:0,logicalBytes:0,triangles:0,tiles:required.length};
 for(const tile of required){cost.bytes+=tile.bytes;cost.logicalBytes+=tile.logicalBytes;cost.triangles+=tile.triangles;}
 const exceeded=(Object.keys(cost) as (keyof StreamBudget)[]).filter(key=>cost[key]>budget[key]);
 return {required,retained,cost,budget:{...budget},exceeded,admitted:exceeded.length===0};
}
