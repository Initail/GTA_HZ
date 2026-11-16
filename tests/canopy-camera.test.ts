import {test} from 'node:test';import assert from 'node:assert/strict';import {CanopyCameraCollision,canopyTriangleSoup} from '../src/city-canopy-camera.ts';
import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
const identity=()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
test('camera stops at actual tree triangle, while high crown overhang remains clear',()=>{const c=new CanopyCameraCollision(),m=identity();const trunk=canopyTriangleSoup([-1,0,-2,1,0,-2,0,4,-2],[0,1,2]);c.add([trunk],m,0);assert.ok(Math.abs(c.fraction({x:0,y:1.6,z:0},{x:0,y:1.6,z:-4},0)-.5)<1e-12);assert.equal(c.fraction({x:0,y:5,z:0},{x:0,y:5,z:-4}),1);assert.ok(c.fraction({x:0,y:1.6,z:0},{x:0,y:1.6,z:-4})<.5);});
test('rotation, scale and translated float32 instances use the render transform',()=>{const c=new CanopyCameraCollision(),m=identity();m[0]=0;m[2]=-2;m[5]=2;m[8]=2;m[10]=0;m[12]=-630.123;m[13]=4.5;m[14]=-1096.24;const p=canopyTriangleSoup([-1,0,-2,1,0,-2,0,4,-2],[0,1,2]);c.add([p],m,0);const a={x:m[12],y:7.7,z:m[14]},b={x:m[12]-8,y:7.7,z:m[14]};assert.ok(Math.abs(c.fraction(a,b,0)-.5)<1e-12);});
test('off-axis near bounding boxes cannot create an invisible camera wall',()=>{const c=new CanopyCameraCollision(),m=identity();c.add([canopyTriangleSoup([-3,0,-2,-1,0,-2,-2,3,-2],[0,1,2])],m,0);assert.equal(c.fraction({x:0,y:1,z:0},{x:0,y:1,z:-4}),1);});
test('LOD rebuild clears invisible instances rather than retaining stale collision',()=>{const c=new CanopyCameraCollision();c.add([canopyTriangleSoup([-1,0,-2,1,0,-2,0,4,-2],[0,1,2])],identity(),0);c.clear();assert.equal(c.fraction({x:0,y:1,z:0},{x:0,y:1,z:-4}),1);});
const witnesses=JSON.parse(readFileSync(new URL('./canopy-camera-witnesses.json',import.meta.url),'utf8')).cases;
for(const w of witnesses)test(`actual model tree ${w.treeOldIndex} LOD ${w.lod} camera witness retreats before triangle`,()=>{
 const path=new URL(`../public/cities/hangzhou/landscape/canopy/${w.modelId}.glb`,import.meta.url);
 assert.equal(createHash('sha256').update(readFileSync(path)).digest('hex'),w.modelSha256);
 const xyz=(p:number[])=>({x:p[0],y:p[1],z:p[2]}),eye=xyz(w.eyeBabylonXYZ),desired=xyz(w.desiredBabylonXYZ),c=new CanopyCameraCollision();
 c.add([canopyTriangleSoup(w.triangleBabylonXYZ.flat(),[0,2,1])],identity(),0);
 assert.ok(Math.abs(c.fraction(eye,desired,0)-w.boomT)<1e-8);
 const fraction=c.fraction(eye,desired),length=Math.hypot(desired.x-eye.x,desired.y-eye.y,desired.z-eye.z);
 assert.ok(fraction<w.boomT);assert.ok(Math.abs((w.boomT-fraction)*length-.22)<1e-7);
});
test('near-eye collision never retreats beyond its first triangle',()=>{const c=new CanopyCameraCollision();c.add([canopyTriangleSoup([-1,0,-.01,1,0,-.01,0,4,-.01],[0,1,2])],identity(),0);assert.equal(c.fraction({x:0,y:1,z:0},{x:0,y:1,z:-4}),0);});
