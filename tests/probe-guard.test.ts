import {test} from 'node:test';import assert from 'node:assert/strict';
import {ProbeResourceGuard} from '../src/city-probe-resource-guard.ts';
test('actual page guard stops once on monitor alarm and does not resume',async()=>{
 let sample=0,alarm=false,calls=0;const messages:string[]=[];
 const guard=new ProbeResourceGuard(m=>messages.push(m),(async()=>{calls++;return new Response(JSON.stringify({sample:sample++,ready:!alarm,stop:alarm,reason:alarm?'resource-alarm':null}));}) as typeof fetch);
 assert(await guard.start());alarm=true;assert.equal(await guard.check(),false);assert.equal(messages.length,1);assert.match(messages[0],/resource-alarm/);assert.equal(await guard.check(),false);assert.equal(calls,2);
});
test('monitor absent, stale, rewind, malformed and network failure all stop before admission',async()=>{
 for(const row of [{sample:0,ready:false,stop:true,reason:'stale-monitor'}, {sample:0,ready:false,stop:true,reason:'monitor-unavailable'}, {sample:0,ready:true,stop:false},'not-json']){
  let calls=0;const messages:string[]=[];const guard=new ProbeResourceGuard(m=>messages.push(m),(async()=>new Response(calls++===0?JSON.stringify({sample:2,ready:true,stop:false}):typeof row==='string'?row:JSON.stringify(row))) as typeof fetch);
  assert(await guard.start());assert.equal(await guard.check(),false);assert.equal(messages.length,1);
 }
 const guard=new ProbeResourceGuard(()=>{},(async()=>{throw Error('offline');}) as typeof fetch);assert.equal(await guard.start(),false);
});
test('intentional page disposal aborts polling without a spurious failure notice',async()=>{
 const messages:string[]=[];const guard=new ProbeResourceGuard(m=>messages.push(m),(async()=>new Response(JSON.stringify({sample:0,ready:true,stop:false}))) as typeof fetch);
 assert(await guard.start());guard.dispose();assert.equal(await guard.check(),false);assert.deepEqual(messages,[]);
});
test('native fetch is not invoked with the guard object as its Window receiver',async()=>{
 const messages:string[]=[];
 const request=function(this:unknown){assert.equal(this,undefined);return Promise.resolve(new Response(JSON.stringify({sample:0,ready:true,stop:false})));};
 const guard=new ProbeResourceGuard(m=>messages.push(m),request as typeof fetch);
 assert(await guard.start());guard.dispose();assert.deepEqual(messages,[]);
});
