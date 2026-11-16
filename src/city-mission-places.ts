import type {CityProfile} from './city-config.ts';
import type {CareerPlaces,CareerPlaceId} from './city-career.ts';
import type {V2} from './city-types.ts';

export type CityLifeLocations={cityId?:string;sites:{id:string;arrival:V2}[];missionPlaces?:Partial<CareerPlaces>};
const roles:CareerPlaceId[]=['hub','bay','office','park','workshop'];

/** Resolve the original five-role interface, with explicit city-bound locations. */
export function resolveCityMissionPlaces(profile:CityProfile,payload:CityLifeLocations,legacyBay:()=>V2):CareerPlaces {
 if(payload.cityId!==profile.id&&!(profile.id==='shenzhen'&&payload.cityId===undefined))throw new Error('职业地点来自其他城市');
 const entries=roles.map(role=>{
  const reference=profile.missionPlaces[role];let point:V2|undefined;
  if(typeof reference!=='string')throw new Error('职业地点尚未配置：'+role);
  if(reference.startsWith('life-sites:'))point=payload.sites.find(s=>s.id===reference.slice(11))?.arrival;
  else if(reference.startsWith('mission-points:'))point=payload.missionPlaces?.[reference.slice(15) as CareerPlaceId];
  else if(reference==='spawn-road:+950'&&profile.id==='shenzhen')point=legacyBay();
  if(!point||point.length!==2||point.some(n=>!Number.isFinite(n)))throw new Error('职业地点缺失或无效：'+role);
  return [role,[point[0],point[1]] as V2] as const;
 });
 return Object.fromEntries(entries) as CareerPlaces;
}
