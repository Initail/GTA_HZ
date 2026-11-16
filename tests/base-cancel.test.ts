import {test} from 'node:test';import assert from 'node:assert/strict';
import {CityBaseStream} from '../src/city-base-stream.ts';
import {CityStreamResidency} from '../src/city-stream-residency.ts';
const tile=(id:string,x:number,triangles=3)=>({id,role:'buildings' as const,file:id+'.glb',baseUrl:'http://test/',sha256:'0'.repeat(64),bytes:10,logicalBytes:20,triangles,bounds:{min:[x,0,0],max:[x+1,1,1]}});
const view=(x:number)=>({x,z:0,overview:false});
function make(tiles:any[],load:any){
 const stream=new CityBaseStream({onDisposeObservable:{addOnce:()=>{}}} as any,{} as any,{attach:()=>()=>{}});
 Object.assign(stream,{tiles,stream:new CityStreamResidency(tiles,load)});return stream;
}
test('an over-budget view cancels the old transfer, drains its late handle, and stays not ready',async()=>{
 let signal!:AbortSignal,finish!:(value:any)=>void,disposed=0,starts=0;
 const stream=make([tile('near',0),tile('over-budget',10000,1_000_001)],async(t:any,s:AbortSignal)=>{starts++;signal=s;return new Promise(resolve=>finish=resolve);});
 const initial=stream.request(view(0));assert.equal(starts,1);
 const rejected=stream.request(view(10000));const aborted=signal.aborted;
 finish({container:{meshes:[]},setVisible:()=>{},dispose:()=>disposed++});await initial;await rejected;
 assert.equal(aborted,true,'a rejected plan must stop its obsolete active import');
 assert.equal(disposed,1);assert.equal(stream.stats.residency!.resident,0);assert.equal(stream.stats.ready,false);
 await stream.request(view(10000));assert.equal(starts,1,'blocked views never retry or fetch the large tile');stream.dispose();
});
test('same visible set with a changed retention set still unloads the old distant tile',async()=>{
 let disposed=0;
 const stream=make([tile('a',0),tile('b',3600)],async()=>({container:{meshes:[]},setVisible:()=>{},dispose:()=>disposed++}));
 await stream.request(view(3500));assert.equal(stream.stats.residency!.resident,1);
 await stream.request(view(0));assert.equal(stream.stats.residency!.resident,2);
 await stream.request(view(-500));assert.equal(stream.stats.residency!.resident,1);assert.equal(disposed,1);stream.dispose();
});
