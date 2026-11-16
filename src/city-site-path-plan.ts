import type {SiteSurface,SiteVertex} from './city-site-surfaces.ts';
export type SitePathDisplay={id:string;floorIds:string[];color:[number,number,number];sourceIds:string[]};
export type SitePathPlan={id:string;color:[number,number,number];sourceIds:string[];positions:number[];indices:number[];bounds:{min:SiteVertex;max:SiteVertex}};
/** Render and walking use identical triangles. No second city scaling or height offset. */
export function planSitePaths(floors:SiteSurface[],displays:SitePathDisplay[]=[]):SitePathPlan[]{
 if(displays.length>32)throw Error('Too many site path display groups');
 const byId=new Map(floors.map(f=>[f.id,f]));if(byId.size!==floors.length)throw Error('Duplicate path floor');
 const seen=new Set<string>(),used=new Set<string>();let total=0;
 return displays.map(d=>{
  if(!d.id||seen.has(d.id)||!d.floorIds.length||!d.sourceIds.length||d.sourceIds.some(id=>!/^way\/\d+$/.test(id))||d.color.length!==3||d.color.some(c=>!Number.isFinite(c)||c<0||c>1))throw Error('Invalid source path display');seen.add(d.id);
  const positions:number[]=[],indices:number[]=[],min:SiteVertex=[Infinity,Infinity,Infinity],max:SiteVertex=[-Infinity,-Infinity,-Infinity];
  for(const id of d.floorIds){const floor=byId.get(id);if(!floor||used.has(id))throw Error('Missing or repeated path floor');used.add(id);
   for(const t of floor.triangles){if(++total>20000||t.length!==3||t.some(v=>v.length!==3||!v.every(Number.isFinite)))throw Error('Path triangle budget or vertices invalid');
    const [a,b,c]=t;if((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<=0)throw Error('Path floor must face upward');
    const n=positions.length/3;for(const v of t){positions.push(v[0],v[2],v[1]);for(let k=0;k<3;k++){min[k]=Math.min(min[k],v[k]);max[k]=Math.max(max[k],v[k]);}}
    // These are direct game XYZ vertices, not a GLB under a mirrored root.
    // Babylon's left-handed winding keeps the original ENU triangle order.
    indices.push(n,n+1,n+2);
   }
  }
  if(!indices.length)throw Error('Empty displayed path');
  return {id:d.id,color:[...d.color],sourceIds:[...d.sourceIds],positions,indices,bounds:{min,max}};
 });
}
