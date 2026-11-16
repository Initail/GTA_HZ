import {closest} from './driving.ts';
import {roadAllows,type TravelMode,type SourceAccessTags} from './road-access.ts';
import type {V2} from './city-types.ts';
// Double-precision contact roundoff in this city frame; far below any mesh
// tolerance or gameplay step/clearance. A 1e-8g penetration remains solid.
const CONTACT_EPSILON_GAME=1e-10;

/** Source-owned site surfaces use east/north/up game units, already scaled. */
export type SiteVertex=[east:number,north:number,up:number];
export type SiteSurface={id:string;triangles:[SiteVertex,SiteVertex,SiteVertex][];openEdges?:[boolean,boolean,boolean][]};
export type SiteWalkHint={id:string|null;height:number};
export type SiteAccessCorridor={sourceId:string;points:V2[];widthGame:number;kind:string;sourceAccessTags:SourceAccessTags};
export type SiteSurfaceData={pathDisplays?:{floorIds:string[]}[];accessCorridors?:SiteAccessCorridor[];cityId:'hangzhou';units:'game east/north/up; scale applied once';terrainCuts:SiteSurface[];walkFloors:SiteSurface[];terrainPatches?:SiteSurface[];roadSurfaces?:(SiteSurface&{roadIds:string[]})[];solidSlabs?:(SiteSurface&{thicknessGame:number})[]};
type Face={id:string;p:[V2,V2,V2];h:[number,number,number];det:number;edgeLengths:[number,number,number];openEdges?:[boolean,boolean,boolean]};

/** Site floors do not create road edges or bypass building collision. The
 * walking caller retains the previous height and the original step limit. */
export class CitySiteSurfaces{
 private reservedPathIds=new Set<string>();
 private accessCells=new Map<string,{sourceId:string;a:V2;b:V2;width:number;denied:Record<TravelMode,boolean>}[]>();
 private cutCells=new Map<string,Face[]>();private floorCells=new Map<string,Face[]>();private size=32;
 private patchCells=new Map<string,Face[]>();private roadCells=new Map<string,Face[]>();private slabCells=new Map<string,Face[]>();
 private roadGroups=new Map<string,string>();private slabThickness=new Map<string,number>();
 constructor(data:SiteSurfaceData){
  if(data.cityId!=='hangzhou'||data.units!=='game east/north/up; scale applied once')throw Error('Invalid site surface units');
  const floorIds=new Set(data.walkFloors.map(f=>f.id));for(const display of data.pathDisplays??[])for(const id of display.floorIds){if(!floorIds.has(id))throw Error('Displayed path floor missing');this.reservedPathIds.add(id);}
  const accessIds=new Set<string>();
  for(const corridor of data.accessCorridors??[]){
   if(!corridor.sourceId||accessIds.has(corridor.sourceId)||!Number.isFinite(corridor.widthGame)||corridor.widthGame<=0||corridor.points.length<2||corridor.points.some(p=>p.length!==2||!p.every(Number.isFinite))||!corridor.sourceAccessTags||Object.values(corridor.sourceAccessTags).some(v=>typeof v!=='string'))throw Error('Invalid site access corridor');
   accessIds.add(corridor.sourceId);
   const denied=Object.fromEntries((['motorcar','foot','bicycle','bus'] as const).map(mode=>[mode,!roadAllows({...corridor,oneway:false},mode).allowed])) as Record<TravelMode,boolean>;
   for(let i=1;i<corridor.points.length;i++){
    const a=corridor.points[i-1],b=corridor.points[i],margin=corridor.widthGame/2;
    const segment={sourceId:corridor.sourceId,a,b,width:corridor.widthGame,denied};
    for(let x=Math.floor((Math.min(a[0],b[0])-margin)/this.size);x<=Math.floor((Math.max(a[0],b[0])+margin)/this.size);x++)for(let z=Math.floor((Math.min(a[1],b[1])-margin)/this.size);z<=Math.floor((Math.max(a[1],b[1])+margin)/this.size);z++){
     const key=x+','+z,cell=this.accessCells.get(key)??[];cell.push(segment);this.accessCells.set(key,cell);
    }
   }
  }
  for(const group of data.roadSurfaces??[])for(const roadId of group.roadIds){if(this.roadGroups.has(roadId))throw Error('Duplicate source road surface');this.roadGroups.set(roadId,group.id);}
  for(const group of data.solidSlabs??[]){if(!Number.isFinite(group.thicknessGame)||group.thicknessGame<=0)throw Error('Invalid solid slab thickness');this.slabThickness.set(group.id,group.thicknessGame);}
  for(const [groups,cells] of [[data.terrainCuts,this.cutCells],[data.walkFloors,this.floorCells],[data.terrainPatches??[],this.patchCells],[data.roadSurfaces??[],this.roadCells],[data.solidSlabs??[],this.slabCells]] as const){
   const ids=new Set<string>();let count=0;
   for(const group of groups){
    if(!group.id||ids.has(group.id))throw Error('Duplicate site surface identity');ids.add(group.id);
    if(group.openEdges&&(group.openEdges.length!==group.triangles.length||group.openEdges.some(e=>e.length!==3||e.some(v=>typeof v!=='boolean'))))throw Error('Invalid site boundary ownership');
    for(const [index,triangle] of group.triangles.entries()){
     if(++count>200000||triangle.length!==3||triangle.some(p=>p.length!==3||!p.every(Number.isFinite)))throw Error('Invalid site surface geometry');
     const p=triangle.map(v=>[v[0],v[1]] as V2) as Face['p'],h=triangle.map(v=>v[2]) as Face['h'];
     const det=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0]);
     if(det<=0)throw Error('Site surface must face upward');
     const edgeLengths=p.map((a,i)=>Math.hypot(p[(i+1)%3][0]-a[0],p[(i+1)%3][1]-a[1])) as Face['edgeLengths'];
     const face={id:group.id,p,h,det,edgeLengths,openEdges:group.openEdges?.[index]},xs=p.map(v=>v[0]),zs=p.map(v=>v[1]);
     for(let x=Math.floor(Math.min(...xs)/this.size);x<=Math.floor(Math.max(...xs)/this.size);x++)
      for(let z=Math.floor(Math.min(...zs)/this.size);z<=Math.floor(Math.max(...zs)/this.size);z++){
       const key=x+','+z,cell=cells.get(key)??[];cell.push(face);cells.set(key,cell);
      }
    }
   }
  }
 }
 /** Prevent generated vegetation roots on explicitly displayed ground paths. Crowns may still shade paths. */
 reservedWalkPath(x:number,z:number){return this.at(this.floorCells,x,z).some(f=>this.reservedPathIds.has(f.id));}
 /** Access is attached to the actual walk deck. A bridge does not restrict
  * unrelated traffic beneath it; public junction priority is decided by caller. */
 restrictedSourceAt(x:number,z:number,feet:number,mode:TravelMode){
  const segments=this.accessCells.get(Math.floor(x/this.size)+','+Math.floor(z/this.size));
  const denied=segments?.find(s=>s.denied[mode]&&closest(x,z,s.a,s.b).d<s.width/2);
  if(!denied||!this.at(this.floorCells,x,z).some(f=>Math.abs(f.height-feet)<1.5))return null;
  return denied.sourceId;
 }
 private at(cells:Map<string,Face[]>,x:number,z:number){
  if(!Number.isFinite(x+z))throw Error('Invalid site surface query');
  const result:{id:string;height:number}[]=[];
  for(const face of cells.get(Math.floor(x/this.size)+','+Math.floor(z/this.size))??[]){
   const [a,b,c]=face.p,dx=x-a[0],dz=z-a[1];
   // One physical shared edge gets one tolerance, regardless of the width
   // of either adjacent triangle. Barycentric EPS grew with face aspect ratio
   // and gave thin skylight trim both a gap and a second lower floor.
   const edgeDistances=face.p.map((p,i)=>{const q=face.p[(i+1)%3];return ((q[0]-p[0])*(z-p[1])-(q[1]-p[1])*(x-p[0]))/face.edgeLengths[i];});
   if(edgeDistances.some(d=>d< -1e-9))continue;
   if(face.openEdges?.some((open,i)=>open&&Math.abs(edgeDistances[i])<=1e-9))continue;
   const u=(dx*(c[1]-a[1])-dz*(c[0]-a[0]))/face.det;
   const v=((b[0]-a[0])*dz-(b[1]-a[1])*dx)/face.det;
   let height=face.h[0]+u*(face.h[1]-face.h[0])+v*(face.h[2]-face.h[0]);
   if(u<0||v<0||u+v>1){
    // A numerical boundary allowance is not permission to extrapolate a
    // nearly collinear source face. Use its nearest finite edge only when
    // the actual Euclidean distance is within the same allowance.
    let distance=Infinity;
    for(let i=0;i<3;i++){
     const p=face.p[i],q=face.p[(i+1)%3],ex=q[0]-p[0],ez=q[1]-p[1];
     const t=Math.max(0,Math.min(1,((x-p[0])*ex+(z-p[1])*ez)/(ex*ex+ez*ez)));
     const d=Math.hypot(x-p[0]-ex*t,z-p[1]-ez*t);
     if(d<distance){distance=d;height=face.h[i]+t*(face.h[(i+1)%3]-face.h[i]);}
    }
    if(distance>1e-9)continue;
   }
   result.push({id:face.id,height});
  }
  return result;
 }
 /** Cuts can lower earth inside explicit source domains; they never raise it. */
 groundAt(x:number,z:number,uncutHeight:number){
  if(!Number.isFinite(uncutHeight))throw Error('Invalid uncut ground height');
  const patches=this.at(this.patchCells,x,z);this.assertContinuous(patches);
  return this.at(this.cutCells,x,z).reduce((y,p)=>Math.min(y,p.height),patches[0]?.height??uncutHeight);
 }
 private assertContinuous(matches:{height:number}[]){if(matches.length&&Math.max(...matches.map(p=>p.height))-Math.min(...matches.map(p=>p.height))>.0001)throw Error('Overlapping source TIN heights disagree');}
 roadAt(roadId:string,x:number,z:number){
  const group=this.roadGroups.get(roadId);if(!group)return undefined;
  const matches=this.at(this.roadCells,x,z).filter(p=>p.id===group);this.assertContinuous(matches);return matches[0]?.height;
 }
 blocked(x:number,z:number,feet:number,bodyHeight=1.6){
  if(!Number.isFinite(feet+bodyHeight)||bodyHeight<=0)throw Error('Invalid actor height');
  return this.at(this.slabCells,x,z).some(p=>feet<p.height-CONTACT_EPSILON_GAME&&feet+bodyHeight>p.height-this.slabThickness.get(p.id)!+CONTACT_EPSILON_GAME);
 }
 walkAt(x:number,z:number,groundHeight:number,previous:number|SiteWalkHint=groundHeight){
  const previousHeight=typeof previous==='number'?previous:previous.height,previousId=typeof previous==='number'?null:previous.id;
  if(!Number.isFinite(groundHeight+previousHeight))throw Error('Invalid walking surface height');
  const available=this.at(this.floorCells,x,z).filter(p=>p.height>=groundHeight-.001);
  // Stay on a still-present source deck. Nearby stacked decks are not steps,
  // and repeated stationary updates must not walk the actor up through them.
  const same=previousId?available.filter(p=>p.id===previousId):[];
  const floors=same.length?same:available.filter(p=>Math.abs(p.height-previousHeight)<.48);
  floors.sort((a,b)=>Math.abs(a.height-previousHeight)-Math.abs(b.height-previousHeight)||b.height-a.height||a.id.localeCompare(b.id));
  return floors[0]??{id:null,height:groundHeight};
 }
}
