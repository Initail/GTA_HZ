import {CITY_CONFIG,type CityProfile} from './city-config.ts';

/** City-dependent interface labels. Source identities and gameplay stay intact. */
export function cityInterfaceCopy(city:CityProfile=CITY_CONFIG){
 const hangzhou=city.id==='hangzhou';
 return {
  city:city.product.city,product:city.product.name,
  district:hangzhou?'杭州主城区':'深圳湾',
  startingDistrict:hangzhou?'杭州 · 武林周边':'南山 · 后海',
  sunset:hangzhou?'钱江日落':'海湾日落',
  flight:hangzhou?'杭城飞行':'海湾飞行',
  freeFlight:hangzhou?'杭城自由飞行':'海湾自由飞行',
  vehicle:hangzhou?'杭城 GT':'海湾 GT',
  lighting:hangzhou?'正在调试钱江的光与倒影':'正在调试海湾的光与倒影',
  planting:hangzhou?'正在种植香樟、桂花与花境':'正在种植榕树、棕榈与花境',
  cafeArea:hangzhou?'钱江新城 · 解放东路':'南山 · 春笋旁',
  cockpit:`${city.product.name}  /  ${hangzhou?'杭城':'海湾'} GT`,
  fictionalDisclosure:`${city.product.name}·虚构品牌`,
 };
}
export const CITY_COPY=cityInterfaceCopy();
