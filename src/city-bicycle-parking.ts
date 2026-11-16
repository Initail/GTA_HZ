import {CityBicycle,type BicyclePose} from './city-bicycle.ts';
export type BicycleParkingStore={getItem(key:string):string|null;setItem(key:string,value:string):void};
export type BicycleParkingIdentity={city:string;projection:string;key:string;extent:readonly number[]};
type ParkingSave={version:1;city:string;projection:string;pose:BicyclePose|null;distance:number};
export type BicycleRestoreResult='empty'|'parked'|'folded'|'invalid'|'blocked'|'unavailable';
/** Separate leisure record: no task, wallet, car save or active-mode recovery. */
export class CityBicycleParking {
 constructor(private bike:CityBicycle,private store:BicycleParkingStore|null,private identity:BicycleParkingIdentity){
  const e=identity.extent;
  if(!identity.city||!identity.projection||!identity.key||e.length!==4||!e.every(Number.isFinite)||e[0]>=e[2]||e[1]>=e[3])throw Error('Invalid bicycle parking identity');
  this.identity={...identity,extent:[...e]};
 }
 private pose(value:unknown):value is BicyclePose {
  if(!value||typeof value!=='object')return false;
  const p=value as BicyclePose,e=this.identity.extent;
  return [p.x,p.z,p.yaw,p.height].every(n=>typeof n==='number'&&Number.isFinite(n))&&p.x>=e[0]&&p.x<=e[2]&&p.z>=e[1]&&p.z<=e[3]&&Math.abs(p.height)<10000;
 }
 restore():BicycleRestoreResult {
  if(!this.store)return 'unavailable';
  let text:string|null;
  try{text=this.store.getItem(this.identity.key);}catch{return 'unavailable';}
  if(text===null)return 'empty';
  if(text.length>2048)return 'invalid';
  let raw:ParkingSave;
  try{raw=JSON.parse(text);}catch{return 'invalid';}
  if(!raw||raw.version!==1||raw.city!==this.identity.city||raw.projection!==this.identity.projection||typeof raw.distance!=='number'||!Number.isFinite(raw.distance)||raw.distance<0||raw.distance>1e9||(raw.pose!==null&&!this.pose(raw.pose)))return 'invalid';
  if(this.bike.active||this.bike.deployed)return 'blocked';
  if(raw.pose&&!this.bike.restoreParked(raw.pose))return 'blocked';
  this.bike.distance=raw.distance;
  return raw.pose?'parked':'folded';
 }
 /** Called at mount/dismount/stow/travel boundaries, never each render frame.
  * A riding session clears the old parking location; reloading cannot revive
  * a second copy at the departure point or resume movement without input. */
 checkpoint():boolean {
  if(!this.store)return false;
  const pose=this.bike.deployed&&!this.bike.active?this.bike.pose:null;
  if(pose&&!this.pose(pose)||!Number.isFinite(this.bike.distance)||this.bike.distance<0||this.bike.distance>1e9)return false;
  const save:ParkingSave={version:1,city:this.identity.city,projection:this.identity.projection,pose,distance:this.bike.distance};
  try{this.store.setItem(this.identity.key,JSON.stringify(save));return true;}catch{return false;}
 }
}
