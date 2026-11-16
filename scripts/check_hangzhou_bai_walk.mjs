/** CPU route replay through the shipped DrivingWorld and CityWalk methods.
 * Debug placement only initializes the first public endpoint; movement is the
 * original step(keys,dt). This is explicitly not a browser or prop/GPU test.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';
import {registerHooks} from 'node:module';
import {ImportMeshAsync,MeshoptCompression,NullEngine,Quaternion,Ray,Scene,Vector3} from '@babylonjs/core';
import '@babylonjs/loaders/glTF/index.js';import {MeshoptDecoder} from 'meshoptimizer';
const [stageArg,routeFile,output]=process.argv.slice(2),stage=path.resolve(stageArg),publicRoot=path.join(stage,'public'),root=path.join(publicRoot,'cities/hangzhou');
if(fs.existsSync(output))throw Error('Preserve previous reports');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const fromStage=name=>import(pathToFileURL(path.join(stage,'src',name)).href);
// Vite accepts this installed package directory; Node ESM needs its entry.
registerHooks({resolve(specifier,context,next){return next(specifier==='@babylonjs/loaders/glTF'?'@babylonjs/loaders/glTF/index.js':specifier,context);},
 load(url,context,next){if(url.endsWith('.css'))return {format:'module',source:'export {};',shortCircuit:true};const result=next(url,context);
  if(url.endsWith('.ts')&&String(result.source).includes('import.meta.env'))return {...result,source:'import.meta.env = {};\n'+String(result.source)};return result;}});
const {loadCityGeography}=await fromStage('city-geography.ts'),{loadLandmarkDetails}=await fromStage('landmark-details.ts');
const {DrivingWorld}=await fromStage('city-world.ts'),{CityWalk,WALK_RADIUS}=await fromStage('city-walk.ts'),{CityCollision}=await fromStage('driving.ts');
const source=read(routeFile),route=source.paths.flatMap((p,i)=>i?p.points.slice(1):p.points),city=read(path.join(root,'city.json'));
const fetchBefore=globalThis.fetch;let geography;
try{globalThis.fetch=async url=>new Response(fs.readFileSync(path.join(publicRoot,String(url))));geography=await loadCityGeography(city);await loadLandmarkDetails(city,{cityId:'hangzhou',manifestSha256:geography.manifestSha256,heightAt:geography.heightAt});}
finally{globalThis.fetch=fetchBefore;}
const collision=new CityCollision(city,(id,x,z,y)=>geography.levels.heightForSourceRoad(id,x,z,y));
await MeshoptDecoder.ready;const prior=MeshoptCompression._Default;
MeshoptCompression._Default={decodeGltfBufferAsync:async(bytes,count,stride,mode,filter)=>{const out=new Uint8Array(count*stride);MeshoptDecoder.decodeGltfBuffer(out,count,stride,bytes,mode,filter);return out;}};
const engine=new NullEngine(),scene=new Scene(engine),results=[];
try{
 const loaded=await ImportMeshAsync(fs.readFileSync(path.join(root,'landmark-detail.glb')),scene,{pluginExtension:'.glb',pluginOptions:{gltf:{skipMaterials:true}}});loaded.meshes[0].rotationQuaternion=Quaternion.Identity();loaded.meshes.forEach(m=>m.computeWorldMatrix(true));
 const decks=new Set(loaded.meshes.filter(m=>/^detail_(?:west-lake-causeways|broken-bridge)_(?:asphalt|pavement|park)$/.test(m.name)));
 const bases=new Set();
 if(process.env.BAI_BASE_CONTEXT){const dir=process.env.BAI_BASE_CONTEXT,proof=read(path.join(dir,'actual-context-verification.json'));if(!proof.pass)throw Error('Unverified actual base context');
  for(const r of proof.results){const file=path.join(dir,'context-'+r.file);if(sha(file)!==r.contextSha256||sha(path.join(root,r.file))!==r.sha256)throw Error('Changed base context');
   const loaded=await ImportMeshAsync(fs.readFileSync(file),scene,{pluginExtension:'.glb',pluginOptions:{gltf:{skipMaterials:true}}});loaded.meshes[0].rotationQuaternion=Quaternion.Identity();loaded.meshes.forEach(m=>{m.computeWorldMatrix(true);if(m.getTotalVertices())bases.add(m);});}}
 for(const running of (process.env.BAI_CASE==='run'?[true]:[false,true]))for(const dt of (process.env.BAI_CASE==='run'?[.05]:[.05,1/60])){
  const world=Object.create(DrivingWorld.prototype);Object.assign(world,{geography,collision,groundHeight:geography.heightAt,bambooCafe:null});
  const walk=new CityWalk((x,z)=>world.actorCollision(x,z,true),(x,z)=>world.walkingSurfaceHeight(x,z));world.walk=walk;
  [walk.x,walk.z]=route[0];walk.active=true;
  const sync=()=>{world.walkSiteHint=world.walkingSurface(walk.x,walk.z);const q=geography.levels.sample(walk.x,walk.z,world.walkRoadHint);world.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};};sync();
  const keys=new Set(running?['KeyW','ShiftLeft']:['KeyW']);const trace={running,dt,initialClear:walk.clear(walk.x,walk.z),legs:[],maxDeckGap:0,missingDeck:0,supportSamples:0,fullFootprintSamples:0,examples:[]};
  let failed=false,lastProbe=-Infinity;
  for(const [direction,points] of [['forward',route],['return',[...route].reverse()]]){
   let steps=0,stuck=0;const failures=[];
   for(let i=1;i<points.length&&!failed;i++){
    const target=points[i];let remaining=Math.hypot(target[0]-walk.x,target[1]-walk.z),budget=Math.ceil(remaining/(running?4.2:1.6)/dt)+100;
    while(remaining>.015&&budget-->0){
     walk.yaw=Math.atan2(target[0]-walk.x,target[1]-walk.z);const before=[walk.x,walk.z],stepDt=Math.min(dt,remaining/(running?4.2:1.6));walk.step(keys,stepDt);sync();steps++;
     const moved=Math.hypot(walk.x-before[0],walk.z-before[1]);stuck=moved<1e-7?stuck+1:0;
     if(stuck>3){const nearby=[];for(let k=-1;k<8;k++){const x=walk.x+(k<0?0:Math.cos(k*Math.PI/4)*WALK_RADIUS),z=walk.z+(k<0?0:Math.sin(k*Math.PI/4)*WALK_RADIUS);nearby.push({x,z,surface:world.walkingSurface(x,z),blocked:world.actorCollision(x,z,true)});}failures.push({kind:'actor-blocked',segment:i,x:walk.x,z:walk.z,height:world.walkingSurfaceHeight(walk.x,walk.z),site:world.walkSiteHint,nearby});failed=true;break;}
     if(walk.distance-lastProbe>=1||remaining<.02){
      lastProbe=walk.distance;
      for(let k=-1;k<8;k++){
       const x=walk.x+(k<0?0:Math.cos(k*Math.PI/4)*WALK_RADIUS),z=walk.z+(k<0?0:Math.sin(k*Math.PI/4)*WALK_RADIUS);
       const hit=scene.pickWithRay(new Ray(new Vector3(x,30,z),new Vector3(0,-1,0),40),m=>decks.has(m)||bases.has(m));
       const floor=world.walkingSurfaceHeight(x,z);trace.supportSamples++;if(k>=0)trace.fullFootprintSamples++;
       const tolerance=hit?.pickedMesh&&bases.has(hit.pickedMesh)?.04:.001;
       if(!hit?.pickedPoint)trace.missingDeck++;else if(tolerance===.001)trace.maxDeckGap=Math.max(trace.maxDeckGap,Math.abs(hit.pickedPoint.y-floor));
       if((!hit?.pickedPoint||Math.abs(hit.pickedPoint.y-floor)>tolerance)&&trace.examples.length<12)trace.examples.push({x,z,floor,mesh:hit?.pickedMesh?.name,visualY:hit?.pickedPoint?.y,tolerance,site:world.walkSiteHint});
      }
     }
     remaining=Math.hypot(target[0]-walk.x,target[1]-walk.z);
    }
    if(budget<=0){failures.push({kind:'movement-timeout',segment:i,remaining});failed=true;}
    // Stopping must not climb through a deck or mutate the source floor.
    const y=world.walkingSurfaceHeight(walk.x,walk.z);for(let j=0;j<12;j++){walk.step(new Set(),dt);sync();}
    if(Math.abs(world.walkingSurfaceHeight(walk.x,walk.z)-y)>.001){failures.push({kind:'stationary-floor-drift',segment:i});failed=true;}
   }
   trace.legs.push({direction,steps,failures,position:[walk.x,walk.z],walkDistance:walk.distance});if(failed)break;
  }
  trace.pass=trace.initialClear&&!failed&&trace.missingDeck===0&&trace.maxDeckGap<=.001&&trace.examples.length===0;results.push(trace);
 }
}finally{scene.dispose();engine.dispose();MeshoptCompression._Default=prior;}
const report={kind:'actual GLB / DrivingWorld walking surface / CityWalk full-footprint replay',stage,
 inputs:Object.fromEntries([routeFile,...['city.json','landmark-detail.glb','landmark-detail.json','geography/manifest.json','geography/site-surfaces.json'].map(p=>path.join(root,p)),...['city-world.ts','city-walk.ts','driving.ts','city-site-surfaces.ts'].map(p=>path.join(stage,'src',p))].map(p=>[p,sha(p)])),
 scope:'debug-initialized endpoint then original walk/run, both directions, 20/60Hz, full 0.23g radius; dynamic parked vehicles/furniture/canopy and browser visual/performance not tested',results,pass:results.every(r=>r.pass)};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,results},null,2));if(!report.pass)process.exitCode=1;
