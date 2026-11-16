/** Verify a rigid candidate floor relocation in real GLBs, not a browser. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
const [commandsFile,output]=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!commandsFile||!output||fs.existsSync(output))throw Error('Placement commands and fresh report required');
const commands=JSON.parse(fs.readFileSync(commandsFile)),io=new NodeIO().registerExtensions(ALL_EXTENSIONS),records=[];
for(const command of commands){
 const args=command.args,newRoot=args[args.indexOf('--output')+1],placementFile=args[args.indexOf('--placement')+1],placement=JSON.parse(fs.readFileSync(placementFile));
 for(const item of placement.sourceInputs)assert.equal(sha(item.path),item.sha256,'Changed placement input '+item.path);
 const oldFile=placement.sourceInputs.find(p=>p.path.endsWith('/model-delivery.json')).path,old=JSON.parse(fs.readFileSync(oldFile)),freshFile=path.join(newRoot,'model-delivery.json'),fresh=JSON.parse(fs.readFileSync(freshFile));
 for(const d of [old,fresh])for(const [p,h] of [['artifact','artifactSha256'],['sourceModule','sourceModuleSha256'],['spec','specSha256']])assert.equal(sha(d[p]),d[h]);
 const before=await io.read(old.artifact),after=await io.read(fresh.artifact),left=before.getRoot().listMeshes(),right=new Map(after.getRoot().listMeshes().map(m=>[m.getName(),m]));
 const matrix=(doc,mesh)=>{const nodes=doc.getRoot().listNodes().filter(n=>n.getMesh()===mesh);assert.equal(nodes.length,1);return nodes[0].getWorldMatrix();};
 const point=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
 assert.equal(left.length,right.size);const delta=fresh.baseYGame-(old.baseYGame??0);let vertices=0,maxError=0;
 for(const m of left){
  const other=right.get(m.getName());assert.ok(other);assert.equal(m.listPrimitives().length,other.listPrimitives().length);const oldMatrix=matrix(before,m),newMatrix=matrix(after,other);
  for(const [index,p] of m.listPrimitives().entries()){
   const q=other.listPrimitives()[index];assert.deepEqual(p.getIndices()?.getArray(),q.getIndices()?.getArray());assert.equal(p.getMaterial()?.getName(),q.getMaterial()?.getName());
   assert.deepEqual(p.listSemantics(),q.listSemantics());
   for(const semantic of p.listSemantics()){
    const a=p.getAttribute(semantic),b=q.getAttribute(semantic);assert.equal(a.getCount(),b.getCount());
    if(semantic!=='POSITION'){assert.deepEqual(a.getArray(),b.getArray(),m.getName()+' '+semantic);continue;}
    const av=[],bv=[];for(let i=0;i<a.getCount();i++){a.getElement(i,av);b.getElement(i,bv);const aw=point(oldMatrix,av),bw=point(newMatrix,bv);vertices++;maxError=Math.max(maxError,Math.abs(bw[0]-aw[0]),Math.abs(bw[2]-aw[2]),Math.abs(bw[1]-aw[1]-delta));}
   }
  }
 }
 const pass=maxError<.00003;records.push({id:command.id,oldArtifact:old.artifact,oldSha256:old.artifactSha256,newArtifact:fresh.artifact,newSha256:fresh.artifactSha256,placementSha256:sha(placementFile),deltaYGame:delta,vertices,maxRigidTranslationErrorGame:maxError,geometryAndAttributesPreserved:pass,browserAccepted:false});
}
const report={kind:'actual-GLB-rigid-floor-translation',commandsSha256:sha(commandsFile),checkerSha256:sha('scripts/check_hangzhou_landmark_placement.mjs'),records,pass:records.every(r=>r.geometryAndAttributesPreserved),pending:['terrain-to-floor foundations and collision sync','actual entrance connection','continuous terrain extrema','browser views/night/performance']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.pass)process.exitCode=1;
