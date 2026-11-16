import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {planBaseStream} from '../src/city-base-stream-plan.ts';
import {CityStreamResidency,BASE_STREAM_LIMITS} from '../src/city-stream-residency.ts';
import {COMPATIBLE_CITY_RANGE} from '../src/city-stream-profile.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';

const tiles:BaseStreamTile[]=Array.from({length:80},(_,i)=>({
 id:'terrain:'+i+',0',role:'terrain',file:'fixture.glb',baseUrl:'http://fixture/',
 bytes:1024*1024,logicalBytes:2*1024*1024,triangles:20000,sha256:'0'.repeat(64),
 bounds:{min:[i*160,0,0],max:[i*160+160,30,160]},
}));

test('full aerial view admits every visible source tile beyond the old radius and 32-tile cap',()=>{
 const plan=planBaseStream(tiles,{x:0,z:0,overview:true,rangeProfile:'full',intersects:()=>true});
 assert.equal(plan.admitted,true,'the full view must not become an empty blocked scene');
 assert.deepEqual(plan.required.map(t=>t.id),tiles.map(t=>t.id));
 assert.equal(plan.budget.tiles,tiles.length);
 assert.equal(plan.budget.bytes,80*1024*1024);
});

test('full-city residency loads and retains the complete requested view',async()=>{
 const budget={tiles:80,bytes:80*1024*1024,logicalBytes:160*1024*1024,triangles:1600000};
 let disposed=0;
 const stream=new CityStreamResidency(tiles,async()=>({setVisible:(_visible:boolean)=>{},dispose:()=>{disposed++;}}),budget,'full-city');
 const ids=tiles.map(t=>t.id);
 await stream.select(0,0,ids,ids);
 assert.equal(stream.stats.ready,true);
 assert.equal(stream.stats.resident,80);
 assert.deepEqual(stream.stats.blocked,[]);
 stream.dispose();assert.equal(disposed,80);
});

test('full-city policy remains bounded by the supplied source catalog',()=>{
 const beyondCatalog={tiles:81,bytes:80*1024*1024,logicalBytes:160*1024*1024,triangles:1600000};
 assert.throws(()=>new CityStreamResidency(tiles,async()=>({setVisible:()=>{},dispose:()=>{}}),beyondCatalog,'full-city'));
 const legacy=planBaseStream(tiles,{x:0,z:0,overview:true,rangeProfile:'compatible'});
 assert.deepEqual(legacy.budget,BASE_STREAM_LIMITS);
});

test('actual world default displays distant aerial ground rather than floating trees',()=>{
 const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8');
 const initializer=source.match(/readonly compatibleRange[^=]*=([^;]+);/)?.[1];assert.ok(initializer);
 const range=new Function('COMPATIBLE_CITY_RANGE','return '+initializer)(COMPATIBLE_CITY_RANGE);
 const begin=source.indexOf('  for(const b of this.blocks){'),end=source.indexOf('\n  for(const m of this.landmarks)',begin);
 const cull=new Function('p','casters','reflect',source.slice(begin,end));
 const mesh={name:'terrain_ground',enabled:false,setEnabled(v:boolean){this.enabled=v;}};
 cull.call({blocks:[{mesh,x:8000,z:0,terrain:true,road:false}],debugFacades:true,overviewEffects:true,compatibleRange:range},{x:0,z:0},[],[]);
 assert.equal(mesh.enabled,true,'visible distant ground must survive world culling');
});
