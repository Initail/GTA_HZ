/** Independent source-range proof. Checks no array value was dropped, duplicated,
 * reordered or rounded, without reassembling a large JS city object. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const [directory]=process.argv.slice(2),m=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'))),fd=fs.openSync(m.source,'r');
assert(!fs.existsSync(path.join(directory,'validation.json')));const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function read(start,end){assert(start>=0&&end>=start&&end-start<=8*1024*1024);const b=Buffer.alloc(end-start);assert.equal(fs.readSync(fd,b,0,b.length,start),b.length);return b;}
const coreBytes=fs.readFileSync(path.join(directory,m.core));assert.equal(sha(coreBytes),m.coreSha256);const core=JSON.parse(coreBytes);let items=0,chunks=0;
assert.deepEqual(Object.keys(core).sort(),[...m.properties.map(p=>p.key),...m.arrays.map(p=>p.key)].sort());
for(const p of m.properties)assert.deepEqual(core[p.key],JSON.parse(read(...p.sourceRange)));
for(const a of m.arrays){
 assert.deepEqual(core[a.key],[]);assert.equal(read(a.sourceRange[0],a.sourceRange[0]+1).toString(),'[');assert.equal(read(a.sourceRange[1]-1,a.sourceRange[1]).toString(),']');let previous=a.sourceRange[0]+1,count=0;
 for(const c of a.chunks){
  const bytes=fs.readFileSync(path.join(directory,c.file));assert.equal(bytes.length,c.bytes);assert.equal(sha(bytes),c.sha256);const parsed=JSON.parse(bytes);
  assert.equal(parsed.key,a.key);assert.equal(parsed.startIndex,count);assert.equal(c.startIndex,count);assert.equal(parsed.values.length,c.count);assert.deepEqual(parsed.sourceRange,c.sourceRange);
  // Delimiters between source spans contain no skipped value or object token.
  const gap=read(previous,c.sourceRange[0]).toString();assert((count?/^\s*,\s*$/:/^\s*$/).test(gap));
  const marker=Buffer.from(',"values":['),start=bytes.indexOf(marker)+marker.length;assert(start>=marker.length);assert(bytes.subarray(-2).equals(Buffer.from(']}')));
  assert(bytes.subarray(start,-2).equals(read(...c.sourceRange)),'Array payload differs from source bytes');
  count+=c.count;previous=c.sourceRange[1];chunks++;
 }
 assert(/^\s*$/.test(read(previous,a.sourceRange[1]-1).toString()));assert.equal(count,a.count);items+=count;
}
fs.closeSync(fd);const hash=crypto.createHash('sha256');for await(const b of fs.createReadStream(m.source,{highWaterMark:64*1024}))hash.update(b);assert.equal(hash.digest('hex'),m.sourceSha256);
const result={pass:true,source:m.source,sourceSha256:m.sourceSha256,sourceBytes:m.sourceBytes,arrays:m.arrays.length,items,chunks,proof:'All payload bytes equal contiguous original source spans; separators prove complete ordered array coverage; scalar/object metadata parsed equivalently; full source hash matches.',browserValidated:false};
fs.writeFileSync(path.join(directory,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
