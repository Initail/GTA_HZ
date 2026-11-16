import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
// Current onboarding contracts are checked. Historical research links may
// reference deliberately unpublished photos/large intermediate candidates.
const files=[...fs.readdirSync(root).filter(f=>f.endsWith('.md')),...fs.readdirSync(path.join(root,'docs')).filter(f=>f.endsWith('.md')).map(f=>'docs/'+f),'scripts/README.md','tests/fixtures/README.md'];
let checked=0;const errors=[];
for(const name of files){
 const text=fs.readFileSync(path.join(root,name),'utf8');
 for(const match of text.matchAll(/\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)){
  const link=match[1];if(/^(?:https?:|mailto:|#)/.test(link))continue;
  const target=decodeURIComponent(link.split('#')[0]);
  if(!target)continue;checked++;
  if(!fs.existsSync(path.resolve(root,path.dirname(name),target)))errors.push(name+' -> '+target);
 }
}
if(errors.length){console.error(errors.join('\n'));process.exit(1);}
console.log(`Checked ${checked} relative links in ${files.length} current onboarding documents.`);
