/** Reuse the proven occupied bounds only for LOD distance, preserving the
 * original six meshes per parent instead of creating 117 child draws. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const root=process.cwd(),base=path.resolve(process.argv[2]??''),out=path.resolve(process.argv[3]??'');assert(process.argv[2]&&process.argv[3]&&base.startsWith(root+path.sep)&&out.startsWith(root+path.sep)&&!fs.existsSync(out));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),json=p=>JSON.parse(fs.readFileSync(p)),parentStage=json(path.join(base,'staging.json')),oldIndex=json(path.join(base,'index.json')),parent=parentStage.parent;
const partition={...json(path.join(base,oldIndex.sourcePartitions[0].file)),representationMode:'whole-parent'},outputs=[],links=[];
function put(file,doc){const bytes=Buffer.from(JSON.stringify(doc)+'\n');outputs.push({file,bytes});return {file,bytes:bytes.length,sha256:hash(bytes)};}
const part=put(oldIndex.sourcePartitions[0].file,partition),sourceAssets={},packs=[];
const nearFile='artifacts/cities/hangzhou/stream-mesh-v2/buildings/'+parent.file,farBase='artifacts/cities/hangzhou/far-lod-investigation-v1/semantic-lod-v1',farProof=json(farBase+'/delivery-manifest.json');assert.equal(farProof.source.sha256,parent.sha256);assert(farProof.exactRetainedAttributes&&farProof.allVerticalBoundsExact);
const textures=oldIndex.textures.filter(t=>t.file.startsWith('textures/buildings-'));
for(const quality of ['near','far']){
 const record=quality==='near'?parent:farProof.output,inputFile=quality==='near'?nearFile:farBase+'/candidate/'+record.file,input=fs.readFileSync(inputFile);assert.equal(input.length,record.bytes);assert.equal(hash(input),record.sha256);
 const oldSize=input.readUInt32LE(12),oldBin=20+oldSize,doc=JSON.parse(input.subarray(20,oldBin));assert.equal(doc.nodes.length,6);assert.equal(doc.images.length,textures.length);
 for(const [i,img] of doc.images.entries()){const file=path.resolve(path.dirname(inputFile),img.uri),b=fs.readFileSync(file);assert.equal(hash(b),textures[i].sha256);img.uri='../'+textures[i].file;}
 const raw=Buffer.from(JSON.stringify(doc)),size=(raw.length+3)&~3,bytes=Buffer.alloc(20+size+input.length-oldBin);input.copy(bytes,0,0,20);bytes.writeUInt32LE(bytes.length,8);bytes.writeUInt32LE(size,12);bytes.fill(32,20,20+size);raw.copy(bytes,20);input.copy(bytes,20+size,oldBin);
 const id=quality+'-buildings--1--2-parent',file='tiles/'+id+'.glb',member={id:parent.id,role:'buildings',quality,referenceSha256:parent.sha256,sourceSha256:record.sha256};
 const metadata={schemaVersion:1,kind:'physical-base-pack',id,file,bytes:bytes.length,sha256:hash(bytes),logicalBytes:record.logicalBytes,triangles:record.triangles,bounds:parent.bounds,textures,members:[member],nodes:doc.nodes.map(n=>({name:n.name,member:parent.id,role:'buildings',quality})),materialOrigins:doc.materials.map((record,index)=>({role:'buildings',index,record})),sourceAsset:{file:inputFile,sha256:record.sha256},scope:'single parent pilot; preserved original mesh batching'};
 const m=put('metadata/'+id+'.json',metadata);outputs.push({file,bytes});packs.push({id,file,bytes:metadata.bytes,sha256:metadata.sha256,logicalBytes:metadata.logicalBytes,triangles:metadata.triangles,bounds:parent.bounds,members:[{id:parent.id,quality,referenceSha256:parent.sha256}],metadata:m});sourceAssets[id]={file:inputFile,sha256:record.sha256};
}
const index={...oldIndex,scope:'single audited parent pilot using occupied-region LOD only',sourcePartitions:[part],chunks:[put('index/0.json',{schemaVersion:1,packs})],totals:{packs:2,nearMembers:1,representations:2}},indexRecord=put('index.json',index);
for(const t of index.textures)links.push({file:t.file,path:path.join(base,t.file)});links.push({file:partition.geometryCoverage.file,path:path.join(base,partition.geometryCoverage.file)});for(const c of partition.children)links.push({file:c.file,path:path.join(base,c.file)});
put('staging.json',{schemaVersion:1,parent,index:indexRecord,sourceAssets,sourcePartition:{file:path.relative(root,path.join(base,oldIndex.sourcePartitions[0].file)),sha256:oldIndex.sourcePartitions[0].sha256},sourceFarProof:{file:farBase+'/delivery-manifest.json',sha256:hash(fs.readFileSync(farBase+'/delivery-manifest.json'))},actualMeshCountPerQuality:6,mainCityInstalled:false,browserAccepted:false});
for(const item of outputs){const file=path.join(out,item.file);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,item.bytes,{flag:'wx'});}
for(const item of links){const file=path.join(out,item.file);fs.mkdirSync(path.dirname(file),{recursive:true});fs.symlinkSync(path.relative(path.dirname(file),item.path),file);}
console.log(JSON.stringify({output:path.relative(root,out),index:indexRecord,packs:packs.map(p=>({id:p.id,bytes:p.bytes,triangles:p.triangles,actualMeshes:6})),mainCityInstalled:false}));
