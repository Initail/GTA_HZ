import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCoastalManifest,type CoastalManifest} from '../src/city-coastal-infrastructure.ts';
import type {CityData} from '../src/city-types.ts';
const data={meta:{cityId:'hangzhou'},roads:[{id:'bridge',sourceId:'way/123',nodeIds:['1','2','3'],name:'桥',kind:'primary',width:6,grade:'1',bridge:'yes',tunnel:'no',points:[[0,0],[10,0],[20,0]],heights:[10,12,11]}]} as unknown as CityData;
function manifest():CoastalManifest{return {schemaVersion:1,cityId:'hangzhou',waterHeight:1,crossings:[{id:'bridge@wet-0',sourceRoadId:'bridge',sourceId:'way/123',nodeIds:['1','2','3'],name:'桥',width:6,points:[[5,0],[10,0],[15,0]],pointStationsGame:[5,10,15],pointHeightsGame:[11,12,11.5],length:10,height:12,ramp:0}],parkLights:[{id:'park-1',name:'公园',x:30,z:40,height:12,radius:34,power:.9,color:[.76,.84,1]}],shoreDistance:{url:'/cities/hangzhou/coastal/shore-distance.png',extent:[-100,-100,100,100],maxDistance:120}};}
test('Hangzhou waterfront preserves source profile and fails closed on an invented crossing or legacy radial ramp',()=>{
 validateCoastalManifest(data,manifest(),'hangzhou');
 const wrong=manifest();wrong.crossings[0].pointHeightsGame![1]=2.8;
 assert.throws(()=>validateCoastalManifest(data,wrong,'hangzhou'),/偏离源节点/);
 const ramp=manifest();ramp.crossings[0].ramp=70;assert.throws(()=>validateCoastalManifest(data,ramp,'hangzhou'),/源剖面/);
 const id=manifest();id.crossings[0].sourceRoadId='geometric-intersection';assert.throws(()=>validateCoastalManifest(data,id,'hangzhou'),/源身份/);
 const empty=manifest();empty.parkLights=[];assert.throws(()=>validateCoastalManifest(data,empty,'hangzhou'),/内容无效/);
 const light=manifest();light.parkLights[0].height=6;assert.throws(()=>validateCoastalManifest(data,light,'hangzhou'),/灯具/);
 const texture=manifest();texture.shoreDistance.maxDistance=60;assert.throws(()=>validateCoastalManifest(data,texture,'hangzhou'),/岸距/);
 for(const key of ['height','length'] as const){const changed=manifest();changed.crossings[0][key]+=100;assert.throws(()=>validateCoastalManifest(data,changed,'hangzhou'),/中点高程/);}
 const lineage=manifest();lineage.crossings[0].nodeIds=['invented'];assert.throws(()=>validateCoastalManifest(data,lineage,'hangzhou'),/谱系/);
 const source=manifest();source.crossings[0].sourceId='way/0';assert.throws(()=>validateCoastalManifest(data,source,'hangzhou'),/谱系/);
});
