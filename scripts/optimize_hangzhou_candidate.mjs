/** Same upstream compression settings, fresh output and explicit UV2 protection. */
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dedup,weld,prune,meshopt} from '@gltf-transform/functions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const [input,output,manifestName='asset-manifest.json']=process.argv.slice(2);
const candidateRoot=path.resolve('artifacts/cities/hangzhou');
const relative=output&&path.relative(candidateRoot,path.resolve(output));
if(!input||!output||relative.startsWith('..')||path.isAbsolute(relative))throw Error('Input and fresh Hangzhou artifacts output required');
try{const entries=await fs.readdir(output);if(entries.length)throw Error('Output exists; preserve previous candidate');}catch(error){if(error.code!=='ENOENT')throw error;}
if(path.basename(manifestName)!==manifestName)throw Error('Expected local manifest filename');
const bytes=await fs.readFile(path.join(input,manifestName));
const source=JSON.parse(bytes);
if(source.cityId!=='hangzhou')throw Error('Hangzhou source manifest required');
const digest=data=>crypto.createHash('sha256').update(data).digest('hex');
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const stats=doc=>({triangles:doc.getRoot().listMeshes().reduce((total,mesh)=>total+mesh.listPrimitives().reduce((sum,p)=>sum+(p.getIndices()?.getCount()??p.getAttribute('POSITION').getCount())/3,0),0),meshes:doc.getRoot().listMeshes().map(m=>m.getName())});
await fs.mkdir(output,{recursive:true});
const report={schemaVersion:1,cityId:'hangzhou',input,inputManifestFile:manifestName,inputManifestSha256:digest(bytes),
 settings:{algorithm:'EXT_meshopt_compression',level:'high',quantizePosition:16,quantizeNormal:10,quantizeTexcoord:14,quantizationVolume:'mesh'},
 status:'compressed-intermediate-not-runtime-accepted',assets:[],pending:source.pending};
for(const asset of source.assets){
 const filename=path.basename(asset.file),sourceFile=path.join(input,filename),data=await fs.readFile(sourceFile);
 if(digest(data)!==asset.sha256)throw Error('Changed source '+filename);
 const doc=await io.read(sourceFile),before=stats(doc);
 if(doc.getRoot().listMeshes().some(m=>m.listPrimitives().some(p=>p.getAttribute('TEXCOORD_1'))))throw Error('UV2 metadata already present; do not dedup/weld final facade assets');
 await doc.transform(dedup(),weld(),prune(),meshopt({encoder:MeshoptEncoder,level:'high',quantizePosition:16,quantizeNormal:10,quantizeTexcoord:14,quantizationVolume:'mesh'}));
 const target=path.join(output,filename);await io.write(target,doc);
 const after=stats(await io.read(target));
 if(after.triangles!==before.triangles||JSON.stringify(after.meshes.slice().sort())!==JSON.stringify(before.meshes.slice().sort()))throw Error('Compression changed triangle count or mesh identities');
 const optimized=await fs.readFile(target);
 report.assets.push({file:filename,inputSha256:asset.sha256,sha256:digest(optimized),beforeBytes:data.length,bytes:optimized.length,triangles:after.triangles,meshes:after.meshes.length});
 console.log(filename,data.length,'->',optimized.length);
 await fs.writeFile(path.join(output,'compression-progress.json'),JSON.stringify(report,null,2)+'\n');
}
await fs.writeFile(path.join(output,'asset-manifest.json'),JSON.stringify(report,null,2)+'\n');
