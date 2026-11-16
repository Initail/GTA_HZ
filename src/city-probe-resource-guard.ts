/** Diagnostic-page control only. No game state, save or global process access. */
export class ProbeResourceGuard {
 private timer:ReturnType<typeof setInterval>|undefined;private abort=new AbortController();
 private busy=false;private ended=false;private previousSample=-1;
 constructor(private stop:(reason:string)=>void,private fetcher:typeof fetch=fetch){}
 async start(){const ready=await this.check();if(ready&&!this.ended)this.timer=setInterval(()=>void this.check(),500);return ready;}
 async check():Promise<boolean>{
  if(this.ended)return false;if(this.busy)return true;this.busy=true;
  try{
   // A native browser fetch cannot use this guard object as its Window receiver.
   const request=this.fetcher;
   const response=await request('/guard.json',{signal:AbortSignal.any([this.abort.signal,AbortSignal.timeout(1500)]),cache:'no-store'});
   if(!response.ok||Number(response.headers.get('content-length'))>2048)throw Error('monitor-unavailable');
   const text=await response.text();if(text.length>2048)throw Error('monitor-response-too-large');const row=JSON.parse(text);
   if(this.ended)return false;
   if(row.ready!==true||row.stop!==false||!Number.isSafeInteger(row.sample)||row.sample<0||row.sample<this.previousSample)throw Error(typeof row.reason==='string'?row.reason:'monitor-invalid');
   this.previousSample=row.sample;return true;
  }catch(error){
   if(!this.ended){const reason=error instanceof Error?error.message:'monitor-unavailable';this.dispose();this.stop('资源监控停止检查：'+reason);}
   return false;
  }finally{this.busy=false;}
 }
 dispose(){if(this.ended)return;this.ended=true;this.abort.abort();if(this.timer)clearInterval(this.timer);}
}
