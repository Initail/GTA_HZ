/** Bind selected models, explicit collision retirement and source arrivals.
 * Offline packet only; props, visual contact and real driving remain gates.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {mergeDetailCollisions} from '../src/landmark-details.ts';
import {CityCollision} from '../src/driving.ts';
import {attachCityRoadLevels} from '../src/city-geography.ts';
import {CitySiteSurfaces} from '../src/city-site-surfaces.ts';
import {CityWaterLevels} from '../src/city-water-levels.ts';
import {mountainHeightAt} from '../src/city-mountains.ts';
import {createObserverDestinationResolver} from '../src/city-observer-destination.ts';
import {RoadGraph} from '../src/navigation.ts';
import {projectCityWgs84,unprojectCityPoint,assertCityAssetIdentity} from '../src/city-config.ts';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
const [source,inventoryFile,modelsDir,output,detailOverride]=process.argv.slice(2);
if(!output||fs.existsSync(output)||!path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep))throw Error('Fresh artifact packet required');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),inputs={};
const read=p=>{inputs[p]=sha(p);return JSON.parse(fs.readFileSync(p));};
const city=read(path.join(source,'city.json')),detail=read(detailOverride??path.join(source,'detail-collision-candidate.json')),g=read(path.join(source,'geography/manifest.json'));
const inventory=read(inventoryFile),models=read(path.join(modelsDir,'asset-manifest.json'));
assert.equal(city.meta.cityId,'hangzhou');assert.equal(models.cityId,'hangzhou');
assertCityAssetIdentity({...g,cityId:'hangzhou'},CITY_PROFILES.hangzhou);
const levelFile=path.join(source,'geography',g.roadLevelsFile),terrainFile=path.join(source,'geography',g.terrainFile),siteFile=path.join(source,'geography',g.siteSurfacesFile);
assert.equal(sha(levelFile),g.roadLevelsSha256);assert.equal(sha(terrainFile),g.terrainSha256);assert.equal(sha(siteFile),g.siteSurfacesSha256);
inputs[terrainFile]=sha(terrainFile);
const sites=new CitySiteSurfaces(read(siteFile)),raw=fs.readFileSync(terrainFile),heights=new Float32Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));
const levels=attachCityRoadLevels(city,read(levelFile).roads,(x,z)=>mountainHeightAt(heights,g.grid,x,z),g.roadTerrainTransitionGame,(x,z,y)=>sites.groundAt(x,z,y),(id,x,z)=>sites.roadAt(id,x,z));
const selectedIds=new Set(models.selected.filter(s=>!s.id.startsWith('foundations:')).map(s=>s.id));
const selected=inventory.objects.filter(o=>selectedIds.has(o.id));assert.equal(selected.length,selectedIds.size);
for(const object of selected){assert.equal(models.selected.find(s=>s.id===object.id).sha256,object.artifactSha256);assert.equal(sha(object.artifact),object.artifactSha256);}
const structuralIds=new Set(detail.structuralCollisionIds??[]),requiredStructuralAssets=detail.requiredStructuralAssets??[];
assert.equal(structuralIds.size,(detail.structuralCollisionIds??[]).length,'Repeated structural collision ID');
assert(!structuralIds.size||requiredStructuralAssets.length,'Structural collisions need actual asset bindings');
for(const asset of requiredStructuralAssets){assert(['roads','landmarks','coastal-bridges'].includes(asset.role),'Unknown structural runtime role');assert.equal(sha(asset.sourceFile),asset.sha256);inputs[asset.sourceFile]=asset.sha256;}
for(const id of structuralIds)assert(detail.collisionFootprints.some(f=>f.id===id),'Missing declared structural body '+id);
const footprints=detail.collisionFootprints.filter(f=>selectedIds.has(f.id.split(':')[0])||structuralIds.has(f.id));
const incoming=new Set(footprints.map(f=>f.id)),replacedCollisionIds=city.buildings.filter(b=>b.style==='landmark-detail'&&!incoming.has(b.id)).map(b=>b.id);
assert(replacedCollisionIds.every(id=>typeof id==='string'&&id.includes(':')),'Retire only explicit prepared detail identities');
const baseBuildingIds=[...new Set(selected.flatMap(o=>o.baseBuildingIds))];
mergeDetailCollisions(city,baseBuildingIds,footprints,replacedCollisionIds);
assert.equal(city.buildings.filter(b=>b.style==='landmark-detail').length,footprints.length);
const navigation=read(path.join(source,'navigation.json')),graph=new RoadGraph(city.roads,navigation);
graph.bindSourceSurfaceHeight((id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));
// Select arrival roads from the existing spawn-connected source graph. Do not
// connect separate ways because their rendered polygons happen to intersect.
const spawnEdge=graph.nearestEdge([city.spawn.x,city.spawn.z]),connected=new Set([spawnEdge.a]),queue=[spawnEdge.a];
for(let i=0;i<queue.length;i++)for(const next of graph.edges[queue[i]].keys())if(!connected.has(next)){connected.add(next);queue.push(next);}
const connectedRoads=city.roads.filter(r=>navigation.roadNodes[r.id].every(id=>connected.has(id)));
const collision=new CityCollision({...city,roads:connectedRoads},(id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y)),waters=new CityWaterLevels(city.water);
const resolve=createObserverDestinationResolver({data:city,collision,groundHeight:(x,z)=>levels.groundAt(x,z),waterHeight:.9,
 waterHeightAt:(x,z)=>{const w=waters.nearest(x,z);return w?.distance===0?w.height:undefined;},
 heightForSourceRoad:(id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y),
 propBlocked:(x,z)=>sites.blocked(x,z,levels.groundAt(x,z)),
});
const landmarks=[],arrivals=[],blocked=[];
for(const object of selected){
 const record=detail.landmarks.find(m=>m.id===object.id);assert(record&&record.artifactSha256===object.artifactSha256,'Collision/model binding '+object.id);
 // These two map destinations already exist, with source feature IDs from
 // the combined causeway object. Do not invent a third synthetic location.
 const ids=object.id==='west-lake-causeways'?['bai-causeway','su-causeway']:[object.id];
 for(const id of ids){
  const base=city.landmarks.find(m=>m.id===id);assert(base,'Missing source map destination '+id);
  const mark={...base,...(id===object.id?record:{}),modelObjectId:object.id,modelStatus:'selected-candidate-not-visually-accepted',detailCollision:true};
  // Model anchors may replace an old source-polygon centroid. Keep the old
  // geographic metadata as provenance, but the displayed coordinates must
  // describe the selected map anchor in the same central projection.
  const anchorWgs84=unprojectCityPoint(mark.x,mark.z,CITY_PROFILES.hangzhou);
  if(Number.isFinite(mark.lon+mark.lat)&&Math.hypot(...projectCityWgs84(mark.lon,mark.lat,CITY_PROFILES.hangzhou).map((v,i)=>v-[mark.x,mark.z][i]))>1e-6){
   mark.previousSourceMapWgs84=[mark.lon,mark.lat];
  }
  [mark.lon,mark.lat]=anchorWgs84;
  mark.mapAnchorBasis='Inverse of selected game x/z using shared Hangzhou WGS84 projection; not an additional measurement';
  // A long causeway's map focus is not a vehicle entrance. Keep the source
  // focus, but select a road near its authored arrival or original path ends.
  // The observer's 300g radius and nine body samples remain unchanged.
  const anchors=[{point:base.arrival,kind:'existing-source-arrival'}];
  if(['bai-causeway','su-causeway','broken-bridge'].includes(id)){
   for(const r of city.roads.filter(r=>base.sourceFeatureIds?.some(sourceId=>r.id.startsWith(sourceId+'#')))){
    for(const k of [0,r.points.length-1])anchors.push({point:r.points[k],kind:'original-source-path-end',sourceRoadId:r.id,sourceNodeId:r.nodeIds[k]});
   }
  }
  const choices=anchors.flatMap(anchor=>{
   const [x,z]=anchor.point,y=levels.groundAt(x,z),candidate=resolve({x,z,y:Math.max(y,object.boundsGameEastUpNorth.max[1])},mark.name);
   return candidate?.arrivalRoadId?[{...candidate,anchor,distance:Math.hypot(candidate.arrival[0]-x,candidate.arrival[1]-z)}]:[];
  }).sort((a,b)=>a.distance-b.distance);
  const result=choices[0];
  const arrival=result?.arrivalRoadId&&result.arrival?levels.sourceArrival(result.arrivalRoadId,...result.arrival):null;
  if(arrival){
   mark.arrival=result.arrival;mark.yaw=result.yaw;mark.arrivalRoadId=arrival.roadId;mark.arrivalHeightGame=arrival.height;
   mark.arrivalData={arrival:mark.arrival,yaw:mark.yaw,roadId:arrival.roadId,grade:city.roads.find(r=>r.id===arrival.roadId).grade,distance:Math.hypot(mark.arrival[0]-mark.x,mark.arrival[1]-mark.z),sourceAnchor:result.anchor};
   const route=graph.route([city.spawn.x,city.spawn.z],mark.arrival),back=graph.route(mark.arrival,[city.spawn.x,city.spawn.z]);
   arrivals.push({id,oldArrival:base.arrival,arrival:mark.arrival,roadId:arrival.roadId,heightGame:arrival.height,sourceAnchor:result.anchor,anchorDistanceGame:result.distance,outwardPoints:route.length,returnPoints:back.length,bodySamples:9});
   if(!route.length||!back.length)blocked.push({id,reason:'no source graph route from/to spawn'});
  }else blocked.push({id,reason:'no body-clear source road within original observer radius'});
  mark.roadAccessStatus='CPU source/body/route candidate; props and real driving pending';
  mark.photoTargetHeight=object.boundsGameEastUpNorth.min[1]+object.heightGame*.38;
  landmarks.push(mark);
 }
}
const manifest={schemaVersion:1,asset:'/cities/hangzhou/landmark-detail.glb',replacedMeshPrefixes:[],baseBuildingIds,replacedCollisionIds,landmarks,collisionFootprints:footprints,requiredStructuralAssets,
 terrain:{kind:'city-geography',cityId:'hangzhou',manifestSha256:sha(path.join(source,'geography/manifest.json'))},
 status:'isolated candidate; no runtime activation',sourceModelManifestSha256:sha(path.join(modelsDir,'asset-manifest.json'))};
fs.mkdirSync(output);
// A failing packet retains its diagnostic report, but never writes an unsafe
// landmark-detail.json that could silently be installed as a usable layer.
const write=(name,data)=>fs.writeFileSync(path.join(output,name),JSON.stringify(data,null,2)+'\n');
if(!blocked.length){write('landmark-detail.json',manifest);fs.copyFileSync(path.join(modelsDir,'landmark-detail.glb'),path.join(output,'landmark-detail.glb'));}
write('arrival-checks.json',arrivals);
inputs['scripts/prepare_hangzhou_detail_packet.mjs']=sha('scripts/prepare_hangzhou_detail_packet.mjs');
for(const file of ['src/landmark-details.ts','src/city-road-levels.ts','src/city-site-surfaces.ts','src/city-observer-destination.ts','src/driving.ts','src/navigation.ts','src/city-config.ts','src/city-profiles.generated.ts','config/cities/hangzhou.json'])inputs[file]=sha(file);
const report={kind:'isolated model/collision/map binding packet',cityId:'hangzhou',inputs,objects:selected.length,mapDestinations:landmarks.length,collisionFootprints:footprints.length,retiredCollisionIds:replacedCollisionIds,omittedModelIds:models.omittedIds,blocked,pass:blocked.length===0,files:Object.fromEntries(fs.readdirSync(output).map(f=>[f,sha(path.join(output,f))])),pending:['all selected object base heights and structural contact','ordinary building floors and near facades final integration','full roadside props/parking/cafe clearance','road arrival to source path entrance walking connection','original graph route does not itself certify one-way compliance','omitted bridge detail and regional base rebuild','actual browser navigation/quick travel/autodrive and visual acceptance']};
write('report.json',report);console.log(JSON.stringify({...report,inputs:undefined,retiredCollisionIds:replacedCollisionIds.length},null,2));if(blocked.length)process.exitCode=1;
