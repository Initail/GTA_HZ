/** Verify nearby source placements against every actual prototype LOD.
 * A circumscribed horizontal radius is conservative for every yaw and height.
 * No planting edits, geometry synthesis, or claimed full-scene acceptance.
 */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
const [input,output]=process.argv.slice(2);assert(input&&output&&!fs.existsSync(output));
assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+'/'));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),sources=[];
function read(file){const b=fs.readFileSync(file);sources.push({file,bytes:b.length,sha256:hash(b)});return JSON.parse(b);}
const proximity=read(input);for(const r of proximity.sources)assert.equal(hash(fs.readFileSync(r.file)),r.sha256,'Placement input changed');
const base='artifacts/cities/hangzhou/demo-v10/dist/cities/hangzhou',overlay='artifacts/cities/hangzhou/city-leisure-v15/public/cities/hangzhou';
const canopy=read(overlay+'/landscape/canopy/manifest.json'),landscape=read(base+'/landscape/manifest.json'),open=read(base+'/open-vegetation/manifest.json'),config=read('config/cities/hangzhou.json');
assert.deepEqual(open.eligibleIndices,{islandTree:[],palm:[]},'Open model substitutions require a separate geometry audit');
await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],cache=new Map();
async function bounds(model){
 const overlayFile=overlay+'/landscape/'+model.file,file=fs.existsSync(overlayFile)?overlayFile:base+'/landscape/'+model.file;
 if(cache.has(file))return cache.get(file);
 const bytes=fs.readFileSync(file),sha256=hash(bytes);if(model.sha256)assert.equal(sha256,model.sha256);assert.equal(bytes.length,model.bytes);
 const doc=await io.readBinary(bytes);assert.equal(doc.getRoot().listAnimations().length,0);let radius=0,vertices=0;const nodes=[];
 for(const n of doc.getRoot().listNodes()){
  if(!n.getMesh())continue;assert.deepEqual(n.getWorldMatrix(),identity,'The runtime resets transforms after mirroring; prototype vertices must be baked');assert(!n.getSkin());
  nodes.push(n.getName());for(const p of n.getMesh().listPrimitives()){
   assert.equal(p.listTargets().length,0);const a=p.getAttribute('POSITION').getArray();assert.equal(a.length%3,0);
   for(let i=0;i<a.length;i+=3){assert(Number.isFinite(a[i]+a[i+1]+a[i+2]));radius=Math.max(radius,Math.hypot(a[i],a[i+2]));vertices++;}
  }
 }
 assert(vertices>0);const r={file,bytes:bytes.length,sha256,vertices,nodes,radiusGame:radius};cache.set(file,r);return r;
}
const rows=[];
for(const group of ['canopyCandidates','baseTreeCandidates','detailCandidates'])for(const row of proximity[group]){
 const [, ,species,scale]=row.placement;assert(scale>0);let models;
 if(group==='canopyCandidates')models=canopy.models.filter(m=>m.species===canopy.species[species].id);
 else{const name=group==='baseTreeCandidates'?config.vegetation.baseTreeNames[species]:['lawn-tuft','flower-shrub','fountain-grass'][species];models=landscape.models.filter(m=>m.id===name||m.id===name+'-lod');}
 assert.equal(models.length,group==='canopyCandidates'?3:group==='baseTreeCandidates'?2:1);
 const lods=[];for(const m of models){const b=await bounds(m);lods.push({id:m.id,file:b.file,radiusGame:b.radiusGame*scale});}
 const radiusGame=Math.max(...lods.map(l=>l.radiusGame)),minimumSeparationGame=row.distanceToPavingGame-radiusGame;
 rows.push({...row,lods,conservativeRadiusGame:radiusGame,minimumSeparationGame,clearAtEveryHeightAndYaw:minimumSeparationGame>0});
}
const pass=rows.every(r=>r.clearAtEveryHeightAndYaw);
fs.writeFileSync(output,JSON.stringify({schemaVersion:1,kind:'read-only all-LOD vertex radius versus actual paving polygon',pass,sources,prototypes:[...cache.values()],placements:rows,
 method:'Actual GLB positions with identity node transforms; the runtime Z mirror and yaw preserve horizontal radius. Scale is each existing placement scale, applied once. A positive separation certifies geometry disjointness at every height; a nonpositive separation is inconclusive, not proof of collision.',
 sourcePlantingsUnchanged:proximity.sources.every(r=>hash(fs.readFileSync(r.file))===r.sha256),
 limits:['Only the listed fixed placements within 15g; no claim about unlisted distant crowns','Supplemental roadside trees and dynamic actors are not included','A follow camera can cross a crown even when the walkway is clear','No full-world or visual acceptance']},null,2)+'\n');
console.log(JSON.stringify({pass,placements:rows.length,prototypes:cache.size,minimumSeparationGame:Math.min(...rows.map(r=>r.minimumSeparationGame))}));assert(pass,'Preserve inconclusive overlaps for precise follow-up');
