/** One independently bounded physical near pack. Never loops over the city.
 * The full-view representation/cost gate is deliberately separate. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {mergeStreamGlbs} from './merge_hangzhou_stream_glbs.mjs';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const root=process.cwd(),taskFile=path.resolve(process.argv[2]),output=path.join(path.dirname(taskFile),'output');
assert(!fs.existsSync(output),'Fresh candidate output required');assert(fs.statSync(taskFile).size<=64*1024);
const taskBytes=fs.readFileSync(taskFile),task=JSON.parse(taskBytes);
assert(task.schemaVersion===1&&/^near-[a-zA-Z0-9_-]+$/.test(task.id)&&task.members.length>0&&task.members.length<=48);
const manifests=new Map();
const inputs=task.members.map(member=>{
 assert(['terrain','roads','buildings'].includes(member.role)&&member.quality==='near','Far representations require their own verified source-binding contract');
 const file=path.resolve(root,member.manifest);assert(file.startsWith(root+path.sep));
 let manifest=manifests.get(file);if(!manifest){assert(fs.statSync(file).size<=256*1024);const raw=fs.readFileSync(file);assert.equal(hash(raw),member.manifestSha256);manifest={doc:JSON.parse(raw),sha256:hash(raw)};manifests.set(file,manifest);}
 assert.equal(manifest.sha256,member.manifestSha256);assert.equal(manifest.doc.role,member.role);
 const record=manifest.doc.tiles.find(t=>t.id===member.id);assert(record);assert.equal(record.sha256,member.sha256);
 const asset=path.resolve(path.dirname(file),record.file);assert(asset.startsWith(path.dirname(file)+path.sep));assert.equal(fs.statSync(asset).size,record.bytes);assert(record.bytes<=8*1024*1024);
 return {...member,record,asset,textures:manifest.doc.textures,base:path.dirname(file)};
});
assert(inputs.reduce((n,i)=>n+i.record.bytes,0)<=8*1024*1024,'Input physical budget');
for(const input of inputs)input.bytes=fs.readFileSync(input.asset);
const merged=mergeStreamGlbs(inputs);assert(merged.descriptor.nodes.length<=512,'Runtime node budget');
const descriptor={...merged.descriptor,id:task.id,file:'tiles/'+task.id+'.glb',taskSha256:hash(taskBytes),packerSha256:hash(fs.readFileSync(new URL('./merge_hangzhou_stream_glbs.mjs',import.meta.url))),writerSha256:hash(fs.readFileSync(new URL('./build_hangzhou_stream_pack.mjs',import.meta.url)))};
// Original members are exact near geometry. Keep both representation identity
// and original source identity explicit for the runtime index.
for(const member of descriptor.members)member.referenceSha256=member.sourceSha256;
const metadata=Buffer.from(JSON.stringify(descriptor)+'\n');assert(metadata.length<=128*1024);
fs.mkdirSync(path.join(output,'tiles'),{recursive:true});fs.mkdirSync(path.join(output,'textures'));
const textures=new Map();for(const input of inputs)for(const texture of input.textures){
 assert(new RegExp('^textures/'+input.role+'-\\d+\\.jpg$').test(texture.file));
 const old=textures.get(texture.file);if(old){assert.deepEqual(old,texture);continue;}
 const source=path.resolve(input.base,texture.file);assert(source.startsWith(input.base+path.sep));assert(texture.bytes<=1024*1024);assert.equal(fs.statSync(source).size,texture.bytes);const bytes=fs.readFileSync(source);assert.equal(hash(bytes),texture.sha256);fs.writeFileSync(path.join(output,texture.file),bytes,{flag:'wx'});textures.set(texture.file,texture);
}
fs.writeFileSync(path.join(output,descriptor.file),merged.bytes,{flag:'wx'});
fs.writeFileSync(path.join(output,'descriptor.json'),metadata,{flag:'wx'});
console.log(JSON.stringify({output,id:task.id,members:inputs.length,physicalContainers:1,bytes:descriptor.bytes,triangles:descriptor.triangles,fullViewCostPassed:false,browserValidated:false}));
