/** Extract support from the actual exported GLBs, using the runtime axis contract. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';
const [input,output]=process.argv.slice(2);
assert(input&&output&&!fs.existsSync(output));assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const manifest=JSON.parse(fs.readFileSync(path.join(input,'asset-manifest.json')));
const sourceFaces=JSON.parse(fs.readFileSync(path.join(input,'source-faces.json')));
const changed=sourceFaces.filter(f=>f.changed),points=changed.flatMap(f=>f.points);
const bounds=[0,1].map(k=>[Math.min(...points.map(p=>p[k])),Math.max(...points.map(p=>p[k]))]);
const io=new NodeIO(),floors=[],vertices=new Set(),rows=[];
const key=p=>p.map(Math.fround).join(',');
for(const asset of manifest.assets){
 const file=path.join(input,asset.file);assert.equal(sha(file),asset.sha256);
 const doc=await io.read(file);let total=0,selected=0,degenerate=0;
 for(const node of doc.getRoot().listNodes()){
  const mesh=node.getMesh();if(!mesh)continue;const m=node.getWorldMatrix();
  for(const primitive of mesh.listPrimitives()){
   const p=primitive.getAttribute('POSITION'),indices=primitive.getIndices().getArray(),value=[];
   const point=i=>{p.getElement(i,value);const[x,y,z]=value;const gx=m[0]*x+m[4]*y+m[8]*z+m[12],gy=m[1]*x+m[5]*y+m[9]*z+m[13],gz=m[2]*x+m[6]*y+m[10]*z+m[14];return [gx,-gz,gy];};
   for(let i=0;i<p.getCount();i++)vertices.add(key(point(i)));
   const material=primitive.getMaterial().getName();
   for(let i=0;i<indices.length;i+=3){
    total++;const t=[point(indices[i]),point(indices[i+1]),point(indices[i+2])];
    if(t.some(p=>p[0]<bounds[0][0]-.001||p[0]>bounds[0][1]+.001||p[1]<bounds[1][0]-.001||p[1]>bounds[1][1]+.001))continue;
    if(!['asphalt','park','pavement'].includes(material))continue;
    const [a,b,c]=t,det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    if(det<=0){if(det===0)degenerate++;continue;}
    // Side walls and vertical trim are not walking support. Asphalt and bank
    // top triangles are directly taken from the export, never resampled.
    const gradient=Math.max(...t.map(p=>p[2]))-Math.min(...t.map(p=>p[2]));
    if(gradient>Math.sqrt(Math.abs(det))*3)continue;
    floors.push(t);selected++;
   }
  }
 }
 rows.push({file:asset.file,sha256:asset.sha256,triangles:total,walkingTriangles:selected,verticalOrCollapsedProjectedTriangles:degenerate});
}
// Blender stores source positions in float32. Verify every rail vertex against
// the real GLB before deriving its finite footprint in the companion script.
let railVertices=0;for(const f of changed.filter(f=>f.rail))for(const p of f.points){assert(vertices.has(key(p)),'Rail vertex missing from GLB');railVertices++;}
fs.mkdirSync(output);
const data={cityId:'hangzhou',units:'game east/north/up; scale applied once',
 terrainCuts:[{id:'bai-route:under-paving',triangles:floors.map(t=>t.map(([x,z,y])=>[x,z,y-.15]))}],
 walkFloors:[{id:'bai-route:actual-paved-and-bank',triangles:floors}],solidSlabs:[]};
fs.writeFileSync(path.join(output,'site-surfaces.json'),JSON.stringify(data)+'\n');
fs.writeFileSync(path.join(output,'support-report.json'),JSON.stringify({inputs:{manifest:sha(path.join(input,'asset-manifest.json')),sourceFaces:sha(path.join(input,'source-faces.json')),extractor:sha('scripts/extract_hangzhou_bai_support.mjs')},assets:rows,railVertices,siteSha256:sha(path.join(output,'site-surfaces.json')),status:'actual triangle support extracted; actors and visual seams pending'},null,2)+'\n');
console.log(JSON.stringify({assets:rows,railVertices,walkingTriangles:floors.length}));
