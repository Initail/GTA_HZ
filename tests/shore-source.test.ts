import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {CityCollision,stepCar} from '../src/driving.ts';
import {CityCollision as OriginalCollision} from './fixtures/baseline-driving/driving.ts';
import {mergeDetailCollisions} from '../src/landmark-details.ts';import {CitySiteSurfaces} from '../src/city-site-surfaces.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import {CpuWorld,mountainHeightAt} from './cpu-world.ts';
const read=(name:string)=>JSON.parse(readFileSync(new URL('./fixtures/fixture/'+name,import.meta.url),'utf8'));
const proof=read('provenance.json');for(const [name,expected] of Object.entries(proof.files))assert.equal(createHash('sha256').update(readFileSync(new URL('./fixtures/fixture/'+name,import.meta.url))).digest('hex'),expected);
const city=read('city.json'),details=read('details.json'),route=read('route.json');
mergeDetailCollisions(city,details.baseBuildingIds,details.collisionFootprints,details.replacedCollisionIds);
for(const m of details.landmarks){const old=city.landmarks.find((o:any)=>o.id===m.id);if(old)Object.assign(old,m);else city.landmarks.push(m);}
const physical=(name:string)=>readFileSync(new URL('./fixtures/fixture-physical-v1/'+name,import.meta.url));
const physicalProof=JSON.parse(physical('provenance.json').toString());for(const [name,expected] of Object.entries(physicalProof.files))assert.equal(createHash('sha256').update(physical(name)).digest('hex'),expected);
const manifest=JSON.parse(physical('manifest.json').toString()),terrainBuffer=physical(manifest.terrainFile),heights=new Float32Array(terrainBuffer.buffer.slice(terrainBuffer.byteOffset,terrainBuffer.byteOffset+terrainBuffer.byteLength));
const sites=new CitySiteSurfaces(JSON.parse(physical(manifest.siteSurfacesFile).toString())),roads=JSON.parse(physical('road-levels.json').toString()).roads;
const levels=new CityRoadLevels(roads,(x,z)=>mountainHeightAt(heights,manifest.grid,x,z),manifest.roadTerrainTransitionGame,(x,z,y)=>sites.groundAt(x,z,y),(id,x,z)=>sites.roadAt(id,x,z));
for(const r of city.roads)r.heights=roads.find((v:any)=>v.id===r.id).heights;
const adapter=(id:string,x:number,z:number,y:number)=>levels.heightForSourceRoad(id,x,z,y);
const collision=new CityCollision(city,adapter),old=new OriginalCollision(city,adapter);
const world=new CpuWorld();Object.assign(world,{geography:{levels,siteSurfaces:sites},groundHeight:(x:number,z:number)=>levels.groundAt(x,z),collision,bambooCafe:null});
test('Bai public-road junction permits cars, while the source motorcar=no corridor stops them',()=>{
 const source=city.roads.find((r:any)=>r.sourceId==='way/4326974');assert.equal(source.sourceAccessTags.motorcar,'no');
 const [a,b]=source.points;const x=a[0]+(b[0]-a[0])*.8,z=a[1]+(b[1]-a[1])*.8,y=source.heights[0]+(source.heights[1]-source.heights[0])*.8;
 assert.equal(collision.blockReason(x,z,y),'restricted-road');assert.equal(collision.blocked(x,z,y,1.6,false,'foot'),false);
 const publicRoad=city.roads.find((r:any)=>r.sourceId==='way/4398107');assert.ok(publicRoad);
 const idx=publicRoad.nodeIds.findIndex((id:any)=>String(id)==='26315529');assert.ok(idx>=0);
 assert.equal(collision.blockReason(...publicRoad.points[idx],publicRoad.heights[idx]),null);
});
test('real Bai and Broken Bridge support stays walkable above the lake, while the lake stays blocked',()=>{
 let samples=0,waterSamples=0,siteFloors=0;const counts:Record<string,number>={};
 for(const [distance,x,z,datum] of route.stations){
  const floor=world.walkingSurface(x,z);world.walkSiteHint=floor;const q=levels.sample(x,z,world.walkRoadHint);world.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};
  if(floor.id)siteFloors++;
  assert.equal(world.actorCollision(x,z,true),false,`walking ${distance}`);
  const reason=collision.blockReason(x,z,floor.height);counts[reason??'clear']=(counts[reason??'clear']??0)+1;samples++;
  // Both source shore sides, 12g from the centreline. Assert water only when
  // the actual city water query reports it; include source holes unchanged.
  for(const dx of [-12,12])if(collision.blockReason(x+dx,z,floor.height)==='water')waterSamples++;
 }
 assert.ok(samples>600);assert.ok(siteFloors>600);assert.ok(waterSamples>100);
 console.log(JSON.stringify({kind:'baseline-source-centreline-without-access-overlay',samples,siteFloors,vehicleBlockReasons:counts,waterSamples,scope:'CPU source/support queries; not render contact or browser driving'}));
});
test('adding explanations preserves original water, access and structure decisions over the local grid',()=>{
 let compared=0;
 for(let x=-930;x<=-320;x+=10)for(let z=-1460;z<=-710;z+=10)for(const y of [4.5,6,8]){
  assert.equal(collision.blocked(x,z,y),old.blocked(x,z,y),`${x},${z},${y}`);compared++;
 }
 assert.equal(compared,14136);
});

test('real west approach drives normally and gives a specific restriction hint before entering Bai',()=>{
 const road=city.roads.find((r:any)=>r.sourceId==='way/4398107'),a=road.points[1],b=road.points[2];
 const messages:string[]=[];const drive=new CpuWorld();Object.assign(drive,{geography:world.geography,groundHeight:world.groundHeight,collision,bambooCafe:null,tank:null,traffic:null,propBlocked:()=>false,time:0,nextDrivingBarrierHint:0,audio:{impact:()=>{}},onMessage:(s:string)=>messages.push(s)});
 drive.state={x:a[0],z:a[1],yaw:Math.atan2(b[0]-a[0],b[1]-a[1]),speed:0,steer:0,distance:0};
 const step=()=>{const q=levels.sample(drive.state.x,drive.state.z,drive.carRoadHint);drive.carRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};const before={...drive.state};stepCar(drive.state,{throttle:1,steer:0,handbrake:false},.05);drive.time+=.05;drive.resolveVehicleMotion(before,.05);};
 for(let i=0;i<30;i++)step();assert.ok(drive.state.distance>9);assert.deepEqual(messages,[]);
 // Debug placement only initializes the junction; subsequent movement uses
 // original driving controls and the real world collision method.
 const path=route.paths[0].points;drive.carRoadHint=undefined;drive.state={x:path[0][0],z:path[0][1],yaw:Math.atan2(path[1][0]-path[0][0],path[1][1]-path[0][1]),speed:0,steer:0,distance:0};
 for(let i=0;i<60;i++)step();assert.ok(drive.state.distance<3);assert.ok(messages.some(s=>s.includes('限制机动车')));assert.equal(messages.length,1);
});
test('source pedestrian access covers the later Bai decks instead of depending on water blockage',()=>{
 const accessData=JSON.parse(readFileSync(new URL('../public/cities/hangzhou/geography/site-surfaces.json',import.meta.url),'utf8'));
 const accessWorld=Object.create(world);accessWorld.geography={...world.geography,siteSurfaces:new CitySiteSurfaces(accessData)};
 let checked=0;
 for(const [distance,x,z] of route.stations){
  if(distance<110||distance>route.stations.at(-1)[0]-6)continue;
  const floor=world.walkingSurface(x,z);if(!floor.id)continue;
  accessWorld.carSurfaceHeight=()=>floor.height;
  assert.equal(accessWorld.actorCollision(x,z),true,`car accepted on source pedestrian deck at ${distance}`);checked++;
 }
 assert.ok(checked>500);
 accessWorld.carSurfaceHeight=world.carSurfaceHeight;
 const publicRoad=city.roads.find((r:any)=>r.sourceId==='way/4398107'),junction=publicRoad.points.at(-1);
 assert.equal(accessWorld.actorCollision(...junction),false,'source public junction stays open');
 let pedestrians=0;for(const [,x,z] of route.stations){accessWorld.walkSiteHint=accessWorld.walkingSurface(x,z);assert.equal(accessWorld.actorCollision(x,z,true),false);pedestrians++;}
 console.log(JSON.stringify({kind:'source-access-overlay',vehicleDeckSamplesDenied:checked,pedestrianCentrelineSamplesClear:pedestrians,publicJunctionOpen:true}));
});
test('player bicycle queries use actual Bai source permissions on the actual rendered floor',()=>{
 const current=new CitySiteSurfaces(JSON.parse(readFileSync(new URL('../public/cities/hangzhou/geography/site-surfaces.json',import.meta.url),'utf8')));
 const w=new CpuWorld();Object.assign(w,{geography:{levels,siteSurfaces:current},groundHeight:(x:number,z:number)=>levels.groundAt(x,z),collision,bambooCafe:null,propBlocked:()=>false,state:{x:1e6,z:1e6,yaw:0},traffic:null,pedestrians:null});
 const corridors=JSON.parse(readFileSync(new URL('../public/cities/hangzhou/geography/site-surfaces.json',import.meta.url),'utf8')).accessCorridors;
 const baselineCorridors=JSON.parse(readFileSync(new URL('./fixtures/westlake-baseline/site-surfaces.json',import.meta.url),'utf8')).accessCorridors;
 const baselineIds=new Set(baselineCorridors.map((r:any)=>r.sourceId));
 const baiCorridors=corridors.filter((r:any)=>baselineIds.has(r.sourceId));assert.deepEqual(baiCorridors,baselineCorridors,'all six original Bai permission records are retained');
 const walkingHistory=route.stations.map((station:number[])=>{
  const x=station[1],z=station[2],floor=w.walkingSurface(x,z);w.walkSiteHint=floor;
  const q=levels.sample(x,z,w.walkRoadHint);w.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};
  return {x,z,floor,roadHint:{...w.walkRoadHint}};
 });
 let allowed=0,restricted=0;
 for(const corridor of baiCorridors){
  const p=corridor.points as number[][];let i=1;
  for(let j=2;j<p.length;j++)if(Math.hypot(p[j][0]-p[j-1][0],p[j][1]-p[j-1][1])>Math.hypot(p[i][0]-p[i-1][0],p[i][1]-p[i-1][1]))i=j;
  const x=(p[i][0]+p[i-1][0])/2,z=(p[i][1]+p[i-1][1])/2;
  // Preserve the physical deck and road identity obtained by walking the full
  // independently authored route; do not spawn underneath it at lakebed height.
  const station=walkingHistory.reduce((a:any,b:any)=>Math.hypot(a.x-x,a.z-z)<Math.hypot(b.x-x,b.z-z)?a:b);
  w.walkSiteHint=station.floor;w.walkRoadHint=station.roadHint;
  const floor=w.walkingSurface(x,z);assert(floor.id,corridor.sourceId+' known route must have deck support');
  const q=w.bicycleSurface(x,z,floor.height);
  if(corridor.sourceAccessTags.bicycle==='no'){assert.equal(q.blocked,'restricted-road',corridor.sourceId);restricted++;}
  else{assert.equal(q.blocked,null,corridor.sourceId);allowed++;}
 }
 assert.equal(allowed,1);assert.equal(restricted,5);
});
