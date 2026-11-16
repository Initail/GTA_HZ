import {test} from 'node:test';import assert from 'node:assert/strict';
import {applyBaseStreamPartition,loadBaseStreamPartitions} from '../src/city-stream-partition.ts';
import {loadBasePackIndex,loadBasePackMetadata} from '../src/city-stream-pack-manifest.ts';
import {planBaseStream,tileCullDistance,tileDistance,tileLodDistance} from '../src/city-base-stream-plan.ts';
import {planBaseStreamPacks} from '../src/city-stream-pack-plan.ts';
import {packFixture} from './stream-pack-manifest.test.ts';

function setup(){
 const f=packFixture(),parent=f.tiles[2];
 const children=['a','b'].map((name,i)=>({...parent,id:parent.id+'/'+name,parentSourceId:parent.id,file:'groups/'+name+'/group.glb',bytes:70,sha256:String(i+8).repeat(64),logicalBytes:100,triangles:10,bounds:{min:[i*320,0,0],max:[(i+1)*320,10,640]}}));
 const partition={schemaVersion:1,kind:'city-base-source-partition',parent:{id:parent.id,sha256:parent.sha256},children,geometryCoverage:{file:'coverage.json',bytes:50,sha256:'c'.repeat(64)}};
 f.raw.members=f.raw.members.slice(0,2).concat(children.map(t=>({id:t.id,quality:'near',referenceSha256:t.sha256})));
 f.meta.members=f.raw.members.map((m:any)=>({...m,role:m.id.split(':')[0],sourceSha256:m.referenceSha256}));
 f.meta.nodes=f.meta.nodes.slice(0,2).concat(children.map(t=>({name:'block_0_0_plaster__'+t.id.at(-1),member:t.id,role:'buildings',quality:'near'})));
 f.root.totals.nearMembers=4;f.root.totals.representations=4;
 const seal=()=>{f.root.sourcePartitions=[f.put('partitions/buildings-0-0.json',partition)];return f.seal();};
 return {f,parent,partition,children,seal};
}
async function run(body:(s:ReturnType<typeof setup>,signal:AbortSignal)=>Promise<void>){
 const s=setup(),oldFetch=globalThis.fetch,oldLocation=Object.getOwnPropertyDescriptor(globalThis,'location');globalThis.fetch=s.f.fetcher;Object.defineProperty(globalThis,'location',{configurable:true,value:new URL('http://pack.test/')});
 try{await body(s,new AbortController().signal);}finally{globalThis.fetch=oldFetch;if(oldLocation)Object.defineProperty(globalThis,'location',oldLocation);else delete (globalThis as any).location;}
}
test('partition replaces exactly its pinned parent and all child near representations are mandatory',()=>run(async(s,signal)=>{
 const catalog=await loadBasePackIndex(s.seal(),s.f.tiles,s.f.textures,s.f.root.sourceManifests,signal);
 assert.equal(catalog.sources.length,4);assert(!catalog.sources.some(t=>t.id===s.parent.id));
 assert.deepEqual(catalog.sources.filter(t=>t.parentSourceId).map(t=>t.id),s.children.map(t=>t.id));
 await loadBasePackMetadata(catalog.packs[0],catalog.textures,signal);
 s.f.raw.members.pop();s.f.root.totals.nearMembers=3;s.f.root.totals.representations=3;
 await assert.rejects(loadBasePackIndex(s.seal(),s.f.tiles,s.f.textures,s.f.root.sourceManifests,signal),/覆盖不完整/);
}));
test('partition coverage checks reject stale parents, missing geometry, bounds drift and forged anchors',()=>{
 const {f,partition}=setup();
 for(const edit of [(p:any)=>p.parent.sha256='f'.repeat(64),(p:any)=>p.children[0].triangles--,(p:any)=>p.children[0].logicalBytes--,(p:any)=>p.children[0].bounds.min[0]=-1,(p:any)=>p.children[0].parentSourceId='buildings:1,0',(p:any)=>p.children[0].id=p.children[1].id]){
  const wrong=structuredClone(partition);edit(wrong);assert.throws(()=>applyBaseStreamPartition(f.tiles,wrong,'http://pack.test/'),/街区细分/);
 }
 const once=applyBaseStreamPartition(f.tiles,partition,'http://pack.test/');assert.throws(()=>applyBaseStreamPartition(once,partition,'http://pack.test/'),/父块缺失/);
});
test('child quality uses its actual bounds while visibility inherits the unchanged original centre',()=>run(async(s,signal)=>{
 const catalog=await loadBasePackIndex(s.seal(),s.f.tiles,s.f.textures,s.f.root.sourceManifests,signal);
 const child=catalog.sources.find(t=>t.id===s.children[0].id)!;
 assert.equal(tileCullDistance(child,320,320),0);assert.equal(tileDistance(child,960,320),640);
 // Original cell centre lies outside reflections although the child bbox does not.
 assert.equal(planBaseStream([child],{x:-1090,z:320,overview:false,intersects:()=>false}).required.length,0);
 const near=catalog.packs[0],far={...near,id:'far',members:near.members.map(m=>({...m,quality:'far' as const}))};
 const promoted=planBaseStreamPacks(catalog.sources,[near,far],{x:960,z:320,overview:false});assert.equal(promoted.representations[child.id].quality,'near');assert.equal(promoted.near.has(child.id),false);
 assert.equal(planBaseStreamPacks(catalog.sources,[near,far],{x:1600,z:320,overview:false}).representations[child.id].quality,'far');
 assert.equal(planBaseStreamPacks(catalog.sources,[near,far],{x:960,z:320,overview:false},new Set([child.id])).representations[child.id].quality,'near');
 assert.throws(()=>tileCullDistance({...child,parentSourceId:'roads:0,0'},0,0),/inherited/);
}));
test('child physical nodes must retain the same original world cull anchor',()=>run(async(s,signal)=>{
 s.f.meta.nodes[2].name='block_1_0_plaster__a';
 const catalog=await loadBasePackIndex(s.seal(),s.f.tiles,s.f.textures,s.f.root.sourceManifests,signal);
 await assert.rejects(loadBasePackMetadata(catalog.packs[0],catalog.textures,signal),/原剔除中心/);
}));
test('partition content is hash checked and cancellation does not fetch its body',()=>run(async(s,signal)=>{
 s.seal();const record=s.f.root.sourcePartitions[0];s.f.files.set('http://pack.test/'+record.file,new TextEncoder().encode('{}'));
 await assert.rejects(loadBaseStreamPartitions([record],'http://pack.test/',s.f.tiles,signal),/哈希/);
 const controller=new AbortController();controller.abort();const count=s.f.requested.length;
 await assert.rejects(loadBaseStreamPartitions([record],'http://pack.test/',s.f.tiles,controller.signal),{name:'AbortError'});assert.equal(s.f.requested.length,count);
}));
test('whole-parent mode refines quality over the real occupied regions while preserving original draw identity',()=>{
 const {f,parent,partition}=setup();
 // Two complete occupied ends leave an empty middle. The overall source bounds
 // remain exact, but that empty middle must not force near detail.
 partition.children[0].bounds.max[0]=20;partition.children[1].bounds.min[0]=620;
 const tiles=applyBaseStreamPartition(f.tiles,{...partition,representationMode:'whole-parent'},'http://pack.test/'),tile=tiles.find(t=>t.id===parent.id)!;
 assert.equal(tiles.length,f.tiles.length);assert.equal(tile.sha256,parent.sha256);assert.equal(tile.lodBounds!.length,2);
 assert.equal(tileDistance(tile,320,-600),600);assert.equal(tileLodDistance(tile,320,-600),Math.hypot(300,600));assert.equal(tileCullDistance(tile,320,320),0);
 assert.deepEqual(planBaseStream(tiles,{x:0,z:0,overview:false}).required.map(t=>t.id),planBaseStream(f.tiles,{x:0,z:0,overview:false}).required.map(t=>t.id));
 assert.throws(()=>applyBaseStreamPartition(tiles,{...partition,representationMode:'whole-parent'},'http://pack.test/'),/父块/);
});
