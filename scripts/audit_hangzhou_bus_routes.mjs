/** Source-bound route audit. No platform permission or live schedule is inferred. */
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {RoadGraph} from '../artifacts/cities/hangzhou/city-leisure-v14/src/navigation.ts';
import {buildBusRoute,busRoutePose} from '../artifacts/cities/hangzhou/city-leisure-v14/src/city-bus-route.ts';
const base=new URL('../artifacts/cities/hangzhou/bus-route-7-v1/',import.meta.url);
const read=name=>JSON.parse(readFileSync(new URL(name,base),'utf8'));
const input=read('prepared-inputs-v1.json'),ways=read('ways.json').records;
const out=new URL('directed-route-audit-v1.json',base);if(existsSync(out))throw Error('Existing audit is protected');
const results=[];
for(const relation of input.relations){
 const sourceWays=relation.members.filter(m=>m.type==='w').map(m=>'way/'+m.id),roads=input.roads.filter(r=>sourceWays.includes(r.sourceId));
 const graph=new RoadGraph(roads,input.graph),stops=relation.members.filter(m=>m.type==='n'&&m.role.startsWith('platform'));
 const candidates=stops.map(m=>{
  const platform=input.anchorCandidates.find(a=>a.sourcePlatformId==='node/'+m.id);
  const positions=platform.sourcePositionCandidates.filter(c=>roads.some(r=>r.nodeIds.includes(c.sourceStopId.split('/')[1])));
  return {platform,positions};
 });
 const missingWays=sourceWays.filter(id=>!roads.some(r=>r.sourceId===id));
 const sourceConnections=[];
 for(let i=1;i<sourceWays.length;i++){
  const a=ways.find(w=>w.id===sourceWays[i-1]),b=ways.find(w=>w.id===sourceWays[i]);
  const shared=a.properties.nodeIds.filter(n=>b.properties.nodeIds.includes(n));
  if(!shared.length)sourceConnections.push({from:a.id,to:b.id,status:'no shared OSM node; cannot invent a junction'});
 }
 const legs=[];
 for(let i=1;i<candidates.length;i++){
  const a=candidates[i-1],b=candidates[i],possibilities=[];
  // Evaluate every source-supported stop-position pairing. A nearest-node
  // guess or equal stop name never creates a new graph connection.
  for(const first of a.positions)for(const last of b.positions){
   const anchor=(p,n)=>({id:p.sourcePlatformId,name:p.name,sourcePlatformId:p.sourcePlatformId,sourceStopId:n.sourceStopId,node:n.node,platform:{x:p.platformGame[0],z:p.platformGame[1],height:n.roadHeightGame}});
   try{
    const route=buildBusRoute(graph,relation.id,'7路体验 · 模拟班次',[anchor(a.platform,first),anchor(b.platform,last)],120,12);
    const pose=busRoutePose(graph,route,0),dx=a.platform.platformGame[0]-pose.x,dz=a.platform.platformGame[1]-pose.z;
    possibilities.push({sourceStart:first.sourceStopId,sourceEnd:last.sourceStopId,distanceGame:route.length,sourceEdges:route.edges.map(e=>[input.graph.sourceNodeIds[e.from],input.graph.sourceNodeIds[e.to]]),platformRightOffsetGame:dx*Math.cos(pose.yaw)-dz*Math.sin(pose.yaw),doorToPlatformGame:Math.hypot(dx-Math.cos(pose.yaw)*1.7-Math.sin(pose.yaw)*3.2,dz+Math.sin(pose.yaw)*1.7-Math.cos(pose.yaw)*3.2),startPlatformDistanceGame:first.horizontalDistanceGame,endPlatformDistanceGame:last.horizontalDistanceGame});
   }catch(error){if(!/no distinct permitted source-node route/.test(String(error)))throw error;}
  }
  possibilities.sort((a,b)=>a.startPlatformDistanceGame+a.endPlatformDistanceGame-b.startPlatformDistanceGame-b.endPlatformDistanceGame);
  legs.push({from:a.platform.name,to:b.platform.name,sourcePlatformIds:[a.platform.sourcePlatformId,b.platform.sourcePlatformId],possibilities,status:possibilities.length?'source-directed paths exist; platform and swept bus-body acceptance pending':'blocked: no source-directed path'});
 }
 results.push({id:relation.id,sourceVersion:relation.version,sourceTimestamp:relation.timestamp,missingWays,sourceConnectionGaps:sourceConnections,legs});
}
const hash=createHash('sha256').update(readFileSync(new URL('prepared-inputs-v1.json',base))).digest('hex');
const result={schemaVersion:1,source:input.source,preparedInputsSha256:hash,routes:results,acceptance:{graphAudit:true,selectedRoute:false,platformHeight:false,platformAccess:false,sweptBusBody:false,boarding:false,browser:false},blockers:['The outbound Chengzhan depot way/1197824998 is access=private,bus=yes and was excluded from the main-city road preparation. Cars must remain prohibited; a bus-specific road/render/collision addition is needed.','Source stop_position is not the bus centre at a usable door. Use a source-bound stopping offset and safe platform approach, not a teleport from the road centre.','Platform terrain heights and curb/door access remain unchecked. The road heights used here are labelled provisional.'],timetable:'Game headway 120 s / dwell 12 s are simulation parameters, not current real schedules.'};
writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({routes:results.length,legs:results.reduce((n,r)=>n+r.legs.length,0),unroutableLegs:results.flatMap(r=>r.legs.filter(l=>!l.possibilities.length).map(l=>({route:r.id,from:l.from,to:l.to}))),sourceConnectionGaps:results.reduce((n,r)=>n+r.sourceConnectionGaps.length,0),platformsAccepted:false,bytes:readFileSync(out).length}));
