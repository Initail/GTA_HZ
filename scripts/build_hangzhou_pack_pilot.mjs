import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {mergeStreamGlbs} from './merge_hangzhou_stream_glbs.mjs';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const root=process.cwd(),taskFile=path.resolve(process.argv[2]),taskBytes=fs.readFileSync(taskFile),task=JSON.parse(taskBytes),output=path.join(path.dirname(taskFile),'output');
assert(task.schemaVersion===1&&task.members.length===3);assert(!fs.existsSync(output),'Fresh output only');
const inputs=task.members.map(member=>{
 const file=path.resolve(root,member.manifest),raw=fs.readFileSync(file);assert.equal(sha(raw),member.manifestSha256);const manifest=JSON.parse(raw);assert.equal(manifest.role,member.role);
 const record=manifest.tiles.find(t=>t.id===member.id);assert(record);assert.equal(record.sha256,member.sha256);const bytes=fs.readFileSync(path.join(path.dirname(file),record.file));
 return {...member,record,bytes,textures:manifest.textures,base:path.dirname(file)};
});
const merged=mergeStreamGlbs(inputs);fs.mkdirSync(path.join(output,'tiles'),{recursive:true});fs.mkdirSync(path.join(output,'textures'));
for(const input of inputs)for(const texture of input.textures){const bytes=fs.readFileSync(path.join(input.base,texture.file));assert.equal(bytes.length,texture.bytes);assert.equal(sha(bytes),texture.sha256);fs.writeFileSync(path.join(output,texture.file),bytes,{flag:'wx'});}
const file='tiles/'+task.id+'.glb';fs.writeFileSync(path.join(output,file),merged.bytes,{flag:'wx'});
const descriptor={...merged.descriptor,id:task.id,file,taskSha256:sha(taskBytes),packerSha256:sha(fs.readFileSync(new URL('./merge_hangzhou_stream_glbs.mjs',import.meta.url)))};
fs.writeFileSync(path.join(output,'descriptor.json'),JSON.stringify(descriptor,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,bytes:descriptor.bytes,logicalBytes:descriptor.logicalBytes,triangles:descriptor.triangles,physicalContainers:1,logicalMembers:3,fullCoverage:false}));
