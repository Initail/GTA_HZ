import {test} from 'node:test';import assert from 'node:assert/strict';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';import {Scene} from '@babylonjs/core/scene.js';import {AssetContainer} from '@babylonjs/core/assetContainer.js';import {PBRMaterial} from '@babylonjs/core/Materials/PBR/pbrMaterial.js';import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {CityBaseMaterialCache,type StreamMaterialOrigin} from '../src/city-stream-ownership.ts';
function loaded(scene:Scene,index:number){const material=new PBRMaterial('same-display-name',scene),mesh=new Mesh('fixture',scene),container=new AssetContainer(scene);(material as any)._internalMetadata={gltf:{pointers:['/materials/'+index]}};mesh.material=material;container.meshes=[mesh];container.materials=[material];return {material,mesh,container};}
test('physical pack material slot reordering preserves original terrain identity and ownership',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),cache=new CityBaseMaterialCache(scene),record={name:'source-grass',pbrMetallicRoughness:{baseColorTexture:{index:0}}};
 try{const first=loaded(scene,0);cache.adopt(first.container,'terrain',[record]);
  const second=loaded(scene,1),origins:StreamMaterialOrigin[]=[{role:'buildings',index:0,record:{name:'concrete'}},{role:'terrain',index:0,record}];cache.adoptMapped(second.container,origins);
  assert.equal(second.mesh.material,first.material);assert.equal(cache.stats.materials,1);assert(!first.container.materials.includes(first.material));
  second.container.dispose();assert(scene.materials.includes(first.material));first.container.dispose();assert(scene.materials.includes(first.material));cache.dispose();assert(!scene.materials.includes(first.material));
 }finally{scene.dispose();engine.dispose();}
});
test('same display name in road and terrain stays separate, building ownership stays local',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),cache=new CityBaseMaterialCache(scene);
 try{const road=loaded(scene,0),terrain=loaded(scene,0),building=loaded(scene,0);cache.adoptMapped(road.container,[{role:'roads',index:0,record:{name:'shared-name'}}]);cache.adoptMapped(terrain.container,[{role:'terrain',index:0,record:{name:'shared-name'}}]);cache.adoptMapped(building.container,[{role:'buildings',index:0,record:{name:'shared-name'}}]);assert.notEqual(road.mesh.material,terrain.mesh.material);assert.equal(cache.stats.materials,2);assert(building.container.materials.includes(building.material));building.container.dispose();cache.dispose();
 }finally{scene.dispose();engine.dispose();}
});
test('changed source signature or invalid pack pointer is rejected before cache mutation',()=>{
 const engine=new NullEngine(),scene=new Scene(engine),cache=new CityBaseMaterialCache(scene);
 try{const first=loaded(scene,0);cache.adoptMapped(first.container,[{role:'roads',index:4,record:{name:'original'}}]);const changed=loaded(scene,0);assert.throws(()=>cache.adoptMapped(changed.container,[{role:'roads',index:4,record:{name:'changed'}}]),/changed/);assert.equal(cache.stats.materials,1);assert(changed.container.materials.includes(changed.material));
  const wrong=loaded(scene,2);assert.throws(()=>cache.adoptMapped(wrong.container,[{role:'terrain',index:0,record:{}}]),/pointer/);assert.equal(cache.stats.materials,1);cache.dispose();
 }finally{scene.dispose();engine.dispose();}
});
