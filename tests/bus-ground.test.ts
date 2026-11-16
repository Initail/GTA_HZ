import {test} from 'node:test';import assert from 'node:assert/strict';
import {selectBusGroundHit,type BusSurfaceHit} from '../src/city-bus-ground.ts';
const binding={sourceRoadId:'way/515407397#0',sourceStopId:'node/12707772318',tier:0};
const hit=(height:number,role:BusSurfaceHit['role']):BusSurfaceHit=>({height,role,tile:role+':1,-3',node:role,triangle:0});
test('source-bound surface stays on the ground road under the actual Chaiduo overpass heights',()=>{
 const hits=[hit(11.046485183352276,'roads'),hit(10.496484992617413,'roads'),hit(7.673364652129785,'roads'),hit(7.579607811674974,'terrain')];
 assert.equal(selectBusGroundHit(hits,binding),hits[2]);assert.equal(hits.length,4,'higher surfaces must remain available for collision');
});
test('unknown source identity, elevated roads and tunnels do not use ground fallback',()=>{
 const hits=[hit(7.58,'terrain'),hit(7.67,'roads'),hit(11.05,'roads')];
 for(const b of [null,{...binding,tier:1},{...binding,tier:-1},{...binding,sourceRoadId:''},{...binding,sourceStopId:''}])assert.equal(selectBusGroundHit(hits,b),null);
});
test('missing terrain or multiple terrain layers never become a guessed bus height',()=>{
 assert.equal(selectBusGroundHit([hit(7.67,'roads'),hit(11.05,'roads')],binding),null);
 assert.equal(selectBusGroundHit([hit(7.58,'terrain'),hit(11.05,'terrain')],binding),null);
 assert.equal(selectBusGroundHit([hit(NaN,'terrain')],binding),null);
});
