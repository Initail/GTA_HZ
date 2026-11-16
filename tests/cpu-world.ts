import {readFileSync} from 'node:fs';import {stripTypeScriptTypes} from 'node:module';import {createHash} from 'node:crypto';
import {BICYCLE_BODY} from '../src/city-bicycle.ts';
import {CityBicycleParking} from '../src/city-bicycle-parking.ts';
import {CITY_CONFIG} from '../src/city-config.ts';
import {tankFootprintClear} from '../src/city-tank-simulation.ts';
import {CAR_BODY,sweepVehicleContact,vehicleImpulse,vehicleBlocksPoint} from '../src/city-vehicle-contact.ts';
export const source=readFileSync(new URL('../src/city-world.ts',import.meta.url),'utf8');
export const worldSourceSha256=createHash('sha256').update(source).digest('hex');
function range(start:string,end:string){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);if(a<0||b<0)throw Error('CPU method boundary changed');return source.slice(a,b);}
const methods=[range(' carSurfaceHeight(',' private groundCollision('),range(' parkedVehicleBlocks(',' get vehicleMeshes'),range(' private walkingSurface(',' async toggleTank('),range(' private restoreBicycleParking(',' async toggleWalking('),range(' get controlMode()',' // Detail and lighting'),range(' async toggleWalking(',' enterPhoto('),range(' resolveVehicleMotion(',' update(dt:number){')].join('\n');
export const CpuWorld=new Function('CityBicycleParking','CITY_CONFIG','BICYCLE_BODY','tankFootprintClear','CAR_BODY','sweepVehicleContact','vehicleImpulse','vehicleBlocksPoint',stripTypeScriptTypes('class Harness { '+methods+' }')+';return Harness;')(CityBicycleParking,CITY_CONFIG,BICYCLE_BODY,tankFootprintClear,CAR_BODY,sweepVehicleContact,vehicleImpulse,vehicleBlocksPoint);
const mountain=readFileSync(new URL('../src/city-mountains.ts',import.meta.url),'utf8');const start=mountain.indexOf('export function mountainHeightAt('),end=mountain.indexOf('\n}',start)+2;
export const mountainHeightAt=new Function(stripTypeScriptTypes(mountain.slice(start,end).replace('export ',''))+';return mountainHeightAt;')();
