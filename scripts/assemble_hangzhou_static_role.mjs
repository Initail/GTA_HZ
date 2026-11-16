/** Assemble a required static runtime role from actual bound assets.
 * Exact contents, no simplification/quantization/axis conversion/public writes.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {Document,NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {mergeDocuments,unpartition} from '@gltf-transform/functions';import {MeshoptDecoder} from 'meshoptimizer';
import {createGltfSnapshot} from './hangzhou_gltf_snapshot.mjs';
const [source,role,output]=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert(['landmarks','coastal-bridges'].includes(role));assert(output&&!fs.existsSync(output));assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const input=path.join(source,'detail-collision-candidate.json'),details=JSON.parse(fs.readFileSync(input)),selected=details.requiredStructuralAssets.filter(a=>a.role===role);
assert(selected.length,'An empty placeholder cannot satisfy a runtime asset role');assert.equal(new Set(selected.map(a=>a.sourceFile)).size,selected.length);
await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder}),snapshot=createGltfSnapshot(io);
const merged=new Document(),scene=merged.createScene('Hangzhou '+role);merged.getRoot().setDefaultScene(scene);
const expected={meshes:[],nodes:[]},names=new Set(),nodeNames=new Set(),inputs={[input]:sha(input)};let triangles=0;
for(const asset of selected){
 assert.equal(sha(asset.sourceFile),asset.sha256);inputs[asset.sourceFile]=asset.sha256;
 const doc=await io.read(asset.sourceFile);assert.equal(doc.getRoot().listScenes().length,1);assert.equal(doc.getRoot().listAnimations().length,0);
 const sourceSnapshot=await snapshot(doc);
 for(const mesh of sourceSnapshot.meshes){assert(!names.has(mesh.name),'Mesh name collision');names.add(mesh.name);for(const p of mesh.primitives){assert.equal(p.mode,4);assert(p.indices);triangles+=p.indices.length/3;}}
 for(const node of sourceSnapshot.nodes){assert(!nodeNames.has(node.name),'Node name collision');nodeNames.add(node.name);}
 expected.meshes.push(...sourceSnapshot.meshes);expected.nodes.push(...sourceSnapshot.nodes);
 const mapping=mergeDocuments(merged,doc),imported=mapping.get(doc.getRoot().listScenes()[0]);for(const child of imported.listChildren())scene.addChild(child);imported.dispose();
}
await merged.transform(unpartition());assert.deepEqual(await snapshot(merged),expected,'In-memory source contents differ');
fs.mkdirSync(output);const file=path.join(output,role+'.glb');await io.write(file,merged);assert.deepEqual(await snapshot(await io.read(file)),expected,'Actual GLB roundtrip differs');
const asset={file:role+'.glb',sha256:sha(file),bytes:fs.statSync(file).size,triangles,meshes:expected.meshes.length};
const report={schemaVersion:1,cityId:'hangzhou',role,kind:'actual nonempty static runtime role assembled from declared source assets',inputs,builders:Object.fromEntries(['scripts/assemble_hangzhou_static_role.mjs','scripts/hangzhou_gltf_snapshot.mjs'].map(p=>[p,sha(p)])),selected,assets:[asset],checks:{attributesExact:true,indicesExact:true,materialsTexturesExact:true,worldMatricesExact:true,glbRoundtripExact:true},pending:['role installation and actual whole-scene projectile/flight collision','referenced terrain/source decks/physics must match','real browser visuals and performance'],active:false};
fs.writeFileSync(path.join(output,'asset-manifest.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({asset,checks:report.checks,selected:selected.length},null,2));
