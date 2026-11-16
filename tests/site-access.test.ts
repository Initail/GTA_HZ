import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {CitySiteSurfaces,type SiteSurfaceData} from '../src/city-site-surfaces.ts';
const make=():SiteSurfaceData=>({cityId:'hangzhou',units:'game east/north/up; scale applied once',terrainCuts:[],walkFloors:[{id:'bridge',triangles:[[[-2,-10,8],[2,-10,8],[2,10,8]],[[-2,-10,8],[2,10,8],[-2,10,8]]]}],accessCorridors:[{sourceId:'way/test',points:[[0,-10],[0,10]],widthGame:4,kind:'pedestrian',sourceAccessTags:{highway:'pedestrian',motorcar:'no',bicycle:'no',cycleway:'yes'}}]});
test('source access attaches to the same bridge deck, not the road below or the ground beside it',()=>{
 const sites=new CitySiteSurfaces(make());assert.equal(sites.restrictedSourceAt(0,0,8,'motorcar'),'way/test');
 assert.equal(sites.restrictedSourceAt(0,0,0,'motorcar'),null);assert.equal(sites.restrictedSourceAt(3,0,8,'motorcar'),null);
 assert.equal(sites.restrictedSourceAt(0,0,8,'foot'),null);assert.equal(sites.restrictedSourceAt(0,0,8,'bicycle'),'way/test');
});
test('legacy site data and optional access do not change ground or floor support',()=>{
 const data=make();delete data.accessCorridors;const old=new CitySiteSurfaces(data),next=new CitySiteSurfaces(make());
 assert.deepEqual(old.walkAt(0,0,0,8),next.walkAt(0,0,0,8));assert.equal(old.restrictedSourceAt(0,0,8,'motorcar'),null);
});
test('malformed or duplicated source access cannot be silently accepted',()=>{
 const duplicate=make();duplicate.accessCorridors!.push(duplicate.accessCorridors![0]);assert.throws(()=>new CitySiteSurfaces(duplicate),/Invalid site access/);
 const bad=make();bad.accessCorridors![0].widthGame=NaN;assert.throws(()=>new CitySiteSurfaces(bad),/Invalid site access/);
});
test('candidate access assets bind the geography and landmark hashes while preserving baseline geometry and binding leisure additions',()=>{
 const read=(path:string)=>readFileSync(new URL('../'+path,import.meta.url));
 const hash=(b:Buffer)=>createHash('sha256').update(b).digest('hex'),contentHash=(value:unknown)=>hash(Buffer.from(JSON.stringify(value)));
 const base=JSON.parse(read('tests/fixtures/fixture-physical-v1/site-surfaces.json').toString()),bytes=read('public/cities/hangzhou/geography/site-surfaces.json'),current=JSON.parse(bytes.toString());
 const additionBytes=read('tests/fixtures/site-path/site-surfaces-candidate.json'),addition=JSON.parse(additionBytes.toString()),stage=JSON.parse(read('tests/fixtures/site-path/staging-report.json').toString());assert.equal(hash(additionBytes),stage.addition.sha256);
 const isAdded=(key:string,g:any)=>(addition[key]??[]).some((a:any)=>(key==='accessCorridors'?a.sourceId===g.sourceId:a.id===g.id));
 // Keep the full equality check without materializing megabytes of assertion
 // diff when a geometry prefix changes. Report the field and both digests.
 for(const key of Object.keys(base)){const values=Array.isArray(current[key])?current[key].filter((g:{id?:string})=>!g.id?.startsWith('leisure:')&&!isAdded(key,g)):current[key];assert.equal(contentHash(values),contentHash(base[key]),key);}
 for(const key of ['walkFloors','accessCorridors','terrainPatches','pathDisplays'])assert.equal(contentHash(current[key].filter((g:any)=>isAdded(key,g))),contentHash(addition[key]),'source-bound path '+key);
 const leisure=JSON.parse(read('public/cities/hangzhou/leisure.json').toString()).sites[0];for(const key of ['walkFloors','solidSlabs'])assert.deepEqual(current[key].filter((g:{id:string})=>g.id.startsWith('leisure:')),leisure[key==='walkFloors'?'floors':key]);
 const oldAccess=current.accessCorridors.filter((c:{sourceId:string})=>!c.sourceId.startsWith('leisure:')&&!isAdded('accessCorridors',c));assert.equal(oldAccess.length,6);for(const c of oldAccess)assert.equal(c.sourceAccessTags.motorcar,'no');assert.deepEqual(current.accessCorridors.filter((c:{sourceId:string})=>c.sourceId.startsWith('leisure:')),leisure.accessCorridors);
 const manifestBytes=read('public/cities/hangzhou/geography/manifest.json'),manifest=JSON.parse(manifestBytes.toString()),detail=JSON.parse(read('public/cities/hangzhou/landmark-detail.json').toString());
 assert.equal(manifest.siteSurfacesSha256,hash(bytes));assert.equal(detail.terrain.manifestSha256,hash(manifestBytes));
});
