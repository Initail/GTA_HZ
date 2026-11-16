import {test} from 'node:test';import assert from 'node:assert/strict';
import {planBaseStreamPacks,type BaseStreamPack} from '../src/city-stream-pack-plan.ts';
import {planBaseStream} from '../src/city-base-stream-plan.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';
const hash='a'.repeat(64);
function source(id:string,x:number,role:BaseStreamTile['role']='buildings'):BaseStreamTile{return {id,role,baseUrl:'http://test/',file:id+'.glb',sha256:hash,bounds:{min:[x,0,0],max:[x+100,20,100]},bytes:100,logicalBytes:200,triangles:10};}
function pack(id:string,ids:string[],quality:'near'|'far',bytes=100):BaseStreamPack{return {id,role:'pack',baseUrl:'http://test/',file:id+'.glb',sha256:hash,bounds:{min:[-100,0,-100],max:[10000,20,100]},bytes,logicalBytes:bytes*2,triangles:20,members:ids.map(id=>({id,quality,referenceSha256:hash}))};}
test('mixed near/far keeps original source coverage with exactly one visible representation',()=>{
 const sources=[source('a',0),source('b',900),source('c',3200),source('outside',6000)],packs=[pack('near-a',['a'],'near'),pack('far-bc',['b','c'],'far')];
 const plan=planBaseStreamPacks(sources,packs,{x:0,z:0,overview:false});assert(plan.admitted);assert.deepEqual(plan.sourceRequired,planBaseStream(sources,{x:0,z:0,overview:false}).required.map(t=>t.id));assert.equal(plan.cost.tiles,2);assert.deepEqual(plan.required.map(p=>p.visibleMembers),[['a'],['b','c']]);assert.equal(Object.keys(plan.representations).length,3);
});
test('packing hidden geometry does not make its full bytes or triangles disappear',()=>{
 const sources=[source('a',0),source('outside',6000)],p=pack('combined',['a','outside'],'near',25*1024*1024),plan=planBaseStreamPacks(sources,[p],{x:0,z:0,overview:false});
 assert.deepEqual(plan.required[0].visibleMembers,['a']);assert.equal(plan.cost.bytes,p.bytes);assert.equal(plan.cost.triangles,p.triangles);assert.equal(plan.admitted,false);assert(plan.exceeded.includes('bytes'));
});
test('near object cannot fall back to far when original geometry is missing',()=>{
 const plan=planBaseStreamPacks([source('a',0)],[pack('far',['a'],'far')],{x:0,z:0,overview:false});assert.equal(plan.admitted,false);assert.deepEqual(plan.missing,['a']);assert.equal(plan.required.length,0);
});
test('far representation can fall back to exact near geometry with full actual cost',()=>{
 const plan=planBaseStreamPacks([source('a',1400)],[pack('near',['a'],'near')],{x:0,z:0,overview:false});assert(plan.admitted);assert.equal(plan.representations.a.quality,'near');assert.equal(plan.cost.bytes,100);
});
test('frustum exclusion does not drop geometry required by reflection or shadow range',()=>{
 const sources=[source('reflection',1000),source('offscreen-road',1000,'roads'),source('overview-shadow',1600)];
 const packs=sources.map(s=>pack(s.id,[s.id],'far'));
 const street=planBaseStreamPacks(sources,packs,{x:0,z:0,overview:false,intersects:()=>false});assert.deepEqual(street.sourceRequired,['reflection']);
 const overview=planBaseStreamPacks(sources,packs,{x:0,z:0,overview:true,intersects:()=>false});assert.deepEqual(overview.sourceRequired,['reflection','overview-shadow']);
});
test('transition hysteresis preserves near quality without two visible copies',()=>{
 const sources=[source('a',700)],packs=[pack('near',['a'],'near'),pack('far',['a'],'far')],view={x:0,z:0,overview:false};
 assert.equal(planBaseStreamPacks(sources,packs,view).representations.a.quality,'far');
 const held=planBaseStreamPacks(sources,packs,view,new Set(['a']));assert.equal(held.representations.a.quality,'near');assert.equal(held.required.length,1);
 const released=planBaseStreamPacks(sources,packs,{...view,x:-101},held.near);assert.equal(released.representations.a.quality,'far');assert.equal(released.required.length,1);
});
test('duplicate coverage, source-version mismatch and many real containers stay blocked',()=>{
 const sources=[source('a',0)];assert.throws(()=>planBaseStreamPacks(sources,[pack('one',['a'],'near'),pack('two',['a'],'near')],{x:0,z:0,overview:false}),/duplicate/);
 const wrong=pack('one',['a'],'near');wrong.members[0].referenceSha256='b'.repeat(64);assert.throws(()=>planBaseStreamPacks(sources,[wrong],{x:0,z:0,overview:false}),/mismatch/);
 const many=Array.from({length:33},(_,i)=>source('source-'+i,0));const plan=planBaseStreamPacks(many,many.map(s=>pack(s.id,[s.id],'near')),{x:0,z:0,overview:false});assert.equal(plan.admitted,false);assert.deepEqual(plan.exceeded,['tiles']);assert.equal(plan.cost.tiles,33);
});
test('a forced near pack serves its distant members without another far payload or enlarged hysteresis',()=>{
 const sources=[source('a',0),source('b',900),source('hidden',6000)],packs=[pack('near',['a','b','hidden'],'near',700),pack('far',['a','b','hidden'],'far',400)];
 for(const ordered of [sources,[...sources].reverse()]){
  const mixed=planBaseStreamPacks(ordered,packs,{x:0,z:0,overview:false});
  assert.equal(mixed.required.length,1);assert.equal(mixed.cost.bytes,700);assert.equal(mixed.cost.triangles,20);assert.equal(mixed.representations.b.quality,'near');assert.deepEqual([...mixed.near],['a']);
  assert(!mixed.required[0].visibleMembers.includes('hidden'));
  const distant=planBaseStreamPacks(ordered,packs,{x:-801,z:0,overview:false},mixed.near);
  assert.equal(distant.required.length,1);assert.equal(distant.representations.a.quality,'far');assert.equal(distant.representations.b.quality,'far');assert.equal(distant.cost.bytes,400);assert.equal(distant.near.size,0);
 }
});
