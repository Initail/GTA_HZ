/** Ordered OSM transit relations and platform identities; never installs geometry. */
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,relative} from 'node:path';
import {roadAllows,roadDirections} from '../artifacts/cities/hangzhou/city-leisure-v15/src/road-access.ts';

const root=resolve(import.meta.dirname,'..'),base=resolve(root,'artifacts/cities/hangzhou/bus-route-7-v1');
const output=resolve(root,process.argv[2]??'artifacts/cities/hangzhou/bus-route-7-v2');
if(!output.startsWith(resolve(root,'artifacts/cities/hangzhou')+'/')||existsSync(output))throw Error('Choose a fresh Hangzhou candidate directory');
const inputs:Record<string,string>={};
function read(p:string){const raw=readFileSync(p);inputs[relative(root,p)]=createHash('sha256').update(raw).digest('hex');return JSON.parse(raw.toString());}
const config=read(resolve(root,'config/cities/hangzhou.json')),g=config.geography;
const project=(p:number[])=>[(p[0]-g.originWGS84[0])*g.eastMetresPerDegree*g.scale,(p[1]-g.originWGS84[1])*g.northMetresPerDegree*g.scale];
const relations=read(resolve(base,'relations.json')),wayDoc=read(resolve(base,'ways.json')),platformDoc=read(resolve(base,'nodes.json'));
const nodes=new Map<string,any>(),ways=new Map<string,any>(wayDoc.records.map((w:any)=>[w.id,w]));
for(let i=0;i<6;i++){
 const shard=read(resolve(base,`way-nodes-bounded-v1-part-${i}.json`));
 if(shard.missing.length||shard.source.sha256!==relations.source.sha256)throw Error('Incomplete source node shard');
 for(const n of shard.records){if(nodes.has(n.id))throw Error('Duplicate source node');nodes.set(n.id,n);}
}
const platforms=new Map<string,any>(platformDoc.records.map((n:any)=>[n.id,n]));
if(wayDoc.source.sha256!==relations.source.sha256||platformDoc.source.sha256!==relations.source.sha256)throw Error('Mixed OSM snapshots');
const results=[];
for(const relation of relations.records){
 const members=relation.members.filter((m:any)=>m.type==='w');
 // Only endpoint joins from the source relation. No x/z proximity or shortest path.
 let alternatives:{nodes:string[];edges:any[]}[]=[{nodes:[],edges:[]}];
 for(const member of members){
  const way=ways.get('way/'+member.id);if(!way)throw Error('Missing source member '+member.id);
  const tags=way.properties.tags,road={kind:tags.highway??'',oneway:false,sourceAccessTags:tags};
  if(!roadAllows(road,'bus').allowed)throw Error('Source relation uses a bus-restricted way '+way.id);
  const direction=roadDirections(road,'bus','osm-forward'),ids=way.properties.nodeIds.map((id:string)=>'node/'+id);
  if(ids.length<2||!ids.every((id:string)=>nodes.has(id)))throw Error('Missing source way geometry');
  for(let i=0;i<ids.length;i++)if(Math.hypot(...nodes.get(ids[i]).wgs84.map((v:number,k:number)=>v-way.geometry.coordinates[i][k]))>1e-10)throw Error('Source node/way coordinates differ');
  const orientations=[{ids,forward:true,allowed:direction.forward},{ids:[...ids].reverse(),forward:false,allowed:direction.backward}];
  const next=[];
  for(const a of alternatives)for(const option of orientations){
   if(option.allowed!==true||member.role==='forward'&&!option.forward||member.role==='backward'&&option.forward)continue;
   if(member.role&&!['forward','backward'].includes(member.role))throw Error('Unsupported way member role');
   if(a.nodes.length&&a.nodes.at(-1)!==option.ids[0])continue;
   const edges=option.ids.slice(1).map((to:string,i:number)=>({from:option.ids[i],to,sourceWayId:way.id,sourceForward:option.forward,sourceGrade:way.properties.grade??'0'}));
   next.push({nodes:[...a.nodes,...option.ids.slice(a.nodes.length?1:0)],edges:[...a.edges,...edges]});
  }
  if(!next.length||next.length>2)throw Error('Unresolved source endpoint chain at '+relation.id+' / '+way.id);
  alternatives=next;
 }
 if(alternatives.length!==1)throw Error('Relation direction remains ambiguous '+relation.id);
 const chain=alternatives[0],points=chain.nodes.map(id=>project(nodes.get(id).wgs84));
 const distances=[0];for(let i=1;i<points.length;i++){const d=Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]);if(d<=0)throw Error('Zero-length source edge');distances.push(distances.at(-1)!+d);}
 const stopMembers=relation.members.filter((m:any)=>m.type==='n'&&m.role.startsWith('platform'));
 const stops=stopMembers.map((member:any)=>{
  const p=platforms.get('node/'+member.id);if(!p)throw Error('Missing platform identity');const point=project(p.wgs84),candidates=[];
  for(let i=0;i<chain.nodes.length;i++){
   const n=nodes.get(chain.nodes[i]);if(n.tags.public_transport!=='stop_position'||n.tags.name!==p.tags.name)continue;
   const a=points[i===points.length-1?i-1:i],b=points[i===points.length-1?i:i+1],yaw=Math.atan2(b[0]-a[0],b[1]-a[1]);
   const dx=point[0]-points[i][0],dz=point[1]-points[i][1],distance=Math.hypot(dx,dz),right=dx*Math.cos(yaw)-dz*Math.sin(yaw);
   candidates.push({sourceStopId:n.id,chainIndex:i,distanceGame:distance,rightOffsetGame:right,roadPointGame:points[i],roadYaw:yaw,eligible:right>0,reason:right>0?'right side of directed source centreline':'opposite side of directed source centreline'});
  }
  candidates.sort((a,b)=>a.distanceGame-b.distanceGame);
  return {sourcePlatformId:p.id,name:p.tags.name,role:member.role,platformWGS84:p.wgs84,platformGame:point,sourceVersion:p.version,sourceTimestamp:p.timestamp,candidates,selection:null as any};
 });
 // Match the entire stop sequence, not independent shortest-path leg endpoints.
 // Retain two best complete assignments so near-equal identities stay unresolved.
 let states:{score:number;last:number;choices:any[]}[]=[{score:0,last:-1,choices:[]}];
 for(const stop of stops){
  const next=[];
  for(const c of stop.candidates.filter(c=>c.eligible)){
   const incoming=states.filter(s=>c.chainIndex>s.last).map(s=>({score:s.score+c.distanceGame**2,last:c.chainIndex,choices:[...s.choices,c]})).sort((a,b)=>a.score-b.score).slice(0,2);
   next.push(...incoming);
  }
  states=next;
 }
 states.sort((a,b)=>a.score-b.score);
 const best=states[0],ambiguous=!!best&&states.length>1&&Math.abs(states[1].score-best.score)<1e-6;
 if(best&&!ambiguous)stops.forEach((s,i)=>s.selection={...best.choices[i],distanceAlongSourceGame:distances[best.choices[i].chainIndex],basis:'inferred: minimum squared platform distance among same-name source stops, right side and globally ordered; not field verification',platformHeight:null,boardingAccepted:false});
 const blockers=[];
 if(!best)blockers.push('No globally ordered right-side assignment for every platform; retain all source alternatives.');
 if(ambiguous)blockers.push('Equal-cost source identities require independent evidence.');
 for(const stop of stops)if(stop.selection&&stop.selection.distanceGame>8)blockers.push(`${stop.sourcePlatformId}: mapped platform is ${stop.selection.distanceGame.toFixed(2)}g from stop_position; no guessed boarding offset.`);
 results.push({id:relation.id,name:relation.tags.name,sourceVersion:relation.version,sourceTimestamp:relation.timestamp,sourceCalendar:relation.tags.opening_hours,sourceWayMemberCount:members.length,chain,pointsGame:points,lengthGame:distances.at(-1),stops,selectionAccepted:!!best&&!ambiguous,blockers});
}
const result={schemaVersion:1,cityId:'hangzhou',source:relations.source,inputs,coordinateContract:g,routes:results,simulation:{headwaySeconds:120,dwellSeconds:12,realTimetable:false},acceptance:{orderedSourceWayChains:true,selectedSourceStops:results.every(r=>r.selectionAccepted),platformHeight:false,physicalRoads:false,sweptBody:false,boarding:false,mainWorld:false,browser:false},installable:false};
mkdirSync(output);writeFileSync(resolve(output,'source-service-catalog.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output:relative(root,output),routes:results.map(r=>({id:r.id,edges:r.chain.edges.length,stops:r.stops.length,selected:r.selectionAccepted,blockers:r.blockers})),installable:false}));
