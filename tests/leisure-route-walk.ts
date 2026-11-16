import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {CityCollision} from '../src/driving.ts';import {CitySiteSurfaces} from '../src/city-site-surfaces.ts';
import {CityWalk} from '../src/city-walk.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';import {CpuWorld} from './cpu-world.ts';
const json=(name:string)=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const data=json('./main-city-fixture-v2.json'),config=json('../public/cities/hangzhou/leisure.json'),site=config.sites[0];
const surfaces=new CitySiteSurfaces(json('../public/cities/hangzhou/geography/site-surfaces.json'));
const terrainManifest='./fixtures/terrain-v10/manifest.json';
const terrainHeights='../public/cities/hangzhou/geography/terrain-game.bin';
const grid=json(terrainManifest).grid;
const binary=readFileSync(new URL(terrainHeights,import.meta.url));
function terrain(x:number,z:number){const X=(x-grid.x0)/grid.step,Z=(z-grid.z0)/grid.step,i=Math.floor(X),j=Math.floor(Z),u=X-i,v=Z-j,k=j*grid.columns+i;const h=(n:number)=>binary.readFloatLE(n*4),a=h(k),b=h(k+1),d=h(k+grid.columns),c=h(k+grid.columns+1);return u+v<=1?a+(b-a)*u+(d-a)*v:c+(d-c)*(1-u)+(b-c)*(1-v);}
let hint={id:null as string|null,height:site.dock.land.height};
const levels=new CityRoadLevels(data.roadLevels,terrain,20,(x,z,y)=>surfaces.groundAt(x,z,y),(id,x,z)=>surfaces.roadAt(id,x,z));
for(const road of data.roads)road.heights=data.roadLevels.find((r:{id:string})=>r.id===road.id).heights;
const collision=new CityCollision(data,(id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));
const world=new CpuWorld();Object.assign(world,{geography:{levels,siteSurfaces:surfaces},collision,groundHeight:(x:number,z:number)=>levels.groundAt(x,z),walkRoadHint:{height:site.dock.land.height,groundOnly:true},walkSiteHint:hint,propBlocked:()=>false});
const floor=(x:number,z:number)=>{world.walkSiteHint=hint;return world.walkingSurface(x,z);};
const walk=new CityWalk((x,z)=>{world.walkSiteHint=hint;return world.actorCollision(x,z,true);},(x,z)=>floor(x,z).height);

const sha=(x:Buffer|string)=>createHash('sha256').update(x).digest('hex');
const section=Number(process.argv[2]),count=8;
const evidenceDir=process.argv[3];
if(!Number.isInteger(section)||section<0||section>=count||!evidenceDir)throw Error('Expected route section 0..7 and an evidence directory');
const inputs=Object.fromEntries([
 './leisure-route-walk.ts','./cpu-world.ts','../src/city-walk.ts','../src/city-road-levels.ts','../src/driving.ts','../src/city-site-surfaces.ts','../src/city-world.ts',
 './main-city-fixture-v2.json','../public/cities/hangzhou/leisure.json','../public/cities/hangzhou/geography/site-surfaces.json',terrainManifest,terrainHeights,
].map(name=>[name,sha(readFileSync(new URL(name,import.meta.url)))]));
const points:number[][]=[site.arrival.point],midpoint=(a:number[],b:number[])=>[(a[0]+b[0])/2,(a[1]+b[1])/2];
for(const f of site.floors){const t=f.triangles;points.push(midpoint(t[0][0],t[0][1]),f.id==='leisure:marina-deck'?[site.dock.land.x,site.dock.land.z]:midpoint(t[0][2],t[1][2]));}
const total=points.length-1,from=Math.floor(total*section/count)+1,to=Math.floor(total*(section+1)/count);let previous=levels.groundAt(...points[0] as [number,number]),priorHash:string|null=null,visited=0;
if(section){const raw=readFileSync(join(evidenceDir,`route-section-${section-1}.json`));const prev=JSON.parse(raw.toString());assert.deepEqual(prev.inputs,inputs);assert.equal(prev.to,from-1);assert.equal(prev.section,section-1);assert.equal(prev.count,count);priorHash=sha(raw);hint=prev.hint;world.walkRoadHint=prev.roadHint;previous=prev.height;visited=prev.visited;}
else hint={id:null,height:previous};
for(let j=from;j<=to;j++){const a=points[j-1],b=points[j],n=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/.15));for(let i=1;i<=n;i++){
 const x=a[0]+(b[0]-a[0])*i/n,z=a[1]+(b[1]-a[1])*i/n,f=floor(x,z);hint=f;
 assert.ok(Math.abs(f.height-previous)<.48,`step at ${x},${z}: ${previous} -> ${f.height}`);previous=f.height;
 assert.ok(walk.clear(x,z),`blocked at ${x},${z} floor ${f.id}`);visited++;
 const q=levels.sample(x,z,world.walkRoadHint);world.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};
}}
const out=join(evidenceDir,`route-section-${section}.json`);
const record={section,count,from,to,total,inputs,priorHash,visited,height:previous,hint,roadHint:world.walkRoadHint};
writeFileSync(out,JSON.stringify(record,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({section,from,to,visited,height:previous}));
