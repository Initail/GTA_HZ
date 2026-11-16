import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8');
const start=source.indexOf(' private prepareBaseFrame(){')+' private prepareBaseFrame(){'.length;
const end=source.indexOf('\n async init(',start);
const prepare=new Function(source.slice(start,end).replace(/\n }\s*$/,''));
test('in-flight streaming leaves rendering and held controls active without a DOM overlay',()=>{
 const keys=new Set(['KeyW']);let culled=0,requested=0;
 const world={keys,baseTravel:null,baseDirty:true,baseView:()=>({}),cull:()=>{culled++;},baseStream:{request:()=>{requested++;},stats:{ready:false}}};
 assert.equal(prepare.call(world),true);
 assert.equal(keys.has('KeyW'),true);assert.equal(culled,1);assert.equal(requested,1);
});
test('explicit fast travel waits to commit while retaining the last rendered frame',()=>{
 const keys=new Set(['KeyW']);
 const world={keys,baseTravel:{landmark:{}},baseDirty:false,baseView:()=>({}),baseStream:{request:()=>{},stats:{ready:false}}};
 assert.equal(prepare.call(world),false);assert.equal(keys.size,0);
});
