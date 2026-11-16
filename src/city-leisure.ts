/** Reusable leisure rules. All distances are already game units; no city projection here.
 * Preview locations are fictional. Real-city integration must supply audited surfaces/docks.
 * This module never receives the career wallet, car odometer or story settlement state. */
export type LeisurePose={x:number;z:number;yaw:number;height:number};
export type LeisureDock={id:string;land:LeisurePose;berth:LeisurePose};
export type LeisureWater=(x:number,z:number,height:number)=>boolean;
export class LeisureBoat {
 active=false; speed=0; distance=0; blocked=false; pose:LeisurePose;
 constructor(readonly dock:LeisureDock,private water:LeisureWater){this.pose={...dock.berth};}
 private clear(p:LeisurePose){
  const s=Math.sin(p.yaw),c=Math.cos(p.yaw);
  for(const u of [-.67,0,.67])for(const v of [-1.75,0,1.75])
   if(!this.water(p.x+c*u+s*v,p.z-s*u+c*v,p.height))return false;
  return true;
 }
 board(walker:LeisurePose,clearLand:(p:LeisurePose)=>boolean):'ok'|'away'|'blocked'{
  if(this.active||!Object.values(walker).every(Number.isFinite)||Math.hypot(walker.x-this.dock.land.x,walker.z-this.dock.land.z)>1.8||Math.abs(walker.height-this.dock.land.height)>.4||Math.hypot(this.pose.x-this.dock.berth.x,this.pose.z-this.dock.berth.z)>2)return 'away';
  if(!clearLand(this.dock.land)||!this.clear(this.pose))return 'blocked';
  this.active=true;this.speed=0;return 'ok';
 }
 disembark(clearLand:(p:LeisurePose)=>boolean):LeisurePose|null{
  if(!this.active||Math.abs(this.speed)>.3||Math.hypot(this.pose.x-this.dock.berth.x,this.pose.z-this.dock.berth.z)>2||!clearLand(this.dock.land))return null;
  this.active=false;this.speed=0;return {...this.dock.land};
 }
 reset(){this.active=false;this.speed=0;this.blocked=false;this.pose={...this.dock.berth};}
 step(keys:ReadonlySet<string>,seconds:number){
  if(!this.active||!Number.isFinite(seconds)||seconds<=0)return;
  const dt=Math.min(.05,seconds),brake=keys.has('Space');
  const throttle=Number(keys.has('KeyW')||keys.has('ArrowUp'))-Number(keys.has('KeyS')||keys.has('ArrowDown'));
  const steer=Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'));
  const target=brake?0:throttle>0?3.2:throttle<0?-1:0,rate=brake?3:throttle?.75:.35;
  this.speed+=Math.sign(target-this.speed)*Math.min(Math.abs(target-this.speed),rate*dt);this.blocked=false;
  // Sweep the full hull, including rotation; long frames never tunnel through shore.
  const n=Math.max(1,Math.ceil((Math.abs(this.speed)+Math.abs(steer)*1.75)*dt/.08));
  for(let i=0;i<n;i++){
   const yaw=this.pose.yaw+steer*.65*Math.min(1,Math.abs(this.speed)/.5)*Math.sign(this.speed)*dt/n;
   const p={...this.pose,yaw,x:this.pose.x+Math.sin(yaw)*this.speed*dt/n,z:this.pose.z+Math.cos(yaw)*this.speed*dt/n};
   if(!this.clear(p)){this.speed=0;this.blocked=true;break;}
   this.distance+=Math.hypot(p.x-this.pose.x,p.z-this.pose.z);this.pose=p;
  }
 }
}

export type FishingPhase='idle'|'waiting'|'bite'|'reeling'|'landed'|'escaped';
export type FishJournal={version:1;released:number;bestCm:number};
export function readFishJournal(raw:unknown):FishJournal{
 const r=raw as Partial<FishJournal>|null;
 return r?.version===1&&Number.isInteger(r.released)&&Number(r.released)>=0&&Number(r.released)<=100000&&Number.isFinite(r.bestCm)&&Number(r.bestCm)>=0&&Number(r.bestCm)<=80
  ?{version:1,released:Number(r.released),bestCm:Number(r.bestCm)}:{version:1,released:0,bestCm:0};
}
export class LeisureFishing {
 phase:FishingPhase='idle';elapsed=0;tension=0;progress=0;sizeCm=0;
 private wait=0;private serial=0;private validSession=false;
 constructor(readonly spot:LeisurePose,readonly journal:FishJournal,private random:()=>number=Math.random){}
 near(p:LeisurePose){return Object.values(p).every(Number.isFinite)&&Math.hypot(p.x-this.spot.x,p.z-this.spot.z)<=1.8&&Math.abs(p.height-this.spot.height)<.4;}
 cast(p:LeisurePose,walking:boolean){
  if(!walking||!this.near(p)||!['idle','escaped'].includes(this.phase))return false;
  const rand=()=>Math.max(0,Math.min(.999999,Number(this.random())||0));
  this.phase='waiting';this.wait=2+rand()*3;this.sizeCm=18+Math.floor(rand()*26);this.elapsed=0;this.progress=0;this.tension=.3;this.serial++;this.validSession=true;return true;
 }
 hook(){if(this.phase!=='bite')return false;this.phase='reeling';this.elapsed=0;this.tension=.3;return true;}
 tick(seconds:number,hold:boolean,pose:LeisurePose,walking:boolean){
  if(!Number.isFinite(seconds)||seconds<=0||['idle','landed','escaped'].includes(this.phase))return;
  if(!walking||!this.near(pose)){this.cancel();return;}
  const dt=Math.min(.05,seconds);this.elapsed+=dt;
  if(this.phase==='waiting'&&this.elapsed>=this.wait){this.phase='bite';this.elapsed=0;}
  else if(this.phase==='bite'&&this.elapsed>1.8){this.phase='escaped';this.validSession=false;}
  else if(this.phase==='reeling'){
   this.tension=Math.max(0,this.tension+dt*(hold?.42:-.27));
   if(this.tension>=1||this.elapsed>18){this.phase='escaped';this.validSession=false;return;}
   if(hold&&this.tension>=.2&&this.tension<=.78)this.progress=Math.min(1,this.progress+dt*.28);
   else this.progress=Math.max(0,this.progress-dt*.025);
   if(this.progress>=1){this.phase='landed';this.elapsed=0;}
  }
 }
 release():number|null{
  if(this.phase!=='landed'||!this.validSession)return null;
  this.validSession=false;this.phase='idle';this.journal.released=Math.min(100000,this.journal.released+1);this.journal.bestCm=Math.max(this.journal.bestCm,this.sizeCm);return this.sizeCm;
 }
 cancel(){this.phase='idle';this.validSession=false;this.elapsed=0;this.progress=0;this.tension=0;}
 get castId(){return this.serial;}
}
