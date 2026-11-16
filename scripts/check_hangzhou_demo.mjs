/** Check the compiled preview's assets with the staged Hangzhou CPU loaders. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const stage = path.resolve(process.argv[2]);
const output = process.argv[3];
const dist = path.join(stage, 'dist');
const importStage = name => import(pathToFileURL(path.join(stage, 'src', name)).href);
const {CITY_CONFIG, assertCityAssetIdentity, cityAssetUrl} = await importStage('city-config.ts');
const {loadCityGeography} = await importStage('city-geography.ts');
const {loadLandmarkDetails} = await importStage('landmark-details.ts');
const {loadCoastalInfrastructure} = await importStage('city-coastal-infrastructure.ts');
const {loadCityMapPlaces} = await importStage('city-map-places.ts');
const {resolveCityMissionPlaces} = await importStage('city-mission-places.ts');
const {CityCollision, stepCar} = await importStage('driving.ts');
const {RoadGraph} = await importStage('navigation.ts');

const requested = [];
const originalFetch = globalThis.fetch;
globalThis.fetch = async resource => {
  const url = String(resource);
  assert(url.startsWith('/cities/hangzhou/'), 'Demo loader must use Hangzhou paths');
  const local = path.resolve(dist, '.' + url);
  assert(local.startsWith(dist + path.sep));
  requested.push(url);
  return new Response(await fs.readFile(local), {headers:{'content-type':'application/json'}});
};

try {
  assert.equal(CITY_CONFIG.id, 'hangzhou');
  assert.equal(CITY_CONFIG.storage.namespace, 'gta-hz-demo');
  const readCity = async file => (await fetch(cityAssetUrl(file))).json();
  const city = await readCity('city.json');
  assertCityAssetIdentity(city.meta);
  const geography = await loadCityGeography(city);
  const detail = await loadLandmarkDetails(city, {cityId:'hangzhou', manifestSha256:geography.manifestSha256, heightAt:geography.heightAt});
  assert(detail);
  const coastal = await loadCoastalInfrastructure(city, geography.heightAt);
  const map = await loadCityMapPlaces();
  assert(map.length > 1000);
  const collision = new CityCollision(city, (id,x,z,y) => geography.levels.heightForSourceRoad(id,x,z,y));
  const graph = new RoadGraph(city.roads, await readCity('navigation.json'));
  graph.bindSourceSurfaceHeight((id,x,z,y) => geography.levels.heightForSourceRoad(id,x,z,y));
  const locations = await readCity('life-sites.json');
  const missionPlaces = resolveCityMissionPlaces(CITY_CONFIG, locations, () => { throw Error('Shenzhen fallback'); });
  const spawn = [city.spawn.x,city.spawn.z];
  const routes = Object.fromEntries(Object.entries(missionPlaces).map(([id,point]) => [id,graph.route(spawn,point).length]));
  assert(Object.values(routes).every(count => count > 1));
  const car = {...city.spawn,speed:0,steer:0,distance:0};
  let hint = geography.levels.sample(car.x,car.z);
  assert(!collision.blocked(car.x,car.z,hint.height));
  for (let i=0;i<30;i++) {
    stepCar(car,{throttle:1,steer:0,handbrake:false},.05);
    hint = geography.levels.sample(car.x,car.z,{height:hint.height,roadId:hint.roadId??undefined,groundOnly:hint.roadId===null});
    assert(!collision.blocked(car.x,car.z,hint.height));
  }
  const report = {pass:true,city:city.meta.cityId,landmarks:detail.manifest.landmarks.length,roads:city.roads.length,graphNodes:graph.nodes.length,mapPlaces:map.length,waterCrossings:coastal.manifest.crossings.length,missionRoutePoints:routes,shortSpawnControllerDistanceGame:car.distance,requested,browserVerified:false};
  await fs.writeFile(output, JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(report,null,2));
} finally {
  globalThis.fetch = originalFetch;
}
