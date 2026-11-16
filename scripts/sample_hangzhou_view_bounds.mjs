/** CPU-only view sensitivity study using the actual DrivingWorld.baseView
 * method. These cameras are SIMULATED, never runtime observations or visual
 * acceptance. Read no geometry and do not create an engine/GPU context. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';import {stripTypeScriptTypes} from 'node:module';
import {Matrix,Vector3} from '@babylonjs/core/Maths/math.vector.js';import {Frustum} from '@babylonjs/core/Maths/math.frustum.js';
const output=path.resolve(process.argv[2]??''),root=process.cwd();assert(process.argv[2]&&output.startsWith(root+path.sep)&&!fs.existsSync(output));
const file='artifacts/cities/hangzhou/city-leisure-v15/src/city-world.ts',source=fs.readFileSync(file,'utf8'),begin=source.indexOf(' private baseView('),end=source.indexOf('\n captureStreamView(',begin);assert(begin>=0&&end>begin);
const Harness=new Function('Matrix','Vector3','Frustum',stripTypeScriptTypes('class Harness{'+source.slice(begin,end)+'}')+'; return Harness;')(Matrix,Vector3,Frustum);
assert(source.includes("this.camera.minZ=.75;this.camera.maxZ=18000;this.camera.fov=.9"),'Review source camera constants after a change');
const spawnFile='artifacts/cities/hangzhou/stream-world-v1/original-range-admission.json',spawn=JSON.parse(fs.readFileSync(spawnFile)).spawn,views=[];
for(const ground of [3,6,9])for(const turn of [0,1,2,3]){
 const yaw=spawn.yaw+turn*Math.PI/2,eye=new Vector3(spawn.x-Math.sin(yaw)*8,ground+3.7,spawn.z-Math.cos(yaw)*8),target=new Vector3(spawn.x,ground+1.1,spawn.z),projection=Matrix.PerspectiveFovLH(.9,16/9,.75,18000),matrix=Matrix.LookAtLH(eye,target,Vector3.Up()).multiply(projection);
 const world=new Harness();Object.assign(world,{camera:{getTransformationMatrix:()=>matrix,getProjectionMatrix:()=>projection},sceneFocus:()=>spawn,overviewEffects:false,groundHeight:()=>ground});const view=world.baseView();
 views.push({id:'spawn-ground-'+ground+'-turn-'+turn,origin:'simulated',x:view.x,z:view.z,overview:view.overview,planes:view.planes.map(p=>({normal:p.normal.asArray(),d:p.d})),assumptions:{groundHeightGame:ground,groundBasis:'sensitivity parameter; not sampled terrain',yaw,eye:eye.asArray(),target:target.asArray(),verticalFov:.9,aspect:16/9,near:.75,far:18000}});
}
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
fs.writeFileSync(output,JSON.stringify({schemaVersion:1,scope:'explicit simulated startup-camera sensitivity only',inputs:[file,spawnFile].map(file=>({file,sha256:hash(file)})),views,actualCameraSamples:0,rendererStarted:false},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,simulatedViews:views.length,actualCameraSamples:0,rendererStarted:false}));
