/** Install a checked overlay only into the private v15 candidate. Keeps a
 * byte-exact rollback and publishes the hash manifest last. No server action.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {CitySiteSurfaces} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-site-surfaces.ts';
import {planSitePaths} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-site-path-plan.ts';
const [staging]=process.argv.slice(2),candidate=path.resolve('artifacts/cities/hangzhou/city-leisure-v15'),target=path.join(candidate,'public/cities/hangzhou/geography');
assert(staging&&path.resolve(staging).startsWith(candidate+'/'));const reportFile=path.join(staging,'candidate-installation.json');assert(!fs.existsSync(reportFile));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),record=file=>{const b=fs.readFileSync(file);return {file:path.relative(process.cwd(),file),bytes:b.length,sha256:hash(b)};};
const stage=JSON.parse(fs.readFileSync(path.join(staging,'staging-report.json')));assert(Object.values(stage.preserved).every(Boolean));
const checked=r=>{const b=fs.readFileSync(r.file);assert.equal(b.length,r.bytes);assert.equal(hash(b),r.sha256);return b;};
checked(stage.baseManifest);checked(stage.baseSurfaces);assert.equal(path.resolve(stage.baseManifest.file),path.join(target,'manifest.json'));assert.equal(path.resolve(stage.baseSurfaces.file),path.join(target,'site-surfaces.json'));
const pending=new Map(stage.outputs.map(r=>[path.basename(r.file),checked(r)]));assert.deepEqual([...pending.keys()].sort(),['manifest.json','site-surfaces.json']);
const manifest=JSON.parse(pending.get('manifest.json')),data=JSON.parse(pending.get('site-surfaces.json'));assert.equal(hash(pending.get('site-surfaces.json')),manifest.siteSurfacesSha256);
new CitySiteSurfaces(data);const plans=planSitePaths(data.walkFloors,data.pathDisplays);assert.equal(plans.reduce((n,p)=>n+p.indices.length/3,0),stage.displayedTriangles);
const detailFile=path.join(target,'../landmark-detail.json'),detail=JSON.parse(fs.readFileSync(detailFile));assert.equal(detail.terrain.manifestSha256,stage.baseManifest.sha256,'Landmark terrain binding changed before installation');
const originalDetail=structuredClone(detail);detail.terrain.manifestSha256=hash(pending.get('manifest.json'));
const detailBytes=JSON.stringify(detail)+'\n',comparison=JSON.parse(detailBytes);comparison.terrain.manifestSha256=originalDetail.terrain.manifestSha256;assert.deepEqual(comparison,originalDetail);
const backup=path.join(staging,'rollback');assert(!fs.existsSync(backup));fs.mkdirSync(backup);
for(const name of pending.keys())fs.copyFileSync(path.join(target,name),path.join(backup,name),fs.constants.COPYFILE_EXCL);
fs.copyFileSync(detailFile,path.join(backup,'landmark-detail.json'),fs.constants.COPYFILE_EXCL);
const detailTemp=detailFile+'.path-overlay.tmp';fs.writeFileSync(detailTemp,detailBytes,{flag:'wx'});fs.renameSync(detailTemp,detailFile);
for(const name of ['site-surfaces.json','manifest.json']){const temp=path.join(target,name+'.path-overlay.tmp');fs.writeFileSync(temp,pending.get(name),{flag:'wx'});fs.renameSync(temp,path.join(target,name));}
const result={schemaVersion:1,kind:'private v15 path overlay installation; not demo publication',staging:record(path.join(staging,'staging-report.json')),rollback:[...pending.keys(),'landmark-detail.json'].map(n=>record(path.join(backup,n))),installed:[...pending.keys()].map(n=>record(path.join(target,n))),landmarkTerrainBinding:{file:record(detailFile),allOtherDetailDataExact:true},
 counts:{floors:data.walkFloors.length,slabs:data.solidSlabs?.length??0,sourceAccessCorridors:data.accessCorridors?.length??0,groundPatches:data.terrainPatches?.length??0,pathTriangles:plans.reduce((n,p)=>n+p.indices.length/3,0)},
 untouched:['root public city assets','v14 frozen candidate','demo-v10 and old playable revisions','all original gameplay rules and saves','all base/landmark GLB geometry'],
 pending:['full-world startup and gameplay validation','temple entrance/annex atomic integration','full-world night lighting'],newPlayableDemoReleased:false};
for(const r of result.installed)assert.equal(r.sha256,hash(pending.get(path.basename(r.file))));
fs.writeFileSync(reportFile,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
