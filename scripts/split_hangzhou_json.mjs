/** Lossless transport partitioning. Reads sequential 64 KiB windows, never
 * parses/holds the entire city. Values and array order remain byte-exact. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const [source,output]=process.argv.slice(2);
assert(source&&output&&!fs.existsSync(output));assert(path.resolve(output).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const fd=fs.openSync(source,'r'),total=fs.fstatSync(fd).size,hash=crypto.createHash('sha256');
const buffer=Buffer.alloc(64*1024);let offset=0,used=0,index=0;
function peek(){if(index===used){used=fs.readSync(fd,buffer,0,buffer.length,offset);index=0;if(!used)return -1;hash.update(buffer.subarray(0,used));}return buffer[index];}
function advance(){assert(peek()!==-1,'Unexpected EOF');index++;offset++;}
const whitespace=c=>c===32||c===10||c===13||c===9;
function space(){while(whitespace(peek()))advance();}
function expect(c){assert.equal(peek(),c,`Unexpected byte at ${offset}`);advance();}
function bytes(start,end){assert(end-start<=8*1024*1024,'Individual JSON value exceeds 8 MiB');const b=Buffer.alloc(end-start);assert.equal(fs.readSync(fd,b,0,b.length,start),b.length);return b;}
function value(){
 space();const start=offset,first=peek();assert(first>=0);let depth=0,string=false,escape=false;
 if(first!==123&&first!==91&&first!==34){while(peek()>=0&&![44,93,125].includes(peek())&&!whitespace(peek()))advance();assert(offset>start);return [start,offset];}
 for(;;){const c=peek();assert(c>=0);advance();assert(offset-start<=8*1024*1024,'Individual JSON value exceeds 8 MiB');
  if(string){if(escape)escape=false;else if(c===92)escape=true;else if(c===34){string=false;if(first===34&&depth===0)break;}}
  else if(c===34)string=true;else if(c===123||c===91)depth++;else if(c===125||c===93){assert(depth>0);if(--depth===0)break;}
 }
 return [start,offset];
}
fs.mkdirSync(output,{recursive:true});const manifest={schemaVersion:1,source,sourceBytes:total,sourceSha256:'',core:'core.json',coreSha256:'',properties:[],arrays:[],limits:{chunkTargetBytes:512*1024,maxValueBytes:8*1024*1024},transportOnly:true};
const core=[],keys=new Set();space();expect(123);space();
while(peek()!==125){
 const keySpan=value(),key=JSON.parse(bytes(...keySpan));assert(typeof key==='string'&&!keys.has(key));keys.add(key);space();expect(58);space();
 if(peek()!==91){const span=value(),raw=bytes(...span);JSON.parse(raw);core.push(Buffer.concat([Buffer.from(JSON.stringify(key)+':'),raw]));manifest.properties.push({key,sourceRange:span});}
 else{
  const opening=offset;expect(91);space();const entry={key,sourceRange:[opening,0],count:0,chunks:[]};let first=-1,last=-1,startIndex=0;
  function flush(){if(first<0)return;const raw=bytes(first,last),name=`array-${manifest.arrays.length}-${entry.chunks.length}.json`;
   const header=Buffer.from(JSON.stringify({key,startIndex,sourceRange:[first,last]}).slice(0,-1)+',"values":['),payload=Buffer.concat([header,raw,Buffer.from(']}')]);
   const parsed=JSON.parse(payload);assert.equal(parsed.values.length,entry.count-startIndex);
   fs.writeFileSync(path.join(output,name),payload,{flag:'wx'});entry.chunks.push({file:name,bytes:payload.length,sha256:crypto.createHash('sha256').update(payload).digest('hex'),startIndex,count:entry.count-startIndex,sourceRange:[first,last]});first=last=-1;startIndex=entry.count;
  }
  while(peek()!==93){const [start,end]=value();if(first>=0&&end-first>manifest.limits.chunkTargetBytes)flush();if(first<0)first=start;last=end;entry.count++;space();if(peek()===93)break;expect(44);space();}
  flush();expect(93);entry.sourceRange[1]=offset;manifest.arrays.push(entry);core.push(Buffer.from(JSON.stringify(key)+':[]'));
 }
 space();if(peek()===125)break;expect(44);space();
}
expect(125);space();assert.equal(peek(),-1,'Trailing JSON data');assert.equal(offset,total);
const coreBytes=Buffer.concat([Buffer.from('{'),...core.flatMap((v,i)=>i?[Buffer.from(','),v]:[v]),Buffer.from('}')]);JSON.parse(coreBytes);
fs.writeFileSync(path.join(output,'core.json'),coreBytes,{flag:'wx'});manifest.coreBytes=coreBytes.length;manifest.coreSha256=crypto.createHash('sha256').update(coreBytes).digest('hex');manifest.sourceSha256=hash.digest('hex');
fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});fs.closeSync(fd);
console.log(JSON.stringify({source,sourceBytes:total,output,coreBytes:coreBytes.length,arrays:manifest.arrays.map(a=>({key:a.key,count:a.count,chunks:a.chunks.length})),maxChunkBytes:Math.max(0,...manifest.arrays.flatMap(a=>a.chunks.map(c=>c.bytes)))}));
