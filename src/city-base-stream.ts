import type {Scene} from '@babylonjs/core/scene.js';
import {loadBaseStreamManifest} from './city-stream-manifest.ts';
import {CityStreamGlbLoader,type BaseStreamHooks,type BaseStreamHandle} from './city-stream-glb.ts';
import type {AssetContainer} from '@babylonjs/core/assetContainer.js';
import {CityStreamResidency,BASE_STREAM_LIMITS,catalogStreamBudget,type StreamBudget} from './city-stream-residency.ts';
import type {BaseStreamTile,StreamTexture} from './city-stream-assets.ts';
import {planBaseStream,type BaseStreamView} from './city-base-stream-plan.ts';
import {loadBasePackIndex,loadBasePackMetadata,type BasePackRecord,type BasePackMetadata,type PackIndexSource} from './city-stream-pack-manifest.ts';
import {CityPackResidency,type PackHandle} from './city-stream-pack-residency.ts';
import {createPackMemberMask} from './city-stream-pack-mask.ts';
type Source={manifestUrl:string;manifestBytes:number;manifestSha256:string;sourceSha256:string};
export type BaseStreamSources={terrain:Source;roads:Source;buildings:Source;decoderUrl:string;packs?:PackIndexSource};
export type BaseWorldHooks=BaseStreamHooks&{attachPack?:(pack:BasePackRecord,container:AssetContainer,materials:readonly unknown[],metadata:BasePackMetadata)=>()=>void};
export class CityBaseStream {
 private stream:CityStreamResidency<BaseStreamTile,Awaited<ReturnType<CityStreamGlbLoader['load']>>>|null=null;
 private loader:CityStreamGlbLoader|null=null;private abort=new AbortController();
 private packed:CityPackResidency<BaseStreamHandle&PackHandle,BasePackRecord>|null=null;private packLoader:CityStreamGlbLoader<BasePackRecord>|null=null;
 private tiles:BaseStreamTile[]=[];private plan:ReturnType<typeof planBaseStream>|null=null;
 private budget:Readonly<StreamBudget>=BASE_STREAM_LIMITS;
 private key='';private operation:Promise<void>=Promise.resolve();private disposed=false;
 constructor(private scene:Scene,private sources:BaseStreamSources,private hooks:BaseWorldHooks){scene.onDisposeObservable.addOnce(()=>this.dispose());}
 async init(view:BaseStreamView){
  const textures:Record<string,StreamTexture[]>={};
  for(const role of ['terrain','roads','buildings'] as const){
   const source=this.sources[role],url=new URL(source.manifestUrl,location.href).href;
   const manifest=await loadBaseStreamManifest(url,{file:'manifest.json',bytes:source.manifestBytes,sha256:source.manifestSha256},role,source.sourceSha256,this.abort.signal);
   this.tiles.push(...manifest.tiles);textures[role]=manifest.textures;
  }
  this.abort.signal.throwIfAborted();
  // Full coverage uses the original verified tiles, including their complete
  // geometry. Optional compatibility LOD packs retain their separate policy.
  if(this.sources.packs&&view.rangeProfile!=='full'){await this.initPacked(textures);await this.request(view);return;}
  const full=view.rangeProfile==='full';this.budget=full?catalogStreamBudget(this.tiles):BASE_STREAM_LIMITS;
  this.loader=new CityStreamGlbLoader(this.scene,textures,this.sources.decoderUrl,this.hooks);
  this.stream=new CityStreamResidency(this.tiles,(tile,signal)=>this.loader!.load(tile,signal),this.budget,full?'full-city':'compatible');
  await this.request(view);
 }
 private async initPacked(textures:Record<string,StreamTexture[]>){
  if(!this.hooks.attachPack)throw Error('合包缺少实际世界图层接入');
  const catalog=await loadBasePackIndex(this.sources.packs!,this.tiles,[...textures.terrain,...textures.roads,...textures.buildings],{terrain:this.sources.terrain.manifestSha256,roads:this.sources.roads.manifestSha256,buildings:this.sources.buildings.manifestSha256},this.abort.signal);
  this.abort.signal.throwIfAborted();
  this.tiles=catalog.sources;
  let pending:{id:string;metadata:BasePackMetadata;mask?:ReturnType<typeof createPackMemberMask>}|null=null;
  this.packLoader=new CityStreamGlbLoader<BasePackRecord>(this.scene,pack=>{if(!pending||pending.id!==pack.id)throw Error('合包说明不在当前导入事务中');return pending.metadata.textures;},this.sources.decoderUrl,{attach:(pack,container,materials)=>{
   if(!pending||pending.id!==pack.id||pending.metadata.materialOrigins.length!==materials.length)throw Error('合包材质与节点映射不完整');
   pending.mask=createPackMemberMask(container,pending.metadata.nodes);
   return this.hooks.attachPack!(pack,container,materials,pending.metadata);
  }});
  this.packed=new CityPackResidency(this.tiles,catalog.packs,async(pack,signal)=>{
   const metadata=await loadBasePackMetadata(pack,catalog.textures,signal);signal.throwIfAborted();
   const transaction:{id:string;metadata:BasePackMetadata;mask?:ReturnType<typeof createPackMemberMask>}={id:pack.id,metadata};pending=transaction;
   let handle:BaseStreamHandle|undefined;
   try{handle=await this.packLoader!.load(pack,signal);if(!transaction.mask)throw Error('合包可见成员尚未绑定');return Object.assign(handle,{selectMembers:transaction.mask.selectMembers});}
   catch(error){handle?.dispose();throw error;}
   finally{if(pending===transaction)pending=null;}
  });
 }
 request(view:BaseStreamView){
  if(this.packed)return this.packed.request(view);
  if(this.disposed||!this.stream)return Promise.resolve();
  const plan=this.plan=planBaseStream(this.tiles,view,this.budget),key=plan.required.map(t=>t.id).join('|')+';'+plan.retained.map(t=>t.id).join('|');
  if(!plan.admitted){this.key='';this.operation=this.stream.select(view.x,view.z,[],[]);return this.operation;}
  if(key===this.key)return this.operation;
  this.key=key;this.operation=this.stream.select(view.x,view.z,plan.required.map(t=>t.id),plan.retained.map(t=>t.id));return this.operation;
 }
 get stats(){if(this.packed){const s=this.packed.stats;return {...s,loader:this.packLoader?.stats??null,sourceTiles:this.tiles.length,limits:BASE_STREAM_LIMITS};}return {ready:!!this.plan?.admitted&&!!this.stream?.stats.ready,plan:this.plan?{cost:this.plan.cost,budget:this.plan.budget,exceeded:this.plan.exceeded,required:this.plan.required.length}:null,residency:this.stream?.stats??null,loader:this.loader?.stats??null,sourceTiles:this.tiles.length,limits:this.budget};}
 get meshes(){return this.packed?.handles.flatMap(h=>h.container.meshes)??this.stream?.handles.flatMap(h=>h.container.meshes)??[];}
 get maximumWorldHeight(){return this.tiles.reduce((height,tile)=>Math.max(height,tile.bounds.max[1]),0);}
 dispose(){if(this.disposed)return;this.disposed=true;this.abort.abort();this.packed?.dispose();this.packLoader?.dispose();this.stream?.dispose();this.loader?.dispose();}
}
