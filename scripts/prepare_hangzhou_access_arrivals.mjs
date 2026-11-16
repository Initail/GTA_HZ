/** Find public parking candidates for records whose old arrival is restricted.
 * Uses the existing full car footprint resolver; outputs a reviewable patch.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';
const [stageArg,output]=process.argv.slice(2),stage=path.resolve(stageArg),publicRoot=path.join(stage,'public'),root=path.join(publicRoot,'cities/hangzhou');
if(fs.existsSync(output))throw Error('Fresh arrival candidate required');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const imp=n=>import(pathToFileURL(path.join(stage,'src',n)).href);
const {roadAllows}=await imp('road-access.ts'),{loadCityGeography}=await imp('city-geography.ts'),{loadLandmarkDetails}=await imp('landmark-details.ts');
const {CityCollision}=await imp('driving.ts'),{CityWaterLevels}=await imp('city-water-levels.ts'),{createObserverDestinationResolver}=await imp('city-observer-destination.ts');
const city=read(path.join(root,'city.json')),prior=globalThis.fetch;let geography;
try{globalThis.fetch=async url=>new Response(fs.readFileSync(path.join(publicRoot,String(url))));geography=await loadCityGeography(city);await loadLandmarkDetails(city,{cityId:'hangzhou',manifestSha256:geography.manifestSha256,heightAt:geography.heightAt});}finally{globalThis.fetch=prior;}
const collision=new CityCollision(city,(id,x,z,y)=>geography.levels.heightForSourceRoad(id,x,z,y)),water=new CityWaterLevels(city.water),byId=new Map(city.roads.map(r=>[r.id,r]));
const resolver=createObserverDestinationResolver({data:city,collision,groundHeight:geography.heightAt,propBlocked:()=>false,waterHeight:0,waterHeightAt:(x,z)=>{const w=water.nearest(x,z);return w?.distance===0?w.height:undefined;},heightForSourceRoad:(id,x,z,y)=>geography.levels.heightForSourceRoad(id,x,z,y)});
const changes=[],blocked=[];
const baiRoute=read('artifacts/cities/hangzhou/bai-route-input-v1/route-input.json');
for(const [file,key] of [['city.json','landmarks'],['landmark-detail.json','landmarks'],['map-places.json','places']])for(const lm of read(path.join(root,file))[key]){
 const roadId=lm.arrivalRoadId??lm.arrivalData?.roadId,road=byId.get(roadId);if(!road||roadAllows(road,'motorcar').allowed)continue;
 const entrance=road.sourceId==='way/4326974'?{point:baiRoute.paths[0].points[0],sourceNodeId:baiRoute.paths[0].sourceNodeIds[0],sourceWayId:road.sourceId}:undefined;
 const [x,z]=entrance?.point??[lm.x,lm.z],waterY=water.nearest(x,z)?.height??-Infinity;
 // This is a map-place query above its terrain, not a claimed physical pick.
 const result=resolver({x,z,y:Math.max(geography.heightAt(x,z),waterY)+2},lm.name);
 if(!result?.arrival){blocked.push({file,id:lm.id,name:lm.name,roadId,reason:'no public full-car-footprint arrival within original 300g resolver radius'});continue;}
 const publicRoad=byId.get(result.arrivalRoadId);
 if(entrance&&!publicRoad.nodeIds.map(String).includes(entrance.sourceNodeId))throw Error('Bai parking must share its actual entrance source node');
 changes.push({file,key,id:lm.id,name:lm.name,previous:{arrival:lm.arrival,yaw:lm.yaw,arrivalRoadId:roadId},next:{arrival:result.arrival,yaw:result.yaw,arrivalRoadId:result.arrivalRoadId,arrivalHeightGame:result.arrivalHeightGame,...(entrance?{walkingEntrance:entrance}:{})},sourceAccess:roadAllows(road,'motorcar'),publicSourceId:publicRoad.sourceId});
}
const report={stage,inputs:Object.fromEntries(['city.json','landmark-detail.json','map-places.json','geography/manifest.json'].map(f=>[f,sha(path.join(root,f))])),changes,blocked,scope:'public source road and original full-car-footprint resolver; parked props, last walking leg and browser pending'};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({changes:changes.length,blocked,bai:changes.filter(c=>c.id==='bai-causeway')},null,2));
