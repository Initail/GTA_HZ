import test from 'node:test';
import assert from 'node:assert/strict';
import {createStartupTrace} from '../src/city-startup-trace.ts';
test('phase checkpoints are bounded and distinguish phase start from completion',()=>{
 let value='',now=0;const record=createStartupTrace({setItem(_k,v){value=v;}},'test',()=>now);
 for(let i=0;i<80;i++){now+=10;record('phase-'+i);}
 const checkpoint=JSON.parse(value);assert.equal(checkpoint.phases.length,64);assert.equal(checkpoint.status,'loading');assert.equal(checkpoint.phases.at(-1).previousPhaseMs,10);
 record('ready');assert.equal(JSON.parse(value).status,'ready');
});
test('unavailable local storage does not interrupt boot',()=>{
 assert.doesNotThrow(()=>createStartupTrace({setItem(){throw Error('unavailable');}},'test')('phase'));
});
