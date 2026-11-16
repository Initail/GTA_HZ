/** Copy bounded RGBA strips into a packed texture. No full-size Canvas/ImageData
 * copy, no two simultaneous image decodes. This preserves source bytes. */
export const RASTER_LIMITS={pixels:18_000_000,dimension:8192,stripRows:128,elapsedMs:15_000,downloadBytes:32*1024*1024} as const;
export function checkRasterSize(width:number,height:number){
 if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1||width>RASTER_LIMITS.dimension||height>RASTER_LIMITS.dimension||width*height>RASTER_LIMITS.pixels)throw Error('City raster exceeds startup budget');
}
export function copyRasterStrip(source:Uint8ClampedArray,target:Uint8Array,targetPixel:number,stride:number,channels:readonly number[]){
 const count=source.length/4;
 if(!Number.isInteger(count)||!Number.isInteger(targetPixel)||targetPixel<0||!Number.isInteger(stride)||stride<1||stride>4||!channels.length||channels.some(c=>!Number.isInteger(c)||c<0||c>=stride)||new Set(channels).size!==channels.length||(targetPixel+count)*stride>target.length)throw Error('Invalid raster strip range');
 for(let i=0;i<count;i++)for(let c=0;c<channels.length;c++)target[(targetPixel+i)*stride+channels[c]]=source[i*4+c];
}
async function boundedBlob(response:Response,signal:AbortSignal){
 if(!response.body)throw Error('Empty city raster');
 const reader=response.body.getReader(),parts:Uint8Array<ArrayBuffer>[]=[];let total=0;
 const cancel=()=>{void reader.cancel().catch(()=>{});};signal.addEventListener('abort',cancel,{once:true});
 try{for(;;){signal.throwIfAborted();const next=await reader.read();signal.throwIfAborted();if(next.done)break;
  total+=next.value.byteLength;if(total>RASTER_LIMITS.downloadBytes)throw Error('City raster download exceeds budget');parts.push(new Uint8Array(next.value));}
  return new Blob(parts,{type:'image/png'});
 }finally{signal.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});reader.releaseLock();}
}
export async function decodeRasterInto(url:string,width:number,height:number,target:Uint8Array,stride:number,channels:readonly number[],signal?:AbortSignal){
 checkRasterSize(width,height);if(target.length!==width*height*stride)throw Error('Raster target length mismatch');
 const controller=new AbortController(),relay=()=>controller.abort(signal?.reason),timer=setTimeout(()=>controller.abort(new Error('City raster timed out')),RASTER_LIMITS.elapsedMs);
 if(signal?.aborted)relay();else signal?.addEventListener('abort',relay,{once:true});
 let bitmap:ImageBitmap|undefined,canvas:OffscreenCanvas|undefined;
 try{
  const response=await fetch(url,{signal:controller.signal});if(!response.ok){await response.body?.cancel();throw Error('City raster unavailable: '+response.status);}
  if(Number(response.headers.get('content-length'))>RASTER_LIMITS.downloadBytes){await response.body?.cancel();throw Error('City raster download exceeds budget');}
  const blob=await boundedBlob(response,controller.signal);
  // Reject incorrect/oversized PNG dimensions before the image decoder allocates.
  const header=new Uint8Array(await blob.slice(0,24).arrayBuffer()),view=new DataView(header.buffer);
  if(header.length<24||[137,80,78,71,13,10,26,10].some((v,i)=>header[i]!==v)||view.getUint32(16)!==width||view.getUint32(20)!==height)throw Error('City raster PNG header does not match metadata');
  controller.signal.throwIfAborted();bitmap=await createImageBitmap(blob,{colorSpaceConversion:'none',premultiplyAlpha:'none'});
  controller.signal.throwIfAborted();if(bitmap.width!==width||bitmap.height!==height)throw Error('City raster dimensions do not match metadata');
  canvas=new OffscreenCanvas(width,Math.min(height,RASTER_LIMITS.stripRows));
  const ctx=canvas.getContext('2d',{willReadFrequently:true});if(!ctx)throw Error('2d context unavailable');
  for(let row=0;row<height;row+=RASTER_LIMITS.stripRows){
   controller.signal.throwIfAborted();const rows=Math.min(RASTER_LIMITS.stripRows,height-row);
   ctx.clearRect(0,0,width,rows);ctx.drawImage(bitmap,0,row,width,rows,0,0,width,rows);
   copyRasterStrip(ctx.getImageData(0,0,width,rows).data,target,row*width,stride,channels);
   // A real task yield lets Cancel/page lifecycle/timeout run between strips.
   await new Promise<void>(resolve=>setTimeout(resolve,0));
  }
  controller.signal.throwIfAborted();
 }finally{clearTimeout(timer);signal?.removeEventListener('abort',relay);bitmap?.close();if(canvas){canvas.width=1;canvas.height=1;}}
}
