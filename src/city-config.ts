import {ACTIVE_CITY_ID, CITY_PROFILES} from './city-profiles.generated.ts';
import type {V2} from './city-types.ts';

export type CityProfile = typeof CITY_PROFILES[keyof typeof CITY_PROFILES];
export const CITY_CONFIG:CityProfile = CITY_PROFILES[ACTIVE_CITY_ID];

/** Keep the public east/north interface. glTF orientation stays with the loader. */
export function projectCityWgs84(lon:number,lat:number,city:CityProfile=CITY_CONFIG):V2 {
  if(!Number.isFinite(lon+lat)||Math.abs(lon)>180||Math.abs(lat)>90)throw new RangeError('Invalid WGS84 longitude/latitude');
  const g=city.geography;
  return [(lon-g.originWGS84[0])*g.eastMetresPerDegree*g.scale,(lat-g.originWGS84[1])*g.northMetresPerDegree*g.scale];
}
export function unprojectCityPoint(east:number,north:number,city:CityProfile=CITY_CONFIG):V2 {
  const g=city.geography;
  return [g.originWGS84[0]+east/(g.eastMetresPerDegree*g.scale),g.originWGS84[1]+north/(g.northMetresPerDegree*g.scale)];
}
export function cityAssetUrl(relative:string,city:CityProfile=CITY_CONFIG){
  if(relative.startsWith('/')||relative.split('/').includes('..'))throw new Error('Expected a city-relative asset path');
  return city.assets.runtimeRoot+'/'+relative;
}

/** Reject geographic assets from another city before they enter collision/maps. */
export function assertCityAssetIdentity(meta:{cityId?:string;originWGS84?:number[];horizontalScale:number;eastMetresPerDegree?:number;northMetresPerDegree?:number},city:CityProfile=CITY_CONFIG){
 const g=city.geography;
 if(meta.cityId!==city.id&&!(city.id==='shenzhen'&&meta.cityId===undefined))throw new Error('城市资产身份与配置不一致');
 if(!meta.originWGS84||meta.originWGS84.length!==2||meta.originWGS84.some((value,index)=>!Number.isFinite(value)||Math.abs(value-g.originWGS84[index])>1e-9))throw new Error('城市资产 WGS84 原点不一致');
 if(!Number.isFinite(meta.horizontalScale)||Math.abs(meta.horizontalScale-g.scale)>1e-9)throw new Error('城市资产缩放不一致');
 if(city.id==='hangzhou')for(const key of ['eastMetresPerDegree','northMetresPerDegree'] as const){
  const value=meta[key];if(value===undefined||!Number.isFinite(value)||Math.abs(value-g[key])>1e-6)throw new Error('城市资产投影参数不一致');
 }
}
