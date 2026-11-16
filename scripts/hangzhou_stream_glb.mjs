/** Header/range-only source reader. Never hand a whole-city GLB to NodeIO. */
import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {MeshoptDecoder} from 'meshoptimizer';
export const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
export async function fileSha(file){const h=crypto.createHash('sha256');for await(const b of fs.createReadStream(file,{highWaterMark:64*1024}))h.update(b);return h.digest('hex');}
export function openSource(file){
 const fd=fs.openSync(file,'r'),stat=fs.fstatSync(fd);
 const read=(start,n,cap=32*1024*1024)=>{
  assert(Number.isSafeInteger(start)&&Number.isSafeInteger(n)&&start>=0&&n>=0&&n<=cap&&start+n<=stat.size,'Source range exceeds budget');
  const b=Buffer.alloc(n);assert.equal(fs.readSync(fd,b,0,n,start),n);return b;
 };
 const h=read(0,20);assert.equal(h.readUInt32LE(0),0x46546c67);assert.equal(h.readUInt32LE(4),2);assert.equal(h.readUInt32LE(8),stat.size);assert.equal(h.readUInt32LE(16),0x4e4f534a);
 const raw=read(20,h.readUInt32LE(12),16*1024*1024),doc=JSON.parse(raw),bin=20+raw.length+8;
 const bh=read(bin-8,8);assert.equal(bh.readUInt32LE(4),0x004e4942);assert.equal(bin+bh.readUInt32LE(0),stat.size);
 assert(!doc.animations?.length&&!doc.skins?.length&&!doc.extensions);
 assert.equal(doc.scenes.length,1);assert.equal(doc.scenes[0].nodes.length,doc.nodes.length);
 assert.equal(new Set(doc.scenes[0].nodes).size,doc.nodes.length);assert(doc.scenes[0].nodes.every(i=>Number.isInteger(i)&&i>=0&&i<doc.nodes.length));
 assert(doc.nodes.every(n=>Number.isInteger(n.mesh)&&!n.children&&!n.camera&&!n.skin&&!n.weights));
 return {file,stat,doc,bin,headerSha256:sha(raw),read,close:()=>fs.closeSync(fd)};
}
export function tileGroups(doc,role){
 const re=role==='buildings'?/^block_(-?\d+)_(-?\d+)_/:role==='roads'?/^roads_(?:site_)?(-?\d+)_(-?\d+)_/:/^terrain_(?:water_)?(-?\d+)_(-?\d+)_/;
 assert(['terrain','roads','buildings'].includes(role));const groups=new Map();
 doc.nodes.forEach((node,index)=>{const m=node.name.match(re);assert(m,'Unmatched node '+node.name);const id=`${Number(m[1])},${Number(m[2])}`;
  if(!groups.has(id))groups.set(id,{id,tile:[Number(m[1]),Number(m[2])],nodes:[]});groups.get(id).nodes.push(index);
 });
 return [...groups.values()].sort((a,b)=>a.tile[0]-b.tile[0]||a.tile[1]-b.tile[1]);
}
function position(v,node){
 if(node.matrix){const m=node.matrix;assert.equal(m.length,16);return [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];}
 const s=node.scale??[1,1,1],q=node.rotation??[0,0,0,1],t=node.translation??[0,0,0],p=v.map((n,i)=>n*s[i]);
 assert(Math.abs(Math.hypot(...q)-1)<1e-5);
 const u=[2*(q[1]*p[2]-q[2]*p[1]),2*(q[2]*p[0]-q[0]*p[2]),2*(q[0]*p[1]-q[1]*p[0])];
 return [p[0]+q[3]*u[0]+q[1]*u[2]-q[2]*u[1]+t[0],p[1]+q[3]*u[1]+q[2]*u[0]-q[0]*u[2]+t[1],p[2]+q[3]*u[2]+q[0]*u[1]-q[1]*u[0]+t[2]];
}
export function tileInfo(doc,group){
 const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];let triangles=0;const views=new Set(),indices=new Set();let indexBytes=0;
 for(const id of group.nodes){const node=doc.nodes[id];for(const p of doc.meshes[node.mesh].primitives){
  assert.equal(p.mode??4,4);assert(!p.targets&&!p.extensions);const a=doc.accessors[p.attributes.POSITION];assert(a.min?.length===3&&a.max?.length===3);
  const normalize=v=>!a.normalized?v:a.componentType===5120?Math.max(v/127,-1):a.componentType===5121?v/255:a.componentType===5122?Math.max(v/32767,-1):a.componentType===5123?v/65535:(assert.fail('Unsupported normalized POSITION'));
  for(let c=0;c<8;c++){
   const v=position([0,1,2].map(i=>normalize((c&(1<<i)?a.max:a.min)[i])),node);v[2]*=-1;
   for(let i=0;i<3;i++){assert(Number.isFinite(v[i]));min[i]=Math.min(min[i],v[i]);max[i]=Math.max(max[i],v[i]);}
  }
  const idx=doc.accessors[p.indices];triangles+=idx.count/3;
  if(!indices.has(p.indices)){indices.add(p.indices);indexBytes+=idx.count*({5121:1,5123:2,5125:4}[idx.componentType]);}
  for(const id of Object.values(p.attributes))views.add(doc.accessors[id].bufferView);
 }}
 assert(Number.isSafeInteger(triangles));
 const logicalBytes=indexBytes+[...views].reduce((s,i)=>s+doc.bufferViews[i].byteLength,0);
 return {bounds:{min,max},triangles,logicalBytes,nodes:group.nodes.length};
}
export async function indexReader(source){
 await MeshoptDecoder.ready;const cache=new Map();let decoded=0;const {doc,bin,read}=source;
 return id=>{
  const a=doc.accessors[id],v=doc.bufferViews[a.bufferView],ext=v.extensions?.EXT_meshopt_compression;
  assert.equal(a.type,'SCALAR');assert(!a.sparse);const stride={5121:1,5123:2,5125:4}[a.componentType];assert(stride);
  if(!ext){assert.equal(v.buffer,0);return read(bin+(v.byteOffset??0)+(a.byteOffset??0),a.count*stride);}
  assert.equal(ext.buffer,0);assert.equal(ext.byteStride,stride);assert(['TRIANGLES','INDICES'].includes(ext.mode)&&!ext.filter);
  if(!cache.has(a.bufferView)){
   decoded+=ext.count*ext.byteStride;assert(decoded<=64*1024*1024,'Shared index cache cap');
   const bytes=new Uint8Array(ext.count*ext.byteStride);MeshoptDecoder.decodeGltfBuffer(bytes,ext.count,ext.byteStride,read(bin+(ext.byteOffset??0),ext.byteLength),ext.mode);cache.set(a.bufferView,bytes);
  }
  const buffer=cache.get(a.bufferView),start=a.byteOffset??0;assert(start+a.count*stride<=buffer.length);
  return Buffer.from(buffer.buffer,buffer.byteOffset+start,a.count*stride);
 };
}
export function extractTile(source,group,readIndex,images){
 const {doc,bin,read}=source;
 // Keep small document metadata; do not clone the source's thousands of meshes.
 const next={...doc,nodes:[],meshes:[],accessors:[],bufferViews:[],buffers:[],images,
  scenes:[{...doc.scenes[0],nodes:[]}],scene:0};
 const parts=[],accessors=new Map(),views=new Map(),meshes=new Map();let binaryLength=0,fallbackLength=0;
 const append=bytes=>{const pad=(4-binaryLength%4)%4;if(pad){parts.push(Buffer.alloc(pad));binaryLength+=pad;}const offset=binaryLength;parts.push(bytes);binaryLength+=bytes.length;assert(binaryLength<=8*1024*1024,'Tile encoded cap');return offset;};
 function copyView(id){
  if(views.has(id))return views.get(id);const v=structuredClone(doc.bufferViews[id]),ext=v.extensions?.EXT_meshopt_compression;
  if(ext){assert.equal(ext.buffer,0);ext.byteOffset=append(read(bin+(ext.byteOffset??0),ext.byteLength));ext.buffer=0;fallbackLength=(fallbackLength+3)&~3;v.buffer=1;v.byteOffset=fallbackLength;fallbackLength+=v.byteLength;assert(fallbackLength<=32*1024*1024,'Tile logical cap');}
  else{assert.equal(v.buffer,0);v.byteOffset=append(read(bin+(v.byteOffset??0),v.byteLength));}
  const at=next.bufferViews.push(v)-1;views.set(id,at);return at;
 }
 function copyAccessor(id,index=false){
  if(accessors.has(id))return accessors.get(id);const a=structuredClone(doc.accessors[id]);assert(!a.sparse);
  if(index){const bytes=readIndex(id);a.byteOffset=0;a.bufferView=next.bufferViews.push({buffer:0,byteOffset:append(bytes),byteLength:bytes.length,target:34963})-1;}
  else a.bufferView=copyView(a.bufferView);
  const at=next.accessors.push(a)-1;accessors.set(id,at);return at;
 }
 for(const id of group.nodes){const node=doc.nodes[id];
  if(!meshes.has(node.mesh)){const mesh=structuredClone(doc.meshes[node.mesh]);for(const p of mesh.primitives){p.indices=copyAccessor(p.indices,true);for(const s of Object.keys(p.attributes))p.attributes[s]=copyAccessor(p.attributes[s]);}meshes.set(node.mesh,next.meshes.push(mesh)-1);}
  next.scenes[0].nodes.push(next.nodes.length);next.nodes.push({...structuredClone(node),mesh:meshes.get(node.mesh)});
 }
 const pad=(4-binaryLength%4)%4;if(pad)parts.push(Buffer.alloc(pad));binaryLength+=pad;
 next.buffers=[{byteLength:binaryLength},{byteLength:fallbackLength,extensions:{EXT_meshopt_compression:{fallback:true}}}];
 const jsonRaw=Buffer.from(JSON.stringify(next)),json=Buffer.concat([jsonRaw,Buffer.alloc((4-jsonRaw.length%4)%4,32)]),header=Buffer.alloc(20),bh=Buffer.alloc(8);
 const length=20+json.length+8+binaryLength;assert(length<=8*1024*1024,'Complete GLB cap');
 header.writeUInt32LE(0x46546c67,0);header.writeUInt32LE(2,4);header.writeUInt32LE(length,8);header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);bh.writeUInt32LE(binaryLength,0);bh.writeUInt32LE(0x004e4942,4);
 return {bytes:Buffer.concat([header,json,bh,...parts]),doc:next};
}
