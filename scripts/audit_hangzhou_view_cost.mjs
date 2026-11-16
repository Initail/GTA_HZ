/** Read only small pinned manifests; never load geometry or start a renderer.
 * Run through run_hangzhou_bounded.py once resources permit:
 * node --experimental-transform-types scripts/audit_hangzhou_view_cost.mjs OUTPUT.json [VIEWS.json]
 * Optional views carry six captured or explicitly simulated frustum planes.
 * No synthetic camera is silently substituted for a runtime observation. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {planBaseStream,tileDistance} from '../artifacts/cities/hangzhou/city-leisure-v15/src/city-base-stream-plan.ts';
import {planBaseStream as legacyPlan} from '../artifacts/cities/hangzhou/stream-world-v1/src/city-base-stream-plan.ts';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),root=process.cwd(),inputs=[];
function read(file,max){assert(fs.statSync(file).size<=max);const raw=fs.readFileSync(file);inputs.push({file,bytes:raw.length,sha256:hash(raw)});return {raw,doc:JSON.parse(raw)};}
const output=path.resolve(process.argv[2]??'');assert(process.argv[2]&&!fs.existsSync(output)&&output.startsWith(root+path.sep),'Fresh repository report required');
const release=read('artifacts/cities/hangzhou/stream-release-v1/descriptor.json',64*1024).doc;
const baseline=read('artifacts/cities/hangzhou/stream-world-v1/original-range-admission.json',16*1024).doc;
assert.equal(baseline.scope,'CPU admission only; original ranges and no frustum reduction');
const tiles=[];
for(const role of ['terrain','roads','buildings']){
 const bound=release.models[role],data=read(bound.manifestPath,256*1024);
 assert.equal(data.raw.length,bound.manifestBytes);assert.equal(hash(data.raw),bound.manifestSha256);assert.equal(data.doc.role,role);assert.equal(data.doc.source.sha256,bound.sourceSha256);
 tiles.push(...data.doc.tiles.map(t=>({...t,role,baseUrl:'http://offline.invalid/'})));
}
const cost=list=>list.reduce((c,t)=>({tiles:c.tiles+1,bytes:c.bytes+t.bytes,logicalBytes:c.logicalBytes+t.logicalBytes,triangles:c.triangles+t.triangles}),{tiles:0,bytes:0,logicalBytes:0,triangles:0});
const byRole=list=>Object.fromEntries(['terrain','roads','buildings'].map(role=>[role,cost(list.filter(t=>t.role===role))]));
const summarize=view=>{
 const plan=planBaseStream(tiles,view),aux=planBaseStream(tiles,{...view,intersects:()=>false});
 return {cost:plan.cost,byRole:byRole(plan.required),nearRequired:byRole(plan.required.filter(t=>tileDistance(t,view.x,view.z)<640)),auxiliaryRequired:byRole(aux.required),budget:plan.budget,exceeded:plan.exceeded,declaredCostAdmitted:plan.admitted,required:plan.required.map(t=>t.id)};
};
const radialEnvelope=summarize({x:baseline.spawn.x,z:baseline.spawn.z,overview:false});
assert.deepEqual(legacyPlan(tiles,{x:baseline.spawn.x,z:baseline.spawn.z,overview:false}).cost,baseline.cost,'Pinned historical radial calculation changed');
const views=[];
if(process.argv[3]){
 const data=read(process.argv[3],64*1024).doc;assert(data.schemaVersion===1&&Array.isArray(data.views)&&data.views.length>0&&data.views.length<=32);
 for(const view of data.views){
  assert(typeof view.id==='string'&&view.id&&['runtime-captured','simulated'].includes(view.origin));
  assert(Number.isFinite(view.x)&&Number.isFinite(view.z)&&typeof view.overview==='boolean');
  assert(Array.isArray(view.planes)&&view.planes.length===6&&view.planes.every(p=>Array.isArray(p.normal)&&p.normal.length===3&&p.normal.every(Number.isFinite)&&Number.isFinite(p.d)&&Math.abs(Math.hypot(...p.normal)-1)<1e-4));
  // Same AABB/plane predicate as DrivingWorld.baseView. Auxiliary coverage is
  // added by the unchanged runtime planner and must not be culled away here.
  const intersects=tile=>view.planes.every(p=>p.normal[0]*tile.bounds[p.normal[0]>=0?'max':'min'][0]+p.normal[1]*tile.bounds[p.normal[1]>=0?'max':'min'][1]+p.normal[2]*tile.bounds[p.normal[2]>=0?'max':'min'][2]+p.d>=0);
  views.push({id:view.id,origin:view.origin,x:view.x,z:view.z,overview:view.overview,planes:view.planes,...summarize({...view,intersects})});
 }
}
for(const file of ['artifacts/cities/hangzhou/city-leisure-v15/src/city-base-stream-plan.ts','artifacts/cities/hangzhou/stream-world-v1/src/city-base-stream-plan.ts','artifacts/cities/hangzhou/city-leisure-v15/src/city-world.ts']){const raw=fs.readFileSync(file);inputs.push({file,bytes:raw.length,sha256:hash(raw)});}
const report={schemaVersion:1,kind:'manifest-view-cost-audit',inputs,spawn:baseline.spawn,historicalRadialEnvelope:{scope:baseline.scope,cost:baseline.cost},radialEnvelope:{scope:'all directions within original street ranges and world cull anchors, without camera frustum reduction',...radialEnvelope},views,measurement:{level:'offline declared asset arithmetic',geometryDecoded:false,rendererStarted:false,browserAcceptance:false,physicalPackCostsIncluded:false},pending:['actual driving, walking, boat and aerial camera samples','cost of every complete physical pack including hidden members','retention and switching peaks','full-world non-base assets','real browser memory and frame time']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,radialEnvelope:radialEnvelope.cost,views:views.length,browserAcceptance:false}));
