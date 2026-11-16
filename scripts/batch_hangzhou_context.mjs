/** Batch one static context candidate by material without changing geometry.
 * Source-object ownership stays in the audit; GPU batches need not recreate
 * 157 separate material primitives for a single small temple precinct.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {joinPrimitives,prune,unpartition} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';

const [input,output,prefix]=process.argv.slice(2);
assert(input&&output&&prefix&&/^detail_[a-z0-9_-]+_$/.test(prefix));
assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep)&&!fs.existsSync(output));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const sha=f=>hash(fs.readFileSync(f));
const inputSha256=sha(input),identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
await Promise.all([MeshoptDecoder.ready,MeshoptEncoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const doc=await io.read(input),root=doc.getRoot(),scene=root.getDefaultScene();
assert.equal(root.listScenes().length,1);assert.equal(root.listAnimations().length,0);
assert.equal(root.listTextures().length,0,'Texture-bearing contexts need a separate material-content audit');
const names=root.listMaterials().map(m=>m.getName());assert.equal(new Set(names).size,names.length);

async function snapshot(document){
 const root=document.getRoot(),json=(await io.writeJSON(document)).json;
 const materials=root.listMaterials();
 const palettes=Object.fromEntries(materials.map((m,i)=>[m.getName(),json.materials[i]]));
 const triangles={},sourceNodes=[];let count=0,primitives=0;
 for(const n of root.listNodes()){
  if(!n.getMesh())continue;
  assert.deepEqual(n.getWorldMatrix(),identity);assert(!n.getSkin()&&!n.listChildren().length);
  const mesh=n.getMesh();let nodeTriangles=0;
  for(const p of mesh.listPrimitives()){
   assert.equal(p.getMode(),4);assert.equal(p.listTargets().length,0);primitives++;
   const semantics=p.listSemantics().sort();
   const attrs=semantics.map(s=>p.getAttribute(s));
   const key=p.getMaterial().getName()+'|'+JSON.stringify(attrs.map((a,i)=>[semantics[i],a.getType(),a.getComponentType(),a.getNormalized()]));
   const list=triangles[key]??=[];
   const idx=p.getIndices().getArray();assert.equal(idx.length%3,0);
   const vertices=new Map();
   const vertex=i=>{
    if(vertices.has(i))return vertices.get(i);
    const text=attrs.map(a=>{const array=a.getArray(),size=a.getElementSize(),step=array.BYTES_PER_ELEMENT;
     return Buffer.from(array.buffer,array.byteOffset+i*size*step,size*step).toString('hex');}).join(':');
    vertices.set(i,text);return text;
   };
   for(let i=0;i<idx.length;i+=3){
    const a=vertex(idx[i]),b=vertex(idx[i+1]),c=vertex(idx[i+2]);
    const rotations=[a+'|'+b+'|'+c,b+'|'+c+'|'+a,c+'|'+a+'|'+b];rotations.sort();
    list.push(hash(rotations[0]));count++;nodeTriangles++;
   }
  }
  sourceNodes.push({name:n.getName(),extras:n.getExtras(),triangles:nodeTriangles});
 }
 return {content:{palettes,triangles:Object.fromEntries(Object.entries(triangles).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,{count:v.length,sha256:hash(v.sort().join(''))}]))},count,primitives,sourceNodes};
}
const before=await snapshot(doc),groups=new Map(),oldNodes=[...root.listNodes()],oldMeshes=[...root.listMeshes()];
for(const node of oldNodes){
 if(!node.getMesh())continue;
 assert.deepEqual(node.getWorldMatrix(),identity);
 for(const p of node.getMesh().listPrimitives()){
  const key=p.getMaterial().getName()+'|'+p.listSemantics().sort().join(',');
  const group=groups.get(key)??{primitives:[],owners:new Set()};
  group.primitives.push(p);group.owners.add(node.getName());groups.set(key,group);
 }
}
let number=0;
for(const [key,group] of groups){
 const primitive=joinPrimitives(group.primitives);
 const name=prefix+key.split('|')[0]+'_'+number++;
 const mesh=doc.createMesh(name).addPrimitive(primitive);
 scene.addChild(doc.createNode(name).setMesh(mesh).setExtras({sourceNodes:[...group.owners],sourceArtifactSha256:inputSha256}));
}
for(const n of oldNodes)n.dispose();
for(const m of oldMeshes)m.dispose();
await doc.transform(prune({keepAttributes:true,keepLeaves:true}),unpartition());
const joined=await snapshot(doc);assert.deepEqual(joined.content,before.content,'Batching changed oriented triangles, vertex attributes or materials');
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
fs.mkdirSync(output,{recursive:true});
const file=path.join(output,'context.glb');await io.write(file,doc);
const actual=await snapshot(await io.read(file));assert.deepEqual(actual.content,before.content,'Written batch geometry differs from source');
assert.equal(sha(input),inputSha256);
const report={kind:'lossless material-batched context candidate',input,inputSha256,scriptSha256:sha('scripts/batch_hangzhou_context.mjs'),
 asset:{file:'context.glb',sha256:sha(file),bytes:fs.statSync(file).size},triangles:actual.count,
 originalPrimitives:before.primitives,batchedPrimitives:actual.primitives,originalSourceNodes:before.sourceNodes,
 content:actual.content,checks:{allOrientedTrianglesExact:true,allVertexAttributesExact:true,materialValuesExact:true,worldTransformsIdentity:true,actualCompressedDecodeExact:true},
 caveat:'Primitive count is a draw-call upper-bound input, not a measured GPU/FPS result. One context precinct now shares visibility bounds; browser culling/performance remains pending.',
 browserAccepted:false};
fs.writeFileSync(path.join(output,'batch-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({triangles:report.triangles,originalPrimitives:before.primitives,batchedPrimitives:actual.primitives,asset:report.asset,checks:report.checks},null,2));
