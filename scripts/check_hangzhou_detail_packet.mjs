/** Actual loader and compressed GLB CPU checks. No browser, materials or GPU. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NullEngine,Scene,ImportMeshAsync,Quaternion,MeshoptCompression} from '@babylonjs/core';
import '@babylonjs/loaders/glTF/index.js';import {MeshoptDecoder} from 'meshoptimizer';
import {loadLandmarkDetails} from '../src/landmark-details.ts';
const [packet,source,inventoryFile,output]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert(output&&!fs.existsSync(output));
const report=read(path.join(packet,'report.json'));assert(report.pass);
for(const [p,h] of Object.entries(report.inputs))assert.equal(sha(p),h,'Input drift '+p);
for(const [p,h] of Object.entries(report.files))assert.equal(sha(path.join(packet,p)),h,'Packet drift '+p);
const city=read(path.join(source,'city.json')),manifest=read(path.join(packet,'landmark-detail.json')),inventory=read(inventoryFile),originalFetch=globalThis.fetch;
const modelManifestPaths=Object.keys(report.inputs).filter(p=>p.endsWith('/asset-manifest.json'));assert.equal(modelManifestPaths.length,1);
const expectedAsset=read(modelManifestPaths[0]).assets.find(a=>a.file==='landmark-detail.glb');assert(expectedAsset);
const oldOrdinary=city.buildings.filter(b=>b.style!=='landmark-detail').length;
try{
 globalThis.fetch=async url=>{assert(String(url).endsWith('/landmark-detail.json'));return new Response(fs.readFileSync(path.join(packet,'landmark-detail.json')));};
 const shared={cityId:'hangzhou',manifestSha256:sha(path.join(source,'geography/manifest.json')),heightAt:()=>0};
 await loadLandmarkDetails(city,shared);const once=JSON.stringify(city);
 await loadLandmarkDetails(city,shared);assert.equal(JSON.stringify(city),once,'Repeated load must not append stale colliders or map points');
 assert.equal(city.buildings.filter(b=>b.style==='landmark-detail').length,manifest.collisionFootprints.length);
 assert(!city.buildings.some(b=>manifest.replacedCollisionIds.includes(b.id)));
 assert.equal(city.buildings.filter(b=>b.style!=='landmark-detail').length,oldOrdinary);
 for(const mark of manifest.landmarks){const actual=city.landmarks.find(m=>m.id===mark.id);assert.equal(actual.arrivalRoadId,mark.arrivalRoadId);assert.deepEqual(actual.arrival,mark.arrival);}
}finally{globalThis.fetch=originalFetch;}
// Use the installed meshoptimizer WASM decoder in this Node-only check. The
// actual Babylon glTF extension still parses/requests each compressed view;
// this adapter replaces only its browser-script/worker bootstrap, not buffers.
await MeshoptDecoder.ready;let decodedViews=0;
const previousDecoder=MeshoptCompression._Default;
MeshoptCompression._Default={decodeGltfBufferAsync:async(bytes,count,stride,mode,filter)=>{decodedViews++;const out=new Uint8Array(count*stride);MeshoptDecoder.decodeGltfBuffer(out,count,stride,bytes,mode,filter);return out;}};
const engine=new NullEngine(),scene=new Scene(engine);let results=[],meshCount=0,triangles=0;
try{
 const loaded=await ImportMeshAsync(fs.readFileSync(path.join(packet,'landmark-detail.glb')),scene,{pluginExtension:'.glb',pluginOptions:{gltf:{skipMaterials:true}}});
 loaded.meshes[0].rotationQuaternion=Quaternion.Identity();
 const meshes=loaded.meshes.filter(m=>m.getTotalVertices()>0);meshCount=meshes.length;
 for(const m of meshes)m.computeWorldMatrix(true);
 triangles=meshes.reduce((s,m)=>s+m.getTotalIndices()/3,0);
 for(const object of inventory.objects.filter(o=>!report.omittedModelIds.includes(o.id))){
  const selected=meshes.filter(m=>m.name.startsWith(object.stats.meshNamePrefix));assert(selected.length);
  const min=[0,1,2].map(i=>Math.min(...selected.map(m=>m.getBoundingInfo().boundingBox.minimumWorld.asArray()[i])));
  const max=[0,1,2].map(i=>Math.max(...selected.map(m=>m.getBoundingInfo().boundingBox.maximumWorld.asArray()[i])));
  const error=Math.max(...min.map((n,i)=>Math.abs(n-object.boundsGameEastUpNorth.min[i])),...max.map((n,i)=>Math.abs(n-object.boundsGameEastUpNorth.max[i])));
  const count=selected.reduce((s,m)=>s+m.getTotalIndices()/3,0);assert.equal(count,object.stats.triangles);assert(error<.003);
  results.push({id:object.id,meshes:selected.length,triangles:count,boundsMaxErrorGame:error});
 }
 assert(decodedViews>0,'Compressed data must actually be decoded');assert.equal(triangles,expectedAsset.triangles);assert.equal(meshCount,expectedAsset.meshes);
}finally{scene.dispose();engine.dispose();MeshoptCompression._Default=previousDecoder;}
const result={kind:'actual detail loader and compressed GLB NullEngine CPU check',packetReportSha256:sha(path.join(packet,'report.json')),checkerSha256:sha('scripts/check_hangzhou_detail_packet.mjs'),checks:{actualDetailLoader:true,repeatedLoadIdempotent:true,retiredIdsRemoved:true,ordinaryBuildingsPreserved:true,sourceArrivalsLoaded:true,compressedViewsDecoded:decodedViews,objectBoundsAndTriangles:true},meshCount,triangles,results,pass:true,pending:['materials/textures/GPU/browser rendering','physical floor and entrance contact','real driving and walking','complete bridge and regional world integration']};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,results:results.length},null,2));
