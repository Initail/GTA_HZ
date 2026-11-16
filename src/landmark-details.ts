import {cityAssetUrl} from './city-config.ts';
import type {CityData,Landmark,V2} from './city-types.ts';

export type DetailLandmark=Landmark & {
 photoDistance?:number;photoTargetHeight?:number;photoElevation?:number;photoAngle?:number;
 detailCollision?:boolean;sourceStatus?:string;candidateKind?:string;
};

/** Candidate block models draw parks as flat `_park` / `_water` slabs 0–0.8 m above the ground
 * (深圳湾公园 874×235 m, 人才公园 414×351 m, 红树林 1123×126 m …). They ignore terrain, bypass the
 * bay water shader and read as glossy blue sheets with trees poking through in aerial view, so the
 * runtime drops them: every candidate `_water` slab, plus `_park` slabs of park-kind candidates that
 * are flat (a 49 m 笔架山 block is terrain, not a slab). Building candidates are untouched.
 */
export function isCandidateGroundSlab(meshName:string,heightSpan:number,manifest:Pick<LandmarkCandidateManifest,'landmarks'>){
 const match=meshName.match(/^landmark_(.+)_(water|park)$/);
 if(!match)return false;
 if(match[2]==='water')return true;
 const landmark=manifest.landmarks.find(l=>l.id.replace(/-/g,'_')===match[1]);
 return landmark?.candidateKind==='park'&&heightSpan<1.5;
}
export type TerrainGrid={x0:number;z0:number;dx:number;dz:number;columns:number;rows:number;heights:number[]};
export type TerrainDetail={schemaVersion:1;id:string;grid:TerrainGrid};
export type DetailCollisionFootprint={id:string;rings:V2[][];minY?:number;maxY?:number;blocksRoad?:boolean};
export type LandmarkDetailManifest={
 schemaVersion:1;asset:string;replacedMeshPrefixes:string[];baseBuildingIds:string[];
 replacedCollisionIds?:string[];
 landmarks:DetailLandmark[];collisionFootprints:DetailCollisionFootprint[];
 terrain:{url:string;kind?:'detail-grid'}|{kind:'city-geography';cityId:'hangzhou';manifestSha256:string};
};
export type SharedDetailTerrain={cityId:'hangzhou';manifestSha256:string;heightAt:(x:number,z:number)=>number};

/** A city candidate can already contain the exact detail colliders. Applying
 * its manifest again replaces those IDs, preserving each explicit Y interval. */
export function mergeDetailCollisions(data:CityData,baseBuildingIds:readonly string[],footprints:readonly DetailCollisionFootprint[],replacedCollisionIds:readonly string[]=[]){
 if(!Array.isArray(replacedCollisionIds)||replacedCollisionIds.some(id=>typeof id!=='string'||!id)||new Set(replacedCollisionIds).size!==replacedCollisionIds.length)throw new Error('Invalid replaced detail collision IDs');
 const incoming=new Set<string>();
 for(const f of footprints){
  if(!f.id||incoming.has(f.id))throw new Error('Duplicate detail collision '+f.id);
  if(!Array.isArray(f.rings)||!f.rings.length||f.rings.some(r=>r.length<3||r.some(p=>p.length!==2||!p.every(Number.isFinite))))throw new Error('Invalid detail footprint '+f.id);
  if((f.minY!==undefined||f.maxY!==undefined)&&(!Number.isFinite(f.minY)||!Number.isFinite(f.maxY)||f.maxY!<=f.minY!))throw new Error('Invalid detail vertical range '+f.id);
  if(f.blocksRoad!==undefined&&typeof f.blocksRoad!=='boolean')throw new Error('Invalid road barrier flag '+f.id);
  incoming.add(f.id);
 }
 const replaced=new Set([...baseBuildingIds,...incoming]);
 const retired=new Set(replacedCollisionIds);
 data.buildings=data.buildings.filter(b=>{const id=(b as typeof b&{id?:string}).id??'';return !replaced.has(id)&&!(b.style==='landmark-detail'&&retired.has(id));});
 for(const footprint of footprints)data.buildings.push({...footprint,height:1,style:'landmark-detail'});
}

/** Returns the exact same triangulated height as the exported terrain surface.
 * Grid rows increase north (+z); Blender east/north/up becomes game east/up/north.
 * Outside the detail patch the established city ground plane remains zero.
 */
export function terrainHeight(grid:TerrainGrid|undefined,x:number,z:number):number {
 if(!grid||!Number.isFinite(x)||!Number.isFinite(z))return 0;
 const c=(x-grid.x0)/grid.dx,r=(z-grid.z0)/grid.dz;
 if(c<0||r<0||c>grid.columns-1||r>grid.rows-1)return 0;
 const i=Math.min(Math.floor(c),grid.columns-2),j=Math.min(Math.floor(r),grid.rows-2);
 const u=c-i,v=r-j,k=j*grid.columns+i,h=grid.heights;
 // Each cell is split SW->NE, matching build_landmark_details.py.
 return u>=v?h[k]*(1-u)+h[k+1]*(u-v)+h[k+grid.columns+1]*v
             :h[k]*(1-v)+h[k+grid.columns+1]*u+h[k+grid.columns]*(v-u);
}

export async function loadLandmarkDetails(data:CityData,sharedTerrain?:SharedDetailTerrain):Promise<{
 manifest:LandmarkDetailManifest;terrain:TerrainDetail|null;heightAt:(x:number,z:number)=>number;
}|null>{
 const response=await fetch(cityAssetUrl("landmark-detail.json"));
 if(response.status===404||(response.ok&&response.headers.get('content-type')?.includes('text/html')))return null;
 if(!response.ok)throw new Error('重点地标清单加载失败');
 const manifest=await response.json() as LandmarkDetailManifest;
 if(manifest.schemaVersion!==1||!manifest.asset||!Array.isArray(manifest.landmarks))throw new Error('重点地标清单格式不受支持');
 let terrain:TerrainDetail|null=null,heightAt:(x:number,z:number)=>number;
 if(manifest.terrain?.kind==='city-geography'){
  const ref=manifest.terrain;
  if(data.meta.cityId!=='hangzhou'||ref.cityId!=='hangzhou'||sharedTerrain?.cityId!=='hangzhou'||
     !/^[0-9a-f]{64}$/.test(ref.manifestSha256)||ref.manifestSha256!==sharedTerrain.manifestSha256)throw new Error('地标与城市全域高程绑定不一致');
  heightAt=sharedTerrain.heightAt;
 }else{
  if(data.meta.cityId==='hangzhou'||!manifest.terrain?.url)throw new Error('地标需要明确的城市高程来源');
  const demResponse=await fetch(manifest.terrain.url);
  if(!demResponse.ok)throw new Error('地标高程加载失败');
  terrain=await demResponse.json() as TerrainDetail;const grid=terrain.grid;
  if(terrain.schemaVersion!==1||!grid||grid.columns<2||grid.rows<2||grid.dx<=0||grid.dz<=0||
     grid.heights.length!==grid.columns*grid.rows||!grid.heights.every(Number.isFinite))throw new Error('地标高程网格无效');
  heightAt=(x,z)=>terrainHeight(grid,x,z);
 }
 mergeDetailCollisions(data,manifest.baseBuildingIds,manifest.collisionFootprints,manifest.replacedCollisionIds);
 for(const landmark of manifest.landmarks){
  const index=data.landmarks.findIndex(m=>m.id===landmark.id);
  if(index>=0)data.landmarks[index]={...data.landmarks[index],...landmark};else data.landmarks.push(landmark);
 }
 data.meta.counts.landmarks=data.landmarks.length;
 return {manifest,terrain,heightAt};
}

export type LandmarkCandidateManifest={
 schemaVersion:1;asset:string;replacedMeshPrefixes:string[];landmarks:DetailLandmark[];
 baseBuildingIds?:string[];collisionFootprints?:DetailCollisionFootprint[];
 replacedCollisionIds?:string[];
 sources:{id:string;runDir:string;glbSha256:string;triangles:number}[];
};

/** Optional second increment produced by scripts/integrate_landmark_candidates.mjs:
 * merged single-object candidates from artifacts/landmark-candidates. Records for
 * ids already in city.json keep the city's placement and collision behaviour;
 * new ids are added as map/photo destinations only. Missing file means no layer.
 */
export async function loadLandmarkCandidates(data:CityData):Promise<LandmarkCandidateManifest|null>{
 const response=await fetch(cityAssetUrl("landmark-candidates.json"));
 if(response.status===404||(response.ok&&response.headers.get('content-type')?.includes('text/html')))return null;
 if(!response.ok)throw new Error('候选地标清单加载失败');
 const manifest=await response.json() as LandmarkCandidateManifest;
 if(manifest.schemaVersion!==1||!manifest.asset||!Array.isArray(manifest.landmarks)||!Array.isArray(manifest.replacedMeshPrefixes))throw new Error('候选地标清单格式不受支持');
 for(const landmark of manifest.landmarks){
  const index=data.landmarks.findIndex(m=>m.id===landmark.id);
  if(index>=0){const base=data.landmarks[index];data.landmarks[index]={...base,height:landmark.height,photoDistance:landmark.photoDistance,photoTargetHeight:landmark.photoTargetHeight,photoElevation:landmark.photoElevation};}
  else data.landmarks.push(landmark);
 }
 // Base blocks cut from buildings.glb keep their OSM footprint for driving collision.
 if(manifest.baseBuildingIds?.length||manifest.collisionFootprints?.length||manifest.replacedCollisionIds?.length)mergeDetailCollisions(data,manifest.baseBuildingIds??[],manifest.collisionFootprints??[],manifest.replacedCollisionIds);
 data.meta.counts.landmarks=data.landmarks.length;
 return manifest;
}
