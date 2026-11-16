/** Geometry ownership and admission, independent of Babylon. The loader owns
 * failed-import cleanup; each successful handle is disposed exactly once here.
 * Budgets are declared asset costs, not measurements of JS/GPU/host memory. */
export type StreamCost={bytes:number;logicalBytes:number;triangles:number};
export type StreamTile=StreamCost&{id:string;bounds:{min:number[];max:number[]}};
export type StreamHandle={setVisible(visible:boolean):void;dispose():void};
export type StreamBudget=StreamCost&{tiles:number};
export const BASE_STREAM_LIMITS:Readonly<StreamBudget>=Object.freeze({bytes:24*1024*1024,logicalBytes:64*1024*1024,triangles:1_000_000,tiles:32});
const dimensions=['bytes','logicalBytes','triangles'] as const;
const zero=():StreamCost=>({bytes:0,logicalBytes:0,triangles:0});
const distance=(tile:StreamTile,x:number,z:number)=>Math.hypot(Math.max(tile.bounds.min[0]-x,0,x-tile.bounds.max[0]),Math.max(tile.bounds.min[2]-z,0,z-tile.bounds.max[2]));

/** Full visual coverage is bounded by the verified source catalog, rather than
 * the compatibility preset. This is declared geometry cost, not host RAM. */
export function catalogStreamBudget(tiles:readonly StreamTile[]):Readonly<StreamBudget>{
 const cost={...zero(),tiles:Math.max(1,tiles.length)};
 for(const tile of tiles)for(const key of dimensions){
  if(!Number.isSafeInteger(tile[key])||tile[key]<0)throw Error('Invalid catalog cost');
  cost[key]+=tile[key];if(!Number.isSafeInteger(cost[key]))throw Error('Catalog cost overflow');
 }
 for(const key of dimensions)cost[key]=Math.max(1,cost[key]);
 return Object.freeze(cost);
}

export class CityStreamResidency<T extends StreamTile,H extends StreamHandle>{
 private resident=new Map<string,{tile:T;handle:H}>();
 private wanted=new Set<string>();private focus={x:0,z:0,visible:0,retain:0};
 private failures=new Map<string,string>();private blocked=new Set<string>();
 private pending:{tile:T;controller:AbortController}|null=null;
 private running:Promise<void>|null=null;private disposed=false;private configured=false;
 constructor(private tiles:readonly T[],private load:(tile:T,signal:AbortSignal)=>Promise<H>,private budget:Readonly<StreamBudget>=BASE_STREAM_LIMITS,policy:'compatible'|'full-city'='compatible'){
  const ceiling=policy==='full-city'?catalogStreamBudget(tiles):BASE_STREAM_LIMITS;
  if(!Number.isSafeInteger(budget.tiles)||budget.tiles<=0||budget.tiles>ceiling.tiles||dimensions.some(k=>!Number.isSafeInteger(budget[k])||budget[k]<=0||budget[k]>ceiling[k]))throw Error('Invalid or raised stream budget');
  const ids=new Set<string>();
  for(const t of tiles){
   if(!t.id||ids.has(t.id)||dimensions.some(k=>!Number.isSafeInteger(t[k])||t[k]<0)||t.bounds.min.length!==3||t.bounds.max.length!==3||t.bounds.min.some((v,i)=>!Number.isFinite(v)||!Number.isFinite(t.bounds.max[i])||v>t.bounds.max[i]))throw Error('Invalid stream tile');
   ids.add(t.id);
  }
  this.budget=Object.freeze({...budget});
  this.tiles=tiles.map(t=>({...t,bounds:{min:[...t.bounds.min],max:[...t.bounds.max]}}));
 }
 /** No work begins until an explicit focus request. A distant move cancels its
  * obsolete transfer, but waits for any non-cancellable decoder before starting another. */
 update(x:number,z:number,visibleRadius:number,retentionRadius:number):Promise<void>{
  if(this.disposed)return Promise.resolve();
  if(!Number.isFinite(x+z+visibleRadius+retentionRadius)||visibleRadius<0||retentionRadius<visibleRadius)throw Error('Invalid stream focus');
  return this.select(x,z,this.tiles.filter(t=>distance(t,x,z)<=visibleRadius).map(t=>t.id),this.tiles.filter(t=>distance(t,x,z)<=retentionRadius).map(t=>t.id));
 }
 /** Explicit selection lets the full world preserve different road, terrain,
  * shadow and reflection ranges without inventing a single smaller radius. */
 select(x:number,z:number,wanted:readonly string[],retain:readonly string[]):Promise<void>{
  if(this.disposed)return Promise.resolve();
  const known=new Set(this.tiles.map(t=>t.id)),retained=new Set(retain);
  if(!Number.isFinite(x+z)||wanted.some(id=>!known.has(id)||!retained.has(id))||retain.some(id=>!known.has(id)))throw Error('Invalid stream selection');
  this.configured=true;this.focus={x,z,visible:0,retain:0};
  this.wanted=new Set(wanted);this.blocked.clear();
  if(this.pending&&!this.wanted.has(this.pending.tile.id))this.pending.controller.abort();
  for(const [id,r] of this.resident){
   if(!retained.has(id))this.release(id);
   else r.handle.setVisible(this.wanted.has(id));
  }
  return this.start();
 }
 private start():Promise<void>{
  if(!this.running)this.running=this.pump().finally(()=>{
   this.running=null;
   // A focus update can arrive after the loop finished but before this promise
   // settled. Drain that new request as part of the same caller-visible wait.
   if(!this.disposed&&this.tiles.some(t=>this.wanted.has(t.id)&&!this.resident.has(t.id)&&!this.failures.has(t.id)&&!this.blocked.has(t.id)))return this.start();
  });
  return this.running;
 }
 private cost(includePending=true){
  const cost=zero();for(const r of this.resident.values())for(const k of dimensions)cost[k]+=r.tile[k];
  if(includePending&&this.pending)for(const k of dimensions)cost[k]+=this.pending.tile[k];return cost;
 }
 private fits(tile:T){const c=this.cost();return this.resident.size+(this.pending?1:0)+1<=this.budget.tiles&&dimensions.every(k=>c[k]+tile[k]<=this.budget[k]);}
 private release(id:string){const r=this.resident.get(id);if(!r)return;this.resident.delete(id);r.handle.dispose();}
 private async pump(){
  while(!this.disposed){
   const {x,z}=this.focus;
   const tile=this.tiles.filter(t=>this.wanted.has(t.id)&&!this.resident.has(t.id)&&!this.failures.has(t.id)&&!this.blocked.has(t.id)).sort((a,b)=>distance(a,x,z)-distance(b,x,z)||a.id.localeCompare(b.id))[0];
   if(!tile)return;
   // Hidden retained tiles are expendable; visible required geometry is never
   // silently removed to pretend the requested area is complete.
   for(const r of [...this.resident.values()].filter(r=>!this.wanted.has(r.tile.id)).sort((a,b)=>distance(b.tile,x,z)-distance(a.tile,x,z))){if(this.fits(tile))break;this.release(r.tile.id);}
   if(!this.fits(tile)){this.blocked.add(tile.id);continue;}
   const controller=new AbortController();this.pending={tile,controller};let handle:H|undefined;
   try{
    handle=await this.load(tile,controller.signal);
    if(this.disposed||controller.signal.aborted||!this.wanted.has(tile.id)){handle.dispose();handle=undefined;}
    else {handle.setVisible(true);this.resident.set(tile.id,{tile,handle});handle=undefined;}
   }catch(error){
    handle?.dispose();
    if(!controller.signal.aborted&&!this.disposed)this.failures.set(tile.id,error instanceof Error?error.message:String(error));
   }finally{this.pending=null;}
  }
 }
 dispose(){if(this.disposed)return;this.disposed=true;this.pending?.controller.abort();for(const id of [...this.resident.keys()])this.release(id);this.wanted.clear();}
 get handles(){return [...this.resident.values()].map(r=>r.handle);}
 get stats(){return {ready:this.configured&&!this.disposed&&!this.pending&&[...this.wanted].every(id=>this.resident.has(id)),disposed:this.disposed,
  pending:this.pending?.tile.id??null,resident:this.resident.size,visible:[...this.resident.keys()].filter(id=>this.wanted.has(id)).length,
  missing:[...this.wanted].filter(id=>!this.resident.has(id)),blocked:[...this.blocked],failed:Object.fromEntries(this.failures),declaredResident:this.cost(false),declaredWithPending:this.cost(),budget:{...this.budget}};}
}
