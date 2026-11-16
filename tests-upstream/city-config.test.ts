import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {CITY_PROFILES,CITY_CONFIG_SOURCE_SHA256} from '../src/city-profiles.generated.ts';
import {projectCityWgs84,unprojectCityPoint,cityAssetUrl} from '../src/city-config.ts';

test('generated profiles are bound to authoritative city JSON',()=>{
  const files=['config/active-city.json','config/cities/hangzhou.json','config/cities/shenzhen.json'];
  const hash=createHash('sha256');for(const file of files)hash.update(readFileSync(file));
  assert.equal(hash.digest('hex'),CITY_CONFIG_SOURCE_SHA256);
});
test('baseline geography preserves the upstream mapping exactly',()=>{
  assert.deepEqual(projectCityWgs84(113.94161,22.517785,CITY_PROFILES.shenzhen),[(113.94161-114.025)*102850*.6,(22.517785-22.536)*111320*.6]);
});
test('Hangzhou coefficients use its latitude and scale geography once',()=>{
  const city=CITY_PROFILES.hangzhou,g=city.geography;
  assert.ok(g.eastMetresPerDegree>95000&&g.eastMetresPerDegree<97000);
  const point: [number,number]=[119.96,30.2648],mapped=projectCityWgs84(...point,city),back=unprojectCityPoint(...mapped,city);
  assert.ok(Math.abs(back[0]-point[0])<1e-12&&Math.abs(back[1]-point[1])<1e-12);
  assert.ok(Math.abs(projectCityWgs84(120.165,30.274,city)[0]-g.eastMetresPerDegree*.006)<1e-8);
});
test('Python preparation and TypeScript agree on a Hangzhou point',()=>{
  const python=process.env.CITY_PYTHON??'python3';
  const result=JSON.parse(execFileSync(python,['-c','from scripts.city_config import *; import json; print(json.dumps(project(119.96,30.2648,load_city("hangzhou"))))'],{encoding:'utf8'}));
  assert.deepEqual(result,projectCityWgs84(119.96,30.2648,CITY_PROFILES.hangzhou));
});
test('all persisted Hangzhou data keys are isolated from Shenzhen',()=>{
  const oldKeys=new Set(Object.values(CITY_PROFILES.shenzhen.storage));
  for(const key of Object.values(CITY_PROFILES.hangzhou.storage)){assert.ok(!oldKeys.has(key));assert.ok(key.startsWith('gta-hz'));}
  assert.equal(cityAssetUrl('city.json',CITY_PROFILES.hangzhou),'/cities/hangzhou/city.json');
  assert.throws(()=>cityAssetUrl('../city/city.json'));
});
test('Hangzhou cannot silently inherit Shenzhen ocean or mission positions',()=>{
  const h=CITY_PROFILES.hangzhou;
  assert.equal(h.water.southernOcean,false);assert.equal(h.water.oppositeShore,false);
  assert.equal(h.missionPlaces.park,'mission-points:park');
  assert.equal(h.missionPlaces.bay,'mission-points:bay');
  assert.equal(h.missionPlaces.workshop,'life-sites:workshop');
  assert.equal(h.delivery.status,'implementation');
});
