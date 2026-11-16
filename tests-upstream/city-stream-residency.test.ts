import test from 'node:test';import assert from 'node:assert/strict';
import {CityStreamResidency,type StreamTile,type StreamHandle} from '../src/city-stream-residency.ts';
const tile=(id:string,x=0):StreamTile=>({id,bytes:10,logicalBytes:20,triangles:3,bounds:{min:[x,0,0],max:[x+1,1,1]}});
const budget={bytes:25,logicalBytes:50,triangles:7,tiles:2};
function handle(){return {visible:false,disposed:0,setVisible(value:boolean){this.visible=value;},dispose(){this.disposed++;}};}
test('only one import runs at once; pending cost counts against the same fixed budget',async()=>{
 let active=0,peak=0;const handles:ReturnType<typeof handle>[]=[];
 const stream=new CityStreamResidency([tile('a'),tile('b')],async()=>{active++;peak=Math.max(peak,active);assert.ok(stream.stats.declaredWithPending.bytes<=25);await Promise.resolve();active--;const h=handle();handles.push(h);return h;},budget);
 assert.equal(stream.stats.ready,false);await stream.update(0,0,3,5);assert.equal(peak,1);assert.equal(stream.stats.ready,true);assert.equal(stream.stats.visible,2);
 stream.dispose();stream.dispose();assert.deepEqual(handles.map(h=>h.disposed),[1,1]);assert.equal(stream.stats.resident,0);
});
test('an area beyond the budget stays visibly incomplete without dropping required geometry',async()=>{
 const stream=new CityStreamResidency([tile('a'),tile('b'),tile('c')],async()=>handle(),budget);
 await stream.update(0,0,3,5);assert.equal(stream.stats.ready,false);assert.deepEqual(stream.stats.blocked,['c']);assert.equal(stream.stats.resident,2);assert.equal(stream.stats.declaredResident.bytes,20);stream.dispose();
});
test('moving unloads far geometry, hides retained geometry, and evicts hidden tiles before admission',async()=>{
 const all=new Map<string,ReturnType<typeof handle>>();const stream=new CityStreamResidency([tile('a',0),tile('b',10),tile('c',20)],async t=>{const h=handle();all.set(t.id,h);return h;},budget);
 await stream.update(0,0,1,30);await stream.update(10,0,1,30);assert.equal(all.get('a')!.visible,false);assert.equal(all.get('a')!.disposed,0);
 await stream.update(20,0,1,30);assert.equal(all.get('a')!.disposed,1);assert.equal(stream.stats.ready,true);assert.equal(stream.stats.resident,2);
 await stream.update(100,0,1,2);assert.equal(stream.stats.resident,0);assert.equal(all.get('b')!.disposed,1);assert.equal(all.get('c')!.disposed,1);stream.dispose();
});
test('focus changes during a non-cancellable decode dispose obsolete output before importing the next tile',async()=>{
 let finish!: (h:StreamHandle)=>void;const calls:string[]=[];let firstSignal:AbortSignal|undefined;const stale=handle(),fresh=handle();
 const stream=new CityStreamResidency([tile('a',0),tile('b',100)],async(t,signal)=>{calls.push(t.id);if(t.id==='a'){firstSignal=signal;return await new Promise<StreamHandle>(resolve=>{finish=resolve;});}return fresh;},budget);
 const pending=stream.update(0,0,1,2);const next=stream.update(100,0,1,2);assert.equal(firstSignal!.aborted,true);assert.deepEqual(calls,['a']);finish(stale);await Promise.all([pending,next]);
 assert.deepEqual(calls,['a','b']);assert.equal(stale.disposed,1);assert.equal(fresh.disposed,0);assert.equal(stream.stats.ready,true);stream.dispose();
});
test('dispose during import releases its late result and does not restart the queue',async()=>{
 let finish!:(h:StreamHandle)=>void;const h=handle();let calls=0;
 const stream=new CityStreamResidency([tile('a'),tile('b')],async()=>{calls++;return new Promise<StreamHandle>(resolve=>{finish=resolve;});},budget);
 const work=stream.update(0,0,1,2);stream.dispose();finish(h);await work;assert.equal(h.disposed,1);assert.equal(calls,1);assert.equal(stream.stats.resident,0);await stream.update(0,0,1,2);assert.equal(calls,1);
});
test('failed imports are recorded once without retry loops or accidental readiness',async()=>{
 let calls=0;const stream=new CityStreamResidency([tile('bad')],async()=>{calls++;throw Error('decode failed');},budget);
 await stream.update(0,0,1,2);await stream.update(0,0,1,2);assert.equal(calls,1);assert.equal(stream.stats.ready,false);assert.deepEqual(stream.stats.failed,{bad:'decode failed'});assert.equal(stream.stats.pending,null);stream.dispose();
});
test('invalid data and raised budgets fail before importing anything',()=>{
 assert.throws(()=>new CityStreamResidency([tile('same'),tile('same')],async()=>handle()));
 assert.throws(()=>new CityStreamResidency([],async()=>handle(),{...budget,tiles:1000}));
 assert.throws(()=>new CityStreamResidency([{...tile('bad'),triangles:NaN}],async()=>handle()));
});
test('a focus request arriving while an empty drain settles is not lost',async()=>{
 let calls=0;const stream=new CityStreamResidency([tile('a')],async()=>{calls++;return handle();},budget);
 const empty=stream.update(100,0,1,2);const work=stream.update(0,0,1,2);await Promise.all([empty,work]);assert.equal(calls,1);assert.equal(stream.stats.ready,true);stream.dispose();
});
