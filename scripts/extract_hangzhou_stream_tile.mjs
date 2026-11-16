/** Bounded offline proof: extract one existing tile without decoding the city.
 * Only shared index streams are decoded; all compressed attributes stay byte-exact.
 * No NodeIO full-city read, Blender, Babylon engine, GPU, or source mutation. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {MeshoptDecoder} from 'meshoptimizer';

const [source,role,tileX,tileZ,output]=process.argv.slice(2);
assert(source&&['terrain','roads','buildings'].includes(role)&&/^-?\d+$/.test(tileX)&&/^-?\d+$/.test(tileZ)&&output);
assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
assert(!fs.existsSync(output),'Use a new candidate directory');
const limit={header:16*1024*1024,encodedRange:32*1024*1024,indexDecode:64*1024*1024,chunk:8*1024*1024};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const fd=fs.openSync(source,'r'),stat=fs.fstatSync(fd);
function read(start,length,max=limit.encodedRange){assert(Number.isSafeInteger(start)&&Number.isSafeInteger(length)&&start>=0&&length>=0&&length<=max&&start+length<=stat.size);const bytes=Buffer.alloc(length);assert.equal(fs.readSync(fd,bytes,0,length,start),length);return bytes;}
const head=read(0,20);assert.equal(head.readUInt32LE(0),0x46546c67);assert.equal(head.readUInt32LE(4),2);assert.equal(head.readUInt32LE(8),stat.size);assert.equal(head.readUInt32LE(16),0x4e4f534a);
const headerBytes=read(20,head.readUInt32LE(12),limit.header),doc=JSON.parse(headerBytes),binHeader=20+headerBytes.length;
assert.equal(read(binHeader,8).readUInt32LE(4),0x004e4942);const binStart=binHeader+8;
assert(!doc.animations?.length&&!doc.skins?.length&&!doc.extensions,'Unsupported document-level reference');
assert.equal(doc.scenes.length,1);assert.equal(doc.scenes[0].nodes.length,doc.nodes.length);assert(doc.nodes.every(n=>Number.isInteger(n.mesh)&&!n.children&&!n.camera&&!n.skin&&!n.weights));
const pattern=role==='buildings'?/^block_(-?\d+)_(-?\d+)_/:role==='roads'?/^roads_(?:site_)?(-?\d+)_(-?\d+)_/:/^terrain_(?:water_)?(-?\d+)_(-?\d+)_/;
const nodes=doc.nodes.map((node,index)=>({node,index})).filter(({node})=>{const m=node.name.match(pattern);return m&&Number(m[1])===Number(tileX)&&Number(m[2])===Number(tileZ);});
assert(nodes.length>0&&nodes.length<=64,'Tile not found or too many nodes');
const next=structuredClone(doc);next.nodes=[];next.meshes=[];next.accessors=[];next.bufferViews=[];next.buffers=[];next.images=[];next.scenes=[{...doc.scenes[0],nodes:[]}];next.scene=0;
const parts=[],accessorMap=new Map(),viewMap=new Map(),indexCache=new Map();let binaryLength=0,fallbackLength=0;
function append(bytes){const padding=(4-binaryLength%4)%4;if(padding){parts.push(Buffer.alloc(padding));binaryLength+=padding;}const offset=binaryLength;parts.push(bytes);binaryLength+=bytes.length;assert(binaryLength<=limit.chunk,'Extracted tile exceeds encoded budget');return offset;}
const evidence={source,sourceBytes:stat.size,sourceHeaderSha256:sha(headerBytes),role,tile:[Number(tileX),Number(tileZ)],nodes:[],attributes:[],indices:[],textures:[],decodedSharedIndexBytes:0};
await MeshoptDecoder.ready;
function copyView(id){
 if(viewMap.has(id))return viewMap.get(id);
 const original=doc.bufferViews[id],view=structuredClone(original),extension=view.extensions?.EXT_meshopt_compression;
 if(extension){
  assert.equal(extension.buffer,0);assert(!doc.buffers[0].uri);
  const bytes=read(binStart+(extension.byteOffset??0),extension.byteLength);
  extension.byteOffset=append(bytes);extension.buffer=0;
  assert(view.byteLength<=32*1024*1024&&fallbackLength+view.byteLength+3<=32*1024*1024,'Tile logical attribute budget');
  fallbackLength=(fallbackLength+3)&~3;view.buffer=1;view.byteOffset=fallbackLength;fallbackLength+=view.byteLength;
  evidence.attributes.push({sourceView:id,encodedSha256:sha(bytes),encodedBytes:bytes.length,logicalBytes:view.byteLength});
 }else{assert.equal(view.buffer,0);view.byteOffset=append(read(binStart+(view.byteOffset??0),view.byteLength));}
 const at=next.bufferViews.push(view)-1;viewMap.set(id,at);return at;
}
function copyAccessor(id,isIndex=false){
 if(accessorMap.has(id)){assert(!isIndex,'Shared index accessor must not be emitted twice');return accessorMap.get(id);}
 const original=doc.accessors[id],accessor=structuredClone(original);assert(!accessor.sparse,'Sparse accessor unsupported');
 if(isIndex){
  assert.equal(accessor.type,'SCALAR');const bytesPerIndex={5121:1,5123:2,5125:4}[accessor.componentType];assert(bytesPerIndex);
  const view=doc.bufferViews[accessor.bufferView],ext=view.extensions?.EXT_meshopt_compression;let bytes;
  if(ext){
   assert(['TRIANGLES','INDICES'].includes(ext.mode)&&!ext.filter);assert.equal(ext.buffer,0);
   assert(ext.count*ext.byteStride<=limit.indexDecode);assert.equal(ext.byteStride,bytesPerIndex);
   if(!indexCache.has(accessor.bufferView)){
    const target=new Uint8Array(ext.count*ext.byteStride);const encoded=read(binStart+(ext.byteOffset??0),ext.byteLength);
    MeshoptDecoder.decodeGltfBuffer(target,ext.count,ext.byteStride,encoded,ext.mode);
    indexCache.set(accessor.bufferView,target);evidence.decodedSharedIndexBytes+=target.length;
    assert(evidence.decodedSharedIndexBytes<=limit.indexDecode,'Total shared index decode budget');
   }
   const decoded=indexCache.get(accessor.bufferView),start=accessor.byteOffset??0,length=accessor.count*bytesPerIndex;
   assert(start+length<=decoded.length);bytes=Buffer.from(decoded.buffer,decoded.byteOffset+start,length);
  }else{assert.equal(view.buffer,0);bytes=read(binStart+(view.byteOffset??0)+(accessor.byteOffset??0),accessor.count*bytesPerIndex);}
  accessor.byteOffset=0;accessor.bufferView=next.bufferViews.push({buffer:0,byteOffset:append(bytes),byteLength:bytes.length,target:34963})-1;
  evidence.indices.push({sourceAccessor:id,count:accessor.count,decodedBytes:bytes.length,exactDecodedSha256:sha(bytes)});
 }else accessor.bufferView=copyView(accessor.bufferView);
 const at=next.accessors.push(accessor)-1;accessorMap.set(id,at);return at;
}
const meshes=new Map();
for(const {node,index} of nodes){
 if(!meshes.has(node.mesh)){
  const mesh=structuredClone(doc.meshes[node.mesh]);
  for(const primitive of mesh.primitives){assert.equal(primitive.mode??4,4);assert(!primitive.targets&&!primitive.extensions);primitive.indices=copyAccessor(primitive.indices,true);for(const semantic of Object.keys(primitive.attributes))primitive.attributes[semantic]=copyAccessor(primitive.attributes[semantic]);}
  meshes.set(node.mesh,next.meshes.push(mesh)-1);
 }
 next.scenes[0].nodes.push(next.nodes.length);next.nodes.push({...structuredClone(node),mesh:meshes.get(node.mesh)});
 evidence.nodes.push({sourceNode:index,name:node.name,sourceMesh:node.mesh,transformSha256:sha(JSON.stringify(Object.fromEntries(Object.entries(node).filter(([k])=>k!=='mesh'))))});
}
// Copy each original texture once to a companion directory. Images remain reference data,
// not decoded/transcoded photos. The tile itself references these exact source bytes.
fs.mkdirSync(output,{recursive:true});fs.mkdirSync(path.join(output,'textures'));
for(const [i,original] of (doc.images??[]).entries()){
 assert(!original.uri&&Number.isInteger(original.bufferView));const view=doc.bufferViews[original.bufferView];assert.equal(view.buffer,0);assert(!view.extensions);
 const bytes=read(binStart+(view.byteOffset??0),view.byteLength),extension={'image/jpeg':'jpg','image/png':'png'}[original.mimeType];assert(extension);
 const uri=`textures/${role}-${i}.${extension}`;fs.writeFileSync(path.join(output,uri),bytes,{flag:'wx'});
 const image={...original,uri};delete image.bufferView;next.images.push(image);evidence.textures.push({uri,sha256:sha(bytes),bytes:bytes.length});
}
const binary=Buffer.concat(parts),pad=(4-binary.length%4)%4,payload=pad?Buffer.concat([binary,Buffer.alloc(pad)]):binary;
next.buffers=[{byteLength:payload.length},{byteLength:fallbackLength,extensions:{EXT_meshopt_compression:{fallback:true}}}];
const jsonRaw=Buffer.from(JSON.stringify(next)),json=Buffer.concat([jsonRaw,Buffer.alloc((4-jsonRaw.length%4)%4,32)]),header=Buffer.alloc(20),bin=Buffer.alloc(8);
header.writeUInt32LE(0x46546c67,0);header.writeUInt32LE(2,4);header.writeUInt32LE(20+json.length+8+payload.length,8);header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);bin.writeUInt32LE(payload.length,0);bin.writeUInt32LE(0x004e4942,4);
const file=path.join(output,`${role}-${tileX}-${tileZ}.glb`);fs.writeFileSync(file,Buffer.concat([header,json,bin,payload]),{flag:'wx'});fs.closeSync(fd);
evidence.output={file,bytes:fs.statSync(file).size,sha256:sha(fs.readFileSync(file)),triangles:next.meshes.reduce((s,m)=>s+m.primitives.reduce((n,p)=>n+next.accessors[p.indices].count/3,0),0),logicalBytes:next.bufferViews.reduce((s,v)=>s+v.byteLength,0)};
evidence.proof='Compressed attribute payloads/metadata, exact decoded index slices, node TRS, materials and texture bytes retained; independent output decode/visual validation pending.';
evidence.runtimeInstalled=false;
fs.writeFileSync(path.join(output,'extraction.json'),JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify({output:evidence.output,nodes:nodes.length,indexDecodeBytes:evidence.decodedSharedIndexBytes}));
