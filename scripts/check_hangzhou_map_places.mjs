/** Independent serialized catalog/runtime checks, without a browser. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {loadCityMapPlaces} from '../src/city-map-places.ts';import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
import {CityCollision,closest} from '../src/driving.ts';import {RoadGraph} from '../src/navigation.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';import {mountainHeightAt} from '../src/city-mountains.ts';
const [packet,root,cityFile,output]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!output||fs.existsSync(output))throw Error('Fresh output required');
const report=read(path.join(packet,'report.json')),placesFile=path.join(packet,'map-places.json');
for(const [p,hash] of Object.entries(report.sourceInputs))if(sha(p)!==hash)throw Error('Changed source '+p);
if(sha(placesFile)!==report.candidateSha256)throw Error('Changed catalog');
const originalFetch=globalThis.fetch;let places;
try{globalThis.fetch=async url=>{if(url!=='/cities/hangzhou/map-places.json')throw Error('Wrong city URL');return new Response(fs.readFileSync(placesFile),{headers:{'content-type':'application/json'}});};places=await loadCityMapPlaces(undefined,CITY_PROFILES.hangzhou);}finally{globalThis.fetch=originalFetch;}
const city=read(cityFile),nav=read(path.join(root,'navigation.json')),manifest=read(path.join(root,'geography/manifest.json')),terrain=fs.readFileSync(path.join(root,'geography',manifest.terrainFile));
const heights=new Float32Array(terrain.buffer.slice(terrain.byteOffset,terrain.byteOffset+terrain.byteLength)),levels=new CityRoadLevels(read(path.join(root,'geography',manifest.roadLevelsFile)).roads,(x,z)=>mountainHeightAt(heights,manifest.grid,x,z),manifest.roadTerrainTransitionGame);
const collision=new CityCollision(city),roads=new Map(city.roads.map(r=>[r.id,r])),graph=new RoadGraph(city.roads,nav),bad=[],ids=new Set();
for(const p of places){
 const road=roads.get(p.arrivalRoadId),[x,z]=p.arrival,y=levels.groundAt(x,z);
 const distance=road?Math.min(...road.points.slice(1).map((point,i)=>closest(x,z,road.points[i],point).d)):Infinity;
 if(ids.has(p.id)||distance>.001||collision.blocked(x,z,y))bad.push({id:p.id,distance,blocked:collision.blocked(x,z,y)});ids.add(p.id);
}
const routeSamples=[...new Map([...places.filter((p,i)=>i%1000===0),...['park','district','landmark','transport','place'].map(c=>places.find(p=>p.category===c))].filter(Boolean).map(p=>[p.id,p])).values()].map(p=>{
 const from=[city.spawn.x,city.spawn.z],outward=graph.route(from,p.arrival),back=graph.route(p.arrival,from);return {id:p.id,outwardPoints:outward.length,returnPoints:back.length,pass:outward.length>0&&back.length>0};
});
const result={kind:'offline-actual-map-catalog-and-runtime-arrivals',sources:{catalogSha256:sha(placesFile),reportSha256:sha(path.join(packet,'report.json')),citySha256:sha(cityFile),checkerSha256:sha('scripts/check_hangzhou_map_places.mjs')},places:places.length,preparedPlaces:report.placeCount,invalidArrivals:bad,routeSamples,pass:places.length===report.placeCount&&!bad.length&&routeSamples.every(r=>r.pass),browser:false,pending:['real map search/select/favorites/autodrive','all physical road passages','current props/facade clearances']};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,routeSamples:routeSamples.length,invalidArrivals:bad.slice(0,5)},null,2));if(!result.pass)process.exitCode=1;
