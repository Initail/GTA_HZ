import type {BaseStreamTile} from './city-stream-assets.ts';
import type {BaseStreamView} from './city-base-stream-plan.ts';
import {planBaseStreamPacks,type BaseStreamPack} from './city-stream-pack-plan.ts';
import {CityStreamResidency,type StreamHandle} from './city-stream-residency.ts';
export type PackHandle=StreamHandle&{selectMembers(ids:readonly string[]):void};
/** Owns real pack imports; selects logical members inside them. The world must
 * keep its loading overlay/input pause until stats.ready, as for base tiles. */
export class CityPackResidency<H extends PackHandle,P extends BaseStreamPack=BaseStreamPack> {
 private stream:CityStreamResidency<P,StreamHandle>;
 private owned=new Map<string,H>();private visible=new Map<string,readonly string[]>();
 private near=new Set<string>();private plan:ReturnType<typeof planBaseStreamPacks>|null=null;
 private key='';private operation:Promise<void>=Promise.resolve();private disposed=false;
 constructor(private sources:readonly BaseStreamTile[],private packs:readonly P[],load:(pack:P,signal:AbortSignal)=>Promise<H>){
  this.stream=new CityStreamResidency(packs,async(pack,signal)=>{
   const handle=await load(pack,signal);this.owned.set(pack.id,handle);let released=false;
   return {setVisible:visible=>{if(released)return;handle.selectMembers(visible?this.visible.get(pack.id)??[]:[]);handle.setVisible(visible);},dispose:()=>{if(released)return;released=true;this.owned.delete(pack.id);handle.dispose();}};
  });
 }
 request(view:BaseStreamView):Promise<void>{
  if(this.disposed)return Promise.resolve();
  const plan=this.plan=planBaseStreamPacks(this.sources,this.packs,view,this.near);
  this.visible=new Map(plan.admitted?plan.required.map(p=>[p.pack.id,p.visibleMembers]):[]);
  // Change member masks before any newly loaded representation is enabled.
  // A retained coarse pack may remain required for neighbouring source blocks.
  for(const [id,handle] of this.owned)handle.selectMembers(this.visible.get(id)??[]);
  if(!plan.admitted){this.key='';this.operation=this.stream.select(view.x,view.z,[],[]);return this.operation;}
  this.near=plan.near;
  const key=JSON.stringify([plan.required.map(p=>[p.pack.id,p.visibleMembers]),plan.retained.map(p=>p.id)]);
  if(key===this.key)return this.operation;
  this.key=key;this.operation=this.stream.select(view.x,view.z,plan.required.map(p=>p.pack.id),plan.retained.map(p=>p.id));return this.operation;
 }
 get handles(){return [...this.owned.values()];}
 get stats(){return {ready:!this.disposed&&!!this.plan?.admitted&&this.stream.stats.ready,disposed:this.disposed,plan:this.plan?{cost:this.plan.cost,exceeded:this.plan.exceeded,missing:this.plan.missing,sourceRequired:this.plan.sourceRequired.length,physicalRequired:this.plan.required.length}:null,residency:this.stream.stats};}
 dispose(){if(this.disposed)return;this.disposed=true;this.visible.clear();this.stream.dispose();}
}
