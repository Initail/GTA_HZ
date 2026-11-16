/** Local Babylon NullEngine GLB import, same root fix as world; no browser/network/rendering. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import {NullEngine,Scene,ImportMeshAsync,Quaternion} from '@babylonjs/core';
import '@babylonjs/loaders/glTF/index.js';
const [inventoryFile,output]=process.argv.slice(2);if(!output)throw new Error('Inventory and report required');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),inventory=JSON.parse(fs.readFileSync(inventoryFile)),results=[];
for(const object of inventory.objects){
 if(sha(object.artifact)!==object.artifactSha256)throw new Error('Changed GLB');
 const engine=new NullEngine(),scene=new Scene(engine);scene.useRightHandedSystem=false;
 const loaded=await ImportMeshAsync(fs.readFileSync(object.artifact),scene,{pluginExtension:'.glb',pluginOptions:{gltf:{skipMaterials:true}}});
 loaded.meshes[0].rotationQuaternion=Quaternion.Identity();
 const meshes=loaded.meshes.filter(m=>m.getTotalVertices()>0);for(const m of meshes)m.computeWorldMatrix(true);
 const minimum=[0,1,2].map(axis=>Math.min(...meshes.map(m=>m.getBoundingInfo().boundingBox.minimumWorld.asArray()[axis]))),maximum=[0,1,2].map(axis=>Math.max(...meshes.map(m=>m.getBoundingInfo().boundingBox.maximumWorld.asArray()[axis])));
 const expected=object.boundsGameEastUpNorth,maxError=Math.max(...minimum.map((v,i)=>Math.abs(v-expected.min[i])),...maximum.map((v,i)=>Math.abs(v-expected.max[i])));
 const triangles=meshes.reduce((sum,m)=>sum+m.getTotalIndices()/3,0);
 results.push({id:object.id,artifactSha256:object.artifactSha256,babylonBoundsGame:{min:minimum,max:maximum},expectedBoundsGame:expected,maxErrorGame:maxError,triangles,
  pass:maxError<.003&&triangles===object.stats.triangles,materialsAndTextures:'not tested; intentionally skipped for NullEngine geometry check',visual:'unknown'});
 scene.dispose();engine.dispose();
}
const report={kind:'local-Babylon-NullEngine-geometry-only',inventorySha256:sha(inventoryFile),coordinateHandling:'Blender east/north/up -> GLB east/up/south; Babylon root identity retains loader Z reflection -> game east/up/north',
 results,pass:results.every(r=>r.pass),pending:['materials/textures','browser WebGL rendering','all named visual/collision/performance checks']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,objects:results.length,failed:results.filter(r=>!r.pass)},null,2));
if(!report.pass)process.exitCode=1;
