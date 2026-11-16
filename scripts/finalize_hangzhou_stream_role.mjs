import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {openSource,tileGroups,tileInfo,sha,fileSha} from './hangzhou_stream_glb.mjs';
const [directory]=process.argv.slice(2),plan=JSON.parse(fs.readFileSync(path.join(directory,'plan.json')));
assert(!fs.existsSync(path.join(directory,'manifest.json')));const source=openSource(plan.source);
assert.equal(source.headerSha256,plan.sourceHeaderSha256);assert.equal(await fileSha(plan.source),plan.sourceSha256);
const original=tileGroups(source.doc,plan.role);assert.equal(plan.tiles.length,original.length);
const nodes=new Set(),tiles=[];
for(const [i,tile] of plan.tiles.entries()){
 assert.equal(tile.id,original[i].id);assert.deepEqual(tile.sourceNodes,original[i].nodes);
 const info=tileInfo(source.doc,original[i]);assert.equal(tile.triangles,info.triangles);
 // JSON represents -0 as 0. Keep exact numeric comparison at that transport boundary.
 assert.deepEqual(tile.bounds,JSON.parse(JSON.stringify(info.bounds)));
 for(const n of tile.sourceNodes){assert(!nodes.has(n));nodes.add(n);}
 const file=path.join(directory,tile.file),record=JSON.parse(fs.readFileSync(file+'.json')),check=JSON.parse(fs.readFileSync(file+'.validation.json'));
 assert.equal(check.pass,true);assert.equal(check.sourceSha256,plan.sourceSha256);assert.equal(check.targetSha256,record.sha256);assert.equal(check.triangles,tile.triangles);assert.equal(record.logicalBytes,tile.logicalBytes);
 assert.equal(fs.statSync(file).size,record.bytes);assert.equal(await fileSha(file),record.sha256);
 tiles.push({id:plan.role+':'+tile.id,file:tile.file,tile:tile.tile,bounds:tile.bounds,bytes:record.bytes,sha256:record.sha256,logicalBytes:record.logicalBytes,triangles:tile.triangles,nodes:tile.nodes});
}
assert.equal(nodes.size,source.doc.nodes.length);source.close();
for(const texture of plan.textures){const bytes=fs.readFileSync(path.join(directory,texture.file));assert.equal(bytes.length,texture.bytes);assert.equal(sha(bytes),texture.sha256);}
const manifest={schemaVersion:1,role:plan.role,source:{sha256:plan.sourceSha256,bytes:plan.sourceBytes},coordinateSpace:plan.coordinateSpace,tileSizeGame:640,
 textures:plan.textures,tiles,totals:{tiles:tiles.length,nodes:nodes.size,bytes:tiles.reduce((n,t)=>n+t.bytes,0),logicalBytes:tiles.reduce((n,t)=>n+t.logicalBytes,0),triangles:tiles.reduce((n,t)=>n+t.triangles,0)},
 validation:{allSourceNodesCoveredExactlyOnce:true,allDecodedAttributesIndicesTransformsMaterialsTexturesEqual:true,browserValidated:false,runtimeInstalled:false}};
fs.writeFileSync(path.join(directory,'manifest.json'),JSON.stringify(manifest)+'\n',{flag:'wx'});console.log(JSON.stringify({...manifest,tiles:undefined,textures:undefined,manifestBytes:fs.statSync(path.join(directory,'manifest.json')).size}));
