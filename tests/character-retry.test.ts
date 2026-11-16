import test from 'node:test';
import assert from 'node:assert/strict';
import {createCityRider} from '../src/city-rider.ts';
import {replaceCafeCharacters} from '../src/city-cafe-characters.ts';
import {characterJobs,characterProgress} from '../src/city-local-characters.ts';

test('public rider manifest failure becomes a retryable error rather than an endless loading state',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response('',{status:503});
 try{
  await assert.rejects(createCityRider(null!),/manifest/i);
  assert.equal(characterJobs.player.phase,'error');
 }finally{globalThis.fetch=original;characterProgress('player','idle',0,'');}
});

test('public cafe manifest failure exposes a retryable character error',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response('',{status:503});
 try{
  await assert.rejects(replaceCafeCharacters(null!,null!,[],()=>false),/manifest/i);
  assert.equal(characterJobs.cafe.phase,'error');
 }finally{globalThis.fetch=original;characterProgress('cafe','idle',0,'');}
});
