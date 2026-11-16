import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {contentSha256,sha256HexPortable} from '../src/city-content-hash.ts';
const expected=(bytes:Uint8Array)=>createHash('sha256').update(bytes).digest('hex');
test('portable SHA-256 matches known vectors, padding boundaries, and nonzero view offsets',async()=>{
 assert.equal(await sha256HexPortable(new Uint8Array()),'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
 assert.equal(await sha256HexPortable(new TextEncoder().encode('abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
 for(const length of [1,55,56,63,64,65,119,120,127,128,129,4097]){
  const bytes=Uint8Array.from({length:length+7},(_,i)=>(i*197+17)&255).subarray(7);
  assert.equal(await sha256HexPortable(bytes),expected(bytes),'length '+length);
 }
});
test('portable path hashes a real release manifest and yields during a large input',async()=>{
 const manifest=readFileSync('artifacts/cities/hangzhou/stream-data-v1/city/manifest.json');
 assert.equal(await sha256HexPortable(manifest),'8bab508c54f83f76c280534876373802e1e52fe443a470643809f4d69c7c8544');
 const bytes=new Uint8Array(2*1024*1024+57);bytes.fill(0xa5);let yielded=false;
 const timer=setTimeout(()=>{yielded=true;},0);
 assert.equal(await sha256HexPortable(bytes),expected(bytes));assert.equal(yielded,true);clearTimeout(timer);
});
test('asset digest works without the crypto.subtle interface',async()=>{
 const descriptor=Object.getOwnPropertyDescriptor(globalThis,'crypto');
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:{}});
 try{const bytes=new TextEncoder().encode('杭城之行 · LAN');assert.equal(await contentSha256(bytes),expected(bytes));assert.equal(await contentSha256(bytes.buffer),expected(bytes));}
 finally{if(descriptor)Object.defineProperty(globalThis,'crypto',descriptor);else Reflect.deleteProperty(globalThis,'crypto');}
});
