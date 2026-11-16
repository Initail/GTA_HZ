import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {loadBaseStreamManifest} from '../src/city-stream-manifest.ts';
const descriptor=JSON.parse(readFileSync('artifacts/cities/hangzhou/stream-release-v1/descriptor.json','utf8'));
test('the externally pinned release descriptor reads all 1912 base chunks and seven shared textures',async()=>{
 const original=globalThis.fetch;let count=0,images=0;
 try{
  for(const role of ['terrain','roads','buildings'] as const){
   const entry=descriptor.models[role],bytes=readFileSync(entry.manifestPath);
   globalThis.fetch=async()=>new Response(bytes);
   const result=await loadBaseStreamManifest('https://fixture.test/'+role+'/manifest.json',{file:'manifest.json',bytes:entry.manifestBytes,sha256:entry.manifestSha256},role,entry.sourceSha256,new AbortController().signal);
   count+=result.tiles.length;images+=result.textures.length;assert.ok(result.tiles.every(t=>t.role===role&&t.baseUrl==='https://fixture.test/'+role+'/'));
  }
 }finally{globalThis.fetch=original;}
 assert.equal(count,1912);assert.equal(images,7);
});
test('a correctly hashed malformed manifest still cannot escape its tile directory or fake completeness',async()=>{
 const original=globalThis.fetch,entry=descriptor.models.terrain;
 try{
  for(const mutate of [(m:any)=>m.tiles[0].file='../roads.glb',(m:any)=>m.tiles[1].id=m.tiles[0].id,(m:any)=>m.totals.triangles++,(m:any)=>m.source.sha256='0'.repeat(64)]){
   const m=JSON.parse(readFileSync(entry.manifestPath,'utf8'));mutate(m);const bytes=Buffer.from(JSON.stringify(m));globalThis.fetch=async()=>new Response(bytes);
   await assert.rejects(loadBaseStreamManifest('https://fixture.test/terrain/manifest.json',{file:'manifest.json',bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')},'terrain',entry.sourceSha256,new AbortController().signal));
  }
 }finally{globalThis.fetch=original;}
});
