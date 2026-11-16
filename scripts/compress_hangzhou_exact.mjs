/** Meshopt entropy coding only: no quantization, welding, or attribute filters. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
const [input,output]=process.argv.slice(2),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
assert(input&&output&&!fs.existsSync(output));assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const bytes=fs.readFileSync(path.join(input,'asset-manifest.json')),source=JSON.parse(bytes);assert.equal(source.cityId,'hangzhou');
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
// Meshopt triangle coding may cyclically rotate (a,b,c) to (b,c,a), preserving
// all attribute associations and winding. Compare that allowed representation
// exactly without constructing an unbounded assertion diff of raw indices.
const indexSignature=p=>{
 const a=p.getIndices()?.getArray();if(!a)return null;
 const b=Buffer.alloc(a.length*4);
 for(let i=0;i<a.length;i+=3){
  if(p.getMode()!==4)throw Error('Exact compressor currently accepts triangles only');
  const t=[a[i],a[i+1],a[i+2]],j=t.indexOf(Math.min(...t));
  for(let k=0;k<3;k++)b.writeUInt32LE(t[(j+k)%3],(i+k)*4);
 }
 return {count:a.length,directedTrianglesSha256:sha(b)};
};
const snapshot=doc=>({
 meshes:doc.getRoot().listMeshes().map(m=>({name:m.getName(),primitives:m.listPrimitives().map(p=>({mode:p.getMode(),material:p.getMaterial()?.getName(),indices:indexSignature(p),attributes:Object.fromEntries(p.listSemantics().map(s=>{const a=p.getAttribute(s);return[s,{type:a.getType(),normalized:a.getNormalized(),componentType:a.getComponentType(),sha256:sha(Buffer.from(a.getArray().buffer,a.getArray().byteOffset,a.getArray().byteLength))}];}))}))})),
 nodes:doc.getRoot().listNodes().map(n=>({name:n.getName(),matrix:n.getWorldMatrix(),mesh:n.getMesh()?.getName()})),
 textures:doc.getRoot().listTextures().map(t=>({mime:t.getMimeType(),sha256:sha(t.getImage())})),
});
fs.mkdirSync(output);const assets=[];
for(const asset of source.assets){
 const file=path.join(input,asset.file);assert.equal(sha(fs.readFileSync(file)),asset.sha256);
 const doc=await io.read(file),before=snapshot(doc);
 doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
 // The extension method selects NONE filters. No quantize() transform is run.
 const target=path.join(output,asset.file);await io.write(target,doc);assert.deepEqual(snapshot(await io.read(target)),before,'Decoded attribute/index/node/texture parity');
 assets.push({...asset,inputSha256:asset.sha256,inputBytes:asset.bytes,bytes:fs.statSync(target).size,sha256:sha(fs.readFileSync(target)),decodedExact:true});
}
const report={...source,assets,inputManifestSha256:sha(bytes),compressorSha256:sha(fs.readFileSync('scripts/compress_hangzhou_exact.mjs')),compression:'EXT_meshopt_compression; no quantization/attribute filters/topology transforms'};
fs.writeFileSync(path.join(output,'asset-manifest.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(assets,null,2));
