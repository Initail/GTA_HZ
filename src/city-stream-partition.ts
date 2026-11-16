import {readStreamFile,STREAM_ASSET_LIMITS,type BaseStreamTile,type StreamFile} from './city-stream-assets.ts';
const integer=(n:unknown):n is number=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0;
const hash=(s:unknown):s is string=>typeof s==='string'&&/^[0-9a-f]{64}$/.test(s);
function check(ok:unknown,message:string):asserts ok{if(!ok)throw Error('街区细分：'+message);}
type Partition={schemaVersion:number;kind:string;parent:{id:string;sha256:string};children:BaseStreamTile[];geometryCoverage:StreamFile;representationMode?:'split'|'whole-parent'};
/** The separately pinned index chooses an audited partition. These checks bind
 * it to the original tile and reject missing counts/bounds; only the offline
 * directed-triangle/attribute audit proves geometric partition equivalence. */
export function applyBaseStreamPartition(tiles:readonly BaseStreamTile[],doc:Partition,baseUrl:string):BaseStreamTile[]{
 check(doc?.schemaVersion===1&&doc.kind==='city-base-source-partition'&&doc.parent,'格式无效');
 const parent=tiles.find(t=>t.id===doc.parent.id);
 check(parent&&parent.role==='buildings'&&!parent.parentSourceId&&!parent.lodBounds&&/^buildings:-?\d+,-?\d+$/.test(parent.id)&&doc.parent.sha256===parent.sha256,'父块缺失或版本不符');
 check(doc.representationMode===undefined||['split','whole-parent'].includes(doc.representationMode),'表示模式无效');
 check(doc.geometryCoverage&&hash(doc.geometryCoverage.sha256)&&integer(doc.geometryCoverage.bytes)&&doc.geometryCoverage.bytes>0&&typeof doc.geometryCoverage.file==='string'&&/^[a-zA-Z0-9_./-]+\.json$/.test(doc.geometryCoverage.file)&&!doc.geometryCoverage.file.split('/').includes('..')&&!doc.geometryCoverage.file.startsWith('/'),'几何审计记录无效');
 check(Array.isArray(doc.children)&&doc.children.length>1&&doc.children.length<=128,'子块数量无效');
 const ids=new Set(tiles.map(t=>t.id)),files=new Set<string>();
 const children=doc.children.map(t=>{
  check(typeof t.id==='string'&&t.id.startsWith(parent.id+'/')&&/^[a-zA-Z0-9_-]+$/.test(t.id.slice(parent.id.length+1))&&!ids.has(t.id)&&t.parentSourceId===parent.id,'子块身份或原剔除中心不符');
  check(typeof t.file==='string'&&/^groups\/[a-zA-Z0-9_-]+\/group\.glb$/.test(t.file)&&!files.has(t.file)&&integer(t.bytes)&&t.bytes>0&&t.bytes<=STREAM_ASSET_LIMITS.glb&&hash(t.sha256)&&integer(t.logicalBytes)&&t.logicalBytes>0&&t.logicalBytes<=32*1024*1024&&integer(t.triangles)&&t.triangles>0,'子块资源无效');
  check(Array.isArray(t.bounds?.min)&&Array.isArray(t.bounds?.max)&&t.bounds.min.length===3&&t.bounds.max.length===3&&t.bounds.min.every((v,i)=>Number.isFinite(v)&&Number.isFinite(t.bounds.max[i])&&v<=t.bounds.max[i]&&v>=parent.bounds.min[i]&&t.bounds.max[i]<=parent.bounds.max[i]),'子块超出原范围');
  ids.add(t.id);files.add(t.file);return {...t,role:parent.role,baseUrl,parentSourceId:parent.id};
 });
 for(const key of ['logicalBytes','triangles'] as const)check(children.reduce((n,t)=>n+t[key],0)===parent[key],'完整近景覆盖数量不符');
 for(let axis=0;axis<3;axis++)check(Math.min(...children.map(t=>t.bounds.min[axis]))===parent.bounds.min[axis]&&Math.max(...children.map(t=>t.bounds.max[axis]))===parent.bounds.max[axis],'完整近景外包范围不符');
 if(doc.representationMode==='whole-parent')return tiles.map(t=>t===parent?{...parent,lodBounds:children.map(c=>c.bounds)}:t);
 return tiles.flatMap(t=>t===parent?children:[t]);
}
export async function loadBaseStreamPartitions(records:readonly StreamFile[]|undefined,baseUrl:string,originals:readonly BaseStreamTile[],signal:AbortSignal){
 if(records===undefined)return [...originals];
 check(Array.isArray(records)&&records.length>0&&records.length<=64,'分区清单数量无效');
 let tiles=[...originals];const files=new Set<string>();
 for(const record of records){
  check(record&&typeof record.file==='string'&&/^partitions\/[a-zA-Z0-9_-]+\.json$/.test(record.file)&&!files.has(record.file),'分区清单路径无效');files.add(record.file);
  const bytes=await readStreamFile(new URL(record.file,baseUrl).href,record,signal,128*1024);
  tiles=applyBaseStreamPartition(tiles,JSON.parse(new TextDecoder().decode(bytes)),baseUrl);
  check(tiles.length<=8192,'细分总量过大');
 }
 return tiles;
}
