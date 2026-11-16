import '@babylonjs/core/Meshes/thinInstanceMesh.js';
import {CAR_BODY,sweepVehicleContact,type VehicleBody} from './city-vehicle-contact.ts';
import {DynamicInstances} from './dynamic-instances.ts';
import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {Matrix,Vector3,Quaternion} from '@babylonjs/core/Maths/math.vector.js';
import {PBRMaterial} from '@babylonjs/core/Materials/PBR/pbrMaterial.js';
import {Color3} from '@babylonjs/core/Maths/math.color.js';
import type {AbstractMesh} from '@babylonjs/core/Meshes/abstractMesh.js';
import type {Scene} from '@babylonjs/core/scene.js';
import type {RoadGraph} from './navigation.ts';
export type TrafficCar={from:number;to:number;t:number;speed:number;x:number;z:number;yaw:number;group:number;actualSpeed?:number};
export class CityTraffic{
 private playerContacts=new WeakSet<TrafficCar>();
 private contacts=new WeakMap<TrafficCar,{vx:number;vz:number;remaining:number;ox:number;oz:number}>();
 /** Optional world hooks preserve the original standalone traffic interface. */
 vehicleObstacle:()=>VehicleBody|null=()=>null;
 contactBlocked:(body:VehicleBody)=>boolean=()=>false;
 onVehicleContact:(speed:number)=>void=()=>{};
 applyImpact(car:TrafficCar,vx:number,vz:number){
  const old=this.contacts.get(car);
  this.contacts.set(car,{vx,vz,remaining:.65,ox:old?.ox??0,oz:old?.oz??0});
  car.actualSpeed=vx*Math.sin(car.yaw)+vz*Math.cos(car.yaw);
 }

 private instances=new DynamicInstances();
 cars:TrafficCar[]=[];meshes:Mesh[][]=[];seed=77;
 /** Distance to a red stop line ahead of (x,z,yaw), or null; cars hold within 6 m of it. */
 signalHold:(x:number,z:number,yaw:number,height?:number)=>number|null=()=>null;
 random(){this.seed=(Math.imul(this.seed,1664525)+1013904223)>>>0;return this.seed/4294967296;}
 constructor(public graph:RoadGraph,source:AbstractMesh[],public scene:Scene,public heightAt:(x:number,z:number)=>number=()=>0,public directionAllowed:(a:number,b:number)=>boolean=()=>true){
  const colors=[new Color3(.52,.56,.53),new Color3(.28,.06,.038),new Color3(.028,.25,.18)];
  for(let i=0;i<3;i++){const group:Mesh[]=[];for(const src of source){if(!(src instanceof Mesh))continue;const m=src.clone('traffic-'+i+'-'+src.name,null,true)!;m.parent=null;m.unfreezeWorldMatrix();m.makeGeometryUnique();m.bakeTransformIntoVertices(Matrix.Scaling(1,1,-1));m.position.setAll(0);m.scaling.setAll(1);m.rotationQuaternion=Quaternion.Identity();m.alwaysSelectAsActiveMesh=true;m.receiveShadows=true;m.isPickable=false;if(src.material instanceof PBRMaterial&&src.material.name==='carpaint'){const mat=src.material.clone('traffic-paint-'+i)!;mat.albedoColor=colors[i];m.material=mat;}m.setEnabled(false);group.push(m);}this.meshes.push(group);}
 }
 place(x:number,z:number){this.cars=[];this.contacts=new WeakMap();this.playerContacts=new WeakSet();const candidates:number[]=[];for(let i=0;i<this.graph.nodes.length;i++){const p=this.graph.nodes[i],d=Math.hypot(p[0]-x,p[1]-z);if(d>14&&d<600&&this.graph.edges[i].size>1)candidates.push(i);}
  candidates.sort((a,b)=>Math.hypot(this.graph.nodes[a][0]-x,this.graph.nodes[a][1]-z)-Math.hypot(this.graph.nodes[b][0]-x,this.graph.nodes[b][1]-z));
  for(let i=0;i<40&&candidates.length;i++){const from=candidates[Math.floor(this.random()*Math.min(candidates.length,i<10?45:candidates.length))],next=[...this.graph.edges[from].keys()].filter(to=>this.directionAllowed(from,to));if(!next.length)continue;const to=next[Math.floor(this.random()*next.length)],p=this.graph.nodes[from];if(this.cars.some(c=>Math.hypot(c.x-p[0],c.z-p[1])<12))continue;this.cars.push({from,to,t:0,speed:7+this.random()*6,x:p[0],z:p[1],yaw:0,group:i%3});}this.origin=[x,z];this.update(.001,x,z);
 }
 origin=[0,0];
 private height(c:CityTraffic['cars'][number]){return this.graph.nodeHeights?this.graph.surfaceHeightOnEdge(c.from,c.to,c.t,0,[c.x,c.z]):this.heightAt(c.x,c.z);}
 surfaceHeight(c:CityTraffic['cars'][number]){return this.height(c);}
 snap(index:number,x:number,z:number,yaw:number){
  const car=this.cars[index];if(!car)return;
  car.x=x;car.z=z;car.yaw=yaw;
  const buffers:number[][]=[[],[],[]];
  for(const c of this.cars)buffers[c.group].push(...Matrix.Compose(Vector3.One(),Quaternion.RotationAxis(Vector3.Up(),c.yaw),new Vector3(c.x,this.height(c)+.14,c.z)).asArray());
  for(let i=0;i<3;i++)for(const m of this.meshes[i])this.instances.update(m,buffers[i]);
 }
 update(dt:number,px:number,pz:number){if(Math.hypot(px-this.origin[0],pz-this.origin[1])>450){this.place(px,pz);return;}const buffers:number[][]=[[],[],[]];for(const c of this.cars){const previous={...c},contact=this.contacts.get(c),oldOffset={x:contact?.ox??0,z:contact?.oz??0},oldHeight=this.height(c);let a=this.graph.nodes[c.from],b=this.graph.nodes[c.to],len=Math.hypot(a[0]-b[0],a[1]-b[1]);const hold=this.signalHold(c.x,c.z,c.yaw,this.graph.nodeHeights?this.height(c):undefined);const blocked=!!contact&&contact.remaining>0||(hold!==null&&hold<6)||this.cars.some(o=>o!==c&&Math.hypot(o.x-c.x,o.z-c.z)<8&&(!this.graph.nodeHeights||Math.abs(this.height(o)-this.height(c))<2.5)&&(o.x-c.x)*Math.sin(c.yaw)+(o.z-c.z)*Math.cos(c.yaw)>0);c.t+=dt*(blocked?0:c.speed)/Math.max(.1,len);let limit=0;
   while(c.t>=1&&limit++<12){c.t=(c.t-1)*len;const old=c.from;c.from=c.to;a=this.graph.nodes[c.from];const options=[...this.graph.edges[c.from].keys()].filter(i=>i!==old&&this.directionAllowed(c.from,i));if(!options.length&&!this.directionAllowed(c.from,old)){c.from=old;c.t=1;a=this.graph.nodes[old];break;}const dx=a[0]-this.graph.nodes[old][0],dz=a[1]-this.graph.nodes[old][1];let best=-Infinity,next=old;for(const i of options){const p=this.graph.nodes[i],l=Math.hypot(p[0]-a[0],p[1]-a[1]);const score=(dx*(p[0]-a[0])+dz*(p[1]-a[1]))/(Math.max(.1,len*l))+this.random()*.7;if(score>best){best=score;next=i;}}c.to=next;b=this.graph.nodes[next];len=Math.hypot(a[0]-b[0],a[1]-b[1]);c.t/=Math.max(.1,len);}
   const yaw=Math.atan2(b[0]-a[0],b[1]-a[1]);c.x=a[0]+(b[0]-a[0])*c.t+Math.cos(yaw)*1.15;c.z=a[1]+(b[1]-a[1])*c.t-Math.sin(yaw)*1.15;c.yaw=yaw;
   const oldBody={...previous,...CAR_BODY,groundY:oldHeight},obstacle=this.vehicleObstacle();
   if(contact){
    const ox=contact.ox,oz=contact.oz;
    if(contact.remaining>0){contact.ox+=contact.vx*dt;contact.oz+=contact.vz*dt;contact.vx*=Math.exp(-dt*5);contact.vz*=Math.exp(-dt*5);contact.remaining=Math.max(0,contact.remaining-dt);}
    else{contact.ox*=Math.exp(-dt*2);contact.oz*=Math.exp(-dt*2);}
    c.x+=contact.ox;c.z+=contact.oz;
    const proposed={...c,...CAR_BODY,groundY:this.height(c)};
    const steps=Math.max(1,Math.ceil(Math.hypot(c.x-previous.x,c.z-previous.z)/.2));let clear=steps<=128;
    for(let i=1;clear&&i<=steps;i++)clear=!this.contactBlocked({...proposed,x:previous.x+(c.x-previous.x)*i/steps,z:previous.z+(c.z-previous.z)*i/steps});
    if(clear)for(const other of this.cars){if(other===c)continue;if(sweepVehicleContact(oldBody,proposed,{...other,...CAR_BODY,groundY:this.height(other)})){clear=false;break;}}
    if(!clear){Object.assign(c,previous);contact.ox=ox;contact.oz=oz;contact.vx=contact.vz=0;contact.remaining=0;}
    if(contact.remaining===0&&Math.hypot(contact.ox,contact.oz)<.001)this.contacts.delete(c);
   }
   if(obstacle){
    const hit=sweepVehicleContact(oldBody,{...c,...CAR_BODY,groundY:this.height(c)},obstacle);
    if(hit){const travel=Math.hypot(c.x-previous.x,c.z-previous.z);Object.assign(c,previous);if(contact){contact.vx=contact.vz=0;contact.remaining=0;contact.ox=oldOffset.x;contact.oz=oldOffset.z;}if(travel>.001&&!this.playerContacts.has(c))this.onVehicleContact(travel/Math.max(.001,dt));this.playerContacts.add(c);}else this.playerContacts.delete(c);
   }
   c.actualSpeed=dt>0?((c.x-previous.x)*Math.sin(c.yaw)+(c.z-previous.z)*Math.cos(c.yaw))/dt:0;

   if(Math.hypot(c.x-px,c.z-pz)>950)continue;buffers[c.group].push(...Matrix.Compose(Vector3.One(),Quaternion.RotationAxis(Vector3.Up(),c.yaw),new Vector3(c.x,this.height(c)+.14,c.z)).asArray());}
  for(let i=0;i<3;i++)for(const m of this.meshes[i]){this.instances.update(m,buffers[i]);}
 }
}
