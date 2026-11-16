import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {assertCityAssetIdentity} from '../src/city-config.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';

const original=JSON.parse(readFileSync('public/city/city.json','utf8')).meta;
const hz={cityId:'hangzhou',originWGS84:[120.155,30.274],horizontalScale:.6,eastMetresPerDegree:96220.11856153939,northMetresPerDegree:110857.07311230902};
test('the original geographic metadata is accepted for the original profile only',()=>{
 assert.doesNotThrow(()=>assertCityAssetIdentity(original,CITY_PROFILES.shenzhen));
 assert.throws(()=>assertCityAssetIdentity(original,CITY_PROFILES.hangzhou),/身份/);
});
test('Hangzhou requires explicit city identity, geographic origin and one scale',()=>{
 assert.doesNotThrow(()=>assertCityAssetIdentity(hz,CITY_PROFILES.hangzhou));
 assert.throws(()=>assertCityAssetIdentity({...hz,cityId:undefined},CITY_PROFILES.hangzhou),/身份/);
 assert.throws(()=>assertCityAssetIdentity({...hz,originWGS84:original.originWGS84},CITY_PROFILES.hangzhou),/原点/);
 assert.throws(()=>assertCityAssetIdentity({...hz,horizontalScale:.36},CITY_PROFILES.hangzhou),/缩放/);
});
test('Hangzhou cannot silently retain the Shenzhen projection coefficients',()=>{
 assert.throws(()=>assertCityAssetIdentity({...hz,eastMetresPerDegree:102850},CITY_PROFILES.hangzhou),/投影/);
 assert.throws(()=>assertCityAssetIdentity({...hz,northMetresPerDegree:111320},CITY_PROFILES.hangzhou),/投影/);
 assert.throws(()=>assertCityAssetIdentity({...hz,northMetresPerDegree:NaN},CITY_PROFILES.hangzhou),/投影/);
});
