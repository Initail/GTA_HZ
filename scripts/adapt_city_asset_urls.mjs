/** One-time/minimal source migration; preview by default, --write applies ranges. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import ts from 'typescript';
const write=process.argv.includes('--write'),results=[];
const sha=text=>crypto.createHash('sha256').update(text).digest('hex');
for(const name of fs.readdirSync('src').filter(n=>n.endsWith('.ts')&&!n.endsWith('.generated.ts'))){
 const file=path.join('src',name),original=fs.readFileSync(file,'utf8'),source=ts.createSourceFile(file,original,ts.ScriptTarget.Latest,true),edits=[];
 function visit(node){
  if((ts.isStringLiteral(node)||ts.isNoSubstitutionTemplateLiteral(node))&&node.text.startsWith('/city/')&&!ts.isLiteralTypeNode(node.parent)){
   edits.push({start:node.getStart(source),end:node.end,text:'cityAssetUrl('+JSON.stringify(node.text.slice(6))+')'});return;
  }
  if(ts.isTemplateExpression(node)&&node.head.text.startsWith('/city/')){
   edits.push({start:node.getStart(source),end:node.end,text:'cityAssetUrl('+node.getText(source).replace(/^`\/city\//,'`')+')'});return;
  }
  ts.forEachChild(node,visit);
 }
 visit(source);if(!edits.length)continue;
 let result=original;for(const edit of edits.sort((a,b)=>b.start-a.start))result=result.slice(0,edit.start)+edit.text+result.slice(edit.end);
 const configImport=source.statements.find(s=>ts.isImportDeclaration(s)&&s.moduleSpecifier.text==='./city-config.ts');
 if(configImport){
  const old=configImport.getText(source);
  if(!old.includes('cityAssetUrl'))result=result.replace(old,old.replace('{','{cityAssetUrl,'));
 }else result="import {cityAssetUrl} from './city-config.ts';\n"+result;
 results.push({file,urls:edits.length,inputSha256:sha(original),outputSha256:sha(result)});
 if(write)fs.writeFileSync(file,result);
}
const report={kind:'city-relative-runtime-URL-migration',write,results};
if(write)fs.writeFileSync('docs/hangzhou/audit/city-asset-url-migration.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
