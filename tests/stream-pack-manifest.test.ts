import {test} from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {loadBasePackIndex,loadBasePackMetadata} from '../src/city-stream-pack-manifest.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';
const sha=(b:Uint8Array)=>createHash('sha256').update(b).digest('hex');
const h=(n:string)=>n.repeat(64),roleHashes={terrain:h('1'),roads:h('2'),buildings:h('3')};
export function packFixture(){
 const files=new Map<string,Uint8Array>(),requested:string[]=[];
 const put=(file:string,data:unknown)=>{const bytes=new TextEncoder().encode(JSON.stringify(data));files.set('http://pack.test/'+file,bytes);return {file,bytes:bytes.length,sha256:sha(bytes)};};
 const tiles:BaseStreamTile[]=['terrain','roads','buildings'].map((role,i)=>({id:role+':0,0',role:role as BaseStreamTile['role'],baseUrl:'http://pack.test/',file:'tiles/'+role+'-0-0.glb',sha256:h(String(i+4)),bytes:100,logicalBytes:200,triangles:20,bounds:{min:[0,0,0],max:[640,10,640]}}));
 const textures=[{file:'textures/roads-0.jpg',bytes:4,sha256:h('a')}];
 const members=tiles.map(t=>({id:t.id,quality:'near' as const,referenceSha256:t.sha256}));
 const meta:any={schemaVersion:1,kind:'physical-base-pack',id:'near-0-0',bytes:300,sha256:h('b'),logicalBytes:600,triangles:60,bounds:{min:[0,0,0],max:[640,10,640]},textures,materialOrigins:[{role:'roads',index:0,record:{name:'asphalt'}}],members:members.map((m,i)=>({...m,role:tiles[i].role,sourceSha256:m.referenceSha256})),nodes:tiles.map(t=>({name:t.role+'_0_0_fixture',member:t.id,role:t.role,quality:'near'}))};
 const raw:any={id:meta.id,file:'tiles/'+meta.id+'.glb',bytes:meta.bytes,sha256:meta.sha256,logicalBytes:meta.logicalBytes,triangles:meta.triangles,bounds:meta.bounds,members,metadata:null};
 const root:any={schemaVersion:1,kind:'city-base-pack-index',sourceManifests:roleHashes,textures,chunks:[],totals:{packs:1,nearMembers:3,representations:3}};
 const seal=()=>{raw.metadata=put('metadata/near-0-0.json',meta);root.chunks=[put('index/0.json',{schemaVersion:1,packs:[raw]})];const entry=put('index.json',root);return {manifestUrl:'http://pack.test/index.json',manifestBytes:entry.bytes,manifestSha256:entry.sha256};};
 const fetcher:typeof fetch=async(url,options)=>{options?.signal?.throwIfAborted();const key=String(url);requested.push(key);const bytes=files.get(key);return new Response(bytes??null,{status:bytes?200:404});};
 return {tiles,textures,meta,raw,root,files,requested,put,seal,fetcher};
}
async function withFixture(run:(f:ReturnType<typeof packFixture>,signal:AbortSignal)=>Promise<void>){
 const f=packFixture(),oldFetch=globalThis.fetch,locationDescriptor=Object.getOwnPropertyDescriptor(globalThis,'location');
 Object.defineProperty(globalThis,'location',{configurable:true,value:new URL('http://pack.test/')});globalThis.fetch=f.fetcher;
 try{await run(f,new AbortController().signal);}finally{globalThis.fetch=oldFetch;if(locationDescriptor)Object.defineProperty(globalThis,'location',locationDescriptor);else delete (globalThis as any).location;}
}
test('all pinned original members are covered before individual pack metadata is read',()=>withFixture(async(f,signal)=>{
 const catalog=await loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal);
 assert.equal(catalog.packs.length,1);assert.equal(catalog.packs[0].role,'pack');assert.equal(f.requested.length,2);
 const metadata=await loadBasePackMetadata(catalog.packs[0],catalog.textures,signal);assert.deepEqual(metadata.nodes,f.meta.nodes);assert.equal(f.requested.length,3);
}));
test('a pilot cannot become a whole-city index by declaring fullCoverage',()=>withFixture(async(f,signal)=>{
 f.raw.members.pop();f.root.fullCoverage=true;f.root.totals.nearMembers=2;f.root.totals.representations=2;
 await assert.rejects(loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal),/覆盖不完整/);
}));
test('a stale original source hash is rejected before fetching pack metadata',()=>withFixture(async(f,signal)=>{
 f.raw.members[1].referenceSha256=h('c');await assert.rejects(loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal),/版本不符/);assert.equal(f.requested.length,2);
}));
test('duplicate representations and bounds omitting source geometry are rejected',()=>withFixture(async(f,signal)=>{
 f.raw.members.push({...f.raw.members[0]});await assert.rejects(loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal),/重复/);
 f.raw.members.pop();f.raw.bounds={min:[1,0,0],max:[640,10,640]};await assert.rejects(loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal),/范围漏掉/);
}));
test('pack metadata rejects mismatched roles, missing nodes and unlisted textures',()=>withFixture(async(f,signal)=>{
 for(const kind of ['role','nodes','texture'] as const){
  const original=structuredClone(f.meta);if(kind==='role')f.meta.members[0].role='roads';if(kind==='nodes')f.meta.nodes.pop();if(kind==='texture')f.meta.textures=[{...f.textures[0],file:'textures/roads-9.jpg'}];
  const catalog=await loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,signal);await assert.rejects(loadBasePackMetadata(catalog.packs[0],catalog.textures,signal),/合包成员版本|实际渲染节点|登记清单/);Object.assign(f.meta,original);
 }
}));
test('hash tampering and cancelled index requests fail closed',()=>withFixture(async(f,signal)=>{
 const source=f.seal();f.files.set(source.manifestUrl,new TextEncoder().encode('corrupt'));
 await assert.rejects(loadBasePackIndex(source,f.tiles,f.textures,roleHashes,signal),/哈希/);
 const abort=new AbortController();abort.abort();const count=f.requested.length;await assert.rejects(loadBasePackIndex(f.seal(),f.tiles,f.textures,roleHashes,abort.signal),{name:'AbortError'});assert.equal(f.requested.length,count);
}));
