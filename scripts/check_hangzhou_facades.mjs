/** Read actual GLB attributes; no browser or visual acceptance implied. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptDecoder} from 'meshoptimizer';
const [root,output,manifestName='manifest.json']=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!root||!output||fs.existsSync(output))throw Error('Candidate root and fresh report required');
if(path.basename(manifestName)!==manifestName)throw Error('Local manifest name required');
const manifest=JSON.parse(fs.readFileSync(path.join(root,manifestName))),records=[];
await MeshoptDecoder.ready;
for(const asset of manifest.assets){
 const file=path.join(root,asset.file);if(sha(file)!==asset.sha256)throw Error('Changed GLB '+file);
 const doc=await new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder}).read(file),primitives=doc.getRoot().listMeshes().flatMap(m=>m.listPrimitives()),colors=new Set();let missing=0,invalid=0,triangles=0,vertices=0;
 for(const p of primitives){
  const positions=p.getAttribute('POSITION'),a=p.getAttribute('COLOR_0'),normals=p.getAttribute('NORMAL');
  vertices+=positions.getCount();triangles+=(p.getIndices()?.getCount()??positions.getCount())/3;
  if(!a||a.getCount()!==positions.getCount()||!normals||normals.getCount()!==positions.getCount()){missing++;continue;}
  // getElement decodes glTF normalized U8/U16 values; raw arrays are integers.
  const element=[];for(let i=0;i<a.getCount();i++){a.getElement(i,element);if(element.some(x=>!Number.isFinite(x)||x<0||x>1))invalid++;colors.add(element.map(x=>x.toFixed(3)).join(','));}
  for(const attribute of [positions,normals])for(const value of attribute.getArray())if(!Number.isFinite(value))invalid++;
 }
 const record={file:asset.file,sha256:asset.sha256,primitives:primitives.length,vertices,triangles,missingAttributes:missing,invalidValues:invalid,uniqueColors:colors.size,texturedMaterials:doc.getRoot().listMaterials().filter(m=>m.getBaseColorTexture()).length};
 records.push({...record,pass:!missing&&!invalid&&colors.size>1&&triangles===asset.triangles});
}
const report={kind:'actual-export-facade-attributes',manifestSha256:sha(path.join(root,manifestName)),checkerSha256:sha('scripts/check_hangzhou_facades.mjs'),smokeSubset:manifest.smokeSubset,records,pass:records.every(r=>r.pass),browser:false,pending:manifest.pending};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.pass)process.exitCode=1;
