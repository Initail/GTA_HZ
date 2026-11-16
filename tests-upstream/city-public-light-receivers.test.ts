import test from 'node:test';
import assert from 'node:assert/strict';
import {isPublicLightReceiver} from '../src/city-public-lighting.ts';
test('Hangzhou shoreline receivers are explicit and retain the legacy selection by default',()=>{
 for(const name of ['roads_0_0_asphalt','terrain_-1_5_park','coastal_bridge_1_2_steel','city_meadow_0']){
  assert.equal(isPublicLightReceiver(name),true);assert.equal(isPublicLightReceiver(name,true),true);
 }
 for(const kind of ['land','park','pavement','concrete','seawall','coastal-rock']){
  const name='coastal_shore_5_-4_'+kind;
  assert.equal(isPublicLightReceiver(name),false);assert.equal(isPublicLightReceiver(name,true),true);
 }
 for(const name of ['coastal_shore_5_-4_water','coastal_shore_5_-4_seawall.001','block_5_-4_concrete','coastal_shore_fake_concrete'])assert.equal(isPublicLightReceiver(name,true),false);
});
