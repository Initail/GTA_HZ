import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {inspectStreamGlb,type BaseStreamTile} from '../src/city-stream-assets.ts';
const root=new URL('./fixtures/base-far-pilot/roads/',import.meta.url);
function fixture(){const d=JSON.parse(readFileSync(new URL('descriptor.json',root),'utf8'));return {d,b:new Uint8Array(readFileSync(new URL(d.tile.file,root))),tile:{...d.tile,baseUrl:'http://test/'} as BaseStreamTile};}
function changed(edit:(d:any)=>void){const f=fixture(),view=new DataView(f.b.buffer),n=view.getUint32(12,true),d=JSON.parse(new TextDecoder().decode(f.b.subarray(20,20+n)));edit(d);const text=new TextEncoder().encode(JSON.stringify(d)),padded=(text.length+3)&~3,bytes=new Uint8Array(20+padded+f.b.length-20-n),head=new DataView(bytes.buffer);bytes.set(f.b.subarray(0,20));head.setUint32(8,bytes.length,true);head.setUint32(12,padded,true);bytes.fill(32,20,20+padded);bytes.set(text,20);bytes.set(f.b.subarray(20+n),20+padded);return {...f,b:bytes,tile:{...f.tile,bytes:bytes.length}};}
test('actual independently sampled road LOD admits triangle index and octahedral normal compression',()=>{const {d,b,tile}=fixture();const {doc}=inspectStreamGlb(b,tile,d.textures);assert.ok(doc.bufferViews.some(v=>v.extensions?.EXT_meshopt_compression?.mode==='TRIANGLES'));assert.equal(tile.triangles,6980);});
test('compression modes, filters and strides are validated before decoder allocation',()=>{
 for(const edit of [(d:any)=>d.bufferViews[0].extensions.EXT_meshopt_compression.mode='UNKNOWN',(d:any)=>d.bufferViews[0].extensions.EXT_meshopt_compression.filter='OCTAHEDRAL',(d:any)=>d.bufferViews[2].extensions.EXT_meshopt_compression.filter='QUATERNION',(d:any)=>d.bufferViews[2].extensions.EXT_meshopt_compression.byteStride=3]){
  const {d,b,tile}=changed(edit);assert.throws(()=>inspectStreamGlb(b,tile,d.textures),/压缩/);
 }
});
