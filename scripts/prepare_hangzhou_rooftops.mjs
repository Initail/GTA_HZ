/** Isolated Hangzhou rooftop proposals. The original typology and instance
 * sizes are retained; only the authored roof ordinate and courtyard domain
 * differ. Exact GEOS validation must run before plan.json is emitted. */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {planRooftop,ROOFTOP_KINDS,ROOF_FINISHES,ROOF_LOOKUP,encodeRoofLookup,rasterizeRing} from '../src/city-rooftop-plan.ts';
const [prepared,facades,output]=process.argv.slice(2);
if(!prepared||!facades||!output||!path.resolve(output).startsWith(path.resolve('artifacts')+path.sep)||fs.existsSync(output))throw Error('Prepared buildings, facade candidate and fresh artifacts output required');
const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const inputs={};
const bind=f=>(inputs[f]=sha(f),f);
const source=bind(path.join(prepared,'buildings.json')),manifest=JSON.parse(fs.readFileSync(bind(path.join(prepared,'manifest.json'))));
assert.equal(manifest.cityId,'hangzhou');assert.equal(inputs[source],manifest.buildingsSha256);
const buildings=JSON.parse(fs.readFileSync(source));
const floors=JSON.parse(fs.readFileSync(bind(path.join(facades,'building-floors.json'))));
const floorManifest=JSON.parse(fs.readFileSync(bind(path.join(facades,'manifest.json'))));
assert.equal(inputs[path.join(facades,'building-floors.json')],floorManifest.floorRecordsSha256);
const floorMap=new Map();for(const b of floors){const key=b.id+'|'+b.baseYGame+'|'+b.mainRoofYGame;floorMap.set(key,b);}
assert.equal(floors.length,buildings.length);
// Compare parsed source values: Python/JS serialize 1.0 and -0 differently.
// The exact source files remain independently SHA-bound in the report.
const floorSource=Object.keys(floorManifest.inputs).find(p=>p.endsWith('/buildings.json'));
assert.ok(floorSource);assert.equal(sha(bind(floorSource)),floorManifest.inputs[floorSource]);
assert.deepEqual(buildings,JSON.parse(fs.readFileSync(floorSource)));
const protoFile=bind('public/city/rooftops/props.glb');bind('public/city/rooftops/props-manifest.json');
bind('src/city-rooftop-plan.ts');bind('scripts/prepare_hangzhou_rooftops.mjs');
// Match CityRooftops.init: detached mesh positions get the existing Z mirror.
// Read the actual prototype support hulls rather than nominal planner sizes.
const prototypes=Object.fromEntries(ROOFTOP_KINDS.map(k=>[k.id,{vertices:[]}]));
const doc=await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(protoFile),identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
for(const node of doc.getRoot().listNodes()){
 if(!node.getMesh())continue;
 assert.deepEqual(node.getMatrix(),identity,'Runtime rooftop prototype must have identity local transform');
 const kind=node.getName().match(/^prop_([a-z-]+)_([a-z]+)$/)?.[1];assert.ok(prototypes[kind],node.getName());
 for(const p of node.getMesh().listPrimitives()){
  const a=p.getAttribute('POSITION'),v=[];
  for(let i=0;i<a.getCount();i++){a.getElement(i,v);prototypes[kind].vertices.push([v[0],-v[2],v[1]]);}
 }
}
for(const p of Object.values(prototypes))assert.ok(p.vertices.length);
const proposals=[],finishes=[],started=performance.now();let minX=Infinity,minZ=Infinity,maxX=-Infinity,maxZ=-Infinity;
for(let i=0;i<buildings.length;i++){
 const b=buildings[i],floor=floorMap.get(b.id+'|'+b.baseYGame+'|'+b.maxY);
 assert.ok(floor,'Missing exact floor '+b.id);assert.equal(floor.mainRoofYGame,b.maxY);
 assert.ok(b.style!=='landmark-detail');
 const plan=planRooftop(b,{roofY:floor.mainRoofYGame,holes:b.rings.slice(1)});
 finishes.push({buildingIndex:i,finish:plan.finish,tint:plan.tint});
 for(const [kind,...instance] of plan.props)proposals.push({buildingIndex:i,kind:ROOFTOP_KINDS[kind].id,instance});
 for(const [x,z] of b.rings[0]){minX=Math.min(minX,x);minZ=Math.min(minZ,z);maxX=Math.max(maxX,x);maxZ=Math.max(maxZ,z);}
 if(i%5000===0)console.log('roof proposals',i,'/',buildings.length);
}
const {cell,pad}=ROOF_LOOKUP;minX=Math.floor(minX)-pad;minZ=Math.floor(minZ)-pad;maxX=Math.ceil(maxX)+pad;maxZ=Math.ceil(maxZ)+pad;
const width=Math.ceil((maxX-minX)/cell),height=Math.ceil((maxZ-minZ)/cell),grid=new Uint8Array(width*height);
for(const f of [...finishes].sort((a,b)=>buildings[a.buildingIndex].maxY-buildings[b.buildingIndex].maxY)){
 const b=buildings[f.buildingIndex];rasterizeRing(b.rings[0],encodeRoofLookup(f.finish,f.tint),grid,width,height,minX,minZ,cell,b.rings.slice(1));
}
fs.mkdirSync(output,{recursive:true});
fs.writeFileSync(path.join(output,'building-lookup.png'),pngGrey(grid,width,height));
const data={version:1,cityId:'hangzhou',inputs,source,prototypes,proposals,finishes,
 lookup:{file:'building-lookup.png',cell,minX,minZ,width,height,encoding:'0 = none; 1+finish*16+tint',finishes:ROOF_FINISHES.map(f=>f.id)},
 placement:{horizontal:'original 0.76 inset, courtyard holes excluded',vertical:'actual mainRoofYGame; no fictional raised crown',units:'existing game metres; no second scale',basis:'artistic typology; not surveyed equipment'},
 seconds:(performance.now()-started)/1000,status:'unverified proposals; exact support and neighbouring structure checks required'};
fs.writeFileSync(path.join(output,'unverified-plan.json'),JSON.stringify(data));
console.log(JSON.stringify({buildings:buildings.length,proposals:proposals.length,lookup:data.lookup,seconds:data.seconds}));

function pngGrey(data,w,h){
 const raw=Buffer.alloc((w+1)*h);for(let y=0;y<h;y++)raw.set(data.subarray(y*w,(y+1)*w),y*(w+1)+1);
 const chunk=(type,body)=>{const length=Buffer.alloc(4);length.writeUInt32BE(body.length);const bytes=Buffer.concat([Buffer.from(type),body]),crc=Buffer.alloc(4);let c=0xffffffff;
  for(const value of bytes){let n=(c^value)&255;for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;c=(c>>>8)^n;}crc.writeUInt32BE((c^0xffffffff)>>>0);return Buffer.concat([length,bytes,crc]);};
 const header=Buffer.alloc(13);header.writeUInt32BE(w,0);header.writeUInt32BE(h,4);header[8]=8;
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
