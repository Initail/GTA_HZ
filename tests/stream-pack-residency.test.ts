import {test} from 'node:test';import assert from 'node:assert/strict';
import {CityPackResidency,type PackHandle} from '../src/city-stream-pack-residency.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';import type {BaseStreamPack} from '../src/city-stream-pack-plan.ts';
const hash='a'.repeat(64);
function source(id:string,x:number):BaseStreamTile{return {id,role:'buildings',baseUrl:'http://test/',file:id+'.glb',sha256:hash,bounds:{min:[x,0,0],max:[x+100,10,100]},bytes:100,logicalBytes:200,triangles:20};}
function pack(id:string,members:string[],quality:'near'|'far'):BaseStreamPack{return {id,role:'pack',baseUrl:'http://test/',file:id+'.glb',sha256:hash,bounds:{min:[0,0,0],max:[2200,10,100]},bytes:100,logicalBytes:200,triangles:20,members:members.map(id=>({id,quality,referenceSha256:hash}))};}
function handle(){let ids:readonly string[]=[],visible=false,disposes=0;return {selectMembers:(v:readonly string[])=>{ids=[...v];},setVisible:(v:boolean)=>{visible=v;},dispose:()=>{disposes++;visible=false;ids=[];},get ids(){return ids;},get visible(){return visible;},get disposes(){return disposes;}};}
test('coarse neighbour pack masks the exact block covered by near geometry, then switches without duplicate coverage',async()=>{
 const sources=[source('a',0),source('b',2000)],packs=[pack('near-a',['a'],'near'),pack('near-b',['b'],'near'),pack('far-ab',['a','b'],'far')],loaded=new Map<string,ReturnType<typeof handle>>();
 const stream=new CityPackResidency(sources,packs,async p=>{const h=handle();loaded.set(p.id,h);return h;});
 await stream.request({x:0,z:0,overview:false});assert(stream.stats.ready);assert.deepEqual(loaded.get('near-a')!.ids,['a']);assert.deepEqual(loaded.get('far-ab')!.ids,['b']);
 await stream.request({x:2000,z:0,overview:false});assert(stream.stats.ready);assert.deepEqual(loaded.get('near-b')!.ids,['b']);assert.deepEqual(loaded.get('far-ab')!.ids,['a']);assert.deepEqual(loaded.get('near-a')!.ids,[]);assert.equal(stream.stats.plan!.physicalRequired,2);
 stream.dispose();for(const h of loaded.values())assert.equal(h.disposes,1);
});
test('rapid travel cancels stale import, waits for its decoder, and releases it exactly once',async()=>{
 const sources=[source('a',0),source('b',2000)],packs=[pack('near-a',['a'],'near'),pack('near-b',['b'],'near'),pack('far',['a','b'],'far')];
 let resolve:(h:ReturnType<typeof handle>)=>void=()=>{},firstSignal:AbortSignal|undefined,active=0,maxActive=0;const stale=handle();
 let enteredResolve:()=>void=()=>{};const entered=new Promise<void>(resolve=>{enteredResolve=resolve;});
 const stream=new CityPackResidency(sources,packs,async(p,signal)=>{active++;maxActive=Math.max(maxActive,active);if(p.id==='near-a'){firstSignal=signal;enteredResolve();try{return await new Promise<ReturnType<typeof handle>>(r=>{resolve=r;});}finally{active--;}}active--;return handle();});
 const first=stream.request({x:0,z:0,overview:false});await entered;
 const second=stream.request({x:2000,z:0,overview:false});assert(firstSignal!.aborted);assert.equal(stream.stats.ready,false);resolve(stale);await Promise.all([first,second]);
 assert(stream.stats.ready);assert.equal(stale.disposes,1);assert.equal(maxActive,1);stream.dispose();
});
test('over-budget or missing near coverage cannot become ready through an empty residency request',async()=>{
 for(const mode of ['budget','missing']){const sourceA=source('a',0),p=pack('near',['a'],mode==='budget'?'near':'far');if(mode==='budget')p.bytes=25*1024*1024;let loads=0;
  const stream=new CityPackResidency([sourceA],[p],async()=>{loads++;return handle();});await stream.request({x:0,z:0,overview:false});assert.equal(stream.stats.ready,false);assert.equal(loads,0);stream.dispose();
 }
});
test('dispose during non-cancellable import owns the late container until disposal',async()=>{
 let resolve:(h:PackHandle)=>void=()=>{};const stream=new CityPackResidency([source('a',0)],[pack('near',['a'],'near')],()=>new Promise<PackHandle>(r=>{resolve=r;}));
 const pending=stream.request({x:0,z:0,overview:false}),late=handle();stream.dispose();resolve(late);await pending;assert.equal(late.disposes,1);assert.equal(stream.stats.ready,false);assert.equal(stream.handles.length,0);
});
test('promoted near members switch together to far without exposing two copies',async()=>{
 const sources=[source('a',0),source('b',900)],packs=[pack('near',['a','b'],'near'),pack('far',['a','b'],'far')],loaded=new Map<string,ReturnType<typeof handle>>();
 const stream=new CityPackResidency(sources,packs,async p=>{const h=handle();loaded.set(p.id,h);return h;});
 await stream.request({x:0,z:0,overview:false});assert.equal(loaded.size,1);assert.deepEqual(loaded.get('near')!.ids,['a','b']);
 await stream.request({x:-801,z:0,overview:false});assert.equal(stream.stats.ready,true);assert.equal(stream.stats.plan!.physicalRequired,1);assert.deepEqual(loaded.get('near')!.ids,[]);assert.deepEqual(loaded.get('far')!.ids,['a','b']);
 stream.dispose();for(const h of loaded.values())assert.equal(h.disposes,1);
});
