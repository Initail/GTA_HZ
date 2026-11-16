/** One bounded far-LOD experiment using the actual immutable tile geometry.
 * Near assets, source collisions, road graph and landmarks are never modified.
 * This candidate has no runtime visibility until geometric/visual gates pass.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {compactPrimitive,prune,unpartition,weld} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder,MeshoptSimplifier} from 'meshoptimizer';
const [role,x,z,version='v1']=process.argv.slice(2);assert(['terrain','roads','buildings'].includes(role)&&/^-?\d+$/.test(x)&&/^-?\d+$/.test(z)&&/^[a-z0-9-]+$/.test(version));
const folder=`artifacts/cities/hangzhou/${role==='buildings'?'stream-mesh-v2':'stream-mesh-v1'}/${role}`,manifest=JSON.parse(fs.readFileSync(folder+'/manifest.json','utf8'));
const tile=manifest.tiles.find(t=>t.tile[0]===Number(x)&&t.tile[1]===Number(z));assert(tile);
const input=path.join(folder,tile.file),output=`artifacts/cities/hangzhou/far-lod-${version}/${role}/${x}_${z}`;assert(!fs.existsSync(output));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');assert.equal(sha(fs.readFileSync(input)),tile.sha256);
await Promise.all([MeshoptDecoder.ready,MeshoptEncoder.ready,MeshoptSimplifier.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const doc=await io.read(input),root=doc.getRoot();assert(!root.listAnimations().length&&!root.listSkins().length);
await doc.transform(weld({overwrite:false}));
const rows=[];let triangles=0,maxError=0;
for(const node of root.listNodes()){
 const mesh=node.getMesh();if(!mesh)continue;const m=node.getWorldMatrix();
 for(const p of mesh.listPrimitives()){
  assert.equal(p.getMode(),4);assert.equal(p.listTargets().length,0);compactPrimitive(p);
  const position=p.getAttribute('POSITION'),indices=p.getIndices(),world=new Float32Array(position.getCount()*3),v=[];
  for(let i=0;i<position.getCount();i++){position.getElement(i,v);world[i*3]=m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12];world[i*3+1]=m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13];world[i*3+2]=m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14];}
  const before=indices.getCount()/3,material=p.getMaterial()?.getName()??'',water=/water/.test(node.getName());
  // Fixed 0.35 game-unit far-field error target; boundaries remain locked.
  // Water is kept exact to retain all shorelines and river/canal openings.
  const [next,error]=water?[new Uint32Array(indices.getArray()),0]:MeshoptSimplifier.simplify(new Uint32Array(indices.getArray()),world,3,Math.max(3,Math.floor(indices.getCount()*.1/3)*3),.35,['LockBorder','ErrorAbsolute']);
  assert(error<=.35001&&next.length>0);assert(next.length<=indices.getCount());
  p.setIndices(doc.createAccessor().setType('SCALAR').setArray(next).setBuffer(indices.getBuffer()));compactPrimitive(p);
  rows.push({node:node.getName(),material,sourceTriangles:before,farTriangles:next.length/3,simplifierErrorGame:error,waterKeptExact:water});triangles+=next.length/3;maxError=Math.max(maxError,error);
 }
}
await doc.transform(prune({keepAttributes:true,keepLeaves:true}),unpartition());
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
fs.mkdirSync(output,{recursive:true});const file=path.join(output,'far.glb');await io.write(file,doc);
const actual=await io.read(file);let actualTriangles=0,logicalBytes=0;const accessors=new Set();
for(const mesh of actual.getRoot().listMeshes())for(const p of mesh.listPrimitives()){actualTriangles+=p.getIndices().getCount()/3;accessors.add(p.getIndices());for(const a of p.listAttributes())accessors.add(a);}
for(const a of accessors)logicalBytes+=a.getArray().byteLength;assert.equal(actualTriangles,triangles);
assert.equal(sha(fs.readFileSync(input)),tile.sha256);
const result={schemaVersion:1,kind:'lossy far-field candidate, not installed',role,tile:tile.id,input:{file:input,sha256:tile.sha256,bytes:tile.bytes,logicalBytes:tile.logicalBytes,triangles:tile.triangles},output:{file:'far.glb',sha256:sha(fs.readFileSync(file)),bytes:fs.statSync(file).size,logicalBytes,triangles},rows,maxErrorGame:maxError,errorBasis:'meshoptimizer reported absolute error; independent geometry-distance and rendered silhouette acceptance still required',nearGeometryUnchanged:true,collisionUnchanged:true,navigationUnchanged:true,visualAccepted:false};
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({role,tile:tile.id,before:result.input,after:result.output,maxErrorGame:maxError,visualAccepted:false}));
