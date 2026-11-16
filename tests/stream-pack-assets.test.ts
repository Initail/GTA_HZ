import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {inspectStreamGlb,bindStreamTextureUrls,type StreamGlbTile} from '../src/city-stream-assets.ts';
const descriptor=JSON.parse(readFileSync(new URL('./fixtures/pack-pilot/descriptor.json',import.meta.url),'utf8'));
const tile:StreamGlbTile={...descriptor,role:'pack',baseUrl:'http://test/'},bytes=new Uint8Array(readFileSync(new URL('./fixtures/pack-pilot/'+descriptor.file,import.meta.url)));
test('real physical terrain/road/building pack is accepted with all original source nodes',()=>{
 const inspected=inspectStreamGlb(bytes,tile,descriptor.textures);assert.equal(inspected.doc.nodes.length,descriptor.nodes.length);assert.equal(descriptor.members.length,3);assert.equal(tile.triangles,36342);
 const roles=new Set(descriptor.nodes.map((n:any)=>n.role));assert.deepEqual(roles,new Set(['terrain','roads','buildings']));
});
test('mixed pack image binding leaves every geometry byte untouched and refuses false cost',()=>{
 const original=inspectStreamGlb(bytes,tile,descriptor.textures),bound=bindStreamTextureUrls(bytes,tile,descriptor.textures,descriptor.textures.map((_:unknown,i:number)=>'blob:pack-'+i)),n=new DataView(bound.buffer).getUint32(12,true);
 assert.deepEqual(bound.subarray(28+n),bytes.subarray(original.bin));
 assert.throws(()=>inspectStreamGlb(bytes,{...tile,triangles:tile.triangles-1},descriptor.textures),/预算不一致/);
 assert.throws(()=>inspectStreamGlb(bytes,{...tile,logicalBytes:tile.logicalBytes-1},descriptor.textures),/预算不一致/);
});
