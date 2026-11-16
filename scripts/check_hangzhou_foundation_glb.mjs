/** Exact local float32 triangle and closed-edge audit of actual exported GLB. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
const [root,output]=process.argv.slice(2),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
assert(root&&output&&!fs.existsSync(output),'Fresh report required');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'asset-manifest.json'))),asset=manifest.assets[0];
assert.equal(sha(fs.readFileSync(path.join(root,asset.file))),asset.sha256);
await MeshoptDecoder.ready;
const doc=await new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder}).read(path.join(root,asset.file)),results=[];
const compare=(a,b)=>{for(let i=0;i<a.length;i++){if(Array.isArray(a[i])){const c=compare(a[i],b[i]);if(c)return c;}else if(a[i]!==b[i])return a[i]-b[i];}return 0;};
const encode=pts=>{const b=Buffer.alloc(pts.length*12);pts.flat().forEach((v,i)=>b.writeFloatLE(v||0,i*4));return b.toString('hex');};
for(const expected of manifest.objects){
 const mesh=doc.getRoot().listMeshes().find(m=>m.getName()===expected.mesh);assert(mesh);
 const nodes=doc.getRoot().listNodes().filter(n=>n.getMesh()===mesh);assert.equal(nodes.length,1);const node=nodes[0],o=expected.originENU;
 assert.deepEqual(node.getWorldMatrix(),[1,0,0,0,0,1,0,0,0,0,1,0,o[0],o[2],-o[1],1]);
 const keys=[],edges=new Map();let zeroArea=0;
 for(const p of mesh.listPrimitives()){
  const position=p.getAttribute('POSITION'),indices=p.getIndices()?.getArray()??Uint32Array.from({length:position.getCount()},(_,i)=>i);
  for(let i=0;i<indices.length;i+=3){
   const t=[0,1,2].map(j=>position.getElement(indices[i+j],[]).map(v=>v||0));
   const rotations=[t,[t[1],t[2],t[0]],[t[2],t[0],t[1]]].sort(compare);keys.push(encode(rotations[0]));
   const a=t[1].map((v,j)=>v-t[0][j]),b=t[2].map((v,j)=>v-t[0][j]);if(Math.hypot(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])===0)zeroArea++;
   for(let j=0;j<3;j++){const pair=[t[j],t[(j+1)%3]],sign=compare(pair[0],pair[1])<0?1:-1,k=encode(pair.slice().sort(compare));const e=edges.get(k)??{count:0,balance:0};e.count++;e.balance+=sign;edges.set(k,e);}
  }
 }
 const triangleSha=sha(keys.sort().join('\n')),badEdges=[...edges.values()].filter(e=>e.count!==2||e.balance!==0).length;
 results.push({id:expected.id,triangles:keys.length,triangleSha256:triangleSha,expectedTriangleSha256:expected.localGltfTrianglesSha256,zeroArea,nonManifoldOrUnpairedDirectedEdges:badEdges,pass:triangleSha===expected.localGltfTrianglesSha256&&keys.length===expected.triangles&&zeroArea===0&&badEdges===0});
}
const report={kind:'actual-foundation-glb-exact-float32-and-closed-edge-check',manifestSha256:sha(fs.readFileSync(path.join(root,'asset-manifest.json'))),checkerSha256:sha(fs.readFileSync('scripts/check_hangzhou_foundation_glb.mjs')),results,pass:results.every(r=>r.pass),pending:['runtime collision/body contact and entrance','browser visual and performance']};fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.pass)process.exitCode=1;
