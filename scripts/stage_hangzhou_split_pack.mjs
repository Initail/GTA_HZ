/** Adapt the audited parent-tile near/far candidate to the runtime wire format.
 * It remains a parent-only pilot: the real main-city index rejects its missing
 * 1911 source tiles. Only image URIs change; all binary/model data is exact. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),root=process.cwd(),inputs=[];
const json=(file,max=256*1024)=>{assert(fs.statSync(file).size<=max);const bytes=fs.readFileSync(file);inputs.push({file:path.relative(root,file),bytes:bytes.length,sha256:hash(bytes)});return {doc:JSON.parse(bytes),bytes,sha256:hash(bytes)};};
const candidate=path.resolve(process.argv[2]??''),out=path.resolve(process.argv[3]??'');
assert(process.argv[2]&&process.argv[3]&&candidate.startsWith(root+path.sep)&&out.startsWith(root+path.sep)&&!fs.existsSync(out));
const release=json(path.join(root,'artifacts/cities/hangzhou/stream-release-v1/descriptor.json')).doc,sourceManifests={},layers={},textures=[],links=[];
for(const role of ['terrain','roads','buildings']){
 const r=release.models[role],file=path.join(root,r.manifestPath),m=json(file);assert.equal(m.sha256,r.manifestSha256);assert.equal(m.bytes.length,r.manifestBytes);sourceManifests[role]=m.sha256;layers[role]=m.doc;
 for(const t of m.doc.textures){const p=path.join(path.dirname(file),t.file);assert.equal(fs.statSync(p).size,t.bytes);assert.equal(hash(fs.readFileSync(p)),t.sha256);textures.push(t);links.push({file:t.file,path:p});}
}
const source=json(path.join(candidate,'partition.json')),p=source.doc,parent=layers.buildings.tiles.find(t=>t.id===p.parent.id);assert(parent&&parent.sha256===p.parent.sha256);
const audit=path.resolve(candidate,p.geometryCoverage.file);assert.equal(fs.statSync(audit).size,p.geometryCoverage.bytes);assert.equal(hash(fs.readFileSync(audit)),p.geometryCoverage.sha256);links.push({file:'evidence/near-coverage.json',path:audit});
const partition={schemaVersion:1,kind:'city-base-source-partition',parent:p.parent,geometryCoverage:{...p.geometryCoverage,file:'evidence/near-coverage.json'},sourcePartitionSha256:source.sha256,children:p.children.map(c=>{
 const name=c.id.slice(parent.id.length+1);assert(/^[a-zA-Z0-9_-]+$/.test(name));const file='groups/'+name+'/group.glb',asset=path.resolve(candidate,c.file);
 assert.equal(fs.statSync(asset).size,c.bytes);assert.equal(hash(fs.readFileSync(asset)),c.sha256);links.push({file,path:asset});return {...c,file};
})};
const outputs=[],write=(file,doc)=>{const bytes=Buffer.from(JSON.stringify(doc)+'\n');outputs.push({file,bytes});return {file,bytes:bytes.length,sha256:hash(bytes)};};
const partitionRecord=write('partitions/buildings--1--2.json',partition),packs=[];
for(const quality of ['near','far']){
 const base=path.join(candidate,'packs/all-'+quality),raw=json(path.join(base,'descriptor.json')),d=raw.doc,v=json(path.join(base,'verification.json')).doc;
 assert(v.pass&&v.packSha256===d.sha256&&v.descriptorSha256===raw.sha256&&v.allChildAttributesAndOrientedTrianglesExact&&v.allChildNodeTransformsExact&&v.uniqueNamesPreserveParentBlockPrefix);
 const input=fs.readFileSync(path.join(base,'pack.glb'));assert(input.length<=8*1024*1024&&input.length===d.bytes&&hash(input)===d.sha256);
 const oldJson=input.readUInt32LE(12),oldBin=20+oldJson,doc=JSON.parse(input.subarray(20,oldBin));assert.equal(doc.images.length,d.textures.length);
 const packTextures=d.textures.map((t,i)=>{const expected=layers.buildings.textures[i];assert(expected&&expected.bytes===t.bytes&&expected.sha256===t.sha256&&doc.images[i].uri===t.uri);doc.images[i].uri='../'+expected.file;return expected;});
 const encoded=Buffer.from(JSON.stringify(doc)),size=(encoded.length+3)&~3,bytes=Buffer.alloc(20+size+input.length-oldBin);input.copy(bytes,0,0,20);bytes.writeUInt32LE(bytes.length,8);bytes.writeUInt32LE(size,12);bytes.fill(32,20,20+size);encoded.copy(bytes,20);input.copy(bytes,20+size,oldBin);
 assert(bytes.subarray(20+size).equals(input.subarray(oldBin)),'Binary chunk changed');
 const id=quality+'-buildings--1--2-split',file='tiles/'+id+'.glb';outputs.push({file,bytes});
 const metadata={...d,id,file,bytes:bytes.length,sha256:hash(bytes),actualBounds:d.bounds,bounds:parent.bounds,textures:packTextures,sourceDescriptorSha256:raw.sha256,sourceGlbSha256:d.sha256,adaptation:'Only image URI relocation and conservative source bounds; all BIN bytes and other GLB JSON unchanged'};
 const metaRecord=write('metadata/'+id+'.json',metadata);assert(metaRecord.bytes<=128*1024);
 packs.push({id,file,bytes:metadata.bytes,sha256:metadata.sha256,logicalBytes:d.logicalBytes,triangles:d.triangles,bounds:parent.bounds,members:d.members.map(m=>({id:m.id,quality:m.quality,referenceSha256:m.referenceSha256})),metadata:metaRecord});
}
const chunk=write('index/0.json',{schemaVersion:1,packs}),index={schemaVersion:1,kind:'city-base-pack-index',scope:'single audited parent pilot; main-city coverage is incomplete',sourceManifests,textures,sourcePartitions:[partitionRecord],chunks:[chunk],totals:{packs:2,nearMembers:partition.children.length,representations:partition.children.length*2}};
const indexRecord=write('index.json',index);
write('staging.json',{schemaVersion:1,scope:index.scope,inputs,index:indexRecord,parent:{...parent,role:'buildings'},sourceCandidate:path.relative(root,candidate),binaryPayloadsExact:true,imageFilesCopied:0,mainCityInstalled:false,browserAccepted:false});
for(const item of outputs){const file=path.join(out,item.file);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,item.bytes,{flag:'wx'});}
for(const item of links){const file=path.join(out,item.file);fs.mkdirSync(path.dirname(file),{recursive:true});fs.symlinkSync(path.relative(path.dirname(file),item.path),file);}
console.log(JSON.stringify({output:path.relative(root,out),index:indexRecord,children:partition.children.length,packs:packs.map(p=>({id:p.id,bytes:p.bytes,triangles:p.triangles})),mainCityInstalled:false}));
