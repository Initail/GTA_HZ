import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {checkCityJsonManifest,loadCityJsonChunks,JSON_CHUNK_LIMITS} from '../src/city-json-chunks.ts';
const digest=(s:string)=>createHash('sha256').update(s).digest('hex');
function fixture(){
 const original={meta:{cityId:'hangzhou',scale:.6},roads:[{id:'a',points:[[1.123456789,-2]]},{id:'b',points:[[5,6]]}],water:[]};
 const core=JSON.stringify({...original,roads:[]}),sourceSha256=digest(JSON.stringify(original));
 const texts=original.roads.map((value,i)=>JSON.stringify({key:'roads',startIndex:i,sourceRange:[40+i*50,85+i*50],values:[value]}));
 const manifest={schemaVersion:1,transportOnly:true,sourceSha256,sourceBytes:300,core:'core.json',coreSha256:digest(core),coreBytes:Buffer.byteLength(core),
  properties:[{key:'meta',sourceRange:[1,30]}],arrays:[{key:'roads',count:2,sourceRange:[35,150],chunks:texts.map((s,i)=>({file:`array-0-${i}.json`,bytes:Buffer.byteLength(s),sha256:digest(s),startIndex:i,count:1,sourceRange:[40+i*50,85+i*50]}))},{key:'water',count:0,sourceRange:[160,162],chunks:[]}]};
 const files:Record<string,string>={'manifest.json':JSON.stringify(manifest),'core.json':core,'array-0-0.json':texts[0],'array-0-1.json':texts[1]};
 const calls:string[]=[];let active=0,maxActive=0;
 const fetcher=(async(input)=>{const name=String(input).split('/').at(-1)!;calls.push(name);active++;maxActive=Math.max(maxActive,active);await Promise.resolve();active--;
  return new Response(files[name],{headers:{'content-type':'application/json'}});}) as typeof fetch;
 return {original,manifest,files,calls,fetcher,maxActive:()=>maxActive,source:{manifestUrl:'https://fixture.test/city/manifest.json',manifestBytes:Buffer.byteLength(files['manifest.json']),manifestSha256:digest(files['manifest.json']),sourceSha256}};
}
test('sequential transport restores every value and order without changing gameplay fields',async()=>{
 const f=fixture();let yields=0;const progress:number[]=[];
 const actual=await loadCityJsonChunks(f.source,{fetcher:f.fetcher,yieldTask:async()=>{yields++;},progress:n=>progress.push(n)});
 assert.deepEqual(actual,f.original);assert.equal(f.maxActive(),1);assert.equal(yields,2);assert.deepEqual(progress,[0,1,2]);
 assert.deepEqual(f.calls,['manifest.json','core.json','array-0-0.json','array-0-1.json']);
});
test('actual city and road-level manifests fit fixed transport limits and pinned source identities',()=>{
 for(const [name,sha] of [['city','5597538370ac4f627df816fc2bd678fe15be69b1b429928c6c5a85a8253aa81a'],['road-levels','0db3134e9a24b53ab0361a3f2fdc1738f818ceddafc56d94c5500b8ba75a25c1']]){
  const m=JSON.parse(readFileSync(`artifacts/cities/hangzhou/stream-data-v1/${name}/manifest.json`,'utf8'));checkCityJsonManifest(m,sha);
 }
});
test('missing, reordered, duplicate, escaped or oversized chunks fail before core download',async()=>{
 for(const mutate of [
  (m:any)=>m.arrays[0].chunks.pop(),(m:any)=>m.arrays[0].chunks.reverse(),
  (m:any)=>m.arrays[0].chunks[1].file=m.arrays[0].chunks[0].file,
  (m:any)=>m.arrays[0].chunks[0].file='../city.json',
  (m:any)=>m.arrays[0].chunks[0].bytes=JSON_CHUNK_LIMITS.chunk+1,
  (m:any)=>m.sourceSha256='0'.repeat(64),(m:any)=>m.arrays[0].key='__proto__',
 ]){
  const f=fixture();mutate(f.manifest);f.files['manifest.json']=JSON.stringify(f.manifest);
  // Even an externally pinned malformed manifest must fail structural admission.
  f.source.manifestBytes=Buffer.byteLength(f.files['manifest.json']);f.source.manifestSha256=digest(f.files['manifest.json']);
  await assert.rejects(loadCityJsonChunks(f.source,{fetcher:f.fetcher}));assert.deepEqual(f.calls,['manifest.json']);
 }
});
test('editing the manifest and its embedded checksums cannot impersonate the pinned release descriptor',async()=>{
 const f=fixture();f.files['manifest.json']=f.files['manifest.json'].replace('"count":2','"count":9');
 await assert.rejects(loadCityJsonChunks(f.source,{fetcher:f.fetcher}),/哈希/);assert.deepEqual(f.calls,['manifest.json']);
});
test('corrupt bytes stop before the next chunk and never fall back to the monolithic file',async()=>{
 const f=fixture();f.files['array-0-0.json']=f.files['array-0-0.json'].replace('1.123','9.123');
 await assert.rejects(loadCityJsonChunks(f.source,{fetcher:f.fetcher}),/哈希/);assert.equal(f.calls.length,3);
});
test('abort at a yield stops subsequent requests; no partial object escapes',async()=>{
 const f=fixture(),controller=new AbortController();
 await assert.rejects(loadCityJsonChunks(f.source,{fetcher:f.fetcher,signal:controller.signal,yieldTask:async()=>{controller.abort();}}),{name:'AbortError'});
 assert.equal(f.calls.length,3);
});
test('an oversized stream without a declared length is cancelled at the manifest bound',async()=>{
 let cancelled=false;
 await assert.rejects(loadCityJsonChunks(fixture().source,{fetcher:async()=>new Response(new ReadableStream({pull(c){c.enqueue(new Uint8Array(64*1024));},cancel(){cancelled=true;}}),{headers:{'content-type':'application/json'}})}),/上限/);
 assert.equal(cancelled,true);
});
