/** Sample the shipped bridge deck and current walking support on the source path. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {ImportMeshAsync,MeshoptCompression,NullEngine,Quaternion,Ray,Scene,Vector3} from '@babylonjs/core';
import '@babylonjs/loaders/glTF/index.js';
import {MeshoptDecoder} from 'meshoptimizer';

const [stageArg,output]=process.argv.slice(2),stage=path.resolve(stageArg),root=path.join(stage,'dist/cities/hangzhou');
const read=file=>JSON.parse(fs.readFileSync(file));
const fromStage=name=>import(pathToFileURL(path.join(stage,'src',name)).href);
const {projectCityWgs84}=await fromStage('city-config.ts');
const {loadCityGeography}=await fromStage('city-geography.ts');
const {loadLandmarkDetails}=await fromStage('landmark-details.ts');
const {CityCollision}=await fromStage('driving.ts');
const originalFetch=globalThis.fetch;
let city,geography;
try{
 globalThis.fetch=async url=>new Response(fs.readFileSync(path.join(stage,'dist',String(url))));
 city=read(path.join(root,'city.json'));geography=await loadCityGeography(city);
 await loadLandmarkDetails(city,{cityId:'hangzhou',manifestSha256:geography.manifestSha256,heightAt:geography.heightAt});
}finally{globalThis.fetch=originalFetch;}
const collision=new CityCollision(city,(id,x,z,y)=>geography.levels.heightForSourceRoad(id,x,z,y));
const specs=read('docs/hangzhou/research/core/west-lake-causeways-round2/spec.json');
const paths=specs.paths.filter(p=>p.causeway==='bai').map(p=>({id:p.sourceId,name:p.label,points:p.coordinatesWGS84.map(p=>projectCityWgs84(...p))}));
const broken=read('docs/hangzhou/research/core/broken-bridge-round2/osm-measurements.json');
const brokenRoad=city.roads.find(r=>r.sourceId==='way/28538289');
if(brokenRoad)paths.push({id:brokenRoad.sourceId,name:'断桥',points:brokenRoad.points});

await MeshoptDecoder.ready;
const priorDecoder=MeshoptCompression._Default;
MeshoptCompression._Default={decodeGltfBufferAsync:async(bytes,count,stride,mode,filter)=>{
 const out=new Uint8Array(count*stride);MeshoptDecoder.decodeGltfBuffer(out,count,stride,bytes,mode,filter);return out;
}};
const engine=new NullEngine(),scene=new Scene(engine),results=[];
try{
 const loaded=await ImportMeshAsync(fs.readFileSync(path.join(root,'landmark-detail.glb')),scene,{pluginExtension:'.glb',pluginOptions:{gltf:{skipMaterials:true}}});
 loaded.meshes[0].rotationQuaternion=Quaternion.Identity();
 for(const mesh of loaded.meshes)mesh.computeWorldMatrix(true);
 const decks=new Set(loaded.meshes.filter(mesh=>/^detail_(?:west-lake-causeways|broken-bridge)_(?:asphalt|pavement)$/.test(mesh.name)));
 if(!decks.size)throw Error('Missing actual paved landmark meshes');
 for(const route of paths){
  let walkHint,roadHint;
  const samples=[];
  for(let i=1;i<route.points.length;i++){
   const a=route.points[i-1],b=route.points[i],count=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/.5));
   for(let j=0;j<=count;j++){
    if(i>1&&j===0)continue;
    const t=j/count,x=a[0]+(b[0]-a[0])*t,z=a[1]+(b[1]-a[1])*t;
    const ray=new Ray(new Vector3(x,160,z),new Vector3(0,-1,0),220);
    const deck=scene.pickWithRay(ray,m=>decks.has(m))?.pickedPoint?.y??null;
    const sample=geography.levels.sample(x,z,roadHint),nearest=collision.nearest(x,z,sample.height);
    const edge=nearest?nearest.d-nearest.road.width/2:Infinity;
    const ground=sample.height+(edge<=0?.105:edge<1.2?.065:0);
    walkHint=geography.siteSurfaces?.walkAt(x,z,ground,walkHint)??{height:ground,id:null};
    roadHint={height:sample.height,roadId:sample.roadId??undefined,groundOnly:sample.roadId===null};
    const blocked=collision.blocked(x,z,walkHint.height,1.6,walkHint.id!==null);
    samples.push({x,z,deck,walkY:walkHint.height,surfaceId:walkHint.id,blocked,deckGap:deck===null?null:Math.abs(deck-walkHint.height)});
   }
  }
  results.push({id:route.id,name:route.name,samples:samples.length,missingDeck:samples.filter(s=>s.deck===null).length,blocked:samples.filter(s=>s.blocked).length,overHalfMetre:samples.filter(s=>s.deckGap!==null&&s.deckGap>.5).length,maxDeckGap:Math.max(0,...samples.map(s=>s.deckGap??0)),examples:samples.filter(s=>s.blocked||s.deckGap!==null&&s.deckGap>.5).slice(0,4)});
 }
}finally{scene.dispose();engine.dispose();MeshoptCompression._Default=priorDecoder;}
const report={kind:'actual preview paved meshes vs source path runtime walking height, CPU',scope:'centre line only; paved hits exclude ordinary roads/land and do not certify browser visuals or actor width',brokenBridgeInVehicleGraph:!!brokenRoad,referenceSource:broken.coordinateReference??'pinned source contract',results,pass:results.filter(r=>r.name==='锦带桥'||r.name==='断桥').every(r=>r.missingDeck===0&&r.blocked===0&&r.overHalfMetre===0)};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({...report,results:results.map(({examples,...row})=>row)},null,2));
if(!report.pass)process.exitCode=1;
