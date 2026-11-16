/** Offline selection/placement checks. In-memory Hangzhou profile; workspace stays Shenzhen. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import {registerHooks} from 'node:module';
const generated=new URL('../src/city-profiles.generated.ts',import.meta.url).href;
registerHooks({load(url,context,nextLoad){const result=nextLoad(url,context);if(url!==generated)return result;
 const original=result.source.toString(),source=original.replace(/export const ACTIVE_CITY_ID="shenzhen" as const;/,'export const ACTIVE_CITY_ID="hangzhou" as const;');
 if(source===original)throw new Error('Expected unchanged Shenzhen workspace profile');return {...result,source};}});
const {CITY_CONFIG}=await import('../src/city-config.ts');
if(CITY_CONFIG.id!=='hangzhou')throw new Error('Offline city selection failed');
const {planBambooCorridor}=await import('../src/city-bamboo-corridor.ts');
const {cafeLayout}=await import('../src/city-cafe-layout.ts');
const {CityCollision}=await import('../src/driving.ts');
const [cityFile,cafeFolder,output]=process.argv.slice(2);
if(!output)throw new Error('Usage: check_hangzhou_street.mjs CITY CAFE REPORT');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const data=JSON.parse(fs.readFileSync(cityFile)),manifest=JSON.parse(fs.readFileSync(cafeFolder+'/bamboo-cafe/manifest.json'));
const collision=new CityCollision(data),layout=cafeLayout(manifest.spec,manifest.colliders,0);
const began=performance.now(),plan=planBambooCorridor(data,{reserved:(x,z,r)=>layout.reserved(x,z,r)}),cpuMs=performance.now()-began;
const counts={},failures=[];
for(const [name,list] of Object.entries(plan)){
 if(!Array.isArray(list)||!list.length||typeof list[0].x!=='number')continue;
 counts[name]=list.length;
 for(const p of list){
  if(!Number.isFinite(p.x+p.z)||('yaw' in p&&!Number.isFinite(p.yaw)))failures.push({name,reason:'nonfinite'});
  if(['plinths','doors','panes','pits','lamps','parked'].includes(name)&&layout.reserved(p.x,p.z,.1))failures.push({name,reason:'cafe-reservation',point:[p.x,p.z]});
 }
}
const report={kind:'offline-street-planning-only-in-memory-Hangzhou-profile',citySha256:sha(cityFile),
 profileSourceSha256:sha(new URL('../config/cities/hangzhou.json',import.meta.url)),selectedCity:CITY_CONFIG.id,
 corridor:plan.corridor,roadMetres:plan.roadMetres,roads:plan.roads,counts,planningCpuMs:cpuMs,failures,
 pass:plan.roads>0&&plan.roadMetres>100&&!failures.length,
 pending:['detailed collisions/terrain','geometry visible in real browser','door/walking/vehicle clearance','day/night material performance','current FPS/frame/memory']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,roads:report.roads,roadMetres:report.roadMetres,counts,failures:failures.slice(0,10)},null,2));
if(!report.pass)process.exitCode=1;
