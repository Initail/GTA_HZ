import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import {inspectStartup,readBoundedJson,startupBudget} from '../src/city-startup-safety.ts';

test('the ordinary page entry cannot automatically import or start the city',()=>{
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 assert.ok(!html.includes('src="/src/main.ts"'),'old entry starts DrivingWorld and GPU work on page open');
 assert.ok(html.includes('src="/src/city-safe-entry.ts"'));
});

test('actual demo-v10 exceeds conservative startup limits, independent of its reported verdict',()=>{
 const report=JSON.parse(readFileSync(new URL('../docs/hangzhou/audit/stability-20261111/demo-v10-startup.json',import.meta.url),'utf8'));
 report.budget={allowed:true};
 const actual=startupBudget(report);
 assert.equal(actual.allowed,false);assert.equal(actual.reasons.length,8);
});
test('missing, duplicate or nonfinite resource budgets fail closed',()=>{
 for(const report of [null,{}, {schemaVersion:1,meshes:[],jsonBytes:{}},
  {schemaVersion:1,meshes:[{path:'roads.glb',bytes:Infinity}],jsonBytes:{}}])assert.equal(startupBudget(report).allowed,false);
});
test('bounded JSON reader cancels oversized streaming bodies even without Content-Length',async()=>{
 let cancelled=false;
 const body=new ReadableStream<Uint8Array>({pull(c){c.enqueue(new Uint8Array(128));},cancel(){cancelled=true;}});
 await assert.rejects(readBoundedJson(new Response(body,{headers:{'content-type':'application/json'}}),new AbortController().signal,64),/读取上限/);
 assert.equal(cancelled,true);
});
test('cancellation ends an outstanding read without an automatic retry',async()=>{
 const controller=new AbortController();let calls=0,cancelled=false;
 const pending=inspectStartup('/startup-inventory.json',controller.signal,async()=>{
  calls++;return new Response(new ReadableStream({cancel(){cancelled=true;}}),{headers:{'content-type':'application/json'}});
 });
 await new Promise(resolve=>setTimeout(resolve,5));controller.abort();
 await assert.rejects(pending,{name:'AbortError'});assert.equal(calls,1);assert.equal(cancelled,true);
});
test('HTML fallback and oversized declared content cannot be parsed as a valid report',async()=>{
 await assert.rejects(readBoundedJson(new Response('<html>',{headers:{'content-type':'text/html'}}),new AbortController().signal));
 await assert.rejects(readBoundedJson(new Response('{}',{headers:{'content-type':'application/json','content-length':'999999'}}),new AbortController().signal));
});
test('a rejected content type cancels its body instead of continuing an unbounded download',async()=>{
 let cancelled=false;
 const response=new Response(new ReadableStream({cancel(){cancelled=true;}}),{headers:{'content-type':'text/html'}});
 await assert.rejects(readBoundedJson(response,new AbortController().signal));assert.equal(cancelled,true);
});
