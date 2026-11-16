/** Crop base terrain/ribbons under actual replacement surfaces in a fresh demo.
 * All non-intersecting primitives retain attributes and index bytes. New edge
 * vertices interpolate existing attributes, with no whole-city remeshing.
 */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
import {NodeIO,Document} from '@gltf-transform/core';import {ALL_EXTENSIONS,EXTMeshoptCompression} from '@gltf-transform/extensions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';import {unpartition,copyToDocument} from '@gltf-transform/functions';
const [stage,support,out]=process.argv.slice(2),root=path.join(stage,'public/cities/hangzhou');
assert(stage&&support&&out&&!fs.existsSync(out)&&!fs.existsSync(path.join(stage,'dist')));
assert(path.resolve(out).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));fs.mkdirSync(out);
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p));
const site=path.join(support,'site-surfaces.json'),sites=read(site),points=sites.walkFloors.flatMap(g=>g.triangles.flat());
const bounds=[0,1].map(k=>[Math.min(...points.map(p=>p[k])),Math.max(...points.map(p=>p[k]))]);
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const accepted=new Set(['land','park','pavement','asphalt','concrete','roadline']);const reports=[];
for(const file of ['terrain.glb','roads.glb']){
 const p=path.join(root,file),original=sha(p),doc=await io.read(p),primitives=[],triangles=[];
 const world=(a,m)=>{const[x,y,z]=a;return[m[0]*x+m[4]*y+m[8]*z+m[12],-(m[2]*x+m[6]*y+m[10]*z+m[14]),m[1]*x+m[5]*y+m[9]*z+m[13]];};
 const near=(ps,margin=0)=>![0,1].some(k=>Math.max(...ps.map(p=>p[k]))<bounds[k][0]-margin||Math.min(...ps.map(p=>p[k]))>bounds[k][1]+margin);
 const contextEntries=[];
 for(const node of doc.getRoot().listNodes())for(const primitive of node.getMesh()?.listPrimitives()??[]){
  if(!accepted.has(primitive.getMaterial()?.getName()))continue;
  const pos=primitive.getAttribute('POSITION'),matrix=node.getWorldMatrix(),lo=pos.getMin([]),hi=pos.getMax([]);
  const corners=[];for(const x of [lo[0],hi[0]])for(const y of [lo[1],hi[1]])for(const z of [lo[2],hi[2]])corners.push(world([x,y,z],matrix));
  if(!near(corners,10))continue;
  contextEntries.push({primitive,node,matrix});
  const id=primitives.length;primitives.push({primitive,matrix});const indices=primitive.getIndices().getArray();
  const v=[];for(let i=0;i<indices.length;i+=3){const ps=[0,1,2].map(k=>{pos.getElement(indices[i+k],v);return world(v,matrix);});if(near(ps))triangles.push({primitive:id,offset:i,world:ps});}
 }
 const scan=path.join(out,file+'.scan.json'),clip=path.join(out,file+'.clip.json');fs.writeFileSync(scan,JSON.stringify({source:p,sha256:original,triangles})+'\n');
 console.log(execFileSync('.venv/bin/python',['scripts/clip_hangzhou_bai_base.py',scan,site,clip],{encoding:'utf8'}).trim());
 const result=read(clip);assert.equal(result.sourceSha256,sha(scan));assert.equal(result.siteSha256,sha(site));let appended=0;
 for(const [id,{primitive,matrix}] of primitives.entries()){
  const changes=new Map(result.records.filter(r=>r.primitive===id).map(r=>[r.offset,r.pieces]));if(!changes.size)continue;
  const pos=primitive.getAttribute('POSITION'),oldIndices=primitive.getIndices().getArray(),attributes=primitive.listSemantics().map(name=>{const a=primitive.getAttribute(name);return {name,a,old:a.getArray(),extra:[],size:a.getElementSize()};});
  const newIndices=[],v=[];let next=pos.getCount();
  for(let i=0;i<oldIndices.length;i+=3){if(!changes.has(i)){newIndices.push(oldIndices[i],oldIndices[i+1],oldIndices[i+2]);continue;}
   const ids=[oldIndices[i],oldIndices[i+1],oldIndices[i+2]],p=ids.map(j=>{pos.getElement(j,v);return world(v,matrix);});
   const det=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0]);assert(Math.abs(det)>1e-12);
   for(let triangle of changes.get(i)){
    if(det<0)triangle=[...triangle].reverse();
    for(const [x,z] of triangle){const u=((x-p[0][0])*(p[2][1]-p[0][1])-(z-p[0][1])*(p[2][0]-p[0][0]))/det,
       w=((p[1][0]-p[0][0])*(z-p[0][1])-(p[1][1]-p[0][1])*(x-p[0][0]))/det,weights=[1-u-w,u,w];
     assert(weights.every(w=>w>-.00001&&w<1.00001),'Clipping extrapolated a source triangle');
     for(const a of attributes){const values=Array.from({length:a.size},(_,k)=>ids.reduce((s,j,n)=>s+weights[n]*a.old[j*a.size+k],0));
      if(a.name==='NORMAL'){const length=Math.hypot(...values);for(let k=0;k<values.length;k++)values[k]/=length;}
      a.extra.push(...values);
     }newIndices.push(next++);appended++;
    }
   }
  }
  for(const a of attributes){const array=new a.old.constructor(a.old.length+a.extra.length);array.set(a.old);array.set(a.extra,a.old.length);const replacement=doc.createAccessor(a.a.getName()).setType(a.a.getType()).setArray(array).setNormalized(a.a.getNormalized()).setBuffer(a.a.getBuffer());primitive.setAttribute(a.name,replacement);}
  primitive.setIndices(doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(newIndices)).setBuffer(pos.getBuffer()));
 }
 const context=new Document(),contextScene=context.createScene('Actual cropped local base surfaces');context.getRoot().setDefaultScene(contextScene);
 for(const {primitive,node,matrix} of contextEntries){const map=copyToDocument(context,doc,[primitive]),mesh=context.createMesh(node.getMesh().getName()).addPrimitive(map.get(primitive));contextScene.addChild(context.createNode(node.getName()).setMesh(mesh).setMatrix(matrix));}
 for(const ext of context.getRoot().listExtensionsUsed())if(ext.extensionName==='EXT_meshopt_compression')ext.dispose();await context.transform(unpartition());await io.write(path.join(out,'context-'+file),context);
 for(const ext of doc.getRoot().listExtensionsUsed())if(ext.extensionName==='EXT_meshopt_compression')ext.dispose();
 doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
 assert.equal(sha(p),original);await io.write(p,doc);reports.push({file,inputSha256:original,sha256:sha(p),localTriangles:triangles.length,deleted:result.deletedTriangles,cut:result.cutTriangles,appendedVertices:appended,clipSha256:sha(clip)});
 console.log(JSON.stringify(reports.at(-1)));
}
fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({stage,inputs:{support:sha(site),script:sha('scripts/clip_hangzhou_bai_base.mjs'),clipper:sha('scripts/clip_hangzhou_bai_base.py')},reports,status:'local geometric crop only; decoded attribute audit, seams and visual review pending'},null,2)+'\n');
