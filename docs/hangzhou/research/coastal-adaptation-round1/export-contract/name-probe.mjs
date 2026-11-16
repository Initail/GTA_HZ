import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {NullEngine,Scene,MeshBuilder,PBRMaterial} from '@babylonjs/core';
import {createBayparkLook,BAYPARK_LOOK} from '../../../../../src/city-baypark-look.ts';
const engine=new NullEngine(),scene=new Scene(engine);
const names=['coastal_shore_5_-4_concrete','coastal_shore_5_-4_seawall','coastal_shore_5_-4_coastal-rock','coastal_shore_5_-4_pavement','terrain_pavement','terrain_5_-4_pavement','coastal_bridge_5_-4_concrete','coastal_shore_5_-4_seawall.001'];
for(const name of names){const mesh=MeshBuilder.CreateBox(name,{size:1},scene);mesh.position.set(BAYPARK_LOOK.center[0],1,BAYPARK_LOOK.center[1]);mesh.material=new PBRMaterial(name+'-material',scene);mesh.computeWorldMatrix(true);}
const look=createBayparkLook(scene,{waterHeight:.9,tiledReceivers:true});
const result={kind:'actual runtime selector under NullEngine, no GPU shader compile or browser',sourceSha256:createHash('sha256').update(fs.readFileSync('src/city-baypark-look.ts')).digest('hex'),inputNames:names,stats:look.stats()};
fs.writeFileSync(path.join(path.dirname(new URL(import.meta.url).pathname),'name-probe-result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));scene.dispose();engine.dispose();
