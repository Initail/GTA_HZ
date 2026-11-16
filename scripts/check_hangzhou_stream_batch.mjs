/** Decode only small output GLBs. Independently compare every source attribute,
 * index, transform, material and image; verify world bounds using decoded vertices. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
import {openSource,sha} from './hangzhou_stream_glb.mjs';
const [directory,first,count]=process.argv.slice(2),start=Number(first),length=Number(count);
assert(Number.isInteger(start)&&start>=0&&Number.isInteger(length)&&length>0&&length<=8);
const plan=JSON.parse(fs.readFileSync(path.join(directory,'plan.json'))),source=openSource(plan.source),doc=source.doc;
assert.equal(source.headerSha256,plan.sourceHeaderSha256);assert.equal(source.stat.size,plan.sourceBytes);
await MeshoptDecoder.ready;const sharedIndices=new Map();let sharedBytes=0;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
function accessorBytes(id,cache,isIndex){
 const a=doc.accessors[id],v=doc.bufferViews[a.bufferView],ext=v.extensions?.EXT_meshopt_compression,store=isIndex?sharedIndices:cache;
 if(!store.has(a.bufferView)){
  let bytes;
  if(ext){assert.equal(ext.buffer,0);const size=ext.count*ext.byteStride;assert(size<=64*1024*1024);bytes=new Uint8Array(size);MeshoptDecoder.decodeGltfBuffer(bytes,ext.count,ext.byteStride,source.read(source.bin+(ext.byteOffset??0),ext.byteLength),ext.mode,ext.filter);}
  else{assert.equal(v.buffer,0);bytes=source.read(source.bin+(v.byteOffset??0),v.byteLength);}
  if(isIndex){sharedBytes+=bytes.length;assert(sharedBytes<=64*1024*1024);}store.set(a.bufferView,bytes);
  if(!isIndex)assert([...cache.values()].reduce((n,b)=>n+b.byteLength,0)<=32*1024*1024,'Source attribute cache cap');
 }
 const bytes=store.get(a.bufferView),component={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a.componentType],arity={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type];assert(component&&arity&&!a.sparse);
 const width=component*arity,stride=v.byteStride??width,offset=a.byteOffset??0,out=Buffer.alloc(a.count*width);assert(offset+(a.count-1)*stride+width<=bytes.length);
 for(let i=0;i<a.count;i++)out.set(bytes.subarray(offset+i*stride,offset+i*stride+width),i*width);
 return out;
}
async function check(tile){
 const file=path.join(directory,tile.file),record=JSON.parse(fs.readFileSync(file+'.json'));assert(!fs.existsSync(file+'.validation.json'));
 const bytes=fs.readFileSync(file);assert.equal(bytes.length,record.bytes);assert.equal(sha(bytes),record.sha256);
 const target=openSource(file),actual=target.doc;target.close();
 for(const key of ['materials','textures','samplers','asset','extensionsUsed','extensionsRequired'])assert.deepEqual(actual[key],doc[key]);
 assert.equal(actual.nodes.length,tile.sourceNodes.length);assert.deepEqual(actual.images,plan.images);
 for(const [i,image] of doc.images.entries()){
  const view=doc.bufferViews[image.bufferView],texture=fs.readFileSync(path.join(path.dirname(file),actual.images[i].uri));
  assert.equal(sha(texture),sha(source.read(source.bin+(view.byteOffset??0),view.byteLength)));
 }
 const small=await io.read(file),cache=new Map();let attributes=0,indices=0,triangles=0,vertices=0;
 const names=new Set(),bounds={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
 for(const id of tile.sourceNodes){
  const originalNode=doc.nodes[id];assert(!names.has(originalNode.name));names.add(originalNode.name);
  const rawNode=actual.nodes.find(n=>n.name===originalNode.name),node=small.getRoot().listNodes().find(n=>n.getName()===originalNode.name);assert(rawNode&&node);
  const transform=n=>Object.fromEntries(Object.entries(n).filter(([k])=>k!=='mesh'));assert.deepEqual(transform(rawNode),transform(originalNode));
  const primitives=doc.meshes[originalNode.mesh].primitives,outputs=node.getMesh().listPrimitives(),rawPrimitives=actual.meshes[rawNode.mesh].primitives;assert.equal(outputs.length,primitives.length);
  for(const [i,p] of primitives.entries()){
   const output=outputs[i];assert.equal(rawPrimitives[i].material,p.material);assert.deepEqual(Object.keys(rawPrimitives[i].attributes).sort(),Object.keys(p.attributes).sort());
   for(const [semantic,aid] of Object.entries({...p.attributes,INDICES:p.indices})){
    const index=semantic==='INDICES',a=index?output.getIndices():output.getAttribute(semantic);assert(a);
    const raw=a.getArray(),decoded=Buffer.from(raw.buffer,raw.byteOffset,raw.byteLength),expected=accessorBytes(aid,cache,index);
    assert.equal(sha(decoded),sha(expected),originalNode.name+':'+semantic);assert.equal(a.getComponentType(),doc.accessors[aid].componentType);assert.equal(a.getType(),doc.accessors[aid].type);assert.equal(a.getNormalized(),doc.accessors[aid].normalized??false);
    if(index){indices++;triangles+=a.getCount()/3;}else attributes++;
   }
   const pos=output.getAttribute('POSITION'),m=node.getWorldMatrix(),v=[];
   for(let j=0;j<pos.getCount();j++){
    pos.getElement(j,v);const world=[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],-(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])];
    for(let k=0;k<3;k++){assert(Number.isFinite(world[k]));assert(world[k]>=tile.bounds.min[k]-.0001&&world[k]<=tile.bounds.max[k]+.0001,'Vertex escapes stream bounds');bounds.min[k]=Math.min(bounds.min[k],world[k]);bounds.max[k]=Math.max(bounds.max[k],world[k]);}vertices++;
   }
  }
 }
 assert.equal(triangles,tile.triangles);assert.equal(actual.bufferViews.reduce((n,v)=>n+v.byteLength,0),tile.logicalBytes);
 const result={pass:true,sourceSha256:plan.sourceSha256,targetSha256:record.sha256,nodes:names.size,attributes,indices,triangles,vertices,decodedBounds:bounds,
  scope:'All decoded accessor bytes and original node/material/texture identities preserved; finite vertices lie inside stream bounds. CPU decode only; no GPU/visual/runtime claim.'};
 fs.writeFileSync(file+'.validation.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});cache.clear();
}
const tiles=plan.tiles.slice(start,start+length);assert.equal(tiles.length,length);
for(const tile of tiles){await check(tile);globalThis.gc?.();}
source.close();console.log(JSON.stringify({role:plan.role,start,count:length,pass:true,sharedIndexBytes:sharedBytes}));
