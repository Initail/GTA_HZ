import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';

const root=fileURLToPath(new URL('..',import.meta.url));
process.chdir(root);
function run(args,executable=process.execPath){
 const result=spawnSync(executable,args,{cwd:root,stdio:'inherit'});
 if(result.error)throw result.error;
 if(result.status!==0)process.exit(result.status??1);
}
run(['tools/assets.py','verify'],process.env.PYTHON??'python3');
run(['--max-old-space-size=512','node_modules/typescript/bin/tsc','--noEmit']);
fs.rmSync(path.join(root,'dist'),{recursive:true,force:true});
// Prebundle once: Rollup processes only the small manual startup shell.
await build({entryPoints:['src/main.ts','src/combat-lab.ts'],bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true,legalComments:'eof',outdir:'dist/runtime',metafile:true,define:{'import.meta.env':'{}'}}).then(result=>{
 fs.mkdirSync('artifacts/build',{recursive:true});fs.writeFileSync('artifacts/build/meta.json',JSON.stringify(result.metafile));
});
run(['--max-old-space-size=512','node_modules/vite/bin/vite.js','build']);
fs.cpSync('public','dist',{recursive:true});
for(const name of ['combat-lab']){
 let html=fs.readFileSync(name+'.html','utf8');
 html=html.replaceAll('/src/combat-lab.css','/runtime/combat-lab.css').replaceAll('/src/combat-lab.ts','/runtime/combat-lab.js').replaceAll('/src/trailer-capture.ts','/runtime/trailer-capture.js');
 fs.writeFileSync('dist/'+name+'.html',html);
}
console.log('Built main city and independent combat lab. Start with npm run preview.');
