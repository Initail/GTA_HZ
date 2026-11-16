import type {LeisurePose} from './city-leisure.ts';

export type BusVector = [number, number, number];
export type BusFrame = {origin:BusVector;right:BusVector;up:BusVector;forward:BusVector};
export type BusSolid = {name:string;motion:string;shape:string;center:BusVector;size:BusVector};
export type BusModelGeometry = {
 id:string;
 derived:{width:number;frontZ:number;rearZ:number;height:number};
 runtimeBody:{halfWidth:number;frontExtent:number;rearExtent:number;height:number;yawSweepRadius:number};
 solids:BusSolid[];
 parts:{name:string;positions:number[]}[];
 doors:{id:string;localSill:BusVector;localGroundPortal:BusVector;leafMotions:{id:string;openTranslation:BusVector}[]}[];
};
export type BusEnvelope = {halfWidth:number;frontExtent:number;rearExtent:number;height:number;turnRadius:number};
function assertBusFrame(frame:BusFrame) {
 const axes=[frame.right,frame.up,frame.forward];
 if(!frame.origin.concat(...axes).every(Number.isFinite)||axes.some(a=>Math.abs(dot(a,a)-1)>1e-6)||Math.abs(dot(axes[0],axes[1]))>1e-6||Math.abs(dot(axes[0],axes[2]))>1e-6||Math.abs(dot(axes[1],axes[2]))>1e-6||dot(cross(axes[0],axes[1]),axes[2])<1-1e-6)throw Error('Bus support frame must be finite, orthonormal and right handed');
}

export function busEnvelope(model:BusModelGeometry):BusEnvelope {
 const d=model.derived;
 if(![d.width,d.frontZ,d.rearZ,d.height].every(Number.isFinite)||d.width<=0||d.frontZ<=0||d.rearZ>=0||d.height<=0)throw Error('Bus model has no valid physical envelope');
 const b=model.runtimeBody;
 if(!Object.values(b).every(Number.isFinite)||b.halfWidth<d.width/2||b.frontExtent<d.frontZ||b.rearExtent<-d.rearZ||b.height<d.height||b.yawSweepRadius<Math.hypot(b.halfWidth,Math.max(b.frontExtent,b.rearExtent)))throw Error('Bus envelope must contain actual mirrors, body and wheels');
 return {halfWidth:b.halfWidth,frontExtent:b.frontExtent,rearExtent:b.rearExtent,height:b.height,turnRadius:b.yawSweepRadius};
}
export function busLocalToWorld(frame:BusFrame,p:BusVector):BusVector {
 return frame.origin.map((v,i)=>v+frame.right[i]*p[0]+frame.up[i]*p[1]+frame.forward[i]*p[2]) as BusVector;
}
/** Distance to a solid, including containment. Door motion must be closed here. */
export function busSolidDistance(point:BusVector,solid:BusSolid):number {
 if(solid.shape!=='box'||!solid.center.concat(solid.size).every(Number.isFinite)||solid.size.some(v=>v<=0))throw Error('Unknown bus solid');
 return Math.hypot(...point.map((v,k)=>Math.max(0,Math.abs(v-solid.center[k])-solid.size[k]/2)));
}
function visualPartBox(part:BusModelGeometry['parts'][number]):BusSolid {
 const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 if(part.positions.length<9||part.positions.length%3)throw Error('Invalid generated bus part');
 part.positions.forEach((v,i)=>{if(!Number.isFinite(v))throw Error('Invalid bus vertex');lo[i%3]=Math.min(lo[i%3],v);hi[i%3]=Math.max(hi[i%3],v);});
 return {name:part.name,shape:'box',motion:'static',center:lo.map((v,i)=>(v+hi[i])/2) as BusVector,size:lo.map((v,i)=>Math.max(1e-8,hi[i]-v)) as BusVector};
}

/** A seated camera, not a scaled standing avatar or walk-through doorway. */
export function prepareBusPassengerCamera(model:BusModelGeometry,seatId=6) {
 const seat=model.solids.find(s=>s.name===`seat-${seatId}-cushion`);
 if(!seat)throw Error('Passenger seat missing from actual model');
 const eye:BusVector=[seat.center[0],seat.center[1]+seat.size[1]/2+.74,seat.center[2]+.06];
 const near=.08,maxVerticalFov=1.05,maxAspect=2.5,cameraRadius=.10;
 // Covers every rotation of the near rectangle, so looking around cannot put
 // a near-plane corner through a seat, window, rail or roof.
 const nearCornerRadius=near*Math.sqrt(1+Math.tan(maxVerticalFov/2)**2*(1+maxAspect**2));
 const radius=Math.max(cameraRadius,nearCornerRadius),clearance=Math.min(...model.solids.map(s=>busSolidDistance(eye,s)),...model.parts.map(p=>busSolidDistance(eye,visualPartBox(p))));
 if(!Number.isFinite(clearance)||clearance<=radius+.005)throw Error('Passenger camera intersects actual bus interior');
 return {seatId,eye,near,maxVerticalFov,maxAspect,radius,clearance,standingAvatarVisible:false as const};
}
export type BusPassengerCamera=ReturnType<typeof prepareBusPassengerCamera>;
export function busPassengerCameraPose(camera:BusPassengerCamera,frame:BusFrame,lookYaw=0,lookPitch=0,aspect=16/9) {
 assertBusFrame(frame);
 const yaw=Math.max(-1.35,Math.min(1.35,lookYaw)),pitch=Math.max(-.55,Math.min(.55,lookPitch));
 if(![yaw,pitch,aspect].every(Number.isFinite)||aspect<=0)throw Error('Invalid passenger view');
 // Widening the viewport reduces vertical FOV, retaining the verified near
 // rectangle diagonal; a wide monitor must not enlarge the clipping envelope.
 const fov=2*Math.atan(Math.tan(camera.maxVerticalFov/2)*Math.min(1,Math.sqrt((1+camera.maxAspect**2)/(1+aspect**2))));
 const c=Math.cos(pitch),direction:BusVector=[Math.sin(yaw)*c,Math.sin(pitch),Math.cos(yaw)*c];
 return {eye:busLocalToWorld(frame,camera.eye),target:busLocalToWorld(frame,camera.eye.map((v,i)=>v+direction[i]) as BusVector),up:[...frame.up] as BusVector,near:camera.near,fov};
}

/** Outside anchor for the same conservative upright box used by busWalkerClear. */
export function busBoardingPoint(model:BusModelGeometry,frame:BusFrame,heightAt:(x:number,z:number)=>number|null,doorId='front'):LeisurePose|null {
 assertBusFrame(frame);
 const door=model.doors.find(d=>d.id===doorId);if(!door)return null;
 const envelope=busEnvelope(model);
 // A world-upright .46 x 1.6 x .46 box projects wider than .23g onto
 // diagonal bus sides. Account for roll and for its centre being .8g above
 // the sampled ground; the existing .4g surface allowance remains unchanged.
 const projectedHalfWidth=.23*Math.abs(frame.right[0])+.8*Math.abs(frame.right[1])+.23*Math.abs(frame.right[2]);
 const side=envelope.halfWidth+projectedHalfWidth+.04+Math.abs(frame.right[1])*(.8+.4);
 const local:BusVector=[side,door.localGroundPortal[1],door.localGroundPortal[2]],world=busLocalToWorld(frame,local);
 const height=heightAt(world[0],world[2]);if(height===null||!Number.isFinite(height)||Math.abs(height-world[1])>.4)return null;
 const point={x:world[0],z:world[2],height,yaw:Math.atan2(frame.forward[0],frame.forward[2])};
 // Check the upright, unchanged player envelope against the tilted bus and
 // both endpoints of its sliding doors. World/path clearance is additional.
 return busWalkerClear(model,frame,point)?point:null;
}
const dot=(a:BusVector,b:BusVector)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a:BusVector,b:BusVector):BusVector=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
/** Conservative upright .46 x 1.6 x .46 player box; no avatar rescaling. */
export function busWalkerClear(model:BusModelGeometry,frame:BusFrame,p:LeisurePose):boolean {
 assertBusFrame(frame);if(![p.x,p.z,p.height].every(Number.isFinite))return false;
 const basis=[frame.right,frame.up,frame.forward],worldAxes:BusVector[]=[[1,0,0],[0,1,0],[0,0,1]],axes=[...worldAxes,...basis,...worldAxes.flatMap(a=>basis.map(b=>cross(a,b)))];
 const player:BusVector=[p.x,p.height+.8,p.z],half:BusVector=[.23,.8,.23];
 for(const solid of model.solids){
  const leaf=model.doors.flatMap(d=>d.leafMotions).find(m=>m.id===solid.motion);
  // Sliding is linear; union at all fractions is bounded by the swept box.
  const shift=leaf?.openTranslation??[0,0,0],center=solid.center.map((v,k)=>v+shift[k]/2) as BusVector,size=solid.size.map((v,k)=>v+Math.abs(shift[k]));
  const body=busLocalToWorld(frame,center),delta=player.map((v,k)=>v-body[k]) as BusVector;
  const separated=axes.some(axis=>{
   if(dot(axis,axis)<1e-14)return false;
   const playerRadius=half.reduce((sum,h,k)=>sum+h*Math.abs(axis[k]),0),bodyRadius=basis.reduce((sum,b,k)=>sum+size[k]/2*Math.abs(dot(b,axis)),0);
   return Math.abs(dot(delta,axis))>playerRadius+bodyRadius+1e-8;
  });
  if(!separated)return false;
 }
 return true;
}
