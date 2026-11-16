import type {StreamTile} from './city-stream-residency.ts';
import {contentSha256} from './city-content-hash.ts';
export type StreamFile={file:string;bytes:number;sha256:string};
export type StreamGlbTile=StreamTile&StreamFile&{role:'terrain'|'roads'|'buildings'|'pack';baseUrl:string};
export type BaseStreamTile=StreamGlbTile&{role:'terrain'|'roads'|'buildings';parentSourceId?:string;lodBounds?:readonly StreamTile['bounds'][]};
export type StreamMaterialOrigin={role:BaseStreamTile['role'];index:number;record:unknown};
export type StreamTexture=StreamFile;
export const STREAM_ASSET_LIMITS=Object.freeze({glb:8*1024*1024,header:256*1024,texture:1024*1024,texturePool:2*1024*1024,texturePixels:6*1024*1024,requestMs:5000});
export const byteHash=contentSha256;
function ensure(ok:unknown,message:string):asserts ok {if(!ok)throw Error('街区资源：'+message);}
export async function readStreamFile(url:string,file:StreamFile,signal:AbortSignal,maxBytes:number,fetcher:typeof fetch=fetch){
 ensure(Number.isSafeInteger(maxBytes)&&maxBytes>0&&maxBytes<=STREAM_ASSET_LIMITS.glb,'读取预算无效');
 ensure(Number.isSafeInteger(file.bytes)&&file.bytes>0&&file.bytes<=maxBytes&&/^[0-9a-f]{64}$/.test(file.sha256),'文件预算无效');
 const request=AbortSignal.any([signal,AbortSignal.timeout(STREAM_ASSET_LIMITS.requestMs)]);request.throwIfAborted();
 const response=await fetcher(url,{signal:request,cache:'no-store'});
 if(!response.ok||!response.body||Number(response.headers.get('content-length'))>file.bytes){await response.body?.cancel();throw Error('街区资源：响应无效或过大');}
 const reader=response.body.getReader();const cancel=()=>{void reader.cancel().catch(()=>{});};request.addEventListener('abort',cancel,{once:true});
 // Exact declared length avoids a growing array of chunks and an extra concat copy.
 const bytes=new Uint8Array(file.bytes);let offset=0;
 try{
  for(;;){request.throwIfAborted();const next=await reader.read();request.throwIfAborted();if(next.done)break;ensure(offset+next.value.byteLength<=bytes.length,'流超过声明长度');bytes.set(next.value,offset);offset+=next.value.byteLength;}
  ensure(offset===bytes.length&&await byteHash(bytes)===file.sha256,'长度或哈希不一致');request.throwIfAborted();return bytes;
 }finally{request.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});reader.releaseLock();}
}
/** The frozen base tiles only contain JPEGs. Inspect dimensions before native decode. */
export function streamJpegSize(bytes:Uint8Array){
 ensure(bytes[0]===255&&bytes[1]===216,'JPEG 头无效');let at=2;
 while(at+4<=bytes.length){
  ensure(bytes[at]===255,'JPEG 标记无效');while(bytes[at]===255)at++;const marker=bytes[at++];
  ensure(![0,0xda,0xd9].includes(marker),'JPEG 缺少尺寸头');const n=(bytes[at]<<8)|bytes[at+1];ensure(n>=2&&at+n<=bytes.length,'JPEG 段越界');
  if([0xc0,0xc1,0xc2].includes(marker)){
   ensure(n>=8,'JPEG 尺寸段无效');const height=(bytes[at+3]<<8)|bytes[at+4],width=(bytes[at+5]<<8)|bytes[at+6];
   ensure(width>0&&height>0&&width<=1024&&height<=1024,'JPEG 尺寸超过上限');return {width,height};
  }
  at+=n;
 }
 throw Error('街区资源：JPEG 尺寸缺失');
}
type GlbDoc={materials:unknown[];buffers:{byteLength:number;uri?:string;extensions?:{EXT_meshopt_compression?:{fallback?:boolean}}}[];
 bufferViews:{buffer:number;byteOffset?:number;byteLength:number;extensions?:{EXT_meshopt_compression?:{buffer:number;byteOffset?:number;byteLength:number;count:number;byteStride:number;mode:string;filter?:string}}}[];
 meshes:{primitives:{mode?:number;indices:number}[]}[];accessors:{count:number}[];
 images:{uri:string;mimeType?:string;bufferView?:number}[];nodes:{mesh?:number;children?:number[]}[];scenes:{nodes:number[]}[];
 animations?:unknown[];skins?:unknown[];cameras?:unknown[];extensionsUsed?:string[];extensionsRequired?:string[]};
export function inspectStreamGlb(bytes:Uint8Array<ArrayBuffer>,tile:StreamGlbTile,textures:readonly StreamTexture[]){
 ensure(bytes.byteLength>=28&&bytes.byteLength===tile.bytes,'GLB 长度不一致');const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 ensure(view.getUint32(0,true)===0x46546c67&&view.getUint32(4,true)===2&&view.getUint32(8,true)===bytes.length&&view.getUint32(16,true)===0x4e4f534a,'GLB 头无效');
 const n=view.getUint32(12,true);ensure(n<=STREAM_ASSET_LIMITS.header&&20+n+8<=bytes.length,'GLB JSON 头过大或越界');const bin=20+n+8;
 ensure(view.getUint32(bin-4,true)===0x004e4942&&bin+view.getUint32(bin-8,true)===bytes.length,'GLB 二进制范围无效');
 const doc=JSON.parse(new TextDecoder().decode(bytes.subarray(20,20+n))) as GlbDoc;
 const known=['EXT_meshopt_compression','KHR_mesh_quantization','KHR_materials_emissive_strength'];
 ensure([...(doc.extensionsUsed??[]),...(doc.extensionsRequired??[])].every(name=>known.includes(name)),'基础块包含未登记扩展');
 ensure(!doc.animations?.length&&!doc.skins?.length&&!doc.cameras?.length&&doc.scenes?.length===1&&Array.isArray(doc.nodes)&&doc.nodes.every(node=>!node.children&&Number.isInteger(node.mesh)),'基础块包含未支持的场景对象');
 ensure(doc.scenes[0].nodes.length===doc.nodes.length&&new Set(doc.scenes[0].nodes).size===doc.nodes.length&&doc.scenes[0].nodes.every(i=>Number.isInteger(i)&&i>=0&&i<doc.nodes.length),'基础块场景覆盖不完整');
 ensure(Array.isArray(doc.buffers)&&doc.buffers.length===2&&doc.buffers.every(b=>!b.uri&&Number.isSafeInteger(b.byteLength)&&b.byteLength>=0)&&doc.buffers[0].byteLength===bytes.length-bin&&doc.buffers[1].extensions?.EXT_meshopt_compression?.fallback===true,'缓冲引用无效');
 ensure(Array.isArray(doc.bufferViews)&&doc.bufferViews.every(v=>Number.isSafeInteger(v.byteLength)&&v.byteLength>=0)&&doc.bufferViews.reduce((sum,v)=>sum+v.byteLength,0)===tile.logicalBytes&&doc.buffers[1].byteLength<=tile.logicalBytes+doc.bufferViews.length*3,'解码缓冲预算不一致');
 ensure(tile.logicalBytes<=32*1024*1024,'单块逻辑缓冲超限');
 for(const v of doc.bufferViews){
  const at=v.byteOffset??0;ensure([0,1].includes(v.buffer)&&Number.isSafeInteger(at)&&at>=0&&at+v.byteLength<=doc.buffers[v.buffer].byteLength,'缓冲视图越界');
  const ext=v.extensions?.EXT_meshopt_compression;
  if(ext){const offset=ext.byteOffset??0;
   ensure(ext.buffer===0&&Number.isSafeInteger(offset)&&offset>=0&&Number.isSafeInteger(ext.byteLength)&&ext.byteLength>0&&offset+ext.byteLength<=doc.buffers[0].byteLength&&Number.isSafeInteger(ext.count)&&ext.count>0&&Number.isSafeInteger(ext.byteStride)&&ext.byteStride>0&&ext.count*ext.byteStride===v.byteLength,'压缩解码范围或预算无效');
   const filter=ext.filter??'NONE';
   // Admit only formats present in the hash-bound source/pilot assets. In
   // particular, a normal filter must never be applied to triangle indices.
   const attributes=ext.mode==='ATTRIBUTES'&&ext.byteStride<=256&&ext.byteStride%4===0&&(filter==='NONE'||filter==='OCTAHEDRAL'&&[4,8].includes(ext.byteStride));
   const triangles=ext.mode==='TRIANGLES'&&[2,4].includes(ext.byteStride)&&ext.count%3===0&&filter==='NONE';
   ensure(attributes||triangles,'压缩模式、步长或过滤器无效');
  }else ensure(v.buffer===0,'未压缩数据不能引用缺省缓冲');
 }
 let triangles=0;
 for(const node of doc.nodes)for(const p of doc.meshes[node.mesh!].primitives){ensure((p.mode??4)===4,'基础块包含非三角几何');const count=doc.accessors[p.indices].count;ensure(Number.isSafeInteger(count)&&count>=0&&count%3===0,'三角索引无效');triangles+=count/3;}
 ensure(triangles===tile.triangles,'三角预算不一致');
 ensure(Array.isArray(doc.images)&&doc.images.length===textures.length&&doc.images.every((im,i)=>im.bufferView===undefined&&im.mimeType==='image/jpeg'&&im.uri==='../'+textures[i].file),'存在未登记图片引用');
 return {doc,bin};
}
/** Only image URLs change in memory. The binary geometry stays byte-exact. */
export function bindStreamTextureUrls(bytes:Uint8Array<ArrayBuffer>,tile:StreamGlbTile,textures:readonly StreamTexture[],urls:readonly string[]){
 const {doc,bin}=inspectStreamGlb(bytes,tile,textures);ensure(urls.length===textures.length&&urls.every(u=>u.startsWith('blob:')),'贴图对象 URL 不完整');
 doc.images.forEach((im,i)=>{im.uri=urls[i];});const raw=new TextEncoder().encode(JSON.stringify(doc)),jsonLength=(raw.length+3)&~3;
 const out=new Uint8Array(20+jsonLength+8+bytes.length-bin),view=new DataView(out.buffer);out.set(bytes.subarray(0,20));view.setUint32(8,out.length,true);view.setUint32(12,jsonLength,true);
 out.fill(32,20,20+jsonLength);out.set(raw,20);out.set(bytes.subarray(bin-8),20+jsonLength);return out;
}
