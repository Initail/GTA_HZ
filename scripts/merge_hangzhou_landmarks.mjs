/** Serial candidate assembly, preserving every selected mesh and its material.
 * No model optimization, axis conversion, public writes or city activation.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {Document,NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {mergeDocuments,unpartition} from '@gltf-transform/functions';
import {MeshoptDecoder} from 'meshoptimizer';
const args=process.argv.slice(2),[inventoryFile,foundationDir,output,...omittedIds]=args;
if(!inventoryFile||!foundationDir||!output)throw Error('inventory, foundation directory, fresh output, optional omitted object IDs required');
if(fs.existsSync(output)||!path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep))throw Error('Fresh candidate required');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),sha=p=>hash(fs.readFileSync(p)),read=p=>JSON.parse(fs.readFileSync(p));
const inventory=read(inventoryFile),foundationFile=path.join(foundationDir,'asset-manifest.json'),foundation=read(foundationFile);
assert.equal(inventory.cityId,'hangzhou');assert.equal(foundation.cityId,'hangzhou');
for(const id of omittedIds)assert(inventory.objects.some(o=>o.id===id),'Unknown omitted object '+id);
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});

async function snapshot(doc){
 const jsonDoc=await io.writeJSON(doc),json=jsonDoc.json;
 // Resolve texture indices to actual image bytes and sampler settings, so
 // document pool reindexing cannot hide material or texture changes.
 const materialValue=value=>{
  if(Array.isArray(value))return value.map(materialValue);
  if(!value||typeof value!=='object')return value;
  return Object.fromEntries(Object.entries(value).map(([key,v])=>{
   if(/texture$/i.test(key)&&v&&typeof v==='object'&&Number.isInteger(v.index)){
    const t=json.textures[v.index],im=json.images[t.source];
    if(!im.uri||!jsonDoc.resources[im.uri])throw Error('Expected self-contained candidate texture');
    return [key,{...v,index:{imageSha256:hash(jsonDoc.resources[im.uri]),sampler:json.samplers?.[t.sampler]??null}}];
   }
   return [key,materialValue(v)];
  }));
 };
 const materials=doc.getRoot().listMaterials();
 const meshes=doc.getRoot().listMeshes().map(m=>({name:m.getName(),primitives:m.listPrimitives().map(p=>({
  mode:p.getMode(),material:materialValue(json.materials?.[materials.indexOf(p.getMaterial())]??null),
  attributes:Object.fromEntries(p.listSemantics().sort().map(s=>{const a=p.getAttribute(s),v=a.getArray();return [s,{type:a.getType(),normalized:a.getNormalized(),componentType:a.getComponentType(),sha256:hash(Buffer.from(v.buffer,v.byteOffset,v.byteLength))}];})),
  indices:p.getIndices()?Array.from(p.getIndices().getArray()):null,
 }))}));
 const nodes=doc.getRoot().listNodes().filter(n=>n.getMesh()).map(n=>({name:n.getName(),mesh:n.getMesh().getName(),worldMatrix:n.getWorldMatrix()}));
 return {meshes,nodes};
}

const merged=new Document(),scene=merged.createScene('Hangzhou selected detail candidates');merged.getRoot().setDefaultScene(scene);
const inputs={[inventoryFile]:sha(inventoryFile),[foundationFile]:sha(foundationFile)},selected=[],expected={meshes:[],nodes:[]};
const meshNames=new Set(),nodeNames=new Set();let triangles=0;
async function add(file,id,expectedSha,expectedTriangles){
 assert.equal(sha(file),expectedSha,'Changed selected artifact '+id);inputs[file]=expectedSha;
 const doc=await io.read(file);assert.equal(doc.getRoot().listScenes().length,1,'One source scene expected');
 assert.equal(doc.getRoot().listAnimations().length,0,'Static landmark assembly only');
 const before=await snapshot(doc);let count=0;
 for(const m of before.meshes){assert(!meshNames.has(m.name),'Duplicate mesh '+m.name);meshNames.add(m.name);for(const p of m.primitives){assert.equal(p.mode,4);assert(p.indices,'Indexed source required');count+=p.indices.length/3;}}
 for(const n of before.nodes){assert(!nodeNames.has(n.name),'Duplicate node '+n.name);nodeNames.add(n.name);}
 assert.equal(count,expectedTriangles,'Selected triangle count drift '+id);triangles+=count;
 expected.meshes.push(...before.meshes);expected.nodes.push(...before.nodes);
 const mapped=mergeDocuments(merged,doc),copyScene=mapped.get(doc.getRoot().listScenes()[0]);
 for(const child of copyScene.listChildren())scene.addChild(child);
 copyScene.dispose();selected.push({id,file,sha256:expectedSha,triangles:count,meshes:before.meshes.length});
}
for(const object of inventory.objects){
 if(omittedIds.includes(object.id))continue;
 assert.equal(sha(object.deliveryFile),object.deliverySha256);inputs[object.deliveryFile]=object.deliverySha256;
 const delivery=read(object.deliveryFile);
 for(const [fileKey,hashKey] of [['sourceModule','sourceModuleSha256'],['spec','specSha256']]){assert.equal(sha(delivery[fileKey]),delivery[hashKey]);inputs[delivery[fileKey]]=delivery[hashKey];}
 await add(object.artifact,object.id,object.artifactSha256,object.stats.triangles);
}
for(const asset of foundation.assets)await add(path.join(foundationDir,asset.file),'foundations:'+asset.file,asset.sha256,asset.triangles);
await merged.transform(unpartition());
assert.deepEqual(await snapshot(merged),expected,'In-memory assembly must preserve all source attributes, materials and world transforms');
fs.mkdirSync(output);const target=path.join(output,'landmark-detail.glb');await io.write(target,merged);
assert.deepEqual(await snapshot(await io.read(target)),expected,'Actual GLB round trip must preserve selected source contents');
const asset={file:'landmark-detail.glb',bytes:fs.statSync(target).size,triangles,meshes:expected.meshes.length,sha256:sha(target)};
const report={schemaVersion:1,cityId:'hangzhou',kind:'merged-selected-landmark-candidate',selected,omittedIds,inputs,builderSha256:sha('scripts/merge_hangzhou_landmarks.mjs'),assets:[asset],checks:{selectedAttributesExact:true,selectedIndicesExact:true,selectedMaterialAndTextureContentExact:true,selectedWorldMatricesExact:true},active:false,pending:['selected object full scope and floor/contact acceptance','omitted object replacements and source bridge/deck ownership','detail JSON/geography/collision/arrival integration','real browser three views, day/night and performance']};
fs.writeFileSync(path.join(output,'asset-manifest.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({asset,selected:selected.map(s=>s.id),omittedIds,checks:report.checks},null,2));
