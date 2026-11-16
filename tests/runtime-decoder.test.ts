import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('the browser stream decoder URL resolves to the shipped decoder code',()=>{
 const source=fs.readFileSync(new URL('../src/main.ts',import.meta.url),'utf8');
 const decoder=source.match(/"decoderUrl":"([^"]+)"/)?.[1];
 assert.ok(decoder,'production stream declaration must bind the decoder');
 const file=new URL('../public'+decoder,import.meta.url);
 assert.ok(fs.existsSync(file),'public decoder requested by the browser must be distributed');
 assert.match(fs.readFileSync(file,'utf8'),/MeshoptDecoder/);
});
