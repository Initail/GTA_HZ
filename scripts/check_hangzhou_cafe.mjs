/** Geographical placement and original local colliders; no browser/camera pass. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import {CityCollision} from '../src/driving.ts';
import {cafeLayout} from '../src/city-cafe-layout.ts';
const [cityFile,cafeFolder,output]=process.argv.slice(2);
if(!output)throw new Error('Usage: check_hangzhou_cafe.mjs CITY CAFE REPORT');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const city=JSON.parse(fs.readFileSync(cityFile)),manifestFile=cafeFolder+'/bamboo-cafe/manifest.json',manifest=JSON.parse(fs.readFileSync(manifestFile));
if(city.meta.cityId!=='hangzhou'||manifest.cityId!=='hangzhou')throw new Error('Wrong cafe/city');
const layout=cafeLayout(manifest.spec,manifest.colliders,0),collision=new CityCollision(city),samples=[];
for(let x=-14;x<=14;x++)for(let z=-24;z<=24;z++){
 const p=layout.world(x,z);if(collision.blocked(p.x,p.z))samples.push([x,z,p.x,p.z]);
}
const path=[];for(let z=-22;z<=-6.15;z+=.25){const p=layout.world(0,z);if(layout.blocked(p.x,p.z)||collision.blocked(p.x,p.z))path.push({local:[0,z],world:[p.x,p.z]});}
const staff=manifest.spec.staff.map(person=>{const p=layout.world(...person.position);return {id:person.id,inside:layout.inside(p.x,p.z)};});
const report={kind:'offline-placement-and-existing-local-collision-functions',citySha256:sha(cityFile),manifestSha256:sha(manifestFile),
 arrivalBlocked:collision.blocked(...manifest.spec.site.arrival),baseBlockedEnvelopeSamples:samples,localDoorPathBlocked:path,staff,
 originalModelHashes:manifest.models.map(m=>({id:m.id,sha256:m.sha256,actualSha256:sha(cafeFolder+'/bamboo-cafe/'+m.file)})),
 localScale:1,pass:!samples.length&&!path.length&&!collision.blocked(...manifest.spec.site.arrival)&&staff.every(s=>s.inside),
 pending:['DEM and finished landmark collision','door/floor/walls/camera in browser','staff animation and interaction','vegetation avoidance','real walking/parking/day/night/performance']};
report.pass&&=report.originalModelHashes.every(m=>m.sha256===m.actualSha256);
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,blockedSamples:samples.length,pathBlocked:path.length,staff},null,2));
if(!report.pass)process.exitCode=1;
