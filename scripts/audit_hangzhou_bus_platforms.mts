/** Small sequential batches of real GLB ground and the actual bus model.
 * This is a physical diagnostic, not permission to publish a bus service.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
import {solveAxleSupport,inspectPhysicalBody} from '../artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4/bus-contact.mjs';
import {busBoardingPoint,busWalkerClear} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-bus-vehicle.ts';
import {selectBusGroundHit,type BusSurfaceHit} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-bus-ground.ts';
const root=path.resolve(import.meta.dirname,'..'),dir=path.resolve(root,process.argv[2]),batch=Number(process.argv[3]);
assert(dir.startsWith(path.resolve(root,'artifacts/cities/hangzhou')+'/')&&Number.isInteger(batch)&&batch>=0);
const revision=process.argv[4]??'';assert(!revision||/^[a-z0-9-]+$/.test(revision));
const target=path.join(dir,`platform-ground-batch-${batch}${revision?'-'+revision:''}.json`);assert(!fs.existsSync(target));
const hashes:Record<string,string>={},sha=(raw:Buffer)=>crypto.createHash('sha256').update(raw).digest('hex');
function read(p:string){const raw=fs.readFileSync(p);hashes[path.relative(root,p)]=sha(raw);return JSON.parse(raw.toString());}
for(const source of [import.meta.filename,...['city-bus-vehicle.ts','city-bus-ground.ts'].map(n=>path.join(root,'artifacts/cities/hangzhou/city-leisure-v15/src',n)),...['bus-contact.mjs','contact-frame.mjs','bus-mesh.mjs'].map(n=>path.join(root,'artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4',n))])hashes[path.relative(root,source)]=sha(fs.readFileSync(source));
const catalog=read(path.join(dir,'source-service-catalog.json')),model=read(path.join(root,'artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4/generated-bus-mesh-v4.json'));
const sourceGround=process.argv.includes('--source-ground'),prepared=sourceGround?read(path.join(root,'artifacts/cities/hangzhou/bus-route-7-v1/prepared-inputs-v1.json')):null;
if(prepared){
 const depot=read(path.join(root,'artifacts/cities/hangzhou/bus-depot-way-v1/source-v1/candidate.json'));
 assert.equal(depot.source.sha256,catalog.source.sha256);assert.equal(prepared.source.sha256,catalog.source.sha256);
 assert(!prepared.roads.some((road:any)=>road.id===depot.road.id));
 // Same source-only depot correction already used by the ordered graph replay.
 // This adds identity/level context, not its pending replacement road geometry.
 prepared.roads.push(depot.road);prepared.roadLevels.push(depot.roadLevel);
}
const unique=new Map<string,any>();for(const r of catalog.routes)for(const stop of r.stops){
 assert(stop.selection);
 // A terminal can reuse one OSM stop in opposite route contexts. Preserve even
 // small incoming/outgoing heading differences; chain indices are per relation.
 const poseKey=sha(Buffer.from(JSON.stringify([stop.platformGame,stop.selection.roadPointGame,stop.selection.roadYaw]))).slice(0,12);
 const id=stop.sourcePlatformId+'@'+stop.selection.sourceStopId+'#'+poseKey;
 if(!unique.has(id))unique.set(id,stop);
}
const all=[...unique.entries()].sort(([a],[b])=>a.localeCompare(b)),selected=all.slice(batch*4,batch*4+4);assert(selected.length,'No stops in this batch');
const records=selected.map(([id,s])=>{const p=s.selection.roadPointGame,q=s.platformGame;return {id,source:s,bounds:[Math.min(p[0],q[0])-8,Math.min(p[1],q[1])-8,Math.max(p[0],q[0])+8,Math.max(p[1],q[1])+8],triangles:[] as any[]};});
const intersects=(a:number[],b:number[])=>a[0]<=b[2]&&a[2]>=b[0]&&a[1]<=b[3]&&a[3]>=b[1];
await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const loaded=[];
for(const role of ['terrain','roads']){
 const folder=path.join(root,'artifacts/cities/hangzhou/stream-mesh-v1',role),manifest=read(path.join(folder,'manifest.json'));
 for(const tile of manifest.tiles){
  const box=[tile.bounds.min[0],tile.bounds.min[2],tile.bounds.max[0],tile.bounds.max[2]];
  const targets=records.filter(r=>intersects(r.bounds,box));if(!targets.length)continue;
  const file=path.join(folder,tile.file),raw=fs.readFileSync(file);assert.equal(sha(raw),tile.sha256);hashes[path.relative(root,file)]=tile.sha256;loaded.push(tile.id);
  const doc=await io.read(file);
  for(const node of doc.getRoot().listNodes()){
   if(!node.getMesh()||node.getName().startsWith('terrain_water'))continue;
   const m=node.getWorldMatrix(),transform=(p:number[])=>[m[0]*p[0]+m[4]*p[1]+m[8]*p[2]+m[12],m[1]*p[0]+m[5]*p[1]+m[9]*p[2]+m[13],-(m[2]*p[0]+m[6]*p[1]+m[10]*p[2]+m[14])];
   for(const primitive of node.getMesh()!.listPrimitives()){
    assert.equal(primitive.getMode(),4);const p=primitive.getAttribute('POSITION')!,ix=primitive.getIndices()!.getArray()!;
    for(let i=0;i<ix.length;i+=3){
     const vertices=[0,1,2].map(k=>transform(p.getElement(ix[i+k],[]))),xs=vertices.map(v=>v[0]),zs=vertices.map(v=>v[2]),b=[Math.min(...xs),Math.min(...zs),Math.max(...xs),Math.max(...zs)];
     for(const r of targets)if(intersects(r.bounds,b))r.triangles.push({vertices,tile:tile.id,nodeName:node.getName(),sourceTriangle:i/3,role,bounds:b});
    }
   }
  }
 }
}
const results=records.map(r=>{
 const failures:string[]=[],ambiguities:any[]=[];
 let sourceLayerBinding:{sourceRoadId:string;sourceStopId:string;tier:number}|null=null;
 if(sourceGround){
  const route=catalog.routes.find((route:any)=>route.stops.includes(r.source)),i=r.source.selection.chainIndex,edge=route.chain.edges[i]??route.chain.edges[i-1];
  const roads=prepared.roads.filter((road:any)=>road.sourceId===edge.sourceWayId&&road.nodeIds.map(String).includes(r.source.selection.sourceStopId.split('/')[1]));
  const levels=prepared.roadLevels.filter((road:any)=>roads.some((r:any)=>r.id===road.id));
  if(roads.length===1&&levels.length===1&&levels[0].tier===0)sourceLayerBinding={sourceRoadId:roads[0].id,sourceStopId:r.source.selection.sourceStopId,tier:levels[0].tier};
  else failures.push('source-ground-road-binding-unresolved');
 }
 function top(x:number,z:number){
  const hits:BusSurfaceHit[]=[];
  for(const t of r.triangles){if(x<t.bounds[0]-1e-7||x>t.bounds[2]+1e-7||z<t.bounds[1]-1e-7||z>t.bounds[3]+1e-7)continue;const [a,b,c]=t.vertices,d=(b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]);if(Math.abs(d)<1e-10)continue;
   const u=((x-a[0])*(c[2]-a[2])-(z-a[2])*(c[0]-a[0]))/d,v=((b[0]-a[0])*(z-a[2])-(b[2]-a[2])*(x-a[0]))/d;
   if(u>=-1e-8&&v>=-1e-8&&u+v<=1+1e-8)hits.push({height:a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]),role:t.role,tile:t.tile,node:t.nodeName,triangle:t.sourceTriangle});
  }
  if(!hits.length)return null;hits.sort((a,b)=>b.height-a.height);
  if(sourceGround)return selectBusGroundHit(hits,sourceLayerBinding);
  // Never choose an overpass/underpass just because it is highest.
  if(hits[0].height-hits.at(-1)!.height>.4){if(ambiguities.length<12)ambiguities.push({x,z,range:[hits.at(-1)!.height,hits[0].height],hits});return null;}
  return hits[0];
 }
 const s=r.source,pose={x:s.selection.roadPointGame[0],z:s.selection.roadPointGame[1],yaw:s.selection.roadYaw};
 const support=solveAxleSupport(model,pose,top);if(support.status!=='generated-model-contacts-within-tolerance')failures.push(support.status);
 const frame=support.frame,platformHit=top(...s.platformGame as [number,number]);
 if(!platformHit)failures.push('platform-missing-or-ambiguous-ground');
 const door=frame?busBoardingPoint(model,frame,(x,z)=>top(x,z)?.height??null):null;if(!door)failures.push('no-safe-actual-door-anchor');
 const doorDistance=door?Math.hypot(door.x-s.platformGame[0],door.z-s.platformGame[1]):null;
 if(doorDistance!==null&&doorDistance>4)failures.push('platform-to-door-exceeds-existing-4g-limit');
 const body=frame?inspectPhysicalBody(model,frame,r.triangles):null;if(body&&(body.bodyIntersectionCount||body.tirePenetrationCount))failures.push('actual-ground-intersects-generated-bus');
 let pathSamples=0,maxStep=0,walkerBusHits=0,missingWalkSamples=0;
 if(door&&platformHit&&frame){
  const count=Math.max(1,Math.ceil(doorDistance!/.1));let previous=platformHit.height;
  for(let i=0;i<=count;i++){const x=s.platformGame[0]+(door.x-s.platformGame[0])*i/count,z=s.platformGame[1]+(door.z-s.platformGame[1])*i/count,h=top(x,z);if(!h){missingWalkSamples++;continue;}maxStep=Math.max(maxStep,Math.abs(h.height-previous));previous=h.height;
   if(!busWalkerClear(model,frame,{x,z,height:h.height,yaw:pose.yaw}))walkerBusHits++;
   for(let j=0;j<9;j++){const a=j*Math.PI/4,dx=j===8?0:Math.cos(a)*.23,dz=j===8?0:Math.sin(a)*.23,q=top(x+dx,z+dz);pathSamples++;if(!q)missingWalkSamples++;else maxStep=Math.max(maxStep,Math.abs(q.height-h.height));}
  }
  if(maxStep>.48)failures.push('walking-step-exceeds-original-0.48g');if(walkerBusHits)failures.push('upright-walker-intersects-bus-or-door-sweep');if(missingWalkSamples)failures.push('walking-footprint-missing-ground');
 }
 return {id:r.id,name:s.name,sourcePlatformId:s.sourcePlatformId,sourceStopId:s.selection.sourceStopId,sourceLayerBinding,sourceStoppingPose:pose,sourcePlatformGame:s.platformGame,triangles:r.triangles.length,groundTriangles:process.argv.includes('--export-ground')?r.triangles:undefined,support,platformHit,door,doorDistance,body,pathSamples,maxWalkingStep:maxStep,walkerBusHits,missingWalkSamples,ambiguities,failures,groundAndDoorDiagnosticPass:!failures.length,
  acceptance:{stationBuildingsAndFurniture:false,publicWalkingAccess:false,roadLayerOwnership:false,fullRouteSweep:false,boarding:false,browser:false},note:'Actual rendered ground and generated model only. This does not invent a kerb, move the source stop, extend the depot road or authorize public walking in a private depot.'};
});
fs.writeFileSync(target,JSON.stringify({schemaVersion:1,batch,totalBatches:Math.ceil(all.length/4),uniqueStops:all.length,inputs:hashes,loadedTiles:loaded,coordinateSpace:'Babylon game XYZ: original node TRS plus original root Z mirror, no additional scale',results,installable:false},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({batch,totalBatches:Math.ceil(all.length/4),loadedTiles:loaded.length,results:results.map(r=>({id:r.id,name:r.name,triangles:r.triangles,pass:r.groundAndDoorDiagnosticPass,failures:r.failures})),installable:false}));
