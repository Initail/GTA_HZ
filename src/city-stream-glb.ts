import {GLTFFileLoader} from '@babylonjs/loaders/glTF/glTFFileLoader.js';
import {MeshoptCompression} from '@babylonjs/core/Meshes/Compression/meshoptCompression.js';
import {Quaternion} from '@babylonjs/core/Maths/math.vector.js';
import {PBRMaterial} from '@babylonjs/core/Materials/PBR/pbrMaterial.js';
import type {Scene} from '@babylonjs/core/scene.js';
import type {AssetContainer} from '@babylonjs/core/assetContainer.js';
import type {AbstractMesh} from '@babylonjs/core/Meshes/abstractMesh.js';
import type {Material} from '@babylonjs/core/Materials/material.js';
import type {BaseTexture} from '@babylonjs/core/Materials/Textures/baseTexture.js';
// The base-tile contract admits exactly these glTF 2 extensions. Register them
// explicitly instead of pulling both glTF versions and unrelated extensions
// into this isolated loader. The full game's existing loaders are unchanged.
import '@babylonjs/loaders/glTF/2.0/glTFLoader.js';
import '@babylonjs/loaders/glTF/2.0/Extensions/EXT_meshopt_compression.js';
import '@babylonjs/loaders/glTF/2.0/Extensions/KHR_mesh_quantization.js';
import '@babylonjs/loaders/glTF/2.0/Extensions/KHR_materials_emissive_strength.js';
import {bindStreamTextureUrls,inspectStreamGlb,readStreamFile,streamJpegSize,STREAM_ASSET_LIMITS,type BaseStreamTile,type StreamGlbTile,type StreamTexture} from './city-stream-assets.ts';
import type {StreamHandle} from './city-stream-residency.ts';
import {preserveSharedContainerResources} from './city-stream-ownership.ts';

export type BaseStreamHandle=StreamHandle&{container:AssetContainer};
export type BaseStreamHooks<T extends StreamGlbTile=BaseStreamTile>={attach:(tile:T,container:AssetContainer,sourceMaterials:readonly unknown[])=>()=>void};
/** Bounded single-import loader. Callers supply world hooks and a validated
 * asset catalog; creating this object never starts an engine or grants a
 * full-scene resource/visual acceptance. */
export class CityStreamGlbLoader<T extends StreamGlbTile=BaseStreamTile>{
 private abort=new AbortController();private busy=false;private disposed=false;
 private textureUrls=new Map<string,string>();private textureBytes=0;private texturePixels=0;
 private handles=new Set<BaseStreamHandle>();
 private initializedRoles=new Set<string>();
 constructor(private scene:Scene,private textures:Readonly<Record<string,readonly StreamTexture[]>>|((tile:T)=>readonly StreamTexture[]),decoderUrl:string,private hooks?:BaseStreamHooks<T>){
  const url=new URL(decoderUrl,location.href);if(url.origin!==location.origin)throw Error('街区解码器必须由当前验证服务提供');
  MeshoptCompression.Configuration={decoder:{url:url.href}};
  scene.onDisposeObservable.addOnce(()=>this.dispose());
 }
 async load(tile:T,signal:AbortSignal):Promise<BaseStreamHandle>{
  if(this.busy||this.disposed||this.scene.isDisposed)throw Error('街区加载器忙碌或已释放');this.busy=true;
  const active=AbortSignal.any([signal,this.abort.signal]);let container:AssetContainer|undefined,plugin:GLTFFileLoader|undefined,transferred=false,detach:(()=>void)|undefined;
  const partialMeshes=new Set<AbstractMesh>(),partialMaterials=new Set<Material>(),partialTextures=new Set<BaseTexture>();
  try{
   active.throwIfAborted();const files=typeof this.textures==='function'?this.textures(tile):this.textures[tile.role];if(!files)throw Error('街区缺少配套贴图清单');
   const bytes=await readStreamFile(new URL(tile.file,tile.baseUrl).href,tile,active,STREAM_ASSET_LIMITS.glb);
   const inspected=inspectStreamGlb(bytes,tile,files);const urls:string[]=[];
   for(const file of files){
    if(!/^textures\/(terrain|roads|buildings)-\d+\.jpg$/.test(file.file))throw Error('街区贴图路径无效');
    const key=new URL(file.file,tile.baseUrl).href+'#'+file.sha256;let url=this.textureUrls.get(key);
    if(!url){
     if(this.textureBytes+file.bytes>STREAM_ASSET_LIMITS.texturePool)throw Error('街区贴图总字节超限');
     const texture=await readStreamFile(new URL(file.file,tile.baseUrl).href,file,active,STREAM_ASSET_LIMITS.texture),size=streamJpegSize(texture);
     if(this.texturePixels+size.width*size.height>STREAM_ASSET_LIMITS.texturePixels)throw Error('街区贴图总像素超限');
     active.throwIfAborted();url=URL.createObjectURL(new Blob([texture],{type:'image/jpeg'}));this.textureUrls.set(key,url);this.textureBytes+=texture.length;this.texturePixels+=size.width*size.height;
    }
    urls.push(url);
   }
   active.throwIfAborted();const bound=bindStreamTextureUrls(bytes,tile,files,urls);
   // glTF decoding/upload may not be interruptible. The residency controller
   // keeps the one-import slot occupied until this resolves, then disposes stale results.
   // Own the plugin instance so failed imports can release allocations created
   // before Babylon has returned its successful AssetContainer.
   plugin=new GLTFFileLoader();
   // Prime the small, pinned terrain/road material catalog once. The existing
   // world surface controllers can then keep the same material identities as
   // tiles arrive; this never loads any additional geometry.
   if(!Array.isArray(inspected.doc.materials)||inspected.doc.materials.length>64)throw Error('Base material catalog exceeds budget');
   const materialCatalog=tile.role==='pack'?JSON.stringify([inspected.doc.materials,inspected.doc.images]):tile.role;
   plugin.loadAllMaterials=!!this.hooks&&tile.role!=='buildings'&&!this.initializedRoles.has(materialCatalog);
   plugin.onMeshLoadedObservable.add(m=>partialMeshes.add(m));plugin.onMaterialLoadedObservable.add(m=>partialMaterials.add(m));plugin.onTextureLoadedObservable.add(t=>partialTextures.add(t));
   const completed=plugin.whenCompleteAsync();void completed.catch(()=>{});
   const jsonLength=new DataView(bound.buffer).getUint32(12,true),binStart=20+jsonLength+8;
   container=await plugin.loadAssetContainerAsync(this.scene,{json:JSON.parse(new TextDecoder().decode(bound.subarray(20,20+jsonLength))),bin:{byteLength:bound.length-binStart,readAsync:async(offset,length)=>{
    if(!Number.isSafeInteger(offset)||!Number.isSafeInteger(length)||offset<0||length<0||binStart+offset+length>bound.length)throw Error('街区解码范围无效');
    return bound.subarray(binStart+offset,binStart+offset+length);
   }}},'',undefined,tile.id+'.glb');await completed;
   active.throwIfAborted();if(this.scene.isDisposed)throw Error('街区场景已释放');
   const root=container.meshes[0];if(!root)throw Error('街区模型缺少根节点');root.rotationQuaternion=Quaternion.Identity();root.setEnabled(false);
   for(const mesh of container.meshes){mesh.isPickable=false;mesh.receiveShadows=true;if(mesh.material instanceof PBRMaterial){mesh.material.environmentIntensity=1;mesh.material.forceIrradianceInFragment=true;mesh.material.maxSimultaneousLights=8;}if(mesh.getTotalVertices())mesh.freezeWorldMatrix();}
   // Install hidden geometry before material hooks so the original scene-wide
   // architecture retirement checks see every live mesh using a material.
   container.addAllToScene();detach=this.hooks?.attach(tile,container,inspected.doc.materials);
   active.throwIfAborted();
   const owned=container,release=detach;let disposed=false;
   const handle:BaseStreamHandle={container:owned,setVisible:visible=>{if(!disposed)root.setEnabled(visible);},dispose:()=>{if(disposed)return;disposed=true;this.handles.delete(handle);release?.();preserveSharedContainerResources(this.scene,owned);owned.dispose();}};
   this.handles.add(handle);this.initializedRoles.add(materialCatalog);transferred=true;container=undefined;return handle;
  }finally{
   if(!transferred){detach?.();plugin?.dispose();if(container){preserveSharedContainerResources(this.scene,container);container.dispose();}else{for(const mesh of [...partialMeshes].reverse())mesh.dispose(false,false);for(const material of partialMaterials)material.dispose(false,false);for(const texture of partialTextures)texture.dispose();}}
   this.busy=false;
  }
 }
 dispose(){if(this.disposed)return;this.disposed=true;this.abort.abort();for(const handle of [...this.handles])handle.dispose();for(const url of this.textureUrls.values())URL.revokeObjectURL(url);this.textureUrls.clear();this.textureBytes=this.texturePixels=0;}
 get stats(){return {busy:this.busy,disposed:this.disposed,containers:this.handles.size,textureFiles:this.textureUrls.size,encodedTextureBytes:this.textureBytes,texturePixels:this.texturePixels,estimatedRgbaMipBytes:Math.ceil(this.texturePixels*4*4/3)};}
}
