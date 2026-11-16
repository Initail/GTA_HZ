import test from 'node:test';
import assert from 'node:assert/strict';
import {checkRasterSize,copyRasterStrip,decodeRasterInto} from '../src/city-raster-decode.ts';
test('sequential RGB + ground-R strips exactly preserve the original ambient RGBA packing',()=>{
 const source=Uint8ClampedArray.from([2,23,199,255,7,88,241,255,0,255,128,255]);
 const ground=Uint8ClampedArray.from([14,14,14,255,51,51,51,255,200,200,200,255]);
 const target=new Uint8Array(12);
 copyRasterStrip(source.subarray(0,8),target,0,4,[0,1,2]);copyRasterStrip(source.subarray(8),target,2,4,[0,1,2]);
 copyRasterStrip(ground,target,0,4,[3]);
 assert.deepEqual([...target],[2,23,199,14,7,88,241,51,0,255,128,200]);
});
test('roof lookup remains exact R8 and invalid ranges fail before writes',()=>{
 const target=new Uint8Array(3);copyRasterStrip(Uint8ClampedArray.from([1,2,3,255,0,0,0,255,175,175,175,255]),target,0,1,[0]);
 assert.deepEqual([...target],[1,0,175]);
 assert.throws(()=>copyRasterStrip(new Uint8ClampedArray(8),target,2,1,[0]));
 assert.throws(()=>copyRasterStrip(new Uint8ClampedArray(4),target,0,1,[1]));
});
test('malformed or oversized raster dimensions fail before allocation',()=>{
 checkRasterSize(5345,3164);
 for(const size of [[Infinity,1],[NaN,1],[-1,1],[9000,1],[5000,5000],[1.5,2]])assert.throws(()=>checkRasterSize(...size as [number,number]));
});
test('the actual async decoder limits readback rows and releases bitmap/canvas on completion and abort',async()=>{
 // CPU test doubles exercise lifetime/control flow; this is not a browser image-decoder test.
 const saved={fetch:globalThis.fetch,bitmap:globalThis.createImageBitmap,canvas:globalThis.OffscreenCanvas};
 let closed=0,readRows:number[]=[],controller:AbortController|undefined;
 const canvases:{width:number;height:number}[]=[];
 const bytes=new Uint8Array(24);bytes.set([137,80,78,71,13,10,26,10]);const header=new DataView(bytes.buffer);header.setUint32(16,2);header.setUint32(20,129);
 try{
  globalThis.fetch=async()=>new Response(bytes);
  globalThis.createImageBitmap=(async()=>({width:2,height:129,close(){closed++;}})) as typeof createImageBitmap;
  globalThis.OffscreenCanvas=class {
   width:number;height:number;
   constructor(width:number,height:number){this.width=width;this.height=height;canvases.push(this);}
   getContext(){return {clearRect(){},drawImage(){},getImageData(_x:number,_y:number,w:number,h:number){readRows.push(h);controller?.abort();return {data:new Uint8ClampedArray(w*h*4).fill(17)};}};}
  } as unknown as typeof OffscreenCanvas;
  const target=new Uint8Array(2*129);await decodeRasterInto('/small-fixture.png',2,129,target,1,[0]);
  assert.ok(target.every(n=>n===17));assert.deepEqual(readRows,[128,1]);assert.equal(closed,1);
  assert.deepEqual(canvases.map(c=>[c.width,c.height]),[[1,1]]);
  controller=new AbortController();readRows=[];
  await assert.rejects(decodeRasterInto('/small-fixture.png',2,129,new Uint8Array(258),1,[0],controller.signal),{name:'AbortError'});
  assert.deepEqual(readRows,[128]);assert.equal(closed,2);assert.equal(canvases[1].width,1);
 }finally{globalThis.fetch=saved.fetch;globalThis.createImageBitmap=saved.bitmap;globalThis.OffscreenCanvas=saved.canvas;}
});
