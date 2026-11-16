import {test} from 'node:test';import assert from 'node:assert/strict';
import {CityBicycle,type BicycleSurface} from '../src/city-bicycle.ts';
import {CityBicycleParking} from '../src/city-bicycle-parking.ts';
const pose={x:8,z:9,yaw:.7,height:2};
const identity={city:'hangzhou',projection:'120.155,30.274;96220.11856153939;110857.07311230902;.6',key:'hangchengzhixing-bicycle-parking-v1',extent:[-100,-100,100,100]};
function fixture(surface:()=>BicycleSurface=()=>({height:2,blocked:null})){
 const values=new Map<string,string>();const writes:string[]=[];
 const store={getItem:(k:string)=>values.get(k)??null,setItem:(k:string,v:string)=>{writes.push(k);values.set(k,v);}};
 const bike=new CityBicycle(surface),parking=new CityBicycleParking(bike,store,identity);
 return {bike,parking,store,values,writes};
}
test('safe parked bicycle survives refresh with mileage, while controls and other saves stay untouched',()=>{
 const f=fixture();f.values.set('career','untouched');f.bike.mount(pose,()=>true);f.bike.distance=72;f.bike.dismount(()=>true);
 assert(f.parking.checkpoint());const next=new CityBicycle(()=>({height:2,blocked:null}));
 assert.equal(new CityBicycleParking(next,f.store,identity).restore(),'parked');
 assert.deepEqual(next.pose,pose);assert.equal(next.active,false);assert.equal(next.speed,0);assert.equal(next.distance,72);assert.equal(f.values.get('career'),'untouched');assert.deepEqual(f.writes,[identity.key]);
});
test('mount clears old parking snapshot; refresh while riding folds bicycle without reviving movement',()=>{
 const f=fixture();f.bike.mount(pose,()=>true);const foot=f.bike.dismount(()=>true)!;f.parking.checkpoint();
 f.bike.mount(foot,()=>true);f.bike.speed=4;assert(f.parking.checkpoint());
 const next=new CityBicycle(()=>({height:2,blocked:null}));assert.equal(new CityBicycleParking(next,f.store,identity).restore(),'folded');assert.equal(next.deployed,false);assert.equal(next.active,false);assert.equal(next.speed,0);
});
test('stowing or accepted travel clearing cannot resurrect a parked bicycle',()=>{
 for(const action of ['stow','travel']){const f=fixture();f.bike.mount(pose,()=>true);const foot=f.bike.dismount(()=>true)!;f.parking.checkpoint();
  if(action==='stow')assert(f.bike.stow(foot));else f.bike.clearDeployment();
  f.parking.checkpoint();const next=new CityBicycle(()=>({height:2,blocked:null}));assert.equal(new CityBicycleParking(next,f.store,identity).restore(),'folded');assert.equal(next.deployed,false);
 }
});
test('changed city, projection, out-of-bounds, malformed or oversized record is rejected without mutation',()=>{
 const f=fixture();f.bike.restoreParked(pose);f.parking.checkpoint();const good=JSON.parse(f.values.get(identity.key)!);
 for(const value of [{...good,city:'shenzhen'},{...good,projection:'old'}, {...good,pose:{...pose,x:101}},{...good,pose:{...pose,height:null}},{...good,distance:-1},{...good,distance:'12'},null,[]]){
  f.values.set(identity.key,JSON.stringify(value));const next=new CityBicycle(()=>({height:2,blocked:null}));assert.equal(new CityBicycleParking(next,f.store,identity).restore(),'invalid');assert.equal(next.deployed,false);assert.equal(next.distance,0);
 }
 for(const text of ['{bad',' '.repeat(2049)]){f.values.set(identity.key,text);assert.equal(new CityBicycleParking(new CityBicycle(()=>({height:2,blocked:null})),f.store,identity).restore(),'invalid');}
});
test('new water, wall, bicycle ban, unsupported wheel or another deck blocks physical restoration',()=>{
 const f=fixture();f.bike.restoreParked(pose);f.parking.checkpoint();const saved=f.values.get(identity.key);
 const surfaces=[()=>({height:2,blocked:'water' as const}),()=>({height:2,blocked:'obstacle' as const}),()=>({height:2,blocked:'restricted-road' as const}),()=>({height:4,blocked:null}), (x:number)=>({height:x>8.3?NaN:2,blocked:null})];
 for(const surface of surfaces){const next=new CityBicycle(surface);assert.equal(new CityBicycleParking(next,f.store,identity).restore(),'blocked');assert.equal(next.deployed,false);assert.equal(next.active,false);assert.equal(f.values.get(identity.key),saved);}
});
test('storage denied or quota failure preserves live state and returns an honest failure',()=>{
 const bike=new CityBicycle(()=>({height:2,blocked:null}));bike.restoreParked(pose);
 for(const store of [null,{getItem:()=>{throw Error('denied');},setItem:()=>{throw Error('quota');}}]){const parking=new CityBicycleParking(bike,store,identity);assert.equal(parking.restore(),'unavailable');assert.equal(parking.checkpoint(),false);assert.deepEqual(bike.pose,pose);assert.equal(bike.deployed,true);}
});
