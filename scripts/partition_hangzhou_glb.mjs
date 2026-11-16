import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {openSource,tileGroups,tileInfo,indexReader,extractTile,sha,fileSha} from './hangzhou_stream_glb.mjs';
const [mode,...args]=process.argv.slice(2);
const safe=p=>assert(path.resolve(p).startsWith(path.resolve('artifacts/cities/hangzhou')+path.sep));
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
if(mode==='plan'){
 const [file,role,out]=args;safe(out);assert(!fs.existsSync(out),'Fresh candidate required');const source=openSource(file),{doc}=source;
 const groups=tileGroups(doc,role),tiles=groups.map(g=>({...g,sourceNodes:g.nodes,...tileInfo(doc,g),file:`tiles/${role}-${g.tile[0]}-${g.tile[1]}.glb`}));
 fs.mkdirSync(path.join(out,'textures'),{recursive:true});fs.mkdirSync(path.join(out,'tiles'));
 const images=[],textures=[];
 for(const [i,original] of (doc.images??[]).entries()){
  assert(!original.uri&&Number.isInteger(original.bufferView));const v=doc.bufferViews[original.bufferView];assert.equal(v.buffer,0);assert(!v.extensions);
  const bytes=source.read(source.bin+(v.byteOffset??0),v.byteLength),ext={'image/jpeg':'jpg','image/png':'png'}[original.mimeType];assert(ext);
  const file=`textures/${role}-${i}.${ext}`;fs.writeFileSync(path.join(out,file),bytes,{flag:'wx'});textures.push({file,bytes:bytes.length,sha256:sha(bytes)});
  const image={...original,uri:'../'+file};delete image.bufferView;images.push(image);
 }
 const plan={schemaVersion:1,source:file,sourceBytes:source.stat.size,sourceSha256:await fileSha(file),sourceHeaderSha256:source.headerSha256,
  role,coordinateSpace:'Babylon game coordinates: original node TRS, loader root rotation identity, retained Z mirror; no new scale',tiles,images,textures,
  totals:{tiles:tiles.length,nodes:doc.nodes.length,triangles:tiles.reduce((s,t)=>s+t.triangles,0),logicalBytes:tiles.reduce((s,t)=>s+t.logicalBytes,0)}};
 write(path.join(out,'plan.json'),plan);source.close();console.log(JSON.stringify({...plan,tiles:undefined,images:undefined,textures:undefined,maxTileTriangles:Math.max(...tiles.map(t=>t.triangles)),maxTileLogicalBytes:Math.max(...tiles.map(t=>t.logicalBytes))}));
}else if(mode==='batch'){
 const [out,first,count]=args;safe(out);const start=Number(first),length=Number(count);assert(Number.isInteger(start)&&start>=0&&Number.isInteger(length)&&length>0&&length<=8);
 const plan=JSON.parse(fs.readFileSync(path.join(out,'plan.json'))),source=openSource(plan.source);assert.equal(source.headerSha256,plan.sourceHeaderSha256);assert.equal(source.stat.size,plan.sourceBytes);
 const readIndex=await indexReader(source),tiles=plan.tiles.slice(start,start+length);assert.equal(tiles.length,length);
 for(const tile of tiles){const target=path.join(out,tile.file);assert(!fs.existsSync(target)&&!fs.existsSync(target+'.json'));
  const {bytes,doc}=extractTile(source,{...tile,nodes:tile.sourceNodes},readIndex,plan.images);
  fs.writeFileSync(target,bytes,{flag:'wx'});const record={...tile,bytes:bytes.length,sha256:sha(bytes),logicalBytes:doc.bufferViews.reduce((s,v)=>s+v.byteLength,0)};
  assert.equal(record.logicalBytes,tile.logicalBytes);write(target+'.json',record);globalThis.gc?.();
 }
 source.close();console.log(JSON.stringify({role:plan.role,start,count:length,pass:true}));
}else throw Error('Expected plan SOURCE ROLE NEW_DIR, or batch DIR START COUNT');
