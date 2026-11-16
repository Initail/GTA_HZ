/** Original 24-direction, three-height horizon bake over Hangzhou world tops.
 * Alpha stores quantized receiver ground in the same texture (no extra pass).
 */
import fs from 'node:fs';import path from 'node:path';import zlib from 'node:zlib';import crypto from 'node:crypto';
import {CITY_AMBIENT,bakeAmbient} from '../src/city-ambient-bake.ts';
const [input,output]=process.argv.slice(2),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(!input||!output||fs.existsSync(output)||!path.resolve(output).startsWith(path.resolve('artifacts')+path.sep))throw Error('Fresh ambient candidate required');
const file=path.join(input,'manifest.json'),source=JSON.parse(fs.readFileSync(file));
if(source.cityId!=='hangzhou'||source.heightReference!=='terrain')throw Error('Wrong ambient reference');
for(const [file,hash] of Object.entries(source.inputs))if(sha(file)!==hash)throw Error('Changed source '+file);
for(const [file,hash] of Object.entries(source.files))if(sha(path.join(input,file))!==hash)throw Error('Changed prepared raster '+file);
const read=(name,Type)=>{const b=fs.readFileSync(path.join(input,name));return new Type(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));};
const grid={...source.grid,heights:read('heights.f32',Float32Array),ids:read('ids.i32',Int32Array),ground:read('ground.f32',Float32Array)};
const alpha=read('ground.u8',Uint8Array),started=performance.now();
const baked=bakeAmbient(grid,CITY_AMBIENT.heights,CITY_AMBIENT.reach,rows=>console.log('ambient rows',rows,'/',grid.height,'seconds',((performance.now()-started)/1000).toFixed(1)));
const rgba=new Uint8Array(grid.width*grid.height*4);
for(let k=0;k<alpha.length;k++){for(let c=0;c<3;c++)rgba[k*4+c]=Math.round(Math.round(baked.data[k*3+c]/255*31)/31*255);rgba[k*4+3]=alpha[k];}
fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'occlusion.png'),png(rgba,grid.width,grid.height));
const meta={version:1,cityId:'hangzhou',file:'occlusion.png',...source.grid,heightReference:'terrain',groundRange:source.groundRange,heights:[...CITY_AMBIENT.heights],fadeTop:CITY_AMBIENT.fadeTop,directions:CITY_AMBIENT.directions,reachMetres:CITY_AMBIENT.reach*grid.cell,
 channels:'RGB visibility at 0/12/40 game metres above local ground; alpha = (ground-groundRange[0])/groundRange[1]',source:'Original horizon-scan approximation over source-bound ordinary roofs and detail footprints; estimated lighting, not measured irradiance'};
fs.writeFileSync(path.join(output,'occlusion.json'),JSON.stringify(meta,null,2)+'\n');
const report={cityId:'hangzhou',inputs:{[file]:sha(file),'scripts/bake_hangzhou_ambient.mjs':sha('scripts/bake_hangzhou_ambient.mjs'),'src/city-ambient-bake.ts':sha('src/city-ambient-bake.ts')},seconds:(performance.now()-started)/1000,activeCells:baked.active,occludedCells:baked.occluded,meanVisibility:baked.mean,groundAlphaQuantizationErrorGame:source.groundAlphaQuantizationErrorGame,
 gpuBytesWithMipmaps:Math.ceil(rgba.length*4/3),files:Object.fromEntries(['occlusion.png','occlusion.json'].map(f=>[f,{sha256:sha(path.join(output,f)),bytes:fs.statSync(path.join(output,f)).size}])),status:'actual offline bake; browser shader, visual and memory acceptance pending'};
fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
function png(data,w,h){
 const stride=w*4,raw=Buffer.alloc((stride+1)*h);
 for(let y=0;y<h;y++){const o=y*(stride+1);raw[o]=4;for(let i=0;i<stride;i++){
  const x=data[y*stride+i],a=i>=4?data[y*stride+i-4]:0,b=y?data[(y-1)*stride+i]:0,c=i>=4&&y?data[(y-1)*stride+i-4]:0,p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);
  raw[o+1+i]=(x-(pa<=pb&&pa<=pc?a:pb<=pc?b:c))&255;
 }}
 const chunk=(type,body)=>{const n=Buffer.alloc(4);n.writeUInt32BE(body.length);const bytes=Buffer.concat([Buffer.from(type),body]),crc=Buffer.alloc(4);let c=0xffffffff;
  for(const v of bytes){let q=(c^v)&255;for(let k=0;k<8;k++)q=q&1?0xedb88320^(q>>>1):q>>>1;c=(c>>>8)^q;}crc.writeUInt32BE((c^0xffffffff)>>>0);return Buffer.concat([n,bytes,crc]);};
 const header=Buffer.alloc(13);header.writeUInt32BE(w,0);header.writeUInt32BE(h,4);header[8]=8;header[9]=6;
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
