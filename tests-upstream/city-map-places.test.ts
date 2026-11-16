import test from 'node:test';
import assert from 'node:assert/strict';
import {cityMapPlacesUrl,loadCityMapPlaces} from '../src/city-map-places.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
import {projectCityWgs84} from '../src/city-config.ts';
test('Hangzhou map sources use the city asset root and reject Shenzhen catalogs',async t=>{
 assert.equal(cityMapPlacesUrl(CITY_PROFILES.hangzhou),'/cities/hangzhou/map-places.json');
 assert.match(String(cityMapPlacesUrl(CITY_PROFILES.shenzhen)),/data\/map-places.json$/);
 t.mock.method(globalThis,'fetch',async()=>new Response(JSON.stringify({schemaVersion:1,places:[]})));
 await assert.rejects(loadCityMapPlaces(undefined,CITY_PROFILES.hangzhou),/城市不一致/);
 assert.deepEqual(await loadCityMapPlaces(undefined,CITY_PROFILES.shenzhen),[]);
});
test('Hangzhou map places preserve verified arrivals instead of resnapping to an overpass',async t=>{
 const [x,z]=projectCityWgs84(120.16,30.27,CITY_PROFILES.hangzhou);
 const place={id:'test',name:'测试地点',category:'place',lon:120.16,lat:30.27,x,z,arrival:[x+15,z+10],yaw:.4,arrivalRoadId:'way/1#0',source:{provider:'OpenStreetMap'}};
 let places:unknown[]=[place];t.mock.method(globalThis,'fetch',async()=>new Response(JSON.stringify({schemaVersion:1,cityId:'hangzhou',places})));
 assert.deepEqual((await loadCityMapPlaces(undefined,CITY_PROFILES.hangzhou))[0],place);
 places=[{...place,arrival:undefined}];await assert.rejects(loadCityMapPlaces(undefined,CITY_PROFILES.hangzhou),/到达点/);
});
