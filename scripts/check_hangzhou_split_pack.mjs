/** Exercise the actual runtime parsers against the real staged near/far GLBs.
 * No renderer/decoder is started. The agent's independent decoded checks remain
 * necessary, and an incomplete parent pilot must fail whole-city admission. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {loadBasePackIndex,loadBasePackMetadata} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-stream-pack-manifest.ts';
import {inspectStreamGlb} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-stream-assets.ts';
import {planBaseStreamPacks} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-stream-pack-plan.ts';
const root=process.cwd(),base=path.resolve(process.argv[2]??''),output=path.resolve(process.argv[3]??'');assert(process.argv[2]&&process.argv[3]&&base.startsWith(root+path.sep)&&output.startsWith(root+path.sep)&&!fs.existsSync(output));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),read=file=>JSON.parse(fs.readFileSync(file)),stage=read(path.join(base,'staging.json')),index=read(path.join(base,'index.json')),controller=new AbortController();
const fetched=[];globalThis.location=new URL('http://split.invalid/');globalThis.fetch=async url=>{const u=new URL(String(url));assert.equal(u.origin,location.origin);const file=path.resolve(base,'.'+decodeURIComponent(u.pathname));assert(file.startsWith(base+path.sep));fetched.push(u.pathname);assert(fs.statSync(file).size<=256*1024);return new Response(fs.readFileSync(file));};
const release=read('artifacts/cities/hangzhou/stream-release-v1/descriptor.json'),originals=[];
for(const role of ['terrain','roads','buildings']){const descriptor=release.models[role],bytes=fs.readFileSync(descriptor.manifestPath);assert.equal(hash(bytes),descriptor.manifestSha256);originals.push(...JSON.parse(bytes).tiles.map(t=>({...t,role,baseUrl:location.href})));}
const source={manifestUrl:location.href+'index.json',manifestBytes:stage.index.bytes,manifestSha256:stage.index.sha256},parent=originals.find(t=>t.id===stage.parent.id);
const catalog=await loadBasePackIndex(source,[parent],index.textures,index.sourceManifests,controller.signal),assets=[];
for(const pack of catalog.packs){
 const metadata=await loadBasePackMetadata(pack,catalog.textures,controller.signal),bytes=fs.readFileSync(path.join(base,pack.file));assert.equal(hash(bytes),pack.sha256);
 const {doc,bin}=inspectStreamGlb(bytes,pack,metadata.textures),rawDescriptor=read(path.join(base,pack.metadata.file)),original=fs.readFileSync(path.join(root,stage.sourceCandidate,'packs/all-'+pack.members[0].quality+'/pack.glb')),originalBin=28+original.readUInt32LE(12),originalDoc=JSON.parse(original.subarray(20,originalBin-8));
 assert(bytes.subarray(bin).equals(original.subarray(originalBin)));doc.images=originalDoc.images;assert.deepEqual(doc,originalDoc);
 assert.equal(rawDescriptor.sourceGlbSha256,hash(original));assets.push({id:pack.id,sha256:pack.sha256,bytes:pack.bytes,triangles:pack.triangles,nodes:metadata.nodes.length,materials:metadata.materialOrigins.length,binaryAndOtherJsonExact:true});
}
const spawn=read('artifacts/cities/hangzhou/stream-world-v1/original-range-admission.json').spawn,view={...spawn,overview:false};
const distant=planBaseStreamPacks(catalog.sources,catalog.packs,view),held=planBaseStreamPacks(catalog.sources,catalog.packs,view,new Set(catalog.sources.map(t=>t.id)));
assert.equal(distant.near.size,0);assert.equal(distant.cost.triangles,15679);assert.equal(distant.cost.tiles,1);assert.equal(held.near.size,9);assert.equal(held.cost.triangles,22337);assert.equal(held.cost.tiles,1);
await assert.rejects(loadBasePackIndex(source,originals,index.textures,index.sourceManifests,controller.signal),/覆盖不完整/);
const report={schemaVersion:1,scope:'actual two-pack parsing, source identity, binary relocation and declared CPU planning; not GLB decode or GPU',children:catalog.sources.length,assets,views:[{origin:'simulated',description:'fixed spawn without previous near',near:distant.near.size,cost:distant.cost},{origin:'simulated',description:'same spawn with prior near hysteresis',near:held.near.size,cost:held.cost}],wholeCityIncompleteRejected:true,fetched,browserAccepted:false};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));
