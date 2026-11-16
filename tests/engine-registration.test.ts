import {test} from 'node:test';import assert from 'node:assert/strict';
import '../src/city-engine-registration.ts';
import {Engine} from '@babylonjs/core/Engines/engine.js';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';
import {Scene} from '@babylonjs/core/scene.js';
import {FreeCamera} from '@babylonjs/core/Cameras/freeCamera.js';
import {Vector3} from '@babylonjs/core/Maths/math.vector.js';
test('production bootstrap retains GPU query and camera ray prototype registration',()=>{
 assert.equal(typeof Engine.prototype.captureGPUFrameTime,'function');
 assert.equal(typeof Engine.prototype.getGPUFrameTimeCounter,'function');
 const engine=new NullEngine(),scene=new Scene(engine);
 try{const camera=new FreeCamera('probe',new Vector3(1,2,3),scene);const ray=camera.getForwardRay(25);assert.equal(ray.length,25);assert.deepEqual(ray.origin.asArray(),[1,2,3]);assert.ok(Math.abs(ray.direction.length()-1)<1e-6);}
 finally{scene.dispose();engine.dispose();}
});
