import {CITY_CONFIG,cityAssetUrl,projectCityWgs84,type CityProfile} from './city-config.ts';
import type {SourcedMapPlace} from './city-map-geometry.ts';

export function cityMapPlacesUrl(city:CityProfile=CITY_CONFIG){
 return city.id==='shenzhen'?new URL('../data/map-places.json',import.meta.url):cityAssetUrl('map-places.json',city);
}
export async function loadCityMapPlaces(signal?:AbortSignal,city:CityProfile=CITY_CONFIG):Promise<SourcedMapPlace[]>{
 const response=await fetch(cityMapPlacesUrl(city),{signal});if(!response.ok)throw Error('地图地点未能载入');
 const doc=await response.json() as {schemaVersion:number;cityId?:string;places:SourcedMapPlace[]};
 if(doc.schemaVersion!==1||!Array.isArray(doc.places)||city.id==='hangzhou'&&doc.cityId!==city.id)throw Error('地图地点与当前城市不一致');
 return doc.places.filter(p=>{
  const point=projectCityWgs84(p.lon,p.lat,city);
  if(!Number.isFinite(p.x+p.z)||Math.hypot(point[0]-p.x,point[1]-p.z)>.02)return false;
  if(city.id==='hangzhou'&&(!p.arrival||p.arrival.length!==2||!p.arrival.every(Number.isFinite)||!Number.isFinite(p.yaw)||!p.arrivalRoadId))throw Error('杭州地图地点缺少已核对道路到达点');
  return true;
 });
}
