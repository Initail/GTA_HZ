import {CityBus} from './city-bus.ts';
import {busPassengerCameraPose,type BusFrame,type BusPassengerCamera} from './city-bus-vehicle.ts';
import type {LeisurePose} from './city-leisure.ts';

export type BusSessionHost={
 pose:()=>LeisurePose;walking:()=>boolean;paused:()=>boolean;busy:()=>boolean;
 frame:()=>BusFrame|null;board:()=>void;land:(p:LeisurePose)=>void;message:(text:string)=>void;
};
/** Passenger state owns no career money, car odometer, travel shortcut or save position. */
export class CityBusSession {
 lookYaw=0;lookPitch=0;
 constructor(readonly bus:CityBus,readonly camera:BusPassengerCamera,private host:BusSessionHost){}
 get active(){return this.bus.passenger;}
 get actor(){return {...this.bus.pose,speed:this.bus.speed,distance:this.bus.distance};}
 get doorsOpen(){return this.bus.currentStop!==null&&Math.abs(this.bus.speed)<.05;}
 private nearStop(){const stop=this.bus.currentStop,p=this.host.pose();return !!stop&&Math.hypot(p.x-stop.platform.x,p.z-stop.platform.z)<=1.8&&Math.abs(p.height-stop.platform.height)<=.5;}
 prompt(){
  if(this.host.paused())return null;
  if(this.active)return this.doorsOpen?'E / F · 到站下车':this.bus.requestedExit?'已预约下车 · 到站后按 E':'E / F · 预约下一站下车';
  if(!this.host.walking()||!this.nearStop()||this.bus.phase!=='dwelling')return null;
  return `E · 乘坐 ${this.bus.route.name} · 约 ${Math.ceil(this.bus.departureIn)} 秒后发车（游戏班次）`;
 }
 interact(){
  if(this.host.paused())return false;
  if(this.active){
   if(!this.doorsOpen){this.bus.requestExit();this.host.message('已预约下一站下车 · 请到站后按 E');return true;}
   const p=this.bus.disembark();
   if(!p){this.bus.requestExit();this.host.message('站台通道暂被占用，公交会等候安全下车');return true;}
   this.host.land(p);this.lookYaw=this.lookPitch=0;this.host.message('已安全下车 · 私家车和单车仍停在原处');return true;
  }
  if(!this.host.walking()||!this.nearStop())return false;
  if(this.host.busy()){this.host.message('请先完成或取消当前任务，再乘坐公交');return true;}
  // Do not enter passenger mode before a supported body frame and camera exist.
  if(!this.host.frame()||!this.bus.board(this.host.pose(),true,false)){this.host.message('请等公交停稳、站台与车门通道畅通后上车');return true;}
  this.lookYaw=this.lookPitch=0;this.host.board();this.host.message('已上车 · 拖动查看窗外，E / F 预约到站下车');return true;
 }
 look(dx:number,dy:number){if(this.active&&Number.isFinite(dx+dy)){this.lookYaw=Math.max(-1.35,Math.min(1.35,this.lookYaw+dx));this.lookPitch=Math.max(-.55,Math.min(.55,this.lookPitch+dy));}}
 view(aspect:number){const frame=this.host.frame();return this.active&&frame?busPassengerCameraPose(this.camera,frame,this.lookYaw,this.lookPitch,aspect):null;}
 step(dt:number){
  // A missing surface may occur while streaming. Keep the last supported pose;
  // never advance a passenger through a chunk that has not been loaded.
  this.bus.step(dt,this.host.paused()||!this.host.frame());
 }
}
