import {readStreamFile,STREAM_ASSET_LIMITS,type BaseStreamTile,type StreamFile,type StreamTexture,type StreamMaterialOrigin} from './city-stream-assets.ts';
import type {BaseStreamPack} from './city-stream-pack-plan.ts';
import {loadBaseStreamPartitions} from './city-stream-partition.ts';
export type PackIndexSource={manifestUrl:string;manifestBytes:number;manifestSha256:string};
export type BasePackRecord=BaseStreamPack&{metadata:StreamFile};
export type BasePackMetadata={textures:StreamTexture[];materialOrigins:StreamMaterialOrigin[];nodes:{name:string;member:string;role:BaseStreamTile['role'];quality:'near'|'far'}[]};
const integer=(n:unknown):n is number=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0;
const hash=(s:unknown):s is string=>typeof s==='string'&&/^[0-9a-f]{64}$/.test(s);
function check(ok:unknown,message:string):asserts ok{if(!ok)throw Error('街区合包：'+message);}
function file(record:StreamFile,max:number,re:RegExp){return record&&integer(record.bytes)&&record.bytes>0&&record.bytes<=max&&hash(record.sha256)&&typeof record.file==='string'&&re.test(record.file);}
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
/** Validate complete near coverage against the independently pinned original
 * layer manifests. No self-reported fullCoverage flag grants admission. */
export async function loadBasePackIndex(source:PackIndexSource,tiles:readonly BaseStreamTile[],expectedTextures:readonly StreamTexture[],sourceManifests:Readonly<Record<string,string>>,signal:AbortSignal){
 const url=new URL(source.manifestUrl,location.href).href,baseUrl=new URL('.',url).href;
 const root=JSON.parse(new TextDecoder().decode(await readStreamFile(url,{file:'index.json',bytes:source.manifestBytes,sha256:source.manifestSha256},signal,64*1024)));
 check(root?.schemaVersion===1&&root.kind==='city-base-pack-index'&&root.sourceManifests&&Object.keys(root.sourceManifests).length===3&&['terrain','roads','buildings'].every(role=>root.sourceManifests[role]===sourceManifests[role]),'源清单身份不符');
 check(Array.isArray(root.textures)&&same(root.textures,expectedTextures),'共享贴图清单不符');
 check(Array.isArray(root.chunks)&&root.chunks.length>0&&root.chunks.length<=64,'索引分片数量无效');
 check(new Set(tiles.map(t=>t.id)).size===tiles.length&&tiles.length>0,'原图层源块重复或为空');
 const refined=await loadBaseStreamPartitions(root.sourcePartitions,baseUrl,tiles,signal);
 const sources=new Map(refined.map(t=>[t.id,t])),representations=new Set<string>(),packIds=new Set<string>(),files=new Set<string>(),near=new Set<string>(),packs:BasePackRecord[]=[];
 for(const chunk of root.chunks as StreamFile[]){
  check(file(chunk,256*1024,/^index\/\d+\.json$/)&&!files.has(chunk.file),'索引分片无效');files.add(chunk.file);
  const body=JSON.parse(new TextDecoder().decode(await readStreamFile(new URL(chunk.file,baseUrl).href,chunk,signal,256*1024)));
  check(body.schemaVersion===1&&Array.isArray(body.packs)&&body.packs.length>0&&body.packs.length<=64,'索引分片内容无效');
  for(const raw of body.packs as BasePackRecord[]){
   check(file(raw,STREAM_ASSET_LIMITS.glb,/^tiles\/(?:near|far)-[a-zA-Z0-9_-]+\.glb$/)&&typeof raw.id==='string'&&!packIds.has(raw.id)&&!files.has(raw.file)&&integer(raw.logicalBytes)&&raw.logicalBytes<=32*1024*1024&&integer(raw.triangles),'合包几何预算无效');
   check(file(raw.metadata,128*1024,/^metadata\/(?:near|far)-[a-zA-Z0-9_-]+\.json$/)&&!files.has(raw.metadata.file),'合包说明无效');
   check(Array.isArray(raw.bounds?.min)&&Array.isArray(raw.bounds?.max)&&raw.bounds.min.length===3&&raw.bounds.max.length===3&&raw.bounds.min.every((v,i)=>Number.isFinite(v)&&Number.isFinite(raw.bounds.max[i])&&v<=raw.bounds.max[i]),'合包范围无效');
   check(Array.isArray(raw.members)&&raw.members.length>0&&raw.members.length<=48,'源块数量无效');
   const local=new Set<string>();
   for(const member of raw.members){const original=sources.get(member.id),key=member.quality+':'+member.id;
    check(original&&member.referenceSha256===original.sha256&&['near','far'].includes(member.quality)&&!local.has(member.id)&&!representations.has(key),'源块缺失、重复或版本不符');
    // The declared pack bounds include every original member, even when the
    // far representation becomes slightly smaller after verified simplification.
    check(original.bounds.min.every((v,i)=>raw.bounds.min[i]<=v&&raw.bounds.max[i]>=original.bounds.max[i]),'合包范围漏掉源块');
    local.add(member.id);representations.add(key);if(member.quality==='near')near.add(member.id);
   }
   packIds.add(raw.id);files.add(raw.file);files.add(raw.metadata.file);packs.push({...raw,members:raw.members.map(m=>({...m,parentSourceId:sources.get(m.id)!.parentSourceId})),role:'pack',baseUrl});check(packs.length<=2048,'合包总量过大');
  }
 }
 check(near.size===sources.size&&refined.every(t=>near.has(t.id)),'近景源块覆盖不完整');
 check(root.totals?.packs===packs.length&&root.totals?.nearMembers===near.size&&root.totals?.representations===representations.size,'索引累计数量不符');
 return {packs,textures:root.textures as StreamTexture[],sources:refined};
}
/** Per-pack bindings are fetched just before its single decoder slot is used. */
export async function loadBasePackMetadata(pack:BasePackRecord,allowedTextures:readonly StreamTexture[],signal:AbortSignal):Promise<BasePackMetadata>{
 const meta=JSON.parse(new TextDecoder().decode(await readStreamFile(new URL(pack.metadata.file,pack.baseUrl).href,pack.metadata,signal,128*1024)));
 check(meta.schemaVersion===1&&meta.kind==='physical-base-pack'&&meta.id===pack.id&&meta.sha256===pack.sha256&&meta.bytes===pack.bytes&&meta.logicalBytes===pack.logicalBytes&&meta.triangles===pack.triangles&&same(meta.bounds,pack.bounds),'合包说明与实际资源不符');
 check(Array.isArray(meta.members)&&meta.members.length===pack.members.length,'合包成员不完整');
 for(const [i,member] of pack.members.entries()){const actual=meta.members[i];check(actual.id===member.id&&actual.quality===member.quality&&['terrain','roads','buildings'].includes(actual.role)&&member.id.startsWith(actual.role+':')&&(actual.referenceSha256??actual.sourceSha256)===member.referenceSha256,'合包成员版本不符');}
 const allowed=new Map(allowedTextures.map(t=>[t.file,t])),images=new Set<string>();
 check(Array.isArray(meta.textures)&&meta.textures.length<=8&&meta.textures.every((t:StreamTexture)=>same(allowed.get(t.file),t)&&!images.has(t.file)&&!!images.add(t.file)),'合包贴图越出登记清单');
 check(Array.isArray(meta.materialOrigins)&&meta.materialOrigins.length<=64&&meta.materialOrigins.every((o:StreamMaterialOrigin)=>['terrain','roads','buildings'].includes(o.role)&&integer(o.index)&&!!o.record&&typeof o.record==='object'),'原始材质映射无效');
 check(Array.isArray(meta.nodes)&&meta.nodes.length>0&&meta.nodes.length<=512,'节点数量无效');
 const members=new Map(meta.members.map((m:{id:string;role:string;quality:string})=>[m.id,m])),names=new Set<string>(),covered=new Set<string>();
 for(const node of meta.nodes as BasePackMetadata['nodes']){const member=members.get(node.member) as {role:string;quality:string}|undefined;
  check(member&&node.role===member.role&&node.quality===member.quality&&typeof node.name==='string'&&node.name.length>0&&!names.has(node.name),'节点来源或名称无效');names.add(node.name);covered.add(node.member);
  const parent=pack.members.find(m=>m.id===node.member)?.parentSourceId;
  if(parent){const cell=parent.match(/^buildings:(-?\d+),(-?\d+)$/),mesh=node.name.match(/^block_(?:site_)?(-?\d+)_(-?\d+)_/);check(cell&&mesh&&cell[1]===mesh[1]&&cell[2]===mesh[2],'细分节点丢失原剔除中心');}
 }
 check(pack.members.every(m=>covered.has(m.id)),'成员缺少实际渲染节点');
 return {textures:meta.textures,materialOrigins:meta.materialOrigins,nodes:meta.nodes};
}
