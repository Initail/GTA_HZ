import {contentSha256 as hash} from './city-content-hash.ts';
/** Lossless transport only: the returned object keeps the complete gameplay data.
 * It bounds individual transfers/parses, not the retained road graph or JS heap. */
export const JSON_CHUNK_LIMITS=Object.freeze({manifest:256*1024,core:64*1024,chunk:2*1024*1024,
 total:96*1024*1024,chunks:512,items:150_000,requestMs:5000});
type Chunk={file:string;bytes:number;sha256:string;startIndex:number;count:number;sourceRange:[number,number]};
type ArrayEntry={key:string;count:number;sourceRange:[number,number];chunks:Chunk[]};
export type CityJsonManifest={schemaVersion:1;sourceSha256:string;sourceBytes:number;core:string;coreSha256:string;coreBytes:number;
 properties:{key:string;sourceRange:[number,number]}[];arrays:ArrayEntry[];transportOnly:true};
export type CityJsonSource={manifestUrl:string;manifestBytes:number;manifestSha256:string;sourceSha256:string};
type Options={signal?:AbortSignal;fetcher?:typeof fetch;yieldTask?:()=>Promise<void>;progress?:(loaded:number,total:number)=>void};
const hashPattern=/^[a-f0-9]{64}$/;
const integer=(n:unknown,max=Number.MAX_SAFE_INTEGER):n is number=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0&&n<=max;
const keyAllowed=(key:unknown):key is string=>typeof key==='string'&&key.length>0&&key.length<=128&&!['__proto__','constructor','prototype'].includes(key);
function requireValue(ok:unknown,message:string):asserts ok {if(!ok)throw Error('城市分块：'+message);}
export function checkCityJsonManifest(value:unknown,sourceSha256:string):CityJsonManifest{
 const m=value as CityJsonManifest;
 requireValue(hashPattern.test(sourceSha256)&&m?.schemaVersion===1&&m.transportOnly===true&&m.sourceSha256===sourceSha256,'源文件身份不一致');
 requireValue(integer(m.sourceBytes,JSON_CHUNK_LIMITS.total)&&m.sourceBytes>0&&m.core==='core.json'&&integer(m.coreBytes,JSON_CHUNK_LIMITS.core)&&m.coreBytes>0&&hashPattern.test(m.coreSha256),'核心元数据无效');
 requireValue(Array.isArray(m.properties)&&Array.isArray(m.arrays)&&m.properties.length+m.arrays.length<=128,'字段清单无效');
 const keys=new Set<string>(),files=new Set<string>();let count=0,total=m.coreBytes,items=0;
 const range=(r:unknown):r is [number,number]=>Array.isArray(r)&&r.length===2&&r.every(n=>integer(n,m.sourceBytes))&&r[0]<r[1];
 for(const row of [...m.properties,...m.arrays]){
  requireValue(row&&keyAllowed(row.key)&&!keys.has(row.key)&&range(row.sourceRange),'字段重复或源范围无效');keys.add(row.key);
 }
 for(const row of m.arrays){
  requireValue(integer(row.count,JSON_CHUNK_LIMITS.items)&&Array.isArray(row.chunks),'数组长度无效');let next=0,previous=row.sourceRange[0];items+=row.count;
  for(const c of row.chunks){
   requireValue(c&&typeof c.file==='string'&&/^array-\d+-\d+\.json$/.test(c.file)&&!files.has(c.file),'分块路径重复或无效');files.add(c.file);
   requireValue(integer(c.bytes,JSON_CHUNK_LIMITS.chunk)&&c.bytes>0&&hashPattern.test(c.sha256),'分块预算或哈希无效');
   requireValue(integer(c.count,row.count)&&c.count>0&&c.startIndex===next&&range(c.sourceRange)&&c.sourceRange[0]>previous&&c.sourceRange[1]<row.sourceRange[1],'数组缺块、乱序或范围无效');
   next+=c.count;previous=c.sourceRange[1];total+=c.bytes;count++;
  }
  requireValue(next===row.count,'数组条目不完整');
 }
 requireValue(count<=JSON_CHUNK_LIMITS.chunks&&total<=JSON_CHUNK_LIMITS.total&&items<=JSON_CHUNK_LIMITS.items,'累计数据超过上限');
 return m;
}

/** One bounded transfer at a time; cancel the stream on all failure paths. */
async function readJson(url:string,maximum:number,signal:AbortSignal,fetcher:typeof fetch,expected?:{bytes:number;sha256:string}){
 const request=AbortSignal.any([signal,AbortSignal.timeout(JSON_CHUNK_LIMITS.requestMs)]);
 request.throwIfAborted();const response=await fetcher(url,{signal:request,cache:'no-store'});
 const declared=Number(response.headers.get('content-length'));
 if(!response.ok||!response.headers.get('content-type')?.includes('application/json')||declared>maximum||!response.body){
  await response.body?.cancel();throw Error('城市分块：响应无效或超过上限');
 }
 const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 const cancel=()=>{void reader.cancel().catch(()=>{});};request.addEventListener('abort',cancel,{once:true});
 try{
  for(;;){request.throwIfAborted();const part=await reader.read();request.throwIfAborted();if(part.done)break;
   size+=part.value.byteLength;requireValue(size<=maximum,'下载超过上限');parts.push(part.value);}
  requireValue(!expected||size===expected.bytes,'分块长度不一致');
  const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}parts.length=0;
  if(expected)requireValue(await hash(bytes)===expected.sha256,'分块哈希不一致');request.throwIfAborted();
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)) as unknown;
 }finally{request.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});reader.releaseLock();}
}

export async function loadCityJsonChunks<T extends object>(source:CityJsonSource,options:Options={}):Promise<T>{
 const signal=options.signal??new AbortController().signal,fetcher=options.fetcher??fetch;
 const yieldTask=options.yieldTask??(()=>new Promise<void>(resolve=>setTimeout(resolve,0)));
 requireValue(integer(source.manifestBytes,JSON_CHUNK_LIMITS.manifest)&&source.manifestBytes>0&&hashPattern.test(source.manifestSha256),'分块清单缺少外部固定哈希或字节数');
 const m=checkCityJsonManifest(await readJson(source.manifestUrl,JSON_CHUNK_LIMITS.manifest,signal,fetcher,{bytes:source.manifestBytes,sha256:source.manifestSha256}),source.sourceSha256);
 const url=(file:string)=>new URL(file,source.manifestUrl).href;
 const core=await readJson(url(m.core),JSON_CHUNK_LIMITS.core,signal,fetcher,{bytes:m.coreBytes,sha256:m.coreSha256}) as Record<string,unknown>;
 requireValue(core&&typeof core==='object'&&!Array.isArray(core),'核心对象无效');
 const keys=[...m.properties,...m.arrays].map(row=>row.key);
 requireValue(Object.keys(core).length===keys.length&&keys.every(key=>Object.hasOwn(core,key)),'核心字段不一致');
 for(const row of m.arrays)requireValue(Array.isArray(core[row.key])&&(core[row.key] as unknown[]).length===0,'核心数组必须为空');
 const total=m.arrays.reduce((n,a)=>n+a.chunks.length,0);let loaded=0;options.progress?.(loaded,total);
 for(const row of m.arrays){
  const target=core[row.key] as unknown[];
  for(const c of row.chunks){
   signal.throwIfAborted();
   const data=await readJson(url(c.file),JSON_CHUNK_LIMITS.chunk,signal,fetcher,c) as {key:string;startIndex:number;sourceRange:number[];values:unknown[]};
   requireValue(data&&data.key===row.key&&data.startIndex===target.length&&Array.isArray(data.values)&&data.values.length===c.count&&Array.isArray(data.sourceRange)&&data.sourceRange.length===2&&data.sourceRange.every((n,i)=>n===c.sourceRange[i]),'分块内容或顺序不一致');
   // Do not spread a large array into a call stack. No record is filtered or rounded.
   for(const value of data.values)target.push(value);
   options.progress?.(++loaded,total);await yieldTask();signal.throwIfAborted();
  }
 }
 signal.throwIfAborted();return core as T;
}
