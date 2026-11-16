/** Rigid placement of an already authored object without retessellation or
 * normal regeneration. The existing Blender → glTF → Babylon axes remain.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO,getBounds} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
const [commandsFile,outputRoot]=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!commandsFile||!outputRoot||fs.existsSync(outputRoot)||!path.resolve(outputRoot).startsWith(path.resolve('artifacts')+path.sep))throw Error('Original placement commands and fresh artifact root required');
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS),commands=JSON.parse(fs.readFileSync(commandsFile)),next=[];
fs.mkdirSync(outputRoot,{recursive:true});
for(const command of commands){
 const args=[...command.args],placementFile=args[args.indexOf('--placement')+1],placement=JSON.parse(fs.readFileSync(placementFile));
 for(const source of placement.sourceInputs)assert.equal(sha(source.path),source.sha256,'Changed placement source '+source.path);
 const oldDeliveryFile=placement.sourceInputs.find(p=>p.path.endsWith('/model-delivery.json')).path,old=JSON.parse(fs.readFileSync(oldDeliveryFile));
 assert.equal(sha(old.artifact),old.artifactSha256);assert.equal(old.id,command.id);
 const doc=await io.read(old.artifact),scenes=doc.getRoot().listScenes();assert.equal(scenes.length,1);
 const delta=placement.landmark.y-(old.baseYGame??0),before=getBounds(scenes[0]);assert.ok(Number.isFinite(delta));
 for(const root of scenes[0].listChildren()){const t=root.getTranslation();root.setTranslation([t[0],t[1]+delta,t[2]]);}
 const directory=path.join(outputRoot,command.id);fs.mkdirSync(directory);const target=path.join(directory,command.id+'.glb');await io.write(target,doc);
 const verified=await io.read(target),bounds=getBounds(verified.getRoot().listScenes()[0]);
 const triangles=verified.getRoot().listMeshes().reduce((sum,m)=>sum+m.listPrimitives().reduce((n,p)=>n+(p.getIndices()?.getCount()??p.getAttribute('POSITION').getCount())/3,0),0);
 assert.equal(triangles,old.glbStats.triangles);assert.ok(Math.abs(bounds.min[1]-before.min[1]-delta)<1e-10&&Math.abs(bounds.max[1]-before.max[1]-delta)<1e-10);
 const bytes=fs.statSync(target).size,record={...old,status:'rigid-floor-placement-candidate-not-verified',artifact:target,artifactSha256:sha(target),baseYGame:placement.landmark.y,
  export:{...old.export,bytes,triangles},glbStats:{...old.glbStats,bytes},placementTransform:{kind:'root-node Y translation in existing glTF Y-up',deltaYGame:delta,sourceBounds:before,placedBounds:bounds},
  sourceInputs:[...(old.sourceInputs??[]),{path:oldDeliveryFile,sha256:sha(oldDeliveryFile),role:'original-model-delivery'},{path:old.artifact,sha256:sha(old.artifact),role:'authored-model'},{path:placementFile,sha256:sha(placementFile),role:'placement',basis:placement.heightBasis},{path:'scripts/place_hangzhou_landmark_candidate.mjs',sha256:sha('scripts/place_hangzhou_landmark_candidate.mjs'),role:'reproducible-placement-script'}],
  pending:[...new Set([...(old.pending??[]),...placement.pending])]};
 fs.writeFileSync(path.join(directory,'model-delivery.json'),JSON.stringify(record,null,2)+'\n');args[args.indexOf('--output')+1]=directory;next.push({...command,args,producer:'scripts/place_hangzhou_landmark_candidate.mjs',originalModel:old.artifact});
 console.log(JSON.stringify({id:command.id,deltaYGame:delta,bytes,triangles,sha256:record.artifactSha256}));
}
fs.writeFileSync(path.join(outputRoot,'commands-for-audit.json'),JSON.stringify(next,null,2)+'\n');
