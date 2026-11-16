/** CPU preflight for the diagnostic's actual physics inputs, before any GPU. */
import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {CityRoadLevels} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-road-levels.ts';
import {CityCollision} from '../artifacts/cities/hangzhou/city-leisure-v15/src/driving.ts';
import {CitySiteSurfaces} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-site-surfaces.ts';
import {CityWalk} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-walk.ts';
const [folder,output,routeFile]=process.argv.slice(2);assert(folder&&output&&!fs.existsSync(output));
const data=JSON.parse(fs.readFileSync(folder+'/scene-data.json','utf8')),files=JSON.parse(fs.readFileSync(folder+'/asset-files.json','utf8'));
for(const r of Object.values(files) as any[]){const b=fs.readFileSync(r.path);assert.equal(b.length,r.bytes);assert.equal(createHash('sha256').update(b).digest('hex'),r.sha256);}
const bytes=fs.readFileSync(files['/terrain.bin'].path),values=new Float32Array(bytes.buffer,bytes.byteOffset,bytes.length/4),g=data.geo.grid;
const terrain=(x:number,z:number)=>{const u=(x-g.x0)/g.step,v=(z-g.z0)/g.step,i=Math.floor(u),j=Math.floor(v);if(i<0||j<0||i>=g.columns-1||j>=g.rows-1)return 0;const fx=u-i,fz=v-j,k=j*g.columns+i,a=values[k],b=values[k+1],d=values[k+g.columns],c=values[k+g.columns+1];return fx+fz<=1?a+(b-a)*fx+(d-a)*fz:c+(d-c)*(1-fx)+(b-c)*(1-fz);};
const site=new CitySiteSurfaces(data.surfaces),levels=new CityRoadLevels(data.levelRoads,terrain,data.geo.roadTerrainTransitionGame,(x,z,y)=>site.groundAt(x,z,y)),collision=new CityCollision(data.city,(id,x,z,h)=>levels.heightForSourceRoad(id,x,z,h));
const height=(x:number,z:number)=>{const g=levels.sample(x,z,{height:levels.groundAt(x,z),groundOnly:true}).height,n=collision.nearest(x,z,g),edge=n?n.d-n.road.width/2:Infinity,w=n&&['trunk','primary','secondary','tertiary'].includes(n.road.kind)?2.4:1.2;return site.walkAt(x,z,g+(edge<=0?.105:edge<w?.065:0),g).height;};
const results=[];
for(const [i,p] of data.starts.entries()){
 const walker=new CityWalk((x,z)=>collision.blocked(x,z,height(x,z),1.6,false,'foot'),height);walker.active=true;walker.x=p.pointGame[0];walker.z=p.pointGame[1];walker.yaw=i===0?-1.81:-.29;
 assert(walker.clear(walker.x,walker.z));const changedHeight=height(walker.x,walker.z)-p.height;assert(Math.abs(changedHeight)<(data.surfaces.terrainPatches?.length?.48:1e-8));
 for(let n=0;n<60;n++)walker.step(new Set(['KeyW']),1/60);
 assert(walker.distance>1.5&&walker.distance<1.61);results.push({start:i,sourcePoint:p.pointGame,changedHeightGame:changedHeight,actualGameDistance:walker.distance,end:[walker.x,walker.z],height:height(walker.x,walker.z)});
}
let floorSamples=0,quantizedDegenerate=0;
for(const f of data.surfaces.walkFloors)for(const t of f.triangles){
 const q=t.map((v:number[])=>v.map(Math.fround));if((q[1][0]-q[0][0])*(q[2][1]-q[0][1])-(q[1][1]-q[0][1])*(q[2][0]-q[0][0])<=0)quantizedDegenerate++;
 for(const w of [[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3,1/3,1/3]]){
  const [x,z,y]=[0,1,2].map(k=>w.reduce((s,n,i)=>s+n*t[i][k],0)),ground=site.groundAt(x,z,terrain(x,z)),contact=site.walkAt(x,z,ground,{id:f.id,height:y});
  assert.equal(contact.id,f.id);assert(Math.abs(contact.height-y)<1e-8);if(data.surfaces.terrainPatches?.length)assert(Math.abs(y-ground-.015)<1e-8);floorSamples++;
 }
}
assert.equal(quantizedDegenerate,0);
let routeAudit:unknown=null;
if(routeFile){
 const bytes=fs.readFileSync(routeFile),route=JSON.parse(bytes.toString()).route,blocked:any[]=[],steps:any[]=[],motorFailures:any[]=[];let previous:number|undefined;
 const walker=new CityWalk((x,z)=>collision.blocked(x,z,height(x,z),1.6,false,'foot'),height);
 for(const row of route){const [x,z]=row.pointGame,h=height(x,z);if(!walker.clear(x,z))blocked.push(row.index);if(previous!==undefined&&Math.abs(h-previous)>=.48)steps.push({index:row.index,delta:h-previous});previous=h;
  if(site.reservedWalkPath(x,z)&&!site.restrictedSourceAt(x,z,h,'motorcar'))motorFailures.push(row.index);
 }
 routeAudit={source:{file:routeFile,sha256:createHash('sha256').update(bytes).digest('hex')},samples:route.length,bodySamplesPerPoint:9,blocked,steps,motorFailures};
 console.log(JSON.stringify(routeAudit));assert.equal(blocked.length,0);assert.equal(steps.length,0);assert.equal(motorFailures.length,0);
}
fs.writeFileSync(output,JSON.stringify({scope:'diagnostic local inputs, all physical floor vertices/edge midpoints/centroids, and actual CityWalk; no GPU',pass:true,results,floorSamples,quantizedDegenerate,routeAudit,wholeCityAccepted:false},null,2)+'\n');console.log(JSON.stringify({results,floorSamples,quantizedDegenerate}));
