import assert from 'node:assert/strict';
import test from 'node:test';
import {CITY_GRAPHICS_PROFILES,cityGraphicsRenderRatio} from '../src/city-graphics-quality.ts';

test('default low quality fits a single-pass compatibility budget on a Retina display',()=>{
 const low=Object.assign({},CITY_GRAPHICS_PROFILES.low);
 assert.equal(Reflect.get(low,'multipass'),false);
 const scale=cityGraphicsRenderRatio('low',2560,1440,2);
 assert.ok(Math.round(2560*scale)*Math.round(1440*scale)<=960*540);
});
