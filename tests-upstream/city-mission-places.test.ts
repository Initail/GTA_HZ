import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
import {resolveCityMissionPlaces,type CityLifeLocations} from '../src/city-mission-places.ts';

test('the Shenzhen roles preserve the actual original reuse and bay callback',()=>{
 const payload=JSON.parse(readFileSync('public/city/life-sites.json','utf8'));
 const actual=resolveCityMissionPlaces(CITY_PROFILES.shenzhen,payload,()=>[123,456]);
 const site=(id:string)=>payload.sites.find((s:{id:string})=>s.id===id).arrival;
 assert.deepEqual(actual,{hub:site('hub'),office:site('office'),park:site('workshop'),workshop:site('office'),bay:[123,456]});
});
test('Hangzhou resolves five independently declared roles without a Shenzhen fallback',()=>{
 const payload:CityLifeLocations={cityId:'hangzhou',sites:[{id:'hub',arrival:[1,2]},{id:'office',arrival:[3,4]},{id:'workshop',arrival:[5,6]}],missionPlaces:{park:[7,8],bay:[9,10]}};
 const actual=resolveCityMissionPlaces(CITY_PROFILES.hangzhou,payload,()=>{throw Error('legacy fallback used');});
 assert.deepEqual(actual,{hub:[1,2],office:[3,4],workshop:[5,6],park:[7,8],bay:[9,10]});
 actual.hub[0]=99;assert.deepEqual(payload.sites[0].arrival,[1,2]);
});
test('wrong-city or incomplete Hangzhou location data fails before accepting jobs',()=>{
 const original=JSON.parse(readFileSync('public/city/life-sites.json','utf8'));
 assert.throws(()=>resolveCityMissionPlaces(CITY_PROFILES.hangzhou,original,()=>[0,0]),/其他城市/);
 assert.throws(()=>resolveCityMissionPlaces(CITY_PROFILES.hangzhou,{cityId:'hangzhou',sites:[]},()=>[0,0]),/缺失/);
});
