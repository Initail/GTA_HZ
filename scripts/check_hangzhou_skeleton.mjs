/** Offline runtime geometry/navigation checks; never a browser/GLB pass. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {RoadGraph} from '../src/navigation.ts';
import {CityCollision} from '../src/driving.ts';
import {assertCityAssetIdentity} from '../src/city-config.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';

const input=process.argv[2];
const output=process.argv[3];
if(!input||!output)throw new Error('Usage: node --experimental-transform-types scripts/check_hangzhou_skeleton.mjs INPUT REPORT');
const json=name=>JSON.parse(fs.readFileSync(path.join(input,name),'utf8'));
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const manifest=json('skeleton-manifest.json');
for(const [name,hash] of Object.entries(manifest.sha256))if(sha(path.join(input,name))!==hash)throw new Error('Changed skeleton '+name);
const city=json('city.json'),navigation=json('navigation.json');
assertCityAssetIdentity(city.meta,CITY_PROFILES.hangzhou);
const graph=new RoadGraph(city.roads,navigation),collision=new CityCollision(city),opening=[city.spawn.x,city.spawn.z];
const results=[];
for(const mark of city.landmarks){
 const began=performance.now(),route=graph.route(opening,mark.arrival),cpuMs=performance.now()-began;
 let distance=0,maxSegment=0;
 for(let i=1;i<route.length;i++){const d=Math.hypot(route[i][0]-route[i-1][0],route[i][1]-route[i-1][1]);distance+=d;maxSegment=Math.max(maxSegment,d);}
 const blocked=collision.blocked(...mark.arrival),direct=Math.hypot(mark.arrival[0]-opening[0],mark.arrival[1]-opening[1]);
 const pass=route.length>0&&!blocked&&maxSegment<=20.001;
 results.push({id:mark.id,name:mark.name,pass,arrival:mark.arrival,arrivalBlocked:blocked,
  routeLengthGameMetres:distance,straightLineGameMetres:direct,detourRatio:distance/(direct||1),
  maxRouteSegmentGameMetres:maxSegment,routePointCount:route.length,routeComputeCpuMs:cpuMs,
  roadAccessStatus:mark.roadAccessStatus,
  browserDriving:'unknown',elevatedSurfaceAndRampAccess:'unknown'});
}
const report={schemaVersion:1,kind:'offline-geographic-runtime-functions-only',input,sourceSha256:manifest.sourceSha256,
 inputSha256:{city:sha(path.join(input,'city.json')),navigation:sha(path.join(input,'navigation.json'))},
 nodeVersion:process.version,host:{platform:process.platform,architecture:process.arch},
 openingBlocked:collision.blocked(...opening),results,pass:results.every(r=>r.pass)&&!collision.blocked(...opening),
 missingPhysicalSurfaceRoads:city.roads.filter(r=>r.grade!=='0'||r.bridge!=='no'||r.tunnel!=='no').length,
 pending:['GLB geometry','DEM/decks/ramps/tunnels','road driving and obstacle avoidance','browser operation','performance frames/memory/cold start']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({pass:report.pass,targets:results.length,failures:results.filter(r=>!r.pass),missingPhysicalSurfaceRoads:report.missingPhysicalSurfaceRoads},null,2));
if(!report.pass)process.exitCode=1;
