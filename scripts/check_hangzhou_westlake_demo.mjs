/** Validate this local ESM preview without creating a browser or GPU context. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const stage=path.resolve('artifacts/cities/hangzhou/westlake-collision-v1');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const candidate=JSON.parse(fs.readFileSync(path.join(stage,'candidate.json')));
const out=path.join(stage,process.argv[2]??'delivery-check.json');
assert(!fs.existsSync(out),'Use a fresh check report');
for(const [name,hash] of Object.entries(candidate.sourceFiles))assert.equal(sha(fs.readFileSync(path.join(stage,name))),hash,name);
const original=path.resolve('artifacts/cities/hangzhou/demo-v11-loading/src');
for(const name of fs.readdirSync(original)){
 if(candidate.changes.includes(name))continue;
 assert.deepEqual(fs.readFileSync(path.join(stage,'src',name)),fs.readFileSync(path.join(original,name)),name);
}
const {CITY_CONFIG}=await import(pathToFileURL(path.join(stage,'src/city-config.ts')).href);
assert.equal(CITY_CONFIG.id,'hangzhou');assert.equal(CITY_CONFIG.storage.namespace,'gta-hz-demo');
const {loadCityGraphicsQuality}=await import(pathToFileURL(path.join(stage,'src/city-graphics-quality.ts')).href);
assert.equal(loadCityGraphicsQuality('',null),'low');assert.equal(loadCityGraphicsQuality('?quality=high',null),'high');
assert.equal(loadCityGraphicsQuality('',{getItem:()=> 'medium'}),'medium');
const main=fs.readFileSync(path.join(stage,'dist/assets/main.js'),'utf8');
// esbuild retains the literal label "<define:import.meta.env>" in a generated
// initializer; that label is not an unresolved runtime import.meta access.
const unresolvedEnv=/\bimport\.meta\.env\b(?!>)/;
assert(unresolvedEnv.test(fs.readFileSync(path.resolve('artifacts/cities/hangzhou/demo-v11-loading/pre-delivery-fix/dist/assets/main.js'),'utf8')),'Negative control must contain the original runtime failure');
assert(!unresolvedEnv.test(main),'Vite-only environment must be replaced in the local ESM build');
const sourceMain=fs.readFileSync(path.join(stage,'src/main.ts'),'utf8');
for(const source of Object.values(candidate.dataSources))assert(sourceMain.includes('new URL('+JSON.stringify(source.manifestUrl)+',location.href).href'),'Chunk URLs must be absolute before URL resolution');
const html=fs.readFileSync(path.join(stage,'dist/index.html'),'utf8');
assert(fs.statSync(path.join(stage,'dist/assets/main.css')).size>0);
const importmap=JSON.parse(html.match(/<script type="importmap">([^<]+)<\/script>/)[1]);
const meta=JSON.parse(fs.readFileSync(path.join(stage,'source-bundle-meta.json')));
const output=Object.values(meta.outputs).find(o=>o.entryPoint?.endsWith('/main.ts'));
const external=[...new Set(output.imports.filter(i=>i.external).map(i=>i.path))];
const modules=new Map();
for(const name of external){
 const mapped=importmap.imports[name]??Object.entries(importmap.imports).find(([prefix])=>prefix.endsWith('/')&&name.startsWith(prefix))?.map((_,i,a)=>i===1?a[1]+name.slice(a[0].length):null)[1];
 assert(mapped&&mapped.startsWith('/vendor/@babylonjs/'),'Missing local mapping: '+name);
 const file=path.resolve('node_modules',mapped.slice('/vendor/'.length));
 assert(fs.existsSync(file),file);modules.set(name,await import(pathToFileURL(file).href));
}
let importedNames=0;
for(const [,names,name] of main.matchAll(/import\s*\{([^}]+)\}\s*from\s*["']([^"']+)["']/g)){
 const module=modules.get(name);assert(module,'Unknown import '+name);
 for(const item of names.split(',')){const exported=item.trim().split(/\s+as\s+/)[0];if(exported){assert(exported in module,'Missing export '+name+':'+exported);importedNames++;}}
}
for(const record of Object.values(candidate.dataSources)){
 const file=path.resolve('artifacts/cities/hangzhou/stream-data-v1',record.manifestUrl.slice('/stream-data/'.length));
 const bytes=fs.readFileSync(file);assert.equal(bytes.length,record.manifestBytes);assert.equal(sha(bytes),record.manifestSha256);
 assert(main.includes(record.manifestSha256),'Compiled source must use the pinned chunk manifest');
}
assert(main.includes('decodeRasterInto'));assert(!main.includes('const ambientLoading = this.ambient.load()'));
const report={offlineReady:true,version:'demo-v12-westlake',format:'local native ESM dependencies plus bundled application',externalModules:external,importedNames,sourceCount:Object.keys(candidate.sourceFiles).length,
 artifacts:Object.fromEntries(['dist/index.html','dist/assets/main.js','dist/assets/main.css',...candidate.assetOverrides.map(name=>'dist/'+name)].map(file=>{const bytes=fs.readFileSync(path.join(stage,file));return [file,{bytes:bytes.length,sha256:sha(bytes)}];})),
 fullTypecheckPassed:false,formalViteBuildPassed:false,browserValidated:false,watchdogResolved:false,glbStreamingInstalled:false};
fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));
