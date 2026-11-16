/** Build a complete, hash-bound near-pack catalog from finished per-pack jobs.
 * Assets are linked, not copied or decoded. This proves index coverage only;
 * runtime validates asset hashes again, and the full-view cost gate stays shut.
 * Run under run_hangzhou_bounded.py. No existing output is overwritten. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const json=(file,max)=>{assert(fs.statSync(file).size<=max,'JSON input budget');const bytes=fs.readFileSync(file);return {bytes,doc:JSON.parse(bytes),sha256:hash(bytes)};};
const inside=(base,file)=>{const resolved=path.resolve(base,file);assert(resolved.startsWith(base+path.sep),'Path outside candidate');return resolved;};
const root=process.cwd(),planFile=path.resolve(process.argv[2]),base=path.dirname(planFile),output=path.resolve(process.argv[3]);
assert(output.startsWith(root+path.sep)&&!fs.existsSync(output),'Fresh repository candidate required');
const plan=json(planFile,1024*1024);assert(plan.doc.schemaVersion===1&&plan.doc.kind==='base-pack-task-plan'&&plan.doc.tasks.length>0&&plan.doc.tasks.length<=2048);
const sources=new Map(),sourceManifests={},textures=[],textureSources=new Map();
for(const role of ['terrain','roads','buildings']){
 const bound=plan.doc.sources[role],file=inside(root,bound.manifest),data=json(file,256*1024);assert.equal(data.bytes.length,bound.bytes);assert.equal(data.sha256,bound.sha256);assert.equal(data.doc.role,role);sourceManifests[role]=bound.sha256;
 for(const tile of data.doc.tiles){assert(tile.id.startsWith(role+':')&&!sources.has(tile.id));sources.set(tile.id,{...tile,role});}
 for(const texture of data.doc.textures){assert(new RegExp('^textures/'+role+'-\\d+\\.jpg$').test(texture.file)&&!textureSources.has(texture.file));textures.push(texture);textureSources.set(texture.file,{record:texture,path:inside(path.dirname(file),texture.file)});}
}
assert(textures.length<=8&&textures.reduce((n,t)=>n+t.bytes,0)<=2*1024*1024);
const seen=new Set(),ids=new Set(),packs=[],assets=[];
for(const entry of plan.doc.tasks){
 assert(/^near-[a-zA-Z0-9_-]+$/.test(entry.id)&&!ids.has(entry.id));ids.add(entry.id);
 const taskFile=inside(base,entry.task),task=json(taskFile,64*1024);assert.equal(task.sha256,entry.sha256);assert.equal(task.doc.id,entry.id);
 const directory=path.join(path.dirname(taskFile),'output'),descriptorFile=path.join(directory,'descriptor.json'),descriptor=json(descriptorFile,128*1024),d=descriptor.doc;
 assert(d.schemaVersion===1&&d.kind==='physical-base-pack'&&d.id===entry.id&&d.taskSha256===entry.sha256&&d.physicalContainers===1);
 assert(d.file==='tiles/'+entry.id+'.glb'&&d.members.length===entry.members&&d.members.length===task.doc.members.length&&d.members.length<=48);
 assert(Number.isSafeInteger(d.bytes)&&d.bytes>0&&d.bytes<=8*1024*1024&&/^[0-9a-f]{64}$/.test(d.sha256));
 assert(Number.isSafeInteger(d.logicalBytes)&&d.logicalBytes>=0&&d.logicalBytes<=32*1024*1024&&Number.isSafeInteger(d.triangles)&&d.triangles>=0);
 assert(d.bounds?.min.length===3&&d.bounds?.max.length===3&&d.bounds.min.every((v,i)=>Number.isFinite(v)&&Number.isFinite(d.bounds.max[i])&&v<=d.bounds.max[i]));
 const members=d.members.map((member,i)=>{
  const original=sources.get(member.id),taskMember=task.doc.members[i];
  assert(original&&!seen.has(member.id)&&member.quality==='near'&&member.role===original.role&&member.id===taskMember.id);
  assert.equal(member.sourceSha256,original.sha256);assert.equal(member.referenceSha256,original.sha256);assert.equal(taskMember.sha256,original.sha256);assert.equal(taskMember.manifestSha256,sourceManifests[member.role]);
  assert.equal(member.sourceBytes,original.bytes);assert.equal(member.logicalBytes,original.logicalBytes);assert.equal(member.triangles,original.triangles);
  assert(original.bounds.min.every((v,j)=>d.bounds.min[j]<=v&&d.bounds.max[j]>=original.bounds.max[j]));seen.add(member.id);
  return {id:member.id,quality:'near',referenceSha256:original.sha256};
 });
 assert.equal(d.logicalBytes,d.members.reduce((n,m)=>n+m.logicalBytes,0));assert.equal(d.triangles,d.members.reduce((n,m)=>n+m.triangles,0));
 assert(d.textures.every(t=>{const expected=textureSources.get(t.file)?.record;return expected&&t.bytes===expected.bytes&&t.sha256===expected.sha256;}));
 const asset=inside(directory,d.file);assert.equal(fs.statSync(asset).size,d.bytes);
 const metadata={file:'metadata/'+entry.id+'.json',bytes:descriptor.bytes.length,sha256:descriptor.sha256};
 packs.push({id:entry.id,file:d.file,bytes:d.bytes,sha256:d.sha256,logicalBytes:d.logicalBytes,triangles:d.triangles,bounds:d.bounds,members,metadata});
 assets.push({file:d.file,path:asset},{file:metadata.file,path:descriptorFile});
}
assert.equal(seen.size,sources.size,'Original near coverage incomplete');assert.equal(seen.size,plan.doc.nearMembers);
for(const [file,source] of textureSources){assert.equal(fs.statSync(source.path).size,source.record.bytes);assert.equal(hash(fs.readFileSync(source.path)),source.record.sha256);assets.push({file,path:source.path});}
// Validate every shard before creating output. Packs are small records; the
// separate metadata retains the larger node/material audit information.
const shards=[];
for(let at=0;at<packs.length;at+=64){const bytes=Buffer.from(JSON.stringify({schemaVersion:1,packs:packs.slice(at,at+64)})+'\n');assert(bytes.length<=256*1024);shards.push({file:'index/'+shards.length+'.json',bytes,sha256:hash(bytes)});}
assert(shards.length<=64);
const index={schemaVersion:1,kind:'city-base-pack-index',sourceManifests,textures,chunks:shards.map(s=>({file:s.file,bytes:s.bytes.length,sha256:s.sha256})),totals:{packs:packs.length,nearMembers:seen.size,representations:seen.size}};
const indexBytes=Buffer.from(JSON.stringify(index)+'\n');assert(indexBytes.length<=64*1024);
fs.mkdirSync(output,{recursive:true});for(const folder of ['index','metadata','tiles','textures'])fs.mkdirSync(path.join(output,folder));
for(const asset of assets)fs.symlinkSync(path.relative(path.dirname(path.join(output,asset.file)),asset.path),path.join(output,asset.file));
for(const shard of shards)fs.writeFileSync(path.join(output,shard.file),shard.bytes,{flag:'wx'});
fs.writeFileSync(path.join(output,'index.json'),indexBytes,{flag:'wx'});
const report={schemaVersion:1,kind:'base-pack-index-preparation',planSha256:plan.sha256,index:{file:'index.json',bytes:indexBytes.length,sha256:hash(indexBytes)},counts:index.totals,sourceManifests,assetStorage:'relative symlinks to immutable hash-bound candidates; materialize for standalone export',glbPayloadsRehashed:false,fullViewCostPassed:false,browserValidated:false,runtimeInstalled:false};
fs.writeFileSync(path.join(output,'preparation.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report));
