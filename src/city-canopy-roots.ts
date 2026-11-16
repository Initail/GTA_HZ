/** Authored bank heights are game units, tied to exact planting bytes. */
export type CanopyRootOverrides={version:1;cityId:string;plantingSha256:string;placements:{treeIndex:number;heightGame:number}[]};
export function bindCanopyRootHeights<T extends readonly number[]>(trees:readonly T[],overrides:CanopyRootOverrides,plantingSha256:string,cityId:string):Map<T,number>{
 if(overrides.version!==1||overrides.cityId!==cityId||overrides.plantingSha256!==plantingSha256)throw Error('Canopy root-height asset binding differs');
 const heights=new Map<T,number>();
 for(const p of overrides.placements){if(!Number.isInteger(p.treeIndex)||p.treeIndex<0||p.treeIndex>=trees.length||!Number.isFinite(p.heightGame)||heights.has(trees[p.treeIndex]))throw Error('Invalid canopy root-height placement');heights.set(trees[p.treeIndex],p.heightGame);}
 return heights;
}
