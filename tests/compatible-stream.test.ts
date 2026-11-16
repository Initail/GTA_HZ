import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {planBaseStream} from '../src/city-base-stream-plan.ts';import {COMPATIBLE_CITY_RANGE} from '../src/city-stream-profile.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';
const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8'),begin=source.indexOf('  for(const b of this.blocks){'),end=source.indexOf('\n  for(const m of this.landmarks)',begin);
const cull=new Function('p','casters','reflect',source.slice(begin,end));
test('compatibility admission and actual world cull share visible, reflection and shadow ranges',()=>{
 for(const overview of [false,true])for(const visible of [false,true])for(const role of ['terrain','roads','buildings'] as const)for(const x of [0,299,520,599,600,759,760,961]){
  const bounds={min:[x,0,319],max:[x+1,1,321]},tile:BaseStreamTile={id:role+':0,0',role,file:'fixture.glb',baseUrl:'http://fixture/',bytes:4,logicalBytes:4,triangles:1,sha256:'0'.repeat(64),bounds};
  const focus=role==='terrain'?{x:0,z:320}:{x:320-x,z:320},mesh={name:'roads_0_0_asphalt',enabled:false,setEnabled(v:boolean){this.enabled=v;}},casters:unknown[]=[],reflect:unknown[]=[];
  const b={mesh,x:320,z:320,road:role==='roads',...(role==='terrain'?{bounds:{minX:x,maxX:x+1,minZ:319,maxZ:321}}:{})};
  cull.call({blocks:[b],debugFacades:true,overviewEffects:overview,compatibleRange:COMPATIBLE_CITY_RANGE},focus,casters,reflect);
  const result=planBaseStream([tile],{...focus,overview,rangeProfile:'compatible',intersects:()=>visible});
  assert.equal(result.required.includes(tile),mesh.enabled&&visible||casters.includes(mesh)||reflect.includes(mesh));
 }
});
test('compatibility view does not admit an entire city on entering aerial mode',()=>{
 const tiles=[0,1,20].map(x=>({id:'buildings:'+x+',0',role:'buildings' as const,file:'fixture.glb',baseUrl:'http://fixture/',bytes:4,logicalBytes:4,triangles:1,sha256:'0'.repeat(64),bounds:{min:[x*640,0,0],max:[x*640+600,30,600]}}));
 const plan=planBaseStream(tiles,{x:320,z:320,overview:true,rangeProfile:'compatible'});assert.deepEqual(plan.required.map(t=>t.id),['buildings:0,0','buildings:1,0']);
 assert.equal(plan.budget.triangles,1_000_000);assert.equal(plan.budget.tiles,32);
});
