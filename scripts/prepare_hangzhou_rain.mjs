/** Source-bound Hangzhou rain candidate. No public assets or fallback writes. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {generateRainPuddleLayout,rainPoolOutline,RAIN_LAYOUT_VERSION,RAIN_PROFILE_COUNT} from '../src/city-rain-puddles.ts';
import {CityRoadLevels} from '../src/city-road-levels.ts';
import {mountainHeightAt} from '../src/city-mountains.ts';
const [root,collisionFile,out]=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!root||!collisionFile||!out||fs.existsSync(out)||!path.resolve(out).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep))throw Error('Inputs and fresh Hangzhou candidate required');
const read=p=>JSON.parse(fs.readFileSync(p)),city=read(path.join(root,'city.json')),detail=read(collisionFile),manifest=read(path.join(root,'geography/manifest.json'));
if(city.meta.cityId!=='hangzhou'||detail.cityId!=='hangzhou')throw Error('Wrong city');
const roadFile=path.join(root,'geography',manifest.roadLevelsFile),terrainFile=path.join(root,'geography',manifest.terrainFile),source=read(roadFile),b=fs.readFileSync(terrainFile);
const heights=new Float32Array(b.buffer.slice(b.byteOffset,b.byteOffset+b.length)),levels=new CityRoadLevels(source.roads,(x,z)=>mountainHeightAt(heights,manifest.grid,x,z),manifest.roadTerrainTransitionGame);
city.buildings.push(...detail.collisionFootprints.map(p=>({...p,height:p.maxY-p.minY,style:'landmark-detail'})));
city.water=city.water.filter(w=>w.renderSurface!==false).flatMap(w=>(w.renderRings??[w.rings]).map(rings=>({...w,rings})));
const start=performance.now(),layout=generateRainPuddleLayout(city,(x,z)=>levels.groundAt(x,z));
const fields=['x','z','dx','dz','length','width','lateral','roadWidth','seed','alpha'],precision=[2,2,6,6,2,2,2,2,0,3];
let roundedReliefRejected=0;
layout.pools=layout.pools.filter(p=>{
 for(let i=0;i<fields.length;i++)p[fields[i]]=Number(p[fields[i]].toFixed(precision[i]));
 p.outlines={water:{},apron:{}};const samples=[[p.x,p.z]];
 for(const steps of [12,6,4])for(const [kind,factor] of [['water',1],['apron',1.08]]){
  const outline=rainPoolOutline(p,factor,steps);p.outlines[kind][steps]=outline;samples.push(...outline);
  // Full width cross-sections at every silhouette station, including interiors.
  for(let i=0;i<=steps;i++){const a=outline[i],b=outline[outline.length-1-i];for(let j=1;j<8;j++)samples.push([a[0]+(b[0]-a[0])*j/8,a[1]+(b[1]-a[1])*j/8]);}
 }
 const sampled=samples.map(([x,z])=>levels.groundAt(x,z)),low=Math.min(...sampled),high=Math.max(...sampled);
 if(!sampled.every(Number.isFinite)||high-low>.028){roundedReliefRejected++;return false;}
 p.baseHeightGame=high;p.groundProbeMinGame=low;p.heightProbes=samples.length;p.outline=p.outlines.apron[12];return true;
});
fs.mkdirSync(out);fs.writeFileSync(path.join(out,'unverified-layout.json'),JSON.stringify({...layout,version:RAIN_LAYOUT_VERSION,profileVariants:RAIN_PROFILE_COUNT,cityId:'hangzhou'}));
const sources=[path.join(root,'city.json'),path.join(root,'geography/manifest.json'),roadFile,terrainFile,collisionFile,'src/city-rain-puddles.ts','src/city-road-levels.ts',import.meta.filename];
const generation={kind:'CPU candidate generation; exact containment and current-render checks still required',cityRoot:root,collisionFile,seconds:(performance.now()-start)/1000,roundedReliefRejected,pools:layout.pools.length,stats:layout.stats,sources:Object.fromEntries(sources.map(p=>[path.relative(process.cwd(),p),sha(p)]))};
fs.writeFileSync(path.join(out,'generation.json'),JSON.stringify(generation,null,2)+'\n');console.log(JSON.stringify(generation,null,2));
