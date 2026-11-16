import {cityAssetUrl,CITY_CONFIG} from './city-config.ts';
import type {CityData,V2} from './city-types.ts';
import {closest} from './driving.ts';
export type BridgeCrossing={id:string;name:string;width:number;points:V2[];length:number;height:number;ramp:number;sourceRoadId?:string;sourceId?:string;nodeIds?:(string|number)[];pointHeightsGame?:number[];pointStationsGame?:number[]};
export type ParkLight={id:string;name:string;x:number;z:number;height:number;radius:number;color:[number,number,number];power:number};
export type CoastalManifest={schemaVersion:1;cityId?:string;waterHeight:number;crossings:BridgeCrossing[];parkLights:ParkLight[];shoreDistance:{url:string;extent:number[];maxDistance:number}};
export function bridgeRamp(distance:number,height=2.8,ramp=70){const t=Math.max(0,Math.min(1,distance/ramp));return height*(1-t*t*(3-2*t));}
export function createBridgeHeightSampler(data:CityData,manifest:CoastalManifest,base:(x:number,z:number)=>number){
 type Seg={a:V2;b:V2;width:number;height?:number;ramp?:number};const crossings=new Map<string,Seg[]>(),roads=new Map<string,Seg[]>();const size=100;
 const add=(map:Map<string,Seg[]>,q:Seg,margin:number)=>{for(let x=Math.floor((Math.min(q.a[0],q.b[0])-margin)/size);x<=Math.floor((Math.max(q.a[0],q.b[0])+margin)/size);x++)for(let z=Math.floor((Math.min(q.a[1],q.b[1])-margin)/size);z<=Math.floor((Math.max(q.a[1],q.b[1])+margin)/size);z++){const k=x+','+z,cell=map.get(k)??[];cell.push(q);map.set(k,cell);}};
 for(const b of manifest.crossings)for(let i=1;i<b.points.length;i++)add(crossings,{a:b.points[i-1],b:b.points[i],width:b.width,height:b.height,ramp:b.ramp},b.ramp);
 for(const r of data.roads)if(Number(r.grade)>=0)for(let i=1;i<r.points.length;i++)add(roads,{a:r.points[i-1],b:r.points[i],width:r.width},r.width/2+8);
 function bridgeHeight(x:number,z:number){const k=Math.floor(x/size)+','+Math.floor(z/size),q=crossings.get(k);if(!q)return 0;let height=0;for(const s of q)height=Math.max(height,bridgeRamp(closest(x,z,s.a,s.b).d,s.height,s.ramp));if(!height)return 0;const onRoad=roads.get(k)?.some(s=>closest(x,z,s.a,s.b).d<=s.width/2+8);return onRoad?height:0;}
 return {bridgeHeight,heightAt:(x:number,z:number)=>Math.max(base(x,z),bridgeHeight(x,z)),stats:{crossings:manifest.crossings.length,bridgeClearance:2.8-manifest.waterHeight,roadAligned:true}};
}
export function validateCoastalManifest(data:CityData,manifest:CoastalManifest,cityId:string=CITY_CONFIG.id){
 const hangzhou=cityId==='hangzhou';
 if(manifest.schemaVersion!==1||!Array.isArray(manifest.crossings)||!Array.isArray(manifest.parkLights)||manifest.crossings.length>(hangzhou?4096:2000)||manifest.parkLights.length>400)throw Error('跨水道路与照明清单无效');
 if(!hangzhou)return;
 if(data.meta.cityId!=='hangzhou'||manifest.cityId!=='hangzhou'||!manifest.crossings.length||!manifest.parkLights.length||!Number.isFinite(manifest.waterHeight))throw Error('杭州水岸数据身份或内容无效');
 const shore=manifest.shoreDistance;
 if(!shore?.url||shore.maxDistance!==120||shore.extent?.length!==4||!shore.extent.every(Number.isFinite)||shore.extent[0]>=shore.extent[2]||shore.extent[1]>=shore.extent[3])throw Error('杭州岸距图编码无效');
 const byId=new Map(data.roads.map(r=>[r.id,r])),ids=new Set<string>();
 for(const crossing of manifest.crossings){
  const road=byId.get(crossing.sourceRoadId??'');
  if(!road||!road.heights||!road.bridge||['no','false','0'].includes(road.bridge)||(road.tunnel&&!['no','false','0'].includes(road.tunnel))||ids.has(crossing.id))throw Error('跨水道路源身份无效');
  ids.add(crossing.id);
  if(!crossing.sourceId||crossing.sourceId!==road.sourceId||!crossing.nodeIds?.length||crossing.nodeIds.length!==road.nodeIds?.length||crossing.nodeIds.some((n,i)=>String(n)!==String(road.nodeIds![i])))throw Error('跨水道路源谱系无效');
  if(crossing.ramp!==0||crossing.width!==road.width||!Number.isFinite(crossing.height+crossing.length)||crossing.length<=0||crossing.points.length<2||crossing.points.length!==crossing.pointHeightsGame?.length||crossing.points.length!==crossing.pointStationsGame?.length)throw Error('跨水道路源剖面无效');
  const stations=[0];for(let i=1;i<road.points.length;i++)stations.push(stations[i-1]+Math.hypot(road.points[i][0]-road.points[i-1][0],road.points[i][1]-road.points[i-1][1]));
  const midpoint=(crossing.pointStationsGame![0]+crossing.pointStationsGame!.at(-1)!)/2;
  let middle=1;while(middle<stations.length-1&&stations[middle]<midpoint)middle++;
  const middleT=(midpoint-stations[middle-1])/(stations[middle]-stations[middle-1]||1),middleY=road.heights[middle-1]+(road.heights[middle]-road.heights[middle-1])*middleT;
  const length=crossing.points.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-crossing.points[i][0],p[1]-crossing.points[i][1]),0);
  if(Math.abs(crossing.height-middleY)>1e-6||Math.abs(crossing.length-length)>1e-6)throw Error('跨水道路长度或中点高程无效');
  for(let i=0;i<crossing.points.length;i++){
   const p=crossing.points[i],s=crossing.pointStationsGame![i],y=crossing.pointHeightsGame![i];
   if(p.length!==2||!p.every(Number.isFinite)||!Number.isFinite(s+y)||s<0||s>stations.at(-1)!+1e-6||(i>0&&s<=crossing.pointStationsGame![i-1]))throw Error('跨水道路点序无效');
   let segment=1;while(segment<stations.length-1&&stations[segment]<s)segment++;
   const t=(s-stations[segment-1])/(stations[segment]-stations[segment-1]||1),a=road.points[segment-1],b=road.points[segment];
   const height=road.heights[segment-1]+(road.heights[segment]-road.heights[segment-1])*t;
   if(Math.hypot(p[0]-a[0]-(b[0]-a[0])*t,p[1]-a[1]-(b[1]-a[1])*t)>.001||Math.abs(y-height)>1e-6)throw Error('跨水道路偏离源节点剖面');
  }
 }
 const lightIds=new Set<string>();
 for(const light of manifest.parkLights){
  if(lightIds.has(light.id)||![light.x,light.z,light.height,light.radius,light.power,...light.color].every(Number.isFinite)||light.height!==12||light.radius<=0||light.power<=0||light.color.length!==3||light.color.some(c=>c<0||c>1))throw Error('杭州公园灯具数据无效');
  lightIds.add(light.id);
 }
}
export async function loadCoastalInfrastructure(data:CityData,base:(x:number,z:number)=>number){
 const response=await fetch(cityAssetUrl("coastal/infrastructure.json"));if(!response.ok)throw Error('跨水道路与照明清单加载失败');
 const manifest=await response.json() as CoastalManifest;validateCoastalManifest(data,manifest);
 if(CITY_CONFIG.id==='hangzhou')return {manifest,heightAt:base,bridgeHeight:()=>0,stats:{crossings:manifest.crossings.length,bridgeClearance:null,roadAligned:true,sourceNodeRoadLevels:true,legacyRadialHeight:false}};
 return {manifest,...createBridgeHeightSampler(data,manifest,base)};
}
