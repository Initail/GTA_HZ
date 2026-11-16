/** Candidate-only reuse of the original shared-atlas building sign layer. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {generateSignage,choosePlacement} from './generate_city_building_signs.mjs';
import {validateBuildingSignManifest,selectBuildingSigns} from '../src/city-building-signs.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
const [source,collision,output]=process.argv.slice(2);
if(!source||!collision||!output||fs.existsSync(output)||!path.resolve(output).startsWith(path.resolve('artifacts')+path.sep))throw Error('Source, collision manifest and fresh artifact output required');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const rawPath='data/processed/hangzhou-261011-extended/buildings.geojson',cityPath=path.join(source,'city.json');
const city=read(cityPath),raw=read(rawPath),excluded=read(collision).baseBuildingIds;
assert.equal(city.meta.cityId,'hangzhou');
const manifest=generateSignage(city,raw.features,excluded);
manifest.sourceCitySha256=sha(cityPath);
assert(validateBuildingSignManifest(manifest,CITY_PROFILES.hangzhou),'runtime validator rejects candidate');
assert.deepEqual(manifest.signs,generateSignage(city,raw.features,excluded).signs,'deterministic regeneration');
const byPart=new Map(city.buildings.filter(b=>b.style!=='landmark-detail').map(b=>[b.id+':'+crypto.createHash('sha256').update(JSON.stringify(b.rings)).digest('hex'),b]));
for(const s of manifest.signs){
 assert(!excluded.includes(s.buildingId));const b=byPart.get(s.buildingId+':'+s.sourceFootprintSha256);
 assert(b&&b.style!=='landmark-detail');
 if(s.kind==='osm-building-name')assert.equal(s.text,b.name);else assert.equal(s.fictionalDisclosure,'杭城之行·虚构品牌');
 assert(s.position[1]+s.height/2<=b.maxY+.1,'sign above actual building roof');
 assert(s.position[1]-s.height/2>b.maxY-b.height,'sign below actual building floor');
}
// Compare algorithms on identical available Shenzhen inputs. The upstream raw
// building tags are absent locally, so this is not a source-asset rebuild pass.
const original=read('public/city/city.json'),oldModule='docs/hangzhou/audit/source-snapshots/generate_city_building_signs-46703e31c1404ea388c783d5fba3fb1377d1e6286961a166abfc0efcdfbc0248.mjs';
const frozen=await import('../'+oldModule),originalExcluded=read('public/city/building-exclusions.json').excludedIds;
const generated=generateSignage(original,[],originalExcluded);
assert.deepEqual(generated.signs,frozen.generateSignage(original,[],originalExcluded).signs,'Shenzhen generator behavior changed');
const rect={rings:[[[0,0],[30,0],[30,20],[0,20],[0,0]]],height:80};
const low=choosePlacement(rect,'楼体测试',127),high=choosePlacement({...rect,minY:48,maxY:130},'楼体测试',127);
assert.equal(high.position[1]-low.position[1],50);
const visible=selectBuildingSigns(manifest.signs,{x:city.spawn.x,y:6,z:city.spawn.z});assert(visible.length<=64);
fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'building-signs.json'),JSON.stringify(manifest)+'\n');
const report={kind:'offline-building-sign-candidate',cityId:'hangzhou',pass:true,stats:manifest.stats,sourceInputs:Object.fromEntries([cityPath,collision,rawPath,'config/cities/hangzhou.json','scripts/generate_city_building_signs.mjs','scripts/prepare_hangzhou_building_signs.mjs','src/city-building-signs.ts',oldModule].map(p=>[p,sha(p)])),
 candidateSha256:sha(path.join(output,'building-signs.json')),visibleAtSpawn:visible.length,originalShenzhenGeneratorParity:true,originalShenzhenAssetRegeneration:'not run; upstream raw building tags unavailable',
 resourcePolicy:{manifestCap:5000,visibleCap:64,sharedAtlas:[2048,1024],newLights:0},
 pending:['actual facade geometry and obstruction','canvas typography and GPU','day/night appearance','performance']};
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,sourceInputs:undefined},null,2));
