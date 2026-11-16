import {test} from 'node:test';import assert from 'node:assert/strict';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';import {Scene} from '@babylonjs/core/scene.js';
import {planSitePaths,type SitePathDisplay} from '../src/city-site-path-plan.ts';import {createCitySitePaths} from '../src/city-site-path-view.ts';
import {CitySiteSurfaces,type SiteSurfaceData} from '../src/city-site-surfaces.ts';
const data:SiteSurfaceData={cityId:'hangzhou',units:'game east/north/up; scale applied once',terrainCuts:[],walkFloors:[{id:'source-path',triangles:[[[10,20,5],[12,20,5],[12,22,5.2]],[[10,20,5],[12,22,5.2],[10,22,5.2]]]}]};
const display:SitePathDisplay={id:'entry-route',floorIds:['source-path'],color:[.55,.54,.49],sourceIds:['way/195189682']};
test('visible vertices exactly reuse physical path ENU triangles without a second scale or lift',()=>{
 const [p]=planSitePaths(data.walkFloors,[display]),surfaces=new CitySiteSurfaces(data);
 assert.deepEqual(p.positions.slice(0,9),[10,5,20,12,5,20,12,5.2,22]);assert.deepEqual(p.indices,[0,1,2,3,4,5]);
 assert.deepEqual(p.bounds,{min:[10,20,5],max:[12,22,5.2]});assert.ok(Math.abs(surfaces.walkAt(11,21,5,{id:'source-path',height:5}).height-5.1)<1e-10);
 assert.deepEqual(planSitePaths(data.walkFloors),[],'existing surfaces are not rendered a second time without explicit display ownership');
});
test('missing or duplicate floor ownership and malformed source data fail closed',()=>{
 assert.throws(()=>planSitePaths(data.walkFloors,[{...display,floorIds:['absent']}]));
 assert.throws(()=>planSitePaths(data.walkFloors,[display,{...display,id:'other'}]));
 assert.throws(()=>planSitePaths(data.walkFloors,[{...display,sourceIds:['estimated-location-only']}]));
 assert.throws(()=>planSitePaths(data.walkFloors,[{...display,color:[2,0,0]}]));
 const bad=structuredClone(data.walkFloors);bad[0].triangles[0].reverse();assert.throws(()=>planSitePaths(bad,[display]));
});
test('actual Babylon path meshes share material, cull by bounds, and dispose idempotently',()=>{
 const engine=new NullEngine(),scene=new Scene(engine);
 try{
  const extra={...data.walkFloors[0],id:'second-path'},plans=planSitePaths([...data.walkFloors,extra],[display,{...display,id:'second',floorIds:['second-path']}]);
  const view=createCitySitePaths(scene,plans);assert.equal(view.meshes.length,2);assert.equal(view.meshes[0].material,view.meshes[1].material);
  assert.deepEqual(Array.from(view.meshes[0].getIndices()!),plans[0].indices);assert.deepEqual(Array.from(view.meshes[0].getVerticesData('position')!).slice(0,6),plans[0].positions.slice(0,6));
  assert.equal(view.meshes[0].receiveShadows,true);assert.equal(view.stats.triangles,4);
  const normals=view.meshes[0].getVerticesData('normal')!;for(let i=1;i<normals.length;i+=3)assert(normals[i]>0,'Babylon left-handed paving must face the sky, not be culled from above');
  assert.equal(view.meshes[0].material!.backFaceCulling,true);
  view.update(11,21);assert.ok(view.meshes.every(m=>m.isEnabled()));view.update(2000,21);assert.ok(view.meshes.every(m=>!m.isEnabled()));
  view.update(11,21);assert.ok(view.meshes.every(m=>m.isEnabled()));view.dispose();view.dispose();assert.ok(view.meshes.every(m=>m.isDisposed()));assert.equal(scene.materials.filter(m=>m.name.startsWith('site-path:')).length,0);
 }finally{scene.dispose();engine.dispose();}
});

test('vegetation reservation affects only explicitly displayed source floors',()=>{
 const original=new CitySiteSurfaces(data),withPath=new CitySiteSurfaces({...data,pathDisplays:[display]});
 assert.equal(original.reservedWalkPath(11,21),false);assert.equal(withPath.reservedWalkPath(11,21),true);assert.equal(withPath.reservedWalkPath(20,21),false);
 assert.throws(()=>new CitySiteSurfaces({...data,pathDisplays:[{floorIds:['missing']}]}));
});
