/** Actual offline road routes and unchanged contract rules; no driving simulation. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {RoadGraph} from '../src/navigation.ts';
import {CityCollision} from '../src/driving.ts';
import {CareerGame} from '../src/city-career.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
import {resolveCityMissionPlaces} from '../src/city-mission-places.ts';

const [input,locationsFile,output]=process.argv.slice(2);
if(!output)throw new Error('Usage: check_hangzhou_life_routes.mjs SKELETON LOCATIONS REPORT');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const cityFile=path.join(input,'city.json'),navFile=path.join(input,'navigation.json');
const city=JSON.parse(fs.readFileSync(cityFile)),nav=JSON.parse(fs.readFileSync(navFile)),locations=JSON.parse(fs.readFileSync(locationsFile));
if(locations.cityId!=='hangzhou'||locations.inputs.citySha256!==sha(cityFile)||locations.inputs.navigationSha256!==sha(navFile))throw new Error('Changed/wrong-city location inputs');
const graph=new RoadGraph(city.roads,nav),collision=new CityCollision(city);
const places=resolveCityMissionPlaces(CITY_PROFILES.hangzhou,locations,()=>{throw new Error('No Shenzhen fallback');});
const length=route=>route.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-route[i][0],p[1]-route[i][1]),0);
const jobs=new CareerGame(places,undefined,CITY_PROFILES.hangzhou).jobs.map(job=>{
 const legs=job.objectives.slice(1).map((objective,i)=>{
  const previous=job.objectives[i],route=graph.route(previous.position,objective.position),roadLength=length(route),directLength=Math.hypot(previous.position[0]-objective.position[0],previous.position[1]-objective.position[1]);
  return {from:previous.id,to:objective.id,routePointCount:route.length,roadLengthGame:roadLength,directLengthGame:directLength,detourRatio:roadLength/directLength,
   minimumActualTravelGame:Math.min(90,directLength*.6),minimumDrivingForComfortGame:Math.max(Math.min(90,directLength*.6),directLength*.65),
   connected:route.length>1,destinationBlocked:collision.blocked(...objective.position)};
 });
 const roadLength=legs.reduce((sum,l)=>sum+l.roadLengthGame,0),deadline=Math.round(job.deadline);
 return {id:job.id,mechanic:job.mechanic,basePay:job.basePay,requiredLevel:job.requiredLevel,deadlineSeconds:deadline,legs,
  requiredMeanSpeedGameToFinishBeforeDeadline:roadLength/deadline,
  hypotheticalTravelSecondsAt11GameMetresPerSecond:roadLength/11,
  timeRemainingAtThatConstantSpeed:deadline-roadLength/11,
  ruleReachability:legs.every(l=>l.connected&&!l.destinationBlocked&&l.roadLengthGame>=l.minimumActualTravelGame),
  realTrafficStopsAndDriving:'unknown'};
});
const report={kind:'offline-routes-and-contract-rules-only',inputSha256:{city:sha(cityFile),navigation:sha(navFile),locations:sha(locationsFile)},places,
 roleObstacles:Object.fromEntries(Object.entries(places).map(([id,p])=>[id,collision.blocked(...p)])),jobs,
 pass:jobs.every(j=>j.ruleReachability)&&Object.values(places).every(p=>!collision.blocked(...p)),
 pending:['detail building and service prefab collision','terrain road decks ramps','traffic stops and actual driver controls','story branches in browser','quality and payout in browser']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({pass:report.pass,jobs:jobs.map(j=>({id:j.id,roadLength:j.legs.reduce((s,l)=>s+l.roadLengthGame,0),deadline:j.deadlineSeconds,requiredMeanSpeed:j.requiredMeanSpeedGameToFinishBeforeDeadline}))},null,2));
if(!report.pass)process.exitCode=1;
