/** A leisure bicycle in game metres. It owns no car, career or save state. */
export type BicyclePose={x:number;z:number;yaw:number;height:number};
export type BicycleBarrier='restricted-road'|'water'|'obstacle'|'step';
export type BicycleSurface={height:number;blocked:BicycleBarrier|null};
export const BICYCLE_BODY={halfWidth:.36,halfLength:1.02,height:1.85} as const;
export const BICYCLE_MAX_SPEED=7;
export class CityBicycle {
 active=false;deployed=false;x=0;z=0;yaw=0;height=0;speed=0;distance=0;
 barrier:BicycleBarrier|null=null;
 constructor(private surface:(x:number,z:number,height:number)=>BicycleSurface){}
 /** Check the complete footprint at the current physical level, not only the hub. */
 private clear(p:BicyclePose):BicycleBarrier|null {
  const c=Math.cos(p.yaw),s=Math.sin(p.yaw);
  for(const u of [-BICYCLE_BODY.halfWidth,0,BICYCLE_BODY.halfWidth])
   for(const v of [-BICYCLE_BODY.halfLength,0,BICYCLE_BODY.halfLength]){
    const q=this.surface(p.x+c*u+s*v,p.z-s*u+c*v,p.height);
    if(q.blocked)return q.blocked;
    if(!Number.isFinite(q.height)||Math.abs(q.height-p.height)>.3)return 'step';
   }
  return null;
 }
 /** First use unfolds the trial bike at the walker; subsequent use returns to it. */
 mount(walker:BicyclePose,walkClear:(x:number,z:number)=>boolean):'ok'|'far'|BicycleBarrier {
  if(!Object.values(walker).every(Number.isFinite))return 'obstacle';
  const target=this.deployed?this.pose:walker;
  if(Math.hypot(walker.x-target.x,walker.z-target.z)>2||Math.abs(walker.height-target.height)>.45)return 'far';
  // Walking to the parked saddle cannot cross a wall or change bridge level.
  if(!this.walkPath(walker,target,walkClear))return 'obstacle';
  const blocked=this.clear(target);if(blocked)return blocked;
  Object.assign(this,target);this.active=true;this.deployed=true;this.speed=0;this.barrier=null;return 'ok';
 }
 private walkPath(from:BicyclePose,to:{x:number;z:number},clear:(x:number,z:number)=>boolean){
  const steps=Math.max(1,Math.ceil(Math.hypot(to.x-from.x,to.z-from.z)/.12));let height=from.height;
  for(let i=1;i<=steps;i++){
   const x=from.x+(to.x-from.x)*i/steps,z=from.z+(to.z-from.z)*i/steps,q=this.surface(x,z,height);
   // Bicycle restrictions don't prohibit walking; walkClear owns foot access.
   if(!clear(x,z)||!Number.isFinite(q.height)||Math.abs(q.height-height)>.3)return false;
   height=q.height;
  }
  return Math.abs(height-from.height)<.45;
 }
 dismount(walkClear:(x:number,z:number)=>boolean):BicyclePose|null {
  if(!this.active||this.speed>.5)return null;
  const c=Math.cos(this.yaw),s=Math.sin(this.yaw);
  for(const side of [.85,-.85,1.25,-1.25]){
   const x=this.x+c*side,z=this.z-s*side,q=this.surface(x,z,this.height);
   if(!this.walkPath(this.pose,{x,z},walkClear))continue;
   this.active=false;this.speed=0;this.barrier=null;
   return {x,z,yaw:this.yaw,height:q.height};
  }
  return null;
 }
 /** Stow beside the parked bike; debug travel uses clear() at its own existing epoch gate. */
 stow(walker:BicyclePose){
  if(this.active||Math.hypot(walker.x-this.x,walker.z-this.z)>2||Math.abs(walker.height-this.height)>.45)return false;
  this.clearDeployment();return true;
 }
 clearDeployment(){this.active=false;this.deployed=false;this.speed=0;this.barrier=null;}
 /** A refresh restores a parked object, never controls or velocity. The same
  * full footprint used for mounting must still be supported in today's world. */
 restoreParked(p:BicyclePose):boolean {
  if(this.active||this.deployed||!Object.values(p).every(Number.isFinite)||this.clear(p))return false;
  Object.assign(this,{x:p.x,z:p.z,yaw:p.yaw,height:p.height});
  this.deployed=true;this.speed=0;this.barrier=null;return true;
 }
 get pose():BicyclePose{return {x:this.x,z:this.z,yaw:this.yaw,height:this.height};}
 step(keys:ReadonlySet<string>,dt:number){
  if(!this.active||!Number.isFinite(dt)||dt<=0)return;
  dt=Math.min(.05,dt);this.barrier=null;
  const pedal=keys.has('KeyW')||keys.has('ArrowUp');
  const brake=keys.has('Space')?8:keys.has('KeyS')||keys.has('ArrowDown')?5:0;
  this.speed=Math.max(0,Math.min(BICYCLE_MAX_SPEED,this.speed+dt*(brake?-brake:pedal?1.8:-.65)));
  const steer=Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'));
  const steps=Math.max(1,Math.ceil(this.speed*dt/.12)),delta=dt/steps;
  for(let i=0;i<steps;i++){
   const yaw=this.yaw+Math.tan(steer*.48)*this.speed/1.15*delta;
   const x=this.x+Math.sin(yaw)*this.speed*delta,z=this.z+Math.cos(yaw)*this.speed*delta;
   const q=this.surface(x,z,this.height);
   const blocked=q.blocked??(!Number.isFinite(q.height)||Math.abs(q.height-this.height)>.16?'step':this.clear({x,z,yaw,height:q.height}));
   if(blocked){this.barrier=blocked;this.speed=0;break;}
   this.distance+=Math.hypot(x-this.x,z-this.z);this.x=x;this.z=z;this.yaw=yaw;this.height=q.height;
  }
 }
}
