/** Actual Python fixture vs runtime TypeScript. This does not render or drive. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import {mountainHeightAt} from '../src/city-mountains.ts';
const [source,output]=process.argv.slice(2);
const json=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const manifest=json(path.join(source,'geography/manifest.json')),audit=json(path.join(output,'python-audit.json'));
const terrainPath=path.join(source,'geography',manifest.terrainFile),roadsPath=path.join(source,'geography',manifest.roadLevelsFile),fixturePath=path.join(output,'sampler-fixture.json');
if(sha(terrainPath)!==manifest.terrainSha256||sha(roadsPath)!==manifest.roadLevelsSha256||sha(fixturePath)!==audit.fixtureSha256)throw Error('Changed sampler input');
for(const [file,hash] of Object.entries(audit.inputs))if(sha(file)!==hash)throw Error('Changed source '+file);
const bytes=fs.readFileSync(terrainPath),heights=new Float32Array(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.length)),terrain=(x,z)=>mountainHeightAt(heights,manifest.grid,x,z);
const levels=new CityRoadLevels(json(roadsPath).roads,terrain,manifest.roadTerrainTransitionGame),samples=json(fixturePath);
let terrainError=0,groundError=0;const failures=[];
for(const sample of samples){
 const te=Math.abs(terrain(sample.x,sample.z)-sample.terrain),ge=Math.abs(levels.groundAt(sample.x,sample.z)-sample.ground);
 terrainError=Math.max(te,terrainError);groundError=Math.max(ge,groundError);
 if(!Number.isFinite(te+ge)||te>1e-8||ge>1e-8)failures.push({...sample,terrainError:te,groundError:ge});
}
const report={kind:'offline-Python-TypeScript-height-parity',samples:samples.length,terrainError,groundError,toleranceGame:1e-8,pass:!failures.length,failures,
 fixtureSha256:sha(fixturePath),checkerSha256:sha('scripts/check_hangzhou_surface.mjs'),pending:['mesh approximation','deck-to-ground joins','browser driving and rendering']};
fs.writeFileSync(path.join(output,'runtime-parity.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,failures:failures.slice(0,4)},null,2));
if(!report.pass)process.exitCode=1;
