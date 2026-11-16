import type {BaseStreamTile,StreamGlbTile} from './city-stream-assets.ts';
import {planBaseStream,tileLodDistance,type BaseStreamView} from './city-base-stream-plan.ts';
import {BASE_STREAM_LIMITS,type StreamBudget} from './city-stream-residency.ts';
export type PackMember={id:string;quality:'near'|'far';referenceSha256:string;parentSourceId?:string};
export type BaseStreamPack=StreamGlbTile&{role:'pack';members:readonly PackMember[]};
/** Required source coverage comes from the unchanged world ranges/frustum and
 * auxiliary views. A pack is one physical asset; hidden members still cost
 * their full resident bytes and triangles. This planner never loads assets. */
export function planBaseStreamPacks(sources:readonly BaseStreamTile[],packs:readonly BaseStreamPack[],view:BaseStreamView,previousNear:ReadonlySet<string>=new Set()){
 const sourceById=new Map(sources.map(s=>[s.id,s]));
 if(sourceById.size!==sources.length)throw Error('Duplicate source tile identity');
 const index=new Map<string,BaseStreamPack>(),packIds=new Set<string>();
 for(const pack of packs){
  if(pack.role!=='pack'||!pack.id||packIds.has(pack.id)||!pack.members.length||pack.members.length>48||pack.bytes<=0||(['bytes','logicalBytes','triangles'] as const).some(key=>!Number.isSafeInteger(pack[key])||pack[key]<0)||pack.bounds.min.length!==3||pack.bounds.max.length!==3||pack.bounds.min.some((v,i)=>!Number.isFinite(v)||!Number.isFinite(pack.bounds.max[i])||v>pack.bounds.max[i]))throw Error('Invalid physical pack');
  packIds.add(pack.id);const members=new Set<string>();
  for(const member of pack.members){
   const source=sourceById.get(member.id),key=member.quality+':'+member.id;
   if(!source||source.sha256!==member.referenceSha256||!['near','far'].includes(member.quality)||members.has(member.id)||index.has(key))throw Error('Pack source coverage mismatch or duplicate representation');
   members.add(member.id);index.set(key,pack);
  }
 }
 const base=planBaseStream(sources,view),required=new Map<string,{pack:BaseStreamPack;visibleMembers:string[]}>(),near=new Set<string>(),missing:string[]=[],representations:Record<string,{pack:string;quality:'near'|'far'}>={},forcedNearPacks=new Set<string>();
 for(const source of base.required){
  const close=tileLodDistance(source,view.x,view.z)<(previousNear.has(source.id)?800:640);
  if(close)near.add(source.id);
  if(close||!index.has('far:'+source.id)){const pack=index.get('near:'+source.id);if(pack)forcedNearPacks.add(pack.id);}
 }
 for(const source of base.required){
  // The exact near geometry can also serve distant members already present in
  // a forced near pack. Do not pay for their far pack as well. This promotion
  // must not enter `near`: 640/800 hysteresis remains geometry-distance based.
  const nearPack=index.get('near:'+source.id);
  const quality=near.has(source.id)||!index.has('far:'+source.id)||nearPack&&forcedNearPacks.has(nearPack.id)?'near':'far',pack=index.get(quality+':'+source.id);
  if(!pack){missing.push(source.id);continue;}
  const selection=required.get(pack.id)??{pack,visibleMembers:[]};selection.visibleMembers.push(source.id);required.set(pack.id,selection);representations[source.id]={pack:pack.id,quality};
 }
 const cost={bytes:0,logicalBytes:0,triangles:0,tiles:required.size};
 for(const {pack} of required.values()){cost.bytes+=pack.bytes;cost.logicalBytes+=pack.logicalBytes;cost.triangles+=pack.triangles;}
 const exceeded=(Object.keys(cost) as (keyof StreamBudget)[]).filter(key=>cost[key]>BASE_STREAM_LIMITS[key]);
 const retentionIds=new Set(base.retained.map(s=>s.id)),retained=packs.filter(p=>p.members.some(m=>retentionIds.has(m.id)));
 return {required:[...required.values()],retained,representations,near,sourceRequired:base.required.map(s=>s.id),missing,cost,budget:{...BASE_STREAM_LIMITS},exceeded,admitted:missing.length===0&&exceeded.length===0};
}
