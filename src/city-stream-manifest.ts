import {readStreamFile,STREAM_ASSET_LIMITS,type BaseStreamTile,type StreamFile,type StreamTexture} from './city-stream-assets.ts';
type Role=BaseStreamTile['role'];
const nonnegative=(n:unknown):n is number=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0;
const validFile=(file:StreamFile,max:number)=>file&&nonnegative(file.bytes)&&file.bytes>0&&file.bytes<=max&&typeof file.sha256==='string'&&/^[0-9a-f]{64}$/.test(file.sha256);
/** Manifest hash is supplied by a separate release descriptor. Never trust a
 * manifest's self-reported pass flag as admission or city identity evidence. */
export async function loadBaseStreamManifest(url:string,record:StreamFile,role:Role,sourceSha256:string,signal:AbortSignal){
 const bytes=await readStreamFile(url,record,signal,256*1024),m=JSON.parse(new TextDecoder().decode(bytes));
 if(m.schemaVersion!==1||m.role!==role||m.source?.sha256!==sourceSha256||m.tileSizeGame!==640||!Array.isArray(m.tiles)||m.tiles.length>1024||!Array.isArray(m.textures)||m.textures.length>8)throw Error('街区清单身份或范围无效');
 const files=new Set<string>();const ids=new Set<string>();const baseUrl=new URL('.',url).href;
 const textures:StreamTexture[]=m.textures.map((t:StreamTexture)=>{
  if(!validFile(t,STREAM_ASSET_LIMITS.texture)||!new RegExp('^textures/'+role+'-\\d+\\.jpg$').test(t.file)||files.has(t.file))throw Error('街区贴图清单无效');files.add(t.file);return {...t};
 });
 if(textures.reduce((n,t)=>n+t.bytes,0)>STREAM_ASSET_LIMITS.texturePool)throw Error('街区配套贴图超限');
 const tiles:BaseStreamTile[]=m.tiles.map((t:BaseStreamTile)=>{
  if(!validFile(t,STREAM_ASSET_LIMITS.glb)||!new RegExp('^tiles/'+role+'--?\\d+--?\\d+\\.glb$').test(t.file)||files.has(t.file)||typeof t.id!=='string'||!t.id.startsWith(role+':')||ids.has(t.id)||!nonnegative(t.logicalBytes)||!nonnegative(t.triangles)||!Array.isArray(t.bounds?.min)||!Array.isArray(t.bounds?.max)||t.bounds.min.length!==3||t.bounds.max.length!==3||t.bounds.min.some((v:number,i:number)=>!Number.isFinite(v)||!Number.isFinite(t.bounds.max[i])||v>t.bounds.max[i]))throw Error('街区几何清单无效');
  if(t.parentSourceId!==undefined||t.lodBounds!==undefined)throw Error('原始街区清单不能自声明父块或质量分区');
  files.add(t.file);ids.add(t.id);return {...t,role,baseUrl};
 });
 for(const key of ['bytes','logicalBytes','triangles'] as const)if(tiles.reduce((n,t)=>n+t[key],0)!==m.totals?.[key])throw Error('街区累计资源与清单不一致');
 if(tiles.length!==m.totals?.tiles)throw Error('街区数量不完整');
 return {tiles,textures,sourceSha256};
}
