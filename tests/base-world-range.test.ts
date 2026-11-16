import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {planBaseStream} from '../src/city-base-stream-plan.ts';
import type {BaseStreamTile} from '../src/city-stream-assets.ts';
const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8');
const begin=source.indexOf('  for(const b of this.blocks){'),end=source.indexOf('\n  for(const m of this.landmarks)',begin);
assert(begin>=0&&end>begin);
const originalCull=new Function('p','casters','reflect',source.slice(begin,end));
function compare(role:'buildings'|'roads',cell:number,minX:number,maxX:number,focusX:number,intersects:boolean){
 const tile:BaseStreamTile={id:role+':'+cell+',0',role,file:'fixture.glb',baseUrl:'http://fixture/',bytes:20,logicalBytes:40,triangles:2,sha256:'0'.repeat(64),bounds:{min:[minX,0,280],max:[maxX,30,360]}};
 const mesh={name:(role==='buildings'?'block_':'roads_')+cell+'_0_asphalt',enabled:false,setEnabled(v:boolean){this.enabled=v;}},casters:unknown[]=[],reflect:unknown[]=[];
 originalCull.call({blocks:[{mesh,x:(cell+.5)*640,z:320,road:role==='roads'}],overviewEffects:false,debugFacades:true},{x:focusX,z:320},casters,reflect);
 const expected=mesh.enabled&&intersects||casters.includes(mesh)||reflect.includes(mesh);
 const plan=planBaseStream([tile],{x:focusX,z:320,overview:false,intersects:()=>intersects});
 assert.equal(plan.required.includes(tile),expected,'Required geometry must match the actual original world cull and auxiliary lists');
}
test('load buildings actually displayed by the world even when their geometry extends beyond the nominal range',()=>compare('buildings',4,3150,3190,-400,true));
test('do not load a distant disabled building just because its bounds extend into the radius',()=>compare('buildings',5,3200,3280,0,true));
test('keep original road range at both sides of the original cell-centre boundary',()=>{compare('roads',3,2500,2550,-200,true);compare('roads',3,1930,1990,-500,true);});
test('off-camera reflection coverage uses the same original building centre as the world',()=>{compare('buildings',1,1250,1270,-400,false);compare('buildings',2,1280,1330,0,false);});
test('refined child and actual original cull agree at inherited centre boundaries',()=>{
 const tile:BaseStreamTile={id:'buildings:4,0/child',parentSourceId:'buildings:4,0',role:'buildings',file:'fixture.glb',baseUrl:'http://fixture/',bytes:20,logicalBytes:40,triangles:2,sha256:'0'.repeat(64),bounds:{min:[3150,0,280],max:[3190,30,360]}};
 for(const focusX of [-450,-400,1470,1490])for(const intersects of [true,false]){
  const mesh={name:'block_4_0_plaster__child',enabled:false,setEnabled(v:boolean){this.enabled=v;}},casters:unknown[]=[],reflect:unknown[]=[];
  originalCull.call({blocks:[{mesh,x:2880,z:320,road:false}],overviewEffects:false,debugFacades:true},{x:focusX,z:320},casters,reflect);
  assert.equal(planBaseStream([tile],{x:focusX,z:320,overview:false,intersects:()=>intersects}).required.includes(tile),mesh.enabled&&intersects||casters.includes(mesh)||reflect.includes(mesh));
 }
});
