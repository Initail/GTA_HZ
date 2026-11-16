/** Candidate-only counterpart of exclude_base_buildings.mjs.
 * Removes exact source-owned ordinary footprints from base and streamed facades.
 * No source city, served preview or other asset is modified. Collisions, roof
 * props, signs, AO and replacement models must be integrated separately.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
import {createGltfSnapshot} from './hangzhou_gltf_snapshot.mjs';

const [source,contractFile,output]=process.argv.slice(2);
assert(source&&contractFile&&output&&!fs.existsSync(output),'New candidate directory required');
assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const read=p=>JSON.parse(fs.readFileSync(p));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const cityFile=path.join(source,'city.json'),city=read(cityFile),contract=read(contractFile);
assert.equal(city.meta.cityId,'hangzhou');
const ids=new Set(contract.baseBuildingIdsToExclude);
assert(ids.size>0&&ids.size===contract.baseBuildingIdsToExclude.length);
const rows=city.buildings.filter(b=>ids.has(b.id));
assert.deepEqual(new Set(rows.map(b=>b.id)),ids,'Every requested source ID must own an existing ordinary building');
const MARGIN=1.2,TILE=640;
const inRing=(x,z,r)=>{let inside=false;for(let i=0,j=r.length-1;i<r.length;j=i++){
 const a=r[i],b=r[j];if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])inside=!inside;
}return inside;};
const nearRing=(x,z,r,margin)=>r.some((a,i)=>{const b=r[(i+1)%r.length],dx=b[0]-a[0],dz=b[1]-a[1],len=dx*dx+dz*dz;
 const t=Math.max(0,Math.min(1,len?((x-a[0])*dx+(z-a[1])*dz)/len:0));return Math.hypot(x-a[0]-dx*t,z-a[1]-dz*t)<=margin;});
const contains=(x,z,rings,margin)=>((inRing(x,z,rings[0])&&!rings.slice(1).some(r=>inRing(x,z,r)))||rings.some(r=>nearRing(x,z,r,margin)));
const targets=rows.map(b=>{const p=b.rings[0],xs=p.map(p=>p[0]),zs=p.map(p=>p[1]);
 return {...b,box:[Math.min(...xs)-MARGIN,Math.min(...zs)-MARGIN,Math.max(...xs)+MARGIN,Math.max(...zs)+MARGIN]};});
const tiles=new Set(targets.flatMap(b=>{const t=[];for(let x=Math.floor(b.box[0]/TILE);x<=Math.floor(b.box[2]/TILE);x++)for(let z=Math.floor(b.box[1]/TILE);z<=Math.floor(b.box[3]/TILE);z++)t.push(x+'_'+z);return t;}));
const transform=(p,m)=>[m[0]*p[0]+m[4]*p[1]+m[8]*p[2]+m[12],-(m[2]*p[0]+m[6]*p[1]+m[10]*p[2]+m[14]),m[1]*p[0]+m[5]*p[1]+m[9]*p[2]+m[13]];
const near=(p,b,margin=MARGIN)=>p[0]>=b.box[0]&&p[0]<=b.box[2]&&p[1]>=b.box[1]&&p[1]<=b.box[3]&&contains(p[0],p[1],b.rings,margin);
// Neighbours are a negative control: an exclusion buffer must not consume a
// nearby unrelated roof or wall. Ambiguities stop integration, not this report.
const neighbours=city.buildings.filter(b=>{
 if(ids.has(b.id))return false;
 const p=b.rings[0],x0=Math.min(...p.map(p=>p[0])),x1=Math.max(...p.map(p=>p[0])),z0=Math.min(...p.map(p=>p[1])),z1=Math.max(...p.map(p=>p[1]));
 return targets.some(t=>x0<=t.box[2]&&x1>=t.box[0]&&z0<=t.box[3]&&z1>=t.box[1]);
});
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const snapshot=createGltfSnapshot(io),facades=read(path.join(source,'facade-tiles.json'));
// The meshopt index codec may rotate (a,b,c) to (b,c,a). This retains the
// exact oriented triangle; reversal, vertex values and triangle order still
// have to match. Do not mistake codec rotation for geometry deformation.
const directed=s=>({...s,meshes:s.meshes.map(m=>({...m,primitives:m.primitives.map(p=>{
 const indices=[];for(let i=0;i<(p.indices?.length??0);i+=3){const t=p.indices.slice(i,i+3),r=[t,[t[1],t[2],t[0]],[t[2],t[0],t[1]]];r.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);indices.push(...r[0]);}
 return {...p,indices:p.indices?indices:null};
})}))});
const files=['buildings.glb',...facades.tiles.filter(t=>tiles.has(t.id)).map(t=>'facade-tiles/'+t.id+'.glb')];
fs.mkdirSync(output,{recursive:true});
const report={kind:'exact-ID ordinary-context exclusion candidate',source,inputs:{[cityFile]:sha(cityFile),[contractFile]:sha(contractFile),'scripts/exclude_hangzhou_context.mjs':sha('scripts/exclude_hangzhou_context.mjs')},marginGame:MARGIN,targets:rows.map(b=>({id:b.id,rings:b.rings,previousHeightGame:b.height})),files:[],ambiguities:[],removedById:Object.fromEntries([...ids].map(id=>[id,0])),pass:false,
 pending:['replacement GLB and collision integration','rooftop props and signs','AO and roof lookup refresh','terrain/entry/walk support','browser visual/night/performance']};
for(const file of files){
 const input=path.join(source,file),inputHash=sha(input),doc=await io.read(input),visited=new Set();let removed=0,touched=0;
 for(const node of doc.getRoot().listNodes()){
  const match=node.getName().match(/^(?:block|facade)_(-?\d+)_(-?\d+)_/);
  if(!match||!tiles.has(match[1]+'_'+match[2])||!node.getMesh())continue;
  const mesh=node.getMesh();assert(!visited.has(mesh),'Shared transformed mesh requires explicit ownership');visited.add(mesh);
  const matrix=node.getWorldMatrix();
  for(const prim of mesh.listPrimitives()){
   assert.equal(prim.getMode(),4);const pos=prim.getAttribute('POSITION'),idx=prim.getIndices(),indices=idx.getArray(),keep=[],v=[];
   for(let n=0;n<indices.length;n+=3){
    const triangle=[0,1,2].map(k=>{pos.getElement(indices[n+k],v);return transform(v,matrix);});
    const owners=targets.filter(b=>triangle.every(p=>near(p,b)));
    if(owners.length){
     const foreign=neighbours.filter(b=>triangle.every(p=>contains(p[0],p[1],b.rings,.002)&&p[2]>=(b.minY??-Infinity)-.04&&p[2]<=(b.maxY??b.height)+2));
     if(foreign.length){report.ambiguities.push({file,mesh:mesh.getName(),offset:n,owners:owners.map(b=>b.id),foreign:foreign.map(b=>b.id)});keep.push(...indices.slice(n,n+3));continue;}
     removed++;for(const b of owners)report.removedById[b.id]++;continue;
    }
    keep.push(...indices.slice(n,n+3));
   }
   if(keep.length===indices.length)continue;touched++;
   // Compact only referenced vertices. All retained attribute components remain
   // byte-identical; old high roofs cannot leave giant unreferenced bounds.
   const used=[...new Set(keep)],remap=new Map(used.map((v,i)=>[v,i]));
   if(!used.length){mesh.removePrimitive(prim);continue;}
   for(const semantic of prim.listSemantics()){
    const a=prim.getAttribute(semantic),old=a.getArray(),size=a.getElementSize(),next=new old.constructor(used.length*size);
    used.forEach((v,i)=>next.set(old.subarray(v*size,(v+1)*size),i*size));prim.setAttribute(semantic,a.clone().setArray(next));
   }
   prim.setIndices(idx.clone().setArray(new indices.constructor(keep.map(v=>remap.get(v)))));
  }
  if(!mesh.listPrimitives().length){node.dispose();mesh.dispose();}
 }
 for(const ext of doc.getRoot().listExtensionsUsed())if(ext.extensionName==='EXT_meshopt_compression')ext.dispose();
 const expected=await snapshot(doc);
 doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
 const target=path.join(output,file);fs.mkdirSync(path.dirname(target),{recursive:true});await io.write(target,doc);
 const actual=await snapshot(await io.read(target));
 if(!isDeepStrictEqual(directed(actual),directed(expected))){
  fs.writeFileSync(path.join(output,'roundtrip-failure.json'),JSON.stringify({file,
   changedMeshes:actual.meshes.filter((m,i)=>!isDeepStrictEqual(directed({meshes:[m]}),directed({meshes:[expected.meshes[i]]}))).map(m=>m.name),
   nodesMatch:isDeepStrictEqual(actual.nodes,expected.nodes)},null,2)+'\n');
  throw Error('Compressed roundtrip changed oriented geometry/attributes/materials/transforms; see roundtrip-failure.json');
 }
 assert.equal(sha(input),inputHash,'Source asset changed');
 report.files.push({file,inputSha256:inputHash,sha256:sha(target),removedTriangles:removed,touchedPrimitives:touched,retainedDecodedContentExact:true});
 console.log(JSON.stringify(report.files.at(-1)));
}
report.pass=report.ambiguities.length===0&&Object.values(report.removedById).every(n=>n>0);
fs.writeFileSync(path.join(output,'exclusion-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({pass:report.pass,ambiguities:report.ambiguities.length,removedById:report.removedById}));
if(!report.pass)process.exitCode=1;
