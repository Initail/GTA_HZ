import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import{pathToFileURL}from'node:url';
const root=process.cwd(),folder='docs/hangzhou/research/coastal-adaptation-round1/export-contract/city-balcony-walk-envelope-v2',read=n=>JSON.parse(fs.readFileSync(path.join(folder,n))),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const {CitySiteSurfaces}=await import(pathToFileURL(path.join(root,'src/city-site-surfaces.ts')).href),data=read('site-surfaces-envelope.json'),sites=new CitySiteSurfaces(data),points=read('query-cases.json');let maxError=0,stationaryQueries=0;const failures=[];
for(const p of points){
 for(const previous of [{id:'city-balcony:upper',height:p.height-.1},{id:'city-balcony:upper',height:p.height+.1}]){
  let result=sites.walkAt(p.x,p.z,p.height-.4,previous);maxError=Math.max(maxError,Math.abs(result.height-p.height));if(result.id!=='city-balcony:upper'||Math.abs(result.height-p.height)>.0001)failures.push({point:p,previous,result});
  for(let i=0;i<4;i++){const next=sites.walkAt(p.x,p.z,p.height-.4,result);if(next.height!==result.height||next.id!==result.id)failures.push({point:p,stationaryFrom:result,stationaryTo:next});result=next;stationaryQueries++;}
 }
}
let slabCases=0;const slabFailures=[];
for(const slab of data.solidSlabs)for(const t of slab.triangles){
 const x=t.reduce((s,p)=>s+p[0],0)/3,z=t.reduce((s,p)=>s+p[1],0)/3,y=t.reduce((s,p)=>s+p[2],0)/3;
 for(const [feet,expected,label] of [[y-.05,true,'head/body enters solid'],[y+.00001,false,'standing on slab'],[y-slab.thicknessGame-1.6-.001,false,'below slab with head clearance'],[y-slab.thicknessGame-1.6+.001,true,'head penetrates underside']]){
  const actual=sites.blocked(x,z,feet,1.6);if(actual!==expected)slabFailures.push({slab:slab.id,x,z,feet,expected,actual,label});slabCases++;
 }
}
const report={sourceSha256:sha('src/city-site-surfaces.ts'),candidateSha256:sha(path.join(folder,'site-surfaces-envelope.json')),sampledPoints:points.length,twoHintSelections:points.length*2,stationaryQueries,maximumHeightErrorGame:maxError,queryFailures:failures.length,queryExamples:failures.slice(0,20),slabCases,slabFailures:slabFailures.length,slabExamples:slabFailures.slice(0,20),pass:!failures.length&&!slabFailures.length,browserOrBodyMovementRun:false};fs.writeFileSync(path.join(folder,'runtime-validation-finite-edge.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.pass)process.exitCode=1;
