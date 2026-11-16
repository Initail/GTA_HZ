import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {mkdirSync,mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {test} from 'node:test';import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {CityCollision} from '../src/driving.ts';import {CitySiteSurfaces} from '../src/city-site-surfaces.ts';
import {CityWalk} from '../src/city-walk.ts';import {LeisureBoat} from '../src/city-leisure.ts';import {CityLeisureWater} from '../src/city-leisure-water.ts';import {roadAllows} from '../src/road-access.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';import {CpuWorld} from './cpu-world.ts';
const json=(name:string)=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const data=json('./main-city-fixture-v2.json'),config=json('../public/cities/hangzhou/leisure.json'),site=config.sites[0];
const surfaces=new CitySiteSurfaces(json('../public/cities/hangzhou/geography/site-surfaces.json'));
const grid=json('./fixtures/terrain-v10/manifest.json').grid;
const binary=readFileSync(new URL('../public/cities/hangzhou/geography/terrain-game.bin',import.meta.url));
function terrain(x:number,z:number){const X=(x-grid.x0)/grid.step,Z=(z-grid.z0)/grid.step,i=Math.floor(X),j=Math.floor(Z),u=X-i,v=Z-j,k=j*grid.columns+i;const h=(n:number)=>binary.readFloatLE(n*4),a=h(k),b=h(k+1),d=h(k+grid.columns),c=h(k+grid.columns+1);return u+v<=1?a+(b-a)*u+(d-a)*v:c+(d-c)*(1-u)+(b-c)*(1-v);}
let hint={id:null as string|null,height:site.dock.land.height};
const levels=new CityRoadLevels(data.roadLevels,terrain,20,(x,z,y)=>surfaces.groundAt(x,z,y),(id,x,z)=>surfaces.roadAt(id,x,z));
for(const road of data.roads)road.heights=data.roadLevels.find((r:{id:string})=>r.id===road.id).heights;
const collision=new CityCollision(data,(id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));const water=new CityLeisureWater(data,new Set(site.waterIds),collision,surfaces,()=>false,(id,x,z,y)=>levels.heightForSourceRoad(id,x,z,y));
const world=new CpuWorld();Object.assign(world,{geography:{levels,siteSurfaces:surfaces},collision,groundHeight:(x:number,z:number)=>levels.groundAt(x,z),walkRoadHint:{height:site.dock.land.height,groundOnly:true},walkSiteHint:hint,propBlocked:()=>false});
const floor=(x:number,z:number)=>{world.walkSiteHint=hint;return world.walkingSurface(x,z);};
const walk=new CityWalk((x,z)=>{world.walkSiteHint=hint;return world.actorCollision(x,z,true);},(x,z)=>floor(x,z).height);
test('fixed snapshot, projection and actual lake identity are retained',()=>{assert.equal(config.cityId,'hangzhou');assert.deepEqual(config.originWGS84,[120.155,30.274]);assert.equal(config.horizontalScale,.6);assert.equal(site.sourceCenterWGS84[0],120.1516361);assert.equal(water.at(site.dock.berth.x,site.dock.berth.z)?.id,'relation/2308774');});
test('arrival is on an admitted actual motor road',()=>{const n=collision.nearest(...site.arrival.point as [number,number]);assert.equal(n?.road.id,site.arrival.roadId);assert.ok(n&&n.d<.001);assert.equal(roadAllows(n!.road,'motorcar').allowed,true);});
test('actual berth admits full boat hull and dock admits full walking body',()=>{hint={id:null,height:site.dock.land.height};assert.ok(walk.clear(site.dock.land.x,site.dock.land.z),'landing obstructed');assert.ok(Math.abs(floor(site.dock.land.x,site.dock.land.z).height-site.dock.land.height)<.05);const boat=new LeisureBoat(site.dock,(x,z,h)=>water.clear(x,z,h));assert.equal(boat.board(site.dock.land,p=>walk.clear(p.x,p.z)),'ok');for(let i=0;i<240;i++)boat.step(new Set(['KeyW']),.05);assert.ok(boat.distance>25,'boat must leave actual berth without clipping pier/shore');assert.equal(boat.disembark(()=>true),null,'cannot disembark on lake');});
test('full source walking route passes eight chained actual-world checks',()=>{
 const root=fileURLToPath(new URL('../artifacts/test-route-evidence/',import.meta.url));
 mkdirSync(root,{recursive:true});
 const directory=mkdtempSync(join(root,'run-'));
 const runner=fileURLToPath(new URL('./leisure-route-walk.ts',import.meta.url));
 const hash=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
 let prior:Buffer|null=null,last=0;
 for(let section=0;section<8;section++){
  const result=spawnSync(process.execPath,['--experimental-transform-types',runner,String(section),directory],{encoding:'utf8',timeout:10_000});
  assert.ifError(result.error);
  assert.equal(result.status,0,`Route section ${section}\n${result.stdout}${result.stderr}`);
  const raw=readFileSync(join(directory,`route-section-${section}.json`));
  const record=JSON.parse(raw.toString());
  assert.equal(record.section,section);
  assert.equal(record.count,8);
  assert.equal(record.from,last+1);
  for(const [name,sha] of Object.entries(record.inputs))assert.equal(hash(readFileSync(new URL(name,import.meta.url))),sha,name);
  assert.equal(record.priorHash,prior?hash(prior):null);
  last=record.to;
  prior=raw;
  if(section===7){
   assert.equal(last,record.total);
   assert.ok(record.visited>1000);
  }
 }
 rmSync(directory,{recursive:true});
});
test('fishing and both people stand on supported dry land',()=>{for(const key of ['fishing','keeper','volunteer']){const p=site[key];hint={id:null,height:p.height};assert.ok(walk.clear(p.x,p.z),key);assert.ok(Math.abs(floor(p.x,p.z).height-p.height)<.1,key+' height');assert.equal(water.at(p.x,p.z),null,key+' water');}});
test('source footpaths and game pier allow walking but reject motor vehicles on that deck',()=>{const p=site.dock.land;assert.equal(surfaces.restrictedSourceAt(p.x,p.z,p.height,'foot'),null);assert.equal(surfaces.restrictedSourceAt(p.x,p.z,p.height,'motorcar'),'leisure:marina-deck');assert.equal(surfaces.restrictedSourceAt(p.x,p.z,p.height,'bicycle'),'leisure:marina-deck');});
test('water volume does not collapse an above-water boat camera',()=>{const p=site.dock.berth,s=Math.sin(p.yaw),c=Math.cos(p.yaw);assert.equal(water.volumeBlocked(p.x+s*20,p.z+c*20,p.height+3,.3),false);});
