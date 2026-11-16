import {cityAssetUrl,assertCityAssetIdentity,CITY_CONFIG} from './city-config.ts';
import {contentSha256 as hash} from './city-content-hash.ts';
import {mountainHeightAt} from './city-mountains.ts';
import {CitySiteSurfaces,type SiteSurfaceData} from './city-site-surfaces.ts';
import {CityRoadLevels,type RoadLevel} from './city-road-levels.ts';
import type {CityData} from './city-types.ts';
import {loadCityJsonChunks,type CityJsonSource} from './city-json-chunks.ts';
import {planSitePaths,type SitePathDisplay,type SitePathPlan} from './city-site-path-plan.ts';
type GeographyManifest={schemaVersion:number;cityId:string;originWGS84:[number,number];horizontalScale:number;eastMetresPerDegree:number;northMetresPerDegree:number;
 units:string;grid:{x0:number;z0:number;step:number;columns:number;rows:number};terrainFile:string;terrainSha256:string;roadLevelsFile:string;roadLevelsSha256:string;roadTerrainTransitionGame:number;siteSurfacesFile?:string;siteSurfacesSha256?:string};
/** Source geometry is already in game units. Actor hints stay outside here. */
export function attachCityRoadLevels(data:CityData,roads:RoadLevel[],terrain:(x:number,z:number)=>number,terrainTransitionGame=20,groundModifier?:(x:number,z:number,height:number)=>number,sourceModifier?:(roadId:string,x:number,z:number)=>number|undefined){
 const byId=new Map(roads.map(r=>[r.id,r]));if(byId.size!==roads.length||roads.length!==data.roads.length)throw new Error('分层道路清单与城市范围不一致');
 const levels=new CityRoadLevels(roads,terrain,terrainTransitionGame,groundModifier,sourceModifier);
 for(const road of data.roads){
  const source=byId.get(road.id);
  if(!source||source.points.length!==road.points.length||source.nodeIds.length!==road.nodeIds?.length||source.width!==road.width||source.points.some((p,i)=>Math.hypot(p[0]-road.points[i][0],p[1]-road.points[i][1])>.001||String(source.nodeIds[i])!==String(road.nodeIds![i])))throw new Error('分层道路源节点不一致：'+road.id);
 }
 for(const road of data.roads)road.heights=byId.get(road.id)!.heights;
 return levels;
}
export async function loadCityGeography(data:CityData,roadChunks?:CityJsonSource,signal?:AbortSignal){
 if(CITY_CONFIG.id!=='hangzhou')throw new Error('杭州地理加载器仅用于杭州配置');
 const base='geography/';const response=await fetch(cityAssetUrl(base+'manifest.json'));if(!response.ok)throw new Error('杭州地形清单加载失败');
 const manifestBytes=await response.arrayBuffer(),manifest=JSON.parse(new TextDecoder().decode(manifestBytes)) as GeographyManifest;assertCityAssetIdentity(manifest);
 const manifestSha256=await hash(manifestBytes);
 const g=manifest.grid;
 if(manifest.schemaVersion!==1||manifest.units!=='game metres; scale applied once'||!g||g.columns<2||g.rows<2||g.columns*g.rows>600000||!Number.isFinite(g.x0+g.z0+g.step)||g.step<=0)throw new Error('杭州地形格式或单位无效');
 const terrainResponse=await fetch(cityAssetUrl(base+manifest.terrainFile),{signal});
 if(!terrainResponse.ok)throw new Error('杭州地形数据加载失败');
 const terrainBytes=await terrainResponse.arrayBuffer();
 if(terrainBytes.byteLength!==g.columns*g.rows*4||await hash(terrainBytes)!==manifest.terrainSha256)throw new Error('杭州地形哈希不一致');
 const heights=new Float32Array(terrainBytes);if(!heights.every(Number.isFinite))throw new Error('杭州地形含无效高程');
 let roadData:{cityId:string;units:string;roads:RoadLevel[]};
 if(roadChunks){
  if(roadChunks.sourceSha256!==manifest.roadLevelsSha256)throw Error('分块桥面源与杭州地理清单不一致');
  roadData=await loadCityJsonChunks(roadChunks,{signal});
 }else{
  const response=await fetch(cityAssetUrl(base+manifest.roadLevelsFile),{signal});if(!response.ok)throw Error('杭州桥面数据加载失败');
  const bytes=await response.arrayBuffer();if(await hash(bytes)!==manifest.roadLevelsSha256)throw Error('杭州桥面哈希不一致');
  roadData=JSON.parse(new TextDecoder().decode(bytes));
 }
 if(roadData.cityId!=='hangzhou'||roadData.units!=='game metres; scale already applied once')throw new Error('杭州桥面单位或城市身份不一致');
 let siteSurfaces:CitySiteSurfaces|undefined;let sitePaths:SitePathPlan[]=[];
 if(manifest.siteSurfacesFile!==undefined||manifest.siteSurfacesSha256!==undefined){
  if(!manifest.siteSurfacesFile||!manifest.siteSurfacesSha256)throw Error('杭州场地表面清单缺少哈希');
  const response=await fetch(cityAssetUrl(base+manifest.siteSurfacesFile));if(!response.ok)throw Error('杭州场地表面加载失败');
  const bytes=await response.arrayBuffer();if(await hash(bytes)!==manifest.siteSurfacesSha256)throw Error('杭州场地表面哈希不一致');
  const surfaces=JSON.parse(new TextDecoder().decode(bytes)) as SiteSurfaceData&{pathDisplays?:SitePathDisplay[]};
  siteSurfaces=new CitySiteSurfaces(surfaces);sitePaths=planSitePaths(surfaces.walkFloors,surfaces.pathDisplays);
 }
 const terrainAt=(x:number,z:number)=>mountainHeightAt(heights,g,x,z),levels=attachCityRoadLevels(data,roadData.roads,terrainAt,manifest.roadTerrainTransitionGame,siteSurfaces?(x,z,y)=>siteSurfaces!.groundAt(x,z,y):undefined,siteSurfaces?(id,x,z)=>siteSurfaces!.roadAt(id,x,z):undefined);
 return {manifest,manifestSha256,levels,siteSurfaces,sitePaths,terrainAt,heightAt:(x:number,z:number)=>levels.groundAt(x,z),
  stats:{source:'Copernicus GLO30 DSM estimate and source-node road surfaces; not a measured DTM',grid:g,nativeResolutionRealMetres:30,units:'game metres; scale applied once',roads:roadData.roads.length,physicalAcceptance:'pending'}};
}
