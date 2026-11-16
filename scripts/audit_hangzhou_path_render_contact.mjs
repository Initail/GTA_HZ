/** Independent actual rendered triangle intersections; never infer visible
 * contact solely from a mathematical terrain sampler. Writes fresh reports.
 */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
const [folder,output,meshOutput]=process.argv.slice(2);assert(folder&&output&&!fs.existsSync(output));if(meshOutput)assert(!fs.existsSync(meshOutput));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p,'utf8')),data=read(path.join(folder,'scene-data.json')),files=read(path.join(folder,'asset-files.json'));
const surface=data.sources.find(r=>r.file.endsWith('/site-surfaces-candidate.json'));assert(surface);const surfaceBytes=fs.readFileSync(surface.file);assert.equal(hash(surfaceBytes),surface.sha256);assert.deepEqual(JSON.parse(surfaceBytes),data.surfaces);
await MeshoptDecoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const cells=new Map(),triangles=[],size=8,sources=[];
for(const tile of data.streams.filter(t=>t.role==='terrain')){
 const record=files[tile.baseUrl+tile.file],bytes=fs.readFileSync(record.path);assert.equal(hash(bytes),record.sha256);sources.push(record);
 const doc=await io.read(record.path);
 for(const node of doc.getRoot().listNodes()){
  if(!node.getMesh()||node.getName().startsWith('terrain_water'))continue;
  const m=node.getWorldMatrix(),transform=p=>[m[0]*p[0]+m[4]*p[1]+m[8]*p[2]+m[12],-(m[2]*p[0]+m[6]*p[1]+m[10]*p[2]+m[14]),m[1]*p[0]+m[5]*p[1]+m[9]*p[2]+m[13]];
  for(const primitive of node.getMesh().listPrimitives()){
   assert.equal(primitive.getMode(),4);const p=primitive.getAttribute('POSITION'),ix=primitive.getIndices().getArray();
   for(let i=0;i<ix.length;i+=3){const vertices=[0,1,2].map(k=>transform(p.getElement(ix[i+k],[]))),id=triangles.length;
    const [a,b,c]=vertices,det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]);if(Math.abs(det)<1e-10)continue;
    triangles.push({vertices,det,node:node.getName(),tile:tile.id,primitiveTriangle:i/3});
    const xs=vertices.map(v=>v[0]),zs=vertices.map(v=>v[1]);for(let x=Math.floor(Math.min(...xs)/size);x<=Math.floor(Math.max(...xs)/size);x++)for(let z=Math.floor(Math.min(...zs)/size);z<=Math.floor(Math.max(...zs)/size);z++){const key=x+','+z,cell=cells.get(key)??[];cell.push(id);cells.set(key,cell);}
   }
  }
 }
}
function top(x,z){let best=null;
 for(const i of cells.get(Math.floor(x/size)+','+Math.floor(z/size))??[]){const t=triangles[i],[a,b,c]=t.vertices,u=((x-a[0])*(c[1]-a[1])-(z-a[1])*(c[0]-a[0]))/t.det,v=((b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0]))/t.det;
  if(u< -1e-9||v< -1e-9||u+v>1+1e-9)continue;const height=a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]);if(!best||height>best.height)best={height,triangle:i,node:t.node};
 }return best;
}
const checks=[];for(const f of data.surfaces.walkFloors)for(const [index,t] of f.triangles.entries())for(const w of [[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3,1/3,1/3]]){
 const v=[0,1,2].map(k=>w.reduce((s,n,i)=>s+n*t[i][k],0)),hit=top(v[0],v[1]);checks.push({floor:f.id,triangle:index,point:v,renderedGround:hit,clearanceGame:hit?v[2]-hit.height:null});
}
const covered=checks.filter(r=>r.renderedGround),buried=covered.filter(r=>r.clearanceGame<-.001),floating=covered.filter(r=>r.clearanceGame>.03),missing=checks.length-covered.length;
if(meshOutput){
 const ps=data.surfaces.walkFloors.flatMap(f=>f.triangles.flat()),xs=ps.map(p=>p[0]),zs=ps.map(p=>p[1]),bounds=[Math.min(...xs),Math.min(...zs),Math.max(...xs),Math.max(...zs)];
 const selected=triangles.filter(t=>{const xs=t.vertices.map(v=>v[0]),zs=t.vertices.map(v=>v[1]);return Math.min(...xs)<=bounds[2]&&Math.max(...xs)>=bounds[0]&&Math.min(...zs)<=bounds[3]&&Math.max(...zs)>=bounds[1];});
 fs.writeFileSync(meshOutput,JSON.stringify({schemaVersion:1,units:'game east/north/up; scale applied once',sources,bounds,triangles:selected})+'\n');
}
const result={schemaVersion:1,scope:'actual decoded terrain triangles with original node transforms and retained Babylon root Z mirror; original materials and vertices unchanged',surface,sources,triangles:triangles.length,contactSamples:checks.length,
 bounds:{minimumClearanceGame:Math.min(...covered.map(r=>r.clearanceGame)),maximumClearanceGame:Math.max(...covered.map(r=>r.clearanceGame))},buriedSamples:buried.length,floatingSamples:floating.length,missingSamples:missing,
 pass:!buried.length&&!floating.length&&!missing,checks,visibleAcceptance:false};
fs.writeFileSync(output,JSON.stringify(result)+'\n');console.log(JSON.stringify({...result,checks:undefined,sources:undefined}));
// An expected diagnosis failure is retained, but is still a failing contact gate.
if(!result.pass)process.exitCode=1;
