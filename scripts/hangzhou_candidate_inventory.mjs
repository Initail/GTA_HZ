/** Inventory current exported models and actual scene bounds, with source hashes. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {NodeIO,getBounds} from '@gltf-transform/core';
const [output,...files]=process.argv.slice(2);if(!files.length)throw new Error('Output and model-delivery files required');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),io=new NodeIO();const objects=[];
for(const file of files){
 const record=JSON.parse(fs.readFileSync(file));
 for(const [key,hash] of [['artifact','artifactSha256'],['sourceModule','sourceModuleSha256'],['spec','specSha256']])if(sha(record[key])!==record[hash])throw new Error('Changed candidate '+record.id+' '+key);
 const document=await io.read(record.artifact),scene=document.getRoot().listScenes()[0],bounds=getBounds(scene);
 if([...bounds.min,...bounds.max].some(v=>!Number.isFinite(v)))throw new Error('Invalid GLB bounds');
 const source=JSON.parse(fs.readFileSync(record.spec));
 objects.push({id:record.id,deliveryFile:file,deliverySha256:sha(file),artifact:record.artifact,artifactSha256:record.artifactSha256,
  sourceModule:record.sourceModule,spec:record.spec,stats:record.glbStats,boundsGltfEastUpSouth:bounds,
  boundsGameEastUpNorth:{min:[bounds.min[0],bounds.min[1],-bounds.max[2]],max:[bounds.max[0],bounds.max[1],-bounds.min[2]]},
  heightGame:bounds.max[1]-bounds.min[1],baseBuildingIds:record.baseBuildingIdsToExclude,
  sourceSnapshotSha256:record.sourceSnapshotSha256,scope:source.scope,
  acceptance:'modelled only; three in-game views/collision/day-night/performance unknown'});
}
if(new Set(objects.map(o=>o.id)).size!==objects.length)throw new Error('One selected candidate per object required');
const inventory={schemaVersion:1,cityId:'hangzhou',kind:'actual-current-model-inventory',objects,
 triangles:objects.reduce((s,o)=>s+o.stats.triangles,0),bytes:objects.reduce((s,o)=>s+o.stats.bytes,0),
 pending:['full object scope and unresolved identities','terrain and road levels','collision and exact arrivals','all in-game visual and performance acceptance']};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(inventory,null,2)+'\n');
console.log(JSON.stringify({objects:objects.length,triangles:inventory.triangles,bytes:inventory.bytes},null,2));
