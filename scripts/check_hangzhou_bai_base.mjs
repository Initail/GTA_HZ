/** Prove the small CPU ray context matches the actual full base GLB contents. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
const [stage,dir]=process.argv.slice(2),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),fileSha=p=>sha(fs.readFileSync(p));
const report=JSON.parse(fs.readFileSync(path.join(dir,'report.json')));await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const snapshot=p=>({material:p.getMaterial().getName(),attributes:Object.fromEntries(p.listSemantics().sort().map(s=>{const a=p.getAttribute(s),v=a.getArray();return [s,{type:a.getType(),component:a.getComponentType(),normalized:a.getNormalized(),sha256:sha(Buffer.from(v.buffer,v.byteOffset,v.byteLength))}];})),indices:(()=>{const v=p.getIndices().getArray(),out=new Uint32Array(v.length);for(let i=0;i<v.length;i+=3){const t=[v[i],v[i+1],v[i+2]],j=t.indexOf(Math.min(...t));for(let k=0;k<3;k++)out[i+k]=t[(j+k)%3];}return sha(Buffer.from(out.buffer));})()});
const results=[];
for(const row of report.reports){
 const file=path.join(stage,'public/cities/hangzhou',row.file),local=path.join(dir,'context-'+row.file);assert.equal(fileSha(file),row.sha256);
 const full=await io.read(file),context=await io.read(local),nodes=new Map(full.getRoot().listNodes().filter(n=>n.getMesh()).map(n=>[n.getName(),n]));let count=0;
 for(const n of context.getRoot().listNodes())if(n.getMesh()){
  const source=nodes.get(n.getName());assert(source);assert.deepEqual(n.getWorldMatrix(),source.getWorldMatrix());
  for(const p of n.getMesh().listPrimitives()){const actual=source.getMesh().listPrimitives().find(q=>q.getMaterial().getName()===p.getMaterial().getName());assert(actual);assert.deepEqual(snapshot(p),snapshot(actual));count++;}
 }
 results.push({file:row.file,sha256:row.sha256,contextSha256:fileSha(local),matchedPrimitives:count});
}
const out=path.join(dir,'actual-context-verification.json');fs.writeFileSync(out,JSON.stringify({pass:true,results,method:'actual decoded attribute bytes, canonical directed indices, materials and world matrices'},null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(results));
