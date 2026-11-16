/** Physically concatenate frozen small GLBs. No decoding, simplification,
 * transforms, material edits or repeated image payloads. Not a release gate. */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const align=n=>(n+3)&~3;
const roles=['terrain','roads','buildings'];
export function parseSmallGlb(bytes){
 assert(bytes.length>=28&&bytes.length<=8*1024*1024,'Small physical GLB budget');
 assert.equal(bytes.readUInt32LE(0),0x46546c67);assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);assert.equal(bytes.readUInt32LE(16),0x4e4f534a);
 const n=bytes.readUInt32LE(12);assert(n<=256*1024&&20+n+8<=bytes.length,'Small JSON budget');
 const bin=28+n;assert.equal(bytes.readUInt32LE(bin-4),0x004e4942);assert.equal(bytes.readUInt32LE(bin-8)+bin,bytes.length);
 return {doc:JSON.parse(bytes.subarray(20,20+n)),bin:bytes.subarray(bin)};
}
function textureOffset(material,offset){
 const next=structuredClone(material);
 for(const [host,keys] of [[next,['normalTexture','occlusionTexture','emissiveTexture']],[next.pbrMetallicRoughness,['baseColorTexture','metallicRoughnessTexture']]])for(const key of keys)if(host?.[key])host[key].index+=offset;
 return next;
}
function makeGlb(doc,parts,binaryLength){
 const raw=Buffer.from(JSON.stringify(doc)),json=Buffer.concat([raw,Buffer.alloc(align(raw.length)-raw.length,32)]);
 assert(json.length<=256*1024,'Combined header budget');const header=Buffer.alloc(20),bh=Buffer.alloc(8),total=28+json.length+binaryLength;
 assert(total<=8*1024*1024,'Combined physical file budget');
 header.writeUInt32LE(0x46546c67);header.writeUInt32LE(2,4);header.writeUInt32LE(total,8);header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);bh.writeUInt32LE(binaryLength);bh.writeUInt32LE(0x004e4942,4);
 return Buffer.concat([header,json,bh,...parts]);
}
export function mergeStreamGlbs(inputs){
 assert(inputs.length>0&&inputs.length<=48,'Physical member count');
 const out={asset:{version:'2.0',generator:'GTA_HZ exact stream packing'},scene:0,scenes:[{nodes:[]}],nodes:[],meshes:[],accessors:[],bufferViews:[],buffers:[],materials:[],textures:[],images:[],samplers:[],extensionsUsed:[],extensionsRequired:[]};
 const parts=[],members=[],nodes=[],materialOrigins=[],catalogs=new Map(),ids=new Set(),names=new Set(),textures=[],textureIds=new Set();
 let binaryLength=0,fallbackLength=0,triangles=0,logicalBytes=0;
 const bounds={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
 for(const input of inputs){
  const {record,role,quality='near',bytes}=input;
  assert(roles.includes(role)&&['near','far'].includes(quality));assert(!ids.has(record.id),'Duplicate logical member');ids.add(record.id);
  assert.equal(bytes.length,record.bytes);assert.equal(sha(bytes),record.sha256,'Changed member bytes');
  assert(record.bounds?.min.length===3&&record.bounds?.max.length===3);
  for(let i=0;i<3;i++){assert(Number.isFinite(record.bounds.min[i])&&Number.isFinite(record.bounds.max[i])&&record.bounds.min[i]<=record.bounds.max[i]);bounds.min[i]=Math.min(bounds.min[i],record.bounds.min[i]);bounds.max[i]=Math.max(bounds.max[i],record.bounds.max[i]);}
  const {doc,bin}=parseSmallGlb(bytes);assert.equal(doc.buffers.length,2);assert.equal(doc.buffers[0].byteLength,bin.length);assert(doc.buffers.every(b=>!b.uri));assert.equal(doc.buffers[1].extensions?.EXT_meshopt_compression?.fallback,true);
  assert(!doc.animations?.length&&!doc.skins?.length&&!doc.cameras?.length&&!doc.extensions);assert.equal(doc.scenes.length,1);assert.equal(doc.scenes[0].nodes.length,doc.nodes.length);
  assert.equal(new Set(doc.scenes[0].nodes).size,doc.nodes.length);assert(doc.scenes[0].nodes.every(i=>Number.isInteger(i)&&i>=0&&i<doc.nodes.length));
  const extensions=[...(doc.extensionsUsed??[]),...(doc.extensionsRequired??[])];assert(extensions.every(e=>['EXT_meshopt_compression','KHR_mesh_quantization','KHR_materials_emissive_strength'].includes(e)));
  const images=doc.images??[];assert.equal(images.length,input.textures.length);
  images.forEach((im,i)=>assert(im.uri==='../'+input.textures[i].file&&im.bufferView===undefined&&im.mimeType==='image/jpeg','Pinned external image references only'));
  const catalogSignature=JSON.stringify([doc.materials??[],doc.textures??[],images,doc.samplers??[],input.textures]);let catalog=catalogs.get(role);
  if(catalog)assert.equal(catalog.signature,catalogSignature,'Role catalog changed within physical pack');
  else{
   catalog={signature:catalogSignature,materialOffset:out.materials.length,textureOffset:out.textures.length,imageOffset:out.images.length,samplerOffset:out.samplers.length};catalogs.set(role,catalog);
   for(const [index,mat] of (doc.materials??[]).entries()){out.materials.push(textureOffset(mat,catalog.textureOffset));materialOrigins.push({role,index,record:structuredClone(mat)});}
   out.textures.push(...(doc.textures??[]).map(t=>{assert(!t.extensions,'Unregistered texture extension');return {...t,source:t.source+catalog.imageOffset,...(t.sampler===undefined?{}:{sampler:t.sampler+catalog.samplerOffset})};}));
   out.images.push(...structuredClone(images));out.samplers.push(...structuredClone(doc.samplers??[]));
   for(const texture of input.textures){assert(!textureIds.has(texture.file),'Image filename collision');textureIds.add(texture.file);textures.push({...texture});}
  }
  assert(out.materials.length<=64&&out.images.length<=8,'Combined material/image catalog budget');
  const offsets={binary:align(binaryLength),fallback:align(fallbackLength),view:out.bufferViews.length,accessor:out.accessors.length,mesh:out.meshes.length,node:out.nodes.length};
  if(offsets.binary>binaryLength)parts.push(Buffer.alloc(offsets.binary-binaryLength));parts.push(bin);binaryLength=offsets.binary+bin.length;fallbackLength=offsets.fallback+doc.buffers[1].byteLength;
  assert(binaryLength<=8*1024*1024&&fallbackLength<=32*1024*1024,'Combined buffers budget');
  for(const view of doc.bufferViews){
   const v=structuredClone(view),ext=v.extensions?.EXT_meshopt_compression,at=v.byteOffset??0;
   assert([0,1].includes(v.buffer)&&Number.isSafeInteger(at)&&at>=0&&Number.isSafeInteger(v.byteLength)&&v.byteLength>=0&&at+v.byteLength<=doc.buffers[v.buffer].byteLength);
   v.byteOffset=at+(v.buffer===0?offsets.binary:offsets.fallback);
   if(ext){assert.equal(ext.buffer,0);assert((ext.byteOffset??0)>=0&&(ext.byteOffset??0)+ext.byteLength<=bin.length);ext.byteOffset=(ext.byteOffset??0)+offsets.binary;}
   else assert.equal(v.buffer,0);
   out.bufferViews.push(v);
  }
  for(const accessor of doc.accessors){assert(!accessor.sparse&&Number.isInteger(accessor.bufferView)&&accessor.bufferView>=0&&accessor.bufferView<doc.bufferViews.length);out.accessors.push({...structuredClone(accessor),bufferView:accessor.bufferView+offsets.view});}
  for(const mesh of doc.meshes){const m=structuredClone(mesh);for(const p of m.primitives){assert.equal(p.mode??4,4);assert(!p.targets&&!p.extensions);assert(Number.isInteger(p.indices)&&p.indices>=0&&p.indices<doc.accessors.length);p.indices+=offsets.accessor;for(const semantic of Object.keys(p.attributes)){assert(Number.isInteger(p.attributes[semantic])&&doc.accessors[p.attributes[semantic]]);p.attributes[semantic]+=offsets.accessor;}if(p.material!==undefined){assert(doc.materials[p.material]);p.material+=catalog.materialOffset;}}out.meshes.push(m);}
  let memberTriangles=0;
  doc.nodes.forEach((node,i)=>{assert(Number.isInteger(node.mesh)&&doc.meshes[node.mesh]&&!node.children&&!node.camera&&!node.skin&&!node.weights);assert(typeof node.name==='string'&&!names.has(node.name),'Unique original node names required');names.add(node.name);
   out.nodes.push({...structuredClone(node),mesh:node.mesh+offsets.mesh});out.scenes[0].nodes.push(out.nodes.length-1);nodes.push({node:out.nodes.length-1,name:node.name,sourceNode:i,member:record.id,role,quality});
   for(const p of doc.meshes[node.mesh].primitives)memberTriangles+=doc.accessors[p.indices].count/3;
  });
  assert(Number.isSafeInteger(memberTriangles));assert.equal(memberTriangles,record.triangles);const memberLogical=doc.bufferViews.reduce((sum,v)=>sum+v.byteLength,0);assert.equal(memberLogical,record.logicalBytes);
  triangles+=memberTriangles;logicalBytes+=memberLogical;
  members.push({id:record.id,role,quality,sourceSha256:record.sha256,sourceBytes:record.bytes,triangles:memberTriangles,logicalBytes:memberLogical,bounds:structuredClone(record.bounds),offsets,nodes:doc.nodes.length,meshes:doc.meshes.length,accessors:doc.accessors.length,views:doc.bufferViews.length,binaryBytes:bin.length});
  out.extensionsUsed=[...new Set([...out.extensionsUsed,...(doc.extensionsUsed??[])])];out.extensionsRequired=[...new Set([...out.extensionsRequired,...(doc.extensionsRequired??[])])];
 }
 out.buffers=[{byteLength:binaryLength},{byteLength:fallbackLength,extensions:{EXT_meshopt_compression:{fallback:true}}}];
 const bytes=makeGlb(out,parts,binaryLength);
 return {bytes,descriptor:{schemaVersion:1,kind:'physical-base-pack',fullCoverage:false,bytes:bytes.length,sha256:sha(bytes),triangles,logicalBytes,bounds,textures,members,nodes,materialOrigins,physicalContainers:1,logicalMembers:members.length,validation:{geometryRebuilt:false,independentVerification:false,browserValidated:false,runtimeInstalled:false}}};
}
