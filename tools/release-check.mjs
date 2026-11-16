import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('..',import.meta.url));
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const pkg=read('package.json'),lock=read('package-lock.json'),assets=read('assets/runtime-lock.json'),manifest=read('assets/runtime-manifest.json');
const errors=[];
if(pkg.version!==lock.version||pkg.version!==assets.version||pkg.version!==manifest.version)errors.push('Version mismatch');
if(!/^[a-f0-9]{64}$/.test(assets.sha256)||assets.bytes<=0)errors.push('Asset archive is not pinned');
if(!assets.url.startsWith('https://github.com/Initail/GTA_HZ/releases/download/'))errors.push('Unexpected public asset source');
if(read('config/active-city.json').cityId!=='hangzhou')errors.push('Wrong active city');
for(const group of ['dependencies','devDependencies'])for(const [name,version]of Object.entries(pkg[group])){
 if(lock.packages['node_modules/'+name]?.version!==version)errors.push('Unpinned dependency '+name);
}
const forbiddenPrefixes=['characters/'];
for(const [name,meta]of Object.entries(manifest.files)){
 if(forbiddenPrefixes.some(p=>name.startsWith(p))||name.startsWith('/')||name.includes('..')||!meta.sha256||!meta.bytes)errors.push('Invalid public asset '+name);
}
// Only compare the explicitly excluded source model hashes, not names: the
// new original models intentionally preserve runtime path contracts.
const excluded=read('assets/excluded-assets.json');
const forbiddenHashes=new Set(excluded.files.map(f=>f.sha256));
for(const [name,meta]of Object.entries(manifest.files))if(forbiddenHashes.has(meta.sha256))errors.push('Restricted asset bytes included: '+name);
const skip=new Set(['.git','node_modules','.cache','public','dist','artifacts','output','.venv','__pycache__']);
let count=0;
function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
 if(skip.has(entry.name))continue;const full=path.join(dir,entry.name),relative=path.relative(root,full);
 if(entry.isSymbolicLink()){errors.push('Source symlink: '+relative);continue;}
 if(entry.isDirectory()){walk(full);continue;}
 const bytes=fs.readFileSync(full);count++;
 if(bytes.length>50*1024*1024)errors.push('Oversized source file: '+relative);
 if(bytes.subarray(0,80).toString().startsWith('version https://git-lfs.github.com/spec/'))errors.push('Unhydrated source fixture: '+relative);
 if(!/\.(?:md|json|ts|js|mjs|py|txt|ya?ml|html|geojson)$/.test(relative))continue;
 const text=bytes.toString('utf8');
 if(new RegExp('/Us'+'ers/[^/\\s]+/').test(text))errors.push('Personal path: '+relative);
 if(/-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----/.test(text)&&!relative.startsWith('tools/'))errors.push('Private key: '+relative);
 if(/gh[pousr]_[A-Za-z0-9]{30,}/.test(text))errors.push('GitHub credential: '+relative);
}}
walk(root);
if(errors.length){console.error([...new Set(errors)].join('\n'));process.exit(1);}
console.log(`Release metadata, ${Object.keys(manifest.files).length} asset entries and ${count} source files checked.`);
