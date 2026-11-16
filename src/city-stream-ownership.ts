import type {AssetContainer} from '@babylonjs/core/assetContainer.js';
import type {Scene} from '@babylonjs/core/scene.js';
import type {Material} from '@babylonjs/core/Materials/material.js';
import type {BaseTexture} from '@babylonjs/core/Materials/Textures/baseTexture.js';
import type {BaseStreamTile,StreamMaterialOrigin} from './city-stream-assets.ts';
export type {StreamMaterialOrigin} from './city-stream-assets.ts';

/** Imported source materials for terrain/roads are scene-owned, like the
 * existing architecture cache. Slot identity comes from the actual glTF
 * material pointer and its source JSON, never a possibly duplicated name. */
export class CityBaseMaterialCache {
 private entries=new Map<string,{signature:string;material:Material}>();
 private textures=new Set<BaseTexture>();private disposed=false;
 constructor(private scene:Scene){scene.onDisposeObservable.addOnce(()=>this.dispose());}
 adopt(container:AssetContainer,role:BaseStreamTile['role'],records:readonly unknown[]){
  if(this.disposed)throw Error('Base material cache disposed');
  if(role==='buildings')return; // The existing architecture cache owns these replacements.
  this.adoptMapped(container,records.map((record,index)=>({role,index,record})));
 }
 /** Packed material slots are local to that file. Preserve the original role
  * and slot as the shared identity, including its original texture indices. */
 adoptMapped(container:AssetContainer,origins:readonly StreamMaterialOrigin[]){
  if(this.disposed)throw Error('Base material cache disposed');
  const replacements=new Map<Material,Material>();
  const planned: {key:string;signature:string;material:Material}[]=[];
  const seen=new Set<string>();
  for(const material of container.materials){
   const raw:unknown=(material as unknown as {_internalMetadata?:{gltf?:{pointers?:unknown}}})._internalMetadata?.gltf?.pointers??[];
   if(!Array.isArray(raw)||raw.some(p=>typeof p!=='string'))throw Error('Source material pointer missing or ambiguous');
   const pointers=raw as string[];
   const indices=[...new Set(pointers.filter(p=>/^\/materials\/\d+$/.test(p)).map(p=>Number(p.slice(11))))];
   const origin=origins[indices[0]];
   if(indices.length!==1||!origin||!['terrain','roads','buildings'].includes(origin.role)||!Number.isSafeInteger(origin.index)||origin.index<0||!origin.record)throw Error('Source material pointer missing or ambiguous');
   if(origin.role==='buildings')continue;
   const key=origin.role+':'+origin.index,signature=JSON.stringify(origin.record),existing=this.entries.get(key);
   if(seen.has(key))throw Error('Duplicate original material in physical pack');seen.add(key);
   if(existing&&existing.signature!==signature)throw Error('Source material changed within a pinned release');
   if(existing)replacements.set(material,existing.material);
   else planned.push({key,signature,material});
  }
  if(this.entries.size+planned.length>64)throw Error('Shared base material budget exceeded');
  for(const entry of planned){this.entries.set(entry.key,entry);for(const texture of entry.material.getActiveTextures())this.textures.add(texture);}
  for(const mesh of container.meshes)if(mesh.material&&replacements.has(mesh.material))mesh.material=replacements.get(mesh.material)!;
  const shared=new Set([...this.entries.values()].map(e=>e.material));
  // Removing ownership entries also keeps removeAllFromScene from unregistering
  // a shared object when one tile leaves the world.
  container.materials=container.materials.filter(m=>!shared.has(m));
  container.textures=container.textures.filter(t=>!this.textures.has(t));
 }
 dispose(){if(this.disposed)return;this.disposed=true;for(const {material} of this.entries.values())material.dispose(false,false);for(const texture of this.textures)texture.dispose();this.entries.clear();this.textures.clear();}
 get stats(){return {materials:this.entries.size,textures:this.textures.size,disposed:this.disposed};}
}

/** An architecture fallback may borrow an imported texture while its atlas
 * downloads. Keep externally referenced objects alive; the scene/cache owns
 * their final disposal. Mirrors and shared shader textures are never tile-owned. */
export function preserveSharedContainerResources(scene:Scene,container:AssetContainer){
 const ownedMeshes=new Set(container.meshes),ownedMaterials=new Set(container.materials);
 const sharedMaterials=new Set(scene.materials.filter(m=>!ownedMaterials.has(m)));
 for(const mesh of scene.meshes)if(!ownedMeshes.has(mesh)&&mesh.material)sharedMaterials.add(mesh.material);
 const sharedTextures=new Set<BaseTexture>();
 for(const material of sharedMaterials)for(const texture of material.getActiveTextures())sharedTextures.add(texture);
 if(scene.environmentTexture)sharedTextures.add(scene.environmentTexture);
 if(scene.environmentBRDFTexture)sharedTextures.add(scene.environmentBRDFTexture);
 container.materials=container.materials.filter(m=>!sharedMaterials.has(m));
 container.textures=container.textures.filter(t=>!sharedTextures.has(t));
}
