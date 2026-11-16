/** Independent small-candidate decode; never loads the source city with NodeIO. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
const [directory]=process.argv.slice(2),report=JSON.parse(fs.readFileSync(path.join(directory,'extraction.json'))),source=report.source;
assert(!fs.existsSync(path.join(directory,'decoded-validation.json')),'Preserve existing validation');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const fd=fs.openSync(source,'r');function read(start,n){assert(n>=0&&n<=64*1024*1024);const b=Buffer.alloc(n);assert.equal(fs.readSync(fd,b,0,n,start),n);return b;}
function parseFile(file){const fd=fs.openSync(file,'r'),head=Buffer.alloc(20);fs.readSync(fd,head,0,20,0);const n=head.readUInt32LE(12);assert(n<=16*1024*1024);const bytes=Buffer.alloc(n);fs.readSync(fd,bytes,0,n,20);fs.closeSync(fd);return {json:JSON.parse(bytes),bin:20+n+8};}
const original=parseFile(source),target=parseFile(report.output.file),doc=original.json;
assert.deepEqual(target.json.materials,doc.materials);assert.deepEqual(target.json.textures,doc.textures);assert.deepEqual(target.json.samplers,doc.samplers);
await MeshoptDecoder.ready;
const cache=new Map();let decodedBytes=0;
function accessorBytes(id){
 const a=doc.accessors[id],v=doc.bufferViews[a.bufferView],ext=v.extensions?.EXT_meshopt_compression;
 if(!cache.has(a.bufferView)){
  let buffer;
  if(ext){assert.equal(ext.buffer,0);assert(ext.count*ext.byteStride<=64*1024*1024);buffer=new Uint8Array(ext.count*ext.byteStride);MeshoptDecoder.decodeGltfBuffer(buffer,ext.count,ext.byteStride,read(original.bin+(ext.byteOffset??0),ext.byteLength),ext.mode,ext.filter);}
  else{assert.equal(v.buffer,0);buffer=read(original.bin+(v.byteOffset??0),v.byteLength);}
  decodedBytes+=buffer.byteLength;assert(decodedBytes<=64*1024*1024);cache.set(a.bufferView,buffer);
 }
 const buffer=cache.get(a.bufferView),component={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a.componentType],arity={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type];assert(component&&arity);
 const size=component*arity,stride=v.byteStride??size,start=a.byteOffset??0,result=Buffer.alloc(a.count*size);
 assert(start+(a.count-1)*stride+size<=buffer.byteLength);
 for(let i=0;i<a.count;i++)result.set(buffer.subarray(start+i*stride,start+i*stride+size),i*size);
 return result;
}
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder}),small=await io.read(report.output.file);
let attributes=0,indices=0,triangles=0;
const checks=[];
for(const row of report.nodes){
 const node=doc.nodes[row.sourceNode],actualNode=target.json.nodes.find(n=>n.name===node.name);assert(actualNode);
 const transform=n=>Object.fromEntries(Object.entries(n).filter(([k])=>k!=='mesh'));
 assert.deepEqual(transform(actualNode),transform(node));
 const mesh=small.getRoot().listNodes().find(n=>n.getName()===node.name)?.getMesh();assert(mesh);
 const primitives=doc.meshes[node.mesh].primitives;assert.equal(mesh.listPrimitives().length,primitives.length);
 for(const [i,p] of primitives.entries()){
  const actual=mesh.listPrimitives()[i];
  for(const [semantic,id] of Object.entries({...p.attributes,INDICES:p.indices})){
   const a=semantic==='INDICES'?actual.getIndices():actual.getAttribute(semantic);assert(a);const raw=a.getArray(),bytes=Buffer.from(raw.buffer,raw.byteOffset,raw.byteLength),expected=accessorBytes(id);
   assert.equal(sha(bytes),sha(expected),node.name+':'+semantic);assert.equal(a.getComponentType(),doc.accessors[id].componentType);assert.equal(a.getNormalized(),doc.accessors[id].normalized??false);
   checks.push({node:node.name,primitive:i,semantic,count:a.getCount(),sha256:sha(bytes)});
   if(semantic==='INDICES'){indices++;triangles+=a.getCount()/3;}else attributes++;
  }
 }
}
for(const [i,image] of doc.images.entries()){
 const view=doc.bufferViews[image.bufferView];assert.equal(view.buffer,0);
 const actual=fs.readFileSync(path.join(directory,target.json.images[i].uri));assert.equal(sha(actual),sha(read(original.bin+(view.byteOffset??0),view.byteLength)));
}
fs.closeSync(fd);
// Stream the source hash, without holding its binary body in memory.
const hash=crypto.createHash('sha256');for await(const bytes of fs.createReadStream(source,{highWaterMark:1024*1024}))hash.update(bytes);
const result={pass:true,sourceSha256:hash.digest('hex'),targetSha256:sha(fs.readFileSync(report.output.file)),nodes:report.nodes.length,attributes,indices,triangles,decodedSourceViewBytes:decodedBytes,checks,
 scope:'Actual small GLB decoded by locked glTF-Transform/meshoptimizer; all attribute/index bytes match source accessor slices; node transforms/material JSON/texture bytes unchanged. No Babylon GPU, streaming runtime or visual claim.'};
fs.writeFileSync(path.join(directory,'decoded-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,checks:undefined}));
