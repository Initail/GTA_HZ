import ts from 'typescript';
import fs from 'node:fs';
import path from 'node:path';
const candidate=path.resolve('artifacts/cities/hangzhou/city-leisure-v15');
const config=ts.readConfigFile(candidate+'/tsconfig.declarations-v2.json',ts.sys.readFile);
const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,candidate);
const queue=[...parsed.fileNames],parents=new Map(queue.map(f=>[f,null])),unresolved=[];
const cache=ts.createModuleResolutionCache(process.cwd(),s=>s,parsed.options);
for(let i=0;i<queue.length;i++){
 const file=queue[i],text=fs.readFileSync(file,'utf8'),info=ts.preProcessFile(text,true,true);
 for(const entry of info.importedFiles){
  const resolved=ts.resolveModuleName(entry.fileName,file,parsed.options,ts.sys,cache).resolvedModule;
  if(!resolved){unresolved.push({file,module:entry.fileName});continue;}
  const next=resolved.resolvedFileName;
  if(!parents.has(next)){parents.set(next,file);queue.push(next);}
 }
}
const rootIndexes=queue.filter(f=>f.endsWith('/core/index.d.ts'));
const chains=rootIndexes.map(file=>{const result=[];for(let p=file;p;p=parents.get(p))result.push(p);return result.reverse().map(p=>path.relative(process.cwd(),p));});
const result={files:queue.length,rootIndexes:chains,unresolved,inputs:queue.map(f=>({file:f,from:parents.get(f)}))};
fs.writeFileSync(candidate+'/type-graph-v2.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({files:queue.length,rootIndexes:chains,unresolved}));
