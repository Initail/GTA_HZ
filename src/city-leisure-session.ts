import {LeisureBoat,LeisureFishing,readFishJournal,type LeisureDock,type LeisurePose,type LeisureWater} from './city-leisure.ts';
export type LeisureSite={id:string;name:string;waterIds:string[];dock:LeisureDock;fishing:LeisurePose;keeper:LeisurePose;volunteer:LeisurePose;sourceIds:string[]};
type Store={getItem(key:string):string|null;setItem(key:string,value:string):void};
export type LeisureHost={
 pose:()=>LeisurePose;walking:()=>boolean;paused:()=>boolean;busy:()=>boolean;
 clear:(p:LeisurePose)=>boolean;path:(from:LeisurePose,to:LeisurePose)=>boolean;
 board:()=>void;land:(p:LeisurePose)=>void;message:(text:string)=>void;
 storage:Store|null;storageKey:string;
};
/** City-mode adapter. No wallet, vehicle odometer, task settlement or debug relocation. */
export class CityLeisureSession {
 readonly boat:LeisureBoat;readonly fishing:LeisureFishing;
 private nextBarrierNotice=0;private clock=0;
 constructor(readonly site:LeisureSite,water:LeisureWater,private host:LeisureHost){
  this.boat=new LeisureBoat(site.dock,water);let raw:unknown=null;
  try{raw=JSON.parse(host.storage?.getItem(host.storageKey)??'null');}catch{}
  this.fishing=new LeisureFishing(site.fishing,readFishJournal(raw));
 }
 get fishingActive(){return !['idle','escaped'].includes(this.fishing.phase);}
 get active(){return this.boat.active||this.fishingActive;}
 get actor(){const b=this.boat;return {...b.pose,speed:b.speed,distance:b.distance};}
 get fishingActor(){return {...this.host.pose(),yaw:this.site.fishing.yaw};}
 private near(p:LeisurePose,r=2.2){const a=this.host.pose();return Math.hypot(a.x-p.x,a.z-p.z)<r&&Math.abs(a.height-p.height)<.7;}
 prompt(){
  if(this.host.paused())return null;
  if(this.boat.active)return 'E / F · 靠近原泊位并停稳下船';
  if(!this.host.walking())return null;
  if(this.fishing.phase==='landed')return `E · 放流 ${this.fishing.sizeCm} cm 的鱼并记录`;
  if(this.fishing.phase==='waiting')return '等待浮漂 · Q 随时收竿';
  if(this.fishing.phase==='bite')return '咬钩了 · 空格提竿';
  if(this.fishing.phase==='reeling')return `收线 ${Math.round(this.fishing.progress*100)}% · 张力 ${Math.round(this.fishing.tension*100)}% · 按住空格收线，松开减力`;
  if(this.near(this.site.dock.land,1.8))return 'E · 游船体验（游戏操控改编）';
  if(this.near(this.site.keeper))return 'E · 与船工交谈';
  if(this.fishing.near(this.host.pose()))return 'Q · 垂钓体验（游戏改编）';
  if(this.near(this.site.volunteer))return 'E · 与湖畔志愿者交谈';
  return null;
 }
 interact(){
  if(this.host.paused())return false;
  if(this.boat.active){this.dismount();return true;}
  if(!this.host.walking())return false;
  if(this.fishing.phase==='landed'){
   if(this.host.busy()){this.cancelFishing();return true;}
   const cm=this.fishing.release();if(cm===null)return true;
   try{if(!this.host.storage)throw Error('Storage unavailable');this.host.storage.setItem(this.host.storageKey,JSON.stringify(this.fishing.journal));this.host.message(`已放流 ${cm} cm · 休闲手账已保存`);}
   catch{this.host.message(`已放流 ${cm} cm · 本次手账保留，浏览器暂不能保存`);}return true;
  }
  if(this.fishingActive){this.host.message('先完成放流，或按 Q 收竿后再交谈');return true;}
  if(this.near(this.site.dock.land,1.8)){
   if(this.host.busy()){this.host.message('请先完成或取消当前职业、顺路单或故事，再开始游船');return true;}
   const pose=this.host.pose();
   if(!this.host.path(pose,this.site.dock.land)){this.host.message('请沿码头入口走到登船点');return true;}
   const status=this.boat.board(pose,p=>this.host.clear(p));
   if(status!=='ok'){this.host.message(status==='away'?'游船尚未贴近泊位，请从登船口登船':'泊位或船身空间不足，暂不能登船');return true;}
   this.host.board();this.host.message('游船 · W 前划 / S 倒划 / A D 转向 / 空格刹停 / E 或 F 靠岸下船');return true;
  }
  if(this.near(this.site.keeper)){this.host.message('船工：这里提供游戏操控体验。沿指示到登船口，返回原泊位停稳后再下船。');return true;}
  if(this.near(this.site.volunteer)){this.host.message('志愿者：这里的垂钓是游戏改编，现实西湖请遵守景区管理。Q 抛竿，空格提竿与控线，放流后只记休闲手账。');return true;}
  return false;
 }
 toggleFishing(){
  if(this.host.paused()||this.boat.active)return false;
  if(this.fishingActive){this.cancelFishing();return true;}
  if(!this.host.walking()||!this.fishing.near(this.host.pose()))return false;
  if(this.host.busy()){this.host.message('请先完成或取消当前任务，再开始休闲体验');return true;}
  if(!this.host.clear(this.host.pose())){this.host.message('请先站稳在安全岸边');return true;}
  if(this.fishing.cast(this.host.pose(),true))this.host.message('已抛竿 · 浮漂下沉时按空格提竿；Q 收竿');return true;
 }
 hook(){if(!this.host.paused()&&!this.host.busy())this.fishing.hook();}
 cancelFishing(){this.fishing.cancel();this.host.message('已收竿 · 未完成的体验不会记入手账');}
 dismount(){
  const p=this.boat.disembark(p=>this.host.clear(p));
  if(!p){this.host.message('回到原泊位、空格刹停后再下船；湖中不能下船');return false;}
  this.host.land(p);this.host.message('已安全靠岸 · 汽车与单车仍停在原处');return true;
 }
 /** Observer temporarily owns input; boat state stays in place and time does not advance. */
 suspend(){this.boat.speed=0;if(this.fishingActive)this.cancelFishing();}
 /** Called only after the world's existing travel/reset admission checks succeed. */
 resetForTravel(){this.boat.reset();this.fishing.cancel();}
 step(keys:ReadonlySet<string>,dt:number,ownsControls:boolean){
  if(this.host.paused()||!ownsControls||!Number.isFinite(dt)||dt<=0)return;
  this.clock+=Math.max(0,Math.min(.05,dt));
  if(this.host.busy()&&this.fishingActive)this.cancelFishing();
  this.boat.step(keys,dt);
  if(this.boat.blocked&&this.clock>=this.nextBarrierNotice){this.nextBarrierNotice=this.clock+2.5;this.host.message('前方岸线、桥体或船身空间不足 · 请向开阔水面调整方向');}
  this.fishing.tick(dt,keys.has('Space'),this.host.pose(),this.host.walking());
 }
}
