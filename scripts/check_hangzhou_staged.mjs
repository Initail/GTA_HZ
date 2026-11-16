/** Read actual staged bytes and exercise runtime data APIs, without a browser. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {RoadGraph} from '../src/navigation.ts';
import {CityCollision} from '../src/driving.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import {mountainHeightAt} from '../src/city-mountains.ts';
const [root,output]=process.argv.slice(2),read=name=>JSON.parse(fs.readFileSync(path.join(root,name))),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!root||!output||fs.existsSync(output))throw Error('Staged input and fresh output required');
const stage=read('stage-manifest.json');for(const [name,hash] of Object.entries(stage.files))if(sha(path.join(root,name))!==hash)throw Error('Changed staged file '+name);
for(const [name,hash] of Object.entries(stage.sources))if(sha(name)!==hash)throw Error('Changed stage source '+name);
const city=read('city.json'),navigation=read('navigation.json'),g=read('geography/manifest.json'),roads=read('geography/'+g.roadLevelsFile);
const bytes=fs.readFileSync(path.join(root,'geography',g.terrainFile)),heights=new Float32Array(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.length));
const levels=new CityRoadLevels(roads.roads,(x,z)=>mountainHeightAt(heights,g.grid,x,z),g.roadTerrainTransitionGame),graph=new RoadGraph(city.roads,navigation),collision=new CityCollision(city);
graph.bindSourceSurfaceHeight((id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));
const arrivals=city.landmarks.map(mark=>{
 const [x,z]=mark.arrival,y=levels.sample(x,z,{height:levels.groundAt(x,z)}).height;
 return {id:mark.id,arrival:mark.arrival,heightGame:y,blocked:collision.blocked(x,z,y)};
});
const mark=city.landmarks.find(m=>m.id==='qiantang-bridge'),route=graph.route([city.spawn.x,city.spawn.z],mark.arrival);
const relocatedRoute={id:mark.id,points:route.length,lengthGame:route.reduce((sum,p,i)=>i?sum+Math.hypot(p[0]-route[i-1][0],p[1]-route[i-1][1]):0,0),pass:route.length>0};
const solid=city.buildings.filter(b=>b.style==='landmark-detail'),ordinary=city.buildings.filter(b=>b.style!=='landmark-detail');
const verticalRanges=city.buildings.every(b=>Number.isFinite(b.minY+b.maxY)&&b.maxY>b.minY);
const spawn=city.spawn,spawnY=levels.sample(spawn.x,spawn.z,{height:levels.groundAt(spawn.x,spawn.z)}).height;
const report={kind:'offline-staged-runtime-data-check',stageManifestSha256:sha(path.join(root,'stage-manifest.json')),checkerSha256:sha('scripts/check_hangzhou_staged.mjs'),
 counts:{ordinary:ordinary.length,detail:solid.length,roadNodes:graph.nodes.length,parked:read('ebikes/parked.json').bikes.length},
 allBuildingVerticalRanges:verticalRanges,spawnBlocked:collision.blocked(spawn.x,spawn.z,spawnY),arrivals,relocatedRoute,
 pass:verticalRanges&&!collision.blocked(spawn.x,spawn.z,spawnY)&&arrivals.every(a=>!a.blocked)&&relocatedRoute.pass,
 physicalMeshAccepted:false,browserRun:false,pending:stage.pending};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,arrivals:arrivals.filter(a=>a.blocked)},null,2));if(!report.pass)process.exitCode=1;
