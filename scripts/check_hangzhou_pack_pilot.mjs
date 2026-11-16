/** Independent packing proof: invert all reference offsets and compare source
 * payload ranges and complete node/material/attribute metadata exactly. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function glb(bytes){assert.equal(bytes.readUInt32LE(0),0x46546c67);assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);const n=bytes.readUInt32LE(12),at=28+n;assert.equal(bytes.readUInt32LE(16),0x4e4f534a);assert.equal(bytes.readUInt32LE(at-4),0x004e4942);assert.equal(at+bytes.readUInt32LE(at-8),bytes.length);return {json:JSON.parse(bytes.subarray(20,20+n)),bin:bytes.subarray(at)};}
const root=process.cwd(),taskFile=path.resolve(process.argv[2]),dir=path.join(path.dirname(taskFile),'output'),report=path.join(path.dirname(taskFile),'pack-verification-v1.json');assert(!fs.existsSync(report));
const taskRaw=fs.readFileSync(taskFile),task=JSON.parse(taskRaw),descriptorRaw=fs.readFileSync(path.join(dir,'descriptor.json')),desc=JSON.parse(descriptorRaw),targetRaw=fs.readFileSync(path.join(dir,desc.file)),target=glb(targetRaw);
assert.equal(sha(taskRaw),desc.taskSha256);assert.equal(sha(targetRaw),desc.sha256);assert.equal(targetRaw.length,desc.bytes);
assert.equal(desc.members.length,task.members.length);assert.equal(desc.physicalContainers,1);assert.equal(target.json.scenes.length,1);assert.equal(target.json.nodes.length,desc.nodes.length);
const used={nodes:new Set(),meshes:new Set(),accessors:new Set(),views:new Set()},evidence=[];let triangles=0,logical=0;
for(const [memberIndex,requested] of task.members.entries()){
 const manifestPath=path.resolve(root,requested.manifest),manifestRaw=fs.readFileSync(manifestPath);assert.equal(sha(manifestRaw),requested.manifestSha256);const manifest=JSON.parse(manifestRaw),record=manifest.tiles.find(t=>t.id===requested.id),member=desc.members[memberIndex];assert.equal(member.id,record.id);assert.equal(member.role,requested.role);assert.equal(member.quality,requested.quality);
 const raw=fs.readFileSync(path.join(path.dirname(manifestPath),record.file));assert.equal(sha(raw),record.sha256);assert.equal(member.sourceSha256,record.sha256);const source=glb(raw),s=source.json,o=member.offsets;
 assert.deepEqual(target.bin.subarray(o.binary,o.binary+source.bin.length),source.bin,'Entire compressed and plain binary payload is byte-identical');
 const claim=(kind,index)=>{assert(!used[kind].has(index),'Duplicate member coverage');used[kind].add(index);};
 for(const [i,node] of s.nodes.entries()){
  claim('nodes',i+o.node);const copy=structuredClone(target.json.nodes[i+o.node]);copy.mesh-=o.mesh;assert.deepEqual(copy,node,'Node TRS/extras/name unchanged');
  assert.deepEqual(desc.nodes[i+o.node],{node:i+o.node,name:node.name,sourceNode:i,member:record.id,role:requested.role,quality:requested.quality});
  for(const p of s.meshes[node.mesh].primitives)triangles+=s.accessors[p.indices].count/3;
 }
 const catalogMap=new Map();
 for(const [i,mat] of s.materials.entries()){
  const matches=desc.materialOrigins.flatMap((origin,j)=>origin.role===requested.role&&origin.index===i?[j]:[]);assert.equal(matches.length,1);const at=matches[0];catalogMap.set(at,i);assert.deepEqual(desc.materialOrigins[at].record,mat);
  const copy=structuredClone(target.json.materials[at]);
  for(const [host,keys] of [[copy,['normalTexture','occlusionTexture','emissiveTexture']],[copy.pbrMetallicRoughness,['baseColorTexture','metallicRoughnessTexture']]])for(const key of keys)if(host?.[key]){
   const sourceHost=host===copy?mat:mat.pbrMetallicRoughness,old=sourceHost[key].index,current=host[key].index,a=structuredClone(target.json.textures[current]),b=s.textures[old];
   assert.deepEqual(target.json.images[a.source],s.images[b.source]);a.source=b.source;
   if(b.sampler!==undefined){assert.deepEqual(target.json.samplers[a.sampler],s.samplers[b.sampler]);a.sampler=b.sampler;}
   assert.deepEqual(a,b);host[key].index=old;
  }
  assert.deepEqual(copy,mat,'Complete material retained after texture reference rebase');
 }
 for(const [i,mesh] of s.meshes.entries()){
  claim('meshes',i+o.mesh);const copy=structuredClone(target.json.meshes[i+o.mesh]);
  for(const p of copy.primitives){p.indices-=o.accessor;for(const key of Object.keys(p.attributes))p.attributes[key]-=o.accessor;if(p.material!==undefined){assert(catalogMap.has(p.material));p.material=catalogMap.get(p.material);}}
  assert.deepEqual(copy,mesh,'Complete primitive/attribute/index identity');
 }
 for(const [i,accessor] of s.accessors.entries()){claim('accessors',i+o.accessor);const copy=structuredClone(target.json.accessors[i+o.accessor]);copy.bufferView-=o.view;assert.deepEqual(copy,accessor,'Accessor type/count/normalization/bounds unchanged');}
 for(const [i,view] of s.bufferViews.entries()){
  claim('views',i+o.view);const copy=structuredClone(target.json.bufferViews[i+o.view]);copy.byteOffset-=view.buffer===0?o.binary:o.fallback;if(view.byteOffset===undefined&&copy.byteOffset===0)delete copy.byteOffset;
  const ext=copy.extensions?.EXT_meshopt_compression;if(ext){ext.byteOffset-=o.binary;if(view.extensions.EXT_meshopt_compression.byteOffset===undefined&&ext.byteOffset===0)delete ext.byteOffset;}
  assert.deepEqual(copy,view,'Compressed stream/filter and buffer metadata unchanged');logical+=view.byteLength;
 }
 for(const texture of manifest.textures){const bytes=fs.readFileSync(path.join(dir,texture.file));assert.equal(bytes.length,texture.bytes);assert.equal(sha(bytes),texture.sha256);}
 evidence.push({id:record.id,sha256:record.sha256,sourceBinarySha256:sha(source.bin),nodes:s.nodes.length,meshPrimitives:s.meshes.reduce((n,m)=>n+m.primitives.length,0),allBinaryAndReferencesExact:true});
}
for(const [kind,key] of [['nodes','nodes'],['meshes','meshes'],['accessors','accessors'],['views','bufferViews']])assert.equal(used[kind].size,target.json[key].length,'No orphan or extra entries');
assert.deepEqual(target.json.scenes[0].nodes,Array.from({length:target.json.nodes.length},(_,i)=>i));assert.equal(triangles,desc.triangles);assert.equal(logical,desc.logicalBytes);
const result={schemaVersion:1,taskSha256:sha(taskRaw),descriptorSha256:sha(descriptorRaw),packSha256:sha(targetRaw),checkerSha256:sha(fs.readFileSync(new URL(import.meta.url))),members:evidence,totals:{triangles,logicalBytes:logical,bytes:targetRaw.length,physicalContainers:1,logicalMembers:task.members.length},exactPacking:true,geometryReduction:false,browserValidated:false,runtimeInstalled:false,fullCoverage:false};
fs.writeFileSync(report,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({exactPacking:true,...result.totals,fullCoverage:false}));
