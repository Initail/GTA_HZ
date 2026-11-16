import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {bindStreamTextureUrls,inspectStreamGlb,readStreamFile,streamJpegSize,type BaseStreamTile} from '../src/city-stream-assets.ts';
import {tileInfo} from '../scripts/hangzhou_stream_glb.mjs';
const roles=['terrain','roads','buildings'] as const;
const fixtureRoot=(role:typeof roles[number])=>new URL(`./fixtures/stream-spawn/${role}/`,import.meta.url);
const assetRoot=(role:typeof roles[number])=>new URL(`../public/stream-models/${role}/`,import.meta.url);
const planFor=(role:typeof roles[number])=>JSON.parse(readFileSync(new URL('plan.json',fixtureRoot(role)),'utf8'));
test('all three actual spawn tiles retain exact binary payloads when binding registered texture URLs',()=>{
 for(const role of roles){
  const plan=planFor(role),entry=plan.tiles.find((t:any)=>t.id==='0,-1');
  const record=JSON.parse(readFileSync(new URL(entry.file+'.json',fixtureRoot(role)),'utf8'));
  const bytes=new Uint8Array(readFileSync(new URL(entry.file,assetRoot(role))));
  const tile={...record,role,baseUrl:'https://fixture.test/'+role+'/'} as BaseStreamTile;
  const old=inspectStreamGlb(bytes,tile,plan.textures),bound=bindStreamTextureUrls(bytes,tile,plan.textures,plan.textures.map((_:unknown,i:number)=>'blob:fixture-'+i)),head=new DataView(bound.buffer),offset=20+head.getUint32(12,true)+8;
  assert.deepEqual(bound.subarray(offset),bytes.subarray(old.bin));
  assert.throws(()=>inspectStreamGlb(bytes,{...tile,triangles:tile.triangles+1},plan.textures),/三角/);
  assert.throws(()=>inspectStreamGlb(bytes,{...tile,logicalBytes:tile.logicalBytes+1},plan.textures),/缓冲/);
  assert.throws(()=>inspectStreamGlb(bytes,tile,[]),/图片/);
 }
});
test('shared source index accessors count once in memory while each primitive still renders',()=>{
 const doc={nodes:[{mesh:0}],meshes:[{primitives:[{indices:0,attributes:{POSITION:1}},{indices:0,attributes:{POSITION:1}}]}],accessors:[{count:3,componentType:5123},{min:[0,0,0],max:[1,1,1],bufferView:0}],bufferViews:[{byteLength:36}]};
 const info=tileInfo(doc,{nodes:[0]});assert.equal(info.triangles,2);assert.equal(info.logicalBytes,42);
});
test('actual shared JPEGs fit pre-decode pixel limits; malformed headers are rejected',()=>{
 let pixels=0;
 for(const role of roles){
  const plan=planFor(role);
  for(const file of plan.textures){const size=streamJpegSize(new Uint8Array(readFileSync(new URL(file.file,assetRoot(role)))));pixels+=size.width*size.height;}
 }
 assert.equal(pixels,5767168);
 for(const bad of [new Uint8Array(),new Uint8Array([255,216,255,0xda,0,2]),new Uint8Array([255,216,255,0xc0,0,8,8,255,255,255,255,1])])assert.throws(()=>streamJpegSize(bad));
});
test('verified binary transfer enforces exact bytes/hash and cancels oversized streams',async()=>{
 const bytes=new Uint8Array([1,3,5]),file={file:'test.glb',bytes:3,sha256:createHash('sha256').update(bytes).digest('hex')},signal=new AbortController().signal;
 assert.deepEqual(await readStreamFile('https://fixture.test/a',file,signal,10,async()=>new Response(bytes)),bytes);
 await assert.rejects(readStreamFile('https://fixture.test/a',{...file,sha256:'0'.repeat(64)},signal,10,async()=>new Response(bytes)),/哈希/);
 let cancelled=false;await assert.rejects(readStreamFile('https://fixture.test/a',file,signal,10,async()=>new Response(new ReadableStream({pull(c){c.enqueue(new Uint8Array(4));},cancel(){cancelled=true;}}))),/长度/);assert.equal(cancelled,true);
});
