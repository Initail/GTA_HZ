/** Serial replacement of two named objects in a fresh demo candidate only. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {mergeDocuments,unpartition,prune} from '@gltf-transform/functions';import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';
import {createGltfSnapshot} from './hangzhou_gltf_snapshot.mjs';
const [stage,model,support]=process.argv.slice(2),root=path.join(stage,'public/cities/hangzhou');
assert(stage&&model&&support&&path.resolve(stage).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
assert(!fs.existsSync(path.join(stage,'dist')),'Never change a built/served demo');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const marker=path.join(stage,'bai-integration.json');assert(!fs.existsSync(marker));
const input=path.join(root,'landmark-detail.glb'),originalSha=sha(input),manifest=read(path.join(model,'asset-manifest.json'));
await Promise.all([MeshoptDecoder.ready,MeshoptEncoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const snapshot=createGltfSnapshot(io),doc=await io.read(input),scene=doc.getRoot().getDefaultScene();
const selected=name=>/^detail_(?:west-lake-causeways|broken-bridge)_/.test(name);
const before=await snapshot(doc),other=s=>({meshes:s.meshes.filter(m=>!selected(m.name)),nodes:s.nodes.filter(n=>!selected(n.mesh))});
for(const n of doc.getRoot().listNodes())if(n.getMesh()&&selected(n.getMesh().getName()))n.dispose();
for(const m of doc.getRoot().listMeshes())if(selected(m.getName()))m.dispose();
for(const ext of doc.getRoot().listExtensionsUsed())if(ext.extensionName==='EXT_meshopt_compression')ext.dispose();
for(const asset of manifest.assets){const p=path.join(model,asset.file);assert.equal(sha(p),asset.sha256);const source=await io.read(p),map=mergeDocuments(doc,source),s=map.get(source.getRoot().getDefaultScene());for(const n of s.listChildren())scene.addChild(n);s.dispose();}
await doc.transform(prune({keepAttributes:true,keepLeaves:true}),unpartition());
assert.deepEqual(other(await snapshot(doc)),other(before),'Unrelated objects must retain exact attributes/materials/transforms');
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
await io.write(input,doc);
assert.deepEqual(other(await snapshot(await io.read(input))),other(before),'Written unrelated objects must match');
const sitesPath=path.join(root,'geography/site-surfaces.json'),sites=read(sitesPath),extra=read(path.join(support,'site-surfaces.json'));
assert(!sites.walkFloors.some(g=>g.id.startsWith('bai-route:')));sites.walkFloors.push(...extra.walkFloors);sites.terrainCuts.push(...extra.terrainCuts);
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v)+'\n');write(sitesPath,sites);
const geoPath=path.join(root,'geography/manifest.json'),geo=read(geoPath);geo.siteSurfacesSha256=sha(sitesPath);write(geoPath,geo);
const detailPath=path.join(root,'landmark-detail.json'),detail=read(detailPath);detail.terrain.manifestSha256=sha(geoPath);
detail.collisionFootprints.push(...read(path.join(support,'rail-collisions.json')).collisionFootprints);
for(const lm of detail.landmarks)if(lm.id==='broken-bridge'){lm.baseYGame=null;lm.artifactSha256=manifest.assets.find(a=>a.file==='broken-bridge.glb').sha256;lm.collisionMethod='actual exported deck triangles and finite rail solids';lm.photoTargetHeight=7;}
write(detailPath,detail);
const report={kind:'local Bai objects and actual walking support; no browser acceptance',stage,originalDetailSha256:originalSha,
 inputs:Object.fromEntries([path.join(model,'asset-manifest.json'),path.join(support,'site-surfaces.json'),path.join(support,'rail-collisions.json')].map(p=>[p,sha(p)])),
 outputs:Object.fromEntries([input,sitesPath,geoPath,detailPath].map(p=>[p,sha(p)])),unrelatedModelsPreserved:true,
 pending:['base ribbon and shoreline visual ownership','actual actor transitions and rail/water controls','browser and performance']};write(marker,report);console.log(JSON.stringify(report,null,2));
