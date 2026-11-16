import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {transform} from 'esbuild';

test('the public build does not request a restricted external character pack by default',async()=>{
 const source=await fs.readFile(new URL('../src/city-local-characters.ts',import.meta.url),'utf8');
 const {code}=await transform(source,{loader:'ts',format:'esm',define:{'import.meta.env':'{}'}});
 const output=new URL('../.cache/public-character-test.mjs',import.meta.url);
 await fs.mkdir(new URL('../.cache/',import.meta.url),{recursive:true});
 await fs.writeFile(output,code);
 const {CHARACTERS_ENABLED,CHARACTER_ASSET_BASE}=await import(output.href+'?test');
 assert.equal(CHARACTERS_ENABLED,false);
 assert.equal(CHARACTER_ASSET_BASE,'');
});
