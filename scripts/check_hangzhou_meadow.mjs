/** Decode every actual mask, then exercise the existing grass loader/LOD in
 * Babylon NullEngine with the actual Hangzhou physical height sampler.
 * No browser, shader compilation, GPU time or visual acceptance is implied.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NullEngine,Scene,FreeCamera,Vector3} from '@babylonjs/core';
import {CityMeadow,validateMeadowManifest,decodeMeadowTile,createMeadowPatch,MEADOW_LIMITS} from '../src/city-meadow.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import {CitySiteSurfaces} from '../src/city-site-surfaces.ts';
import {mountainHeightAt} from '../src/city-mountains.ts';
const [candidate,source,output]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert(output&&!fs.existsSync(output));
const prepared=read(path.join(candidate,'report.json')),manifest=validateMeadowManifest(read(path.join(candidate,'meadow.json')));
assert.equal(sha(path.join(candidate,'meadow.json')),prepared.manifestSha256);
for(const [p,h] of Object.entries(prepared.inputs))assert.equal(sha(p),h,'Source drift '+p);
let safeCells=0,eligible=0,clumpsChecked=0;const locations=[];
for(const tile of manifest.tiles){
 const file=path.join(candidate,tile.url);assert.equal(sha(file),tile.sha256);
 const bytes=fs.readFileSync(file),patches=decodeMeadowTile(manifest,tile,bytes);safeCells+=tile.count;eligible+=patches.length;
 if(patches.length){
  const patch=patches[Math.floor(patches.length/2)];locations.push(patch);
  for(const c of createMeadowPatch(patch)){
   assert(Math.hypot(c.x-patch.x,c.z-patch.z)+MEADOW_LIMITS.leafMargin<=patch.safeRadius+1e-9);clumpsChecked++;
  }
 }
}
assert.equal(safeCells,prepared.budgets.safeCells);assert.equal(eligible,prepared.budgets.runtimeEligibleCells);assert(locations.length>=8);
const g=read(path.join(source,'geography/manifest.json'));
assert.equal(sha(path.join(source,'geography/manifest.json')),manifest.sourceSHA[path.join(source,'geography/manifest.json')]);
const buf=fs.readFileSync(path.join(source,'geography',g.terrainFile)),heights=new Float32Array(buf.buffer.slice(buf.byteOffset,buf.byteOffset+buf.byteLength));
const sites=new CitySiteSurfaces(read(path.join(source,'geography',g.siteSurfacesFile)));
const levels=new CityRoadLevels(read(path.join(source,'geography',g.roadLevelsFile)).roads,(x,z)=>mountainHeightAt(heights,g.grid,x,z),g.roadTerrainTransitionGame,(x,z,y)=>sites.groundAt(x,z,y),(id,x,z)=>sites.roadAt(id,x,z));
const probes=prepared.samplePoints.map(([x,z,y])=>Math.abs(levels.groundAt(x,z)-y));assert(Math.max(...probes)<1e-7);
const engine=new NullEngine(),scene=new Scene(engine),camera=new FreeCamera('actual-meadow-cpu',Vector3.Zero(),scene);scene.activeCamera=camera;
const fetches=[],base='https://offline.invalid/cities/hangzhou/grassland-v2/';
// In-memory/local adapter only. No requests are made to the marker URL.
const fetcher=async value=>{const url=String(value);assert(url.startsWith(base));const relative=url.slice(base.length);assert(!relative.includes('..'));
 fetches.push(relative);return new Response(fs.readFileSync(path.join(candidate,relative)));};
const meadow=new CityMeadow(scene,(x,z)=>levels.groundAt(x,z),{manifestURL:base+'meadow.json',fetcher});
const visits=[];
try{
 await meadow.init();assert.equal(meadow.ready,true);
 for(let i=0;i<8;i++){
  const p=locations[Math.floor(i*(locations.length-1)/7)],floor=levels.groundAt(p.x,p.z);
  camera.position.set(p.x,floor+2,p.z);camera.getViewMatrix(true);meadow.update(p.x,p.z);
  for(let tick=0;tick<8;tick++){await new Promise(r=>setTimeout(r,20));meadow.update(p.x,p.z);}
  const stats=meadow.stats;assert.equal(stats.status,'ready');assert.equal(stats.pendingTiles,0);assert(stats.instances>0);
  assert(stats.instances<=MEADOW_LIMITS.clumps);assert(stats.drawCalls<=MEADOW_LIMITS.meshes);
  assert(stats.triangles<=MEADOW_LIMITS.clumps*MEADOW_LIMITS.blades*5);
  assert(meadow.meshes.every(m=>!m.checkCollisions&&!m.isPickable));
  visits.push({x:p.x,z:p.z,floor,stats});
 }
 const last=visits.at(-1);meadow.update(last.x,last.z,true);assert.equal(meadow.stats.instances,0);
 assert(meadow.meshes.every(m=>!m.isEnabled()));
 meadow.dispose();assert.equal(meadow.stats.status,'disposed');assert.equal(meadow.meshes.length,0);
}finally{meadow.dispose();scene.dispose();engine.dispose();}
const report={kind:'actual masks and Babylon NullEngine grass CPU integration',inputs:{[path.join(candidate,'report.json')]:sha(path.join(candidate,'report.json')),[path.join(candidate,'meadow.json')]:sha(path.join(candidate,'meadow.json')),'src/city-meadow.ts':sha('src/city-meadow.ts'),'scripts/check_hangzhou_meadow.mjs':sha('scripts/check_hangzhou_meadow.mjs')},tiles:manifest.tiles.length,safeCells,eligible,clumpsChecked,physicalParity:{samples:probes.length,maximumErrorGame:Math.max(...probes)},visits,localFetchCount:fetches.length,checks:{allTileHashesAndCounts:true,allMasksDecoded:true,grassClumpsInsideReservedDiscs:true,actualHeightSampler:true,originalLimits:true,aerialDisables:true,disposal:true},pass:true,pending:['independent whole-disc source geometry audit','GPU shader and day/night rendering','browser performance and full-city integration']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,inputs:undefined,visits:visits.length},null,2));
