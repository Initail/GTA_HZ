import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const root=process.cwd(),folder='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-surface-proposal',read=n=>JSON.parse(fs.readFileSync(path.join(root,folder,n),'utf8')),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const {CitySiteSurfaces}=await import(pathToFileURL(path.join(root,'src/city-site-surfaces.ts')).href);
const upperData=read('site-surfaces-upper-only.json'),allData=read('site-surfaces-all-public-geometry.json'),upper=new CitySiteSurfaces(upperData),all=new CitySiteSurfaces(allData),seams=read('entry-seams.json');let samples=0,maxSoleDetailOffset=0;
for(const floor of upperData.walkFloors)for(const t of floor.triangles){
 const x=t.reduce((s,v)=>s+v[0],0)/3,z=t.reduce((s,v)=>s+v[1],0)/3,h=t.reduce((s,v)=>s+v[2],0)/3;
 const result=upper.walkAt(x,z,h-.4,h);assert(result.id?.startsWith('city-balcony:upper'));assert(result.height>=h-1e-8&&result.height<=h+.051);maxSoleDetailOffset=Math.max(maxSoleDetailOffset,result.height-h);samples++;
 const distant=upper.walkAt(x,z,h-.4,h+1);assert.equal(distant.id,null);
}
let gatedLower=0,allCandidateLower=0;
for(const t of allData.walkFloors.find(f=>f.id==='city-balcony:lower').triangles){
 const x=t.reduce((s,v)=>s+v[0],0)/3,z=t.reduce((s,v)=>s+v[1],0)/3,h=t.reduce((s,v)=>s+v[2],0)/3;
 assert.equal(upper.walkAt(x,z,h-.4,h-.4).id,null);gatedLower++;
 assert.equal(all.walkAt(x,z,h-.4,h-.4).id,'city-balcony:lower');allCandidateLower++;
}
let seamSamples=0;
for(const seam of seams.seams)for(const p of seam.crossingSamples){
 const [x,h,z]=p.insidePointGameXYZ,[ox,oh,oz]=p.outsidePointGameXYZ;
 const entered=upper.walkAt(x,z,h-.4,oh);assert(entered.id?.startsWith('city-balcony:upper'));assert(Math.abs(entered.height-oh)<.48);
 const exited=upper.walkAt(ox,oz,oh,entered.height);assert.equal(exited.id,null);assert.equal(exited.height,oh);seamSamples++;
}
const report={kind:'actual CitySiteSurfaces constructor/query with proposed data only',sourceSha256:sha(path.join(root,'src/city-site-surfaces.ts')),upperCentroidSamples:samples,maxSameLevelDetailSoleOffsetGame:maxSoleDetailOffset,lowerTrianglesGatedInRecommendedData:gatedLower,demonstratedAllFloorCandidateWouldSelectLowerFromGroundCap:allCandidateLower,actualSeamQueries:seamSamples,terrainCutsIncluded:false,bodyCollisionOrBrowserTested:false,pass:true};fs.writeFileSync(path.join(root,folder,'site-interface-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
