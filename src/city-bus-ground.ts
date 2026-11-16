export type BusSurfaceHit = {height:number;role:'terrain'|'roads';tile:string;node:string;triangle:number};
export type BusGroundBinding = {sourceRoadId:string;sourceStopId:string;tier:number};

/** Resolve a source-bound ground road beneath an overpass using actual terrain.
 * The caller must verify this binding against the route's source way/node.
 * This selects support only: all higher triangles remain collision obstacles.
 * Elevated roads/tunnels need their own source-owned deck, never this fallback.
 */
export function selectBusGroundHit(hits:readonly BusSurfaceHit[],binding:BusGroundBinding|null):BusSurfaceHit|null {
 if(!binding||binding.tier!==0||!binding.sourceRoadId||!binding.sourceStopId||!hits.length||hits.some(h=>!Number.isFinite(h.height)))return null;
 const terrain=hits.filter(h=>h.role==='terrain');if(!terrain.length)return null;
 const low=Math.min(...terrain.map(h=>h.height)),high=Math.max(...terrain.map(h=>h.height));
 // Retain the diagnostic's existing .4g ambiguity band; this is not the
 // unchanged .04g tire-contact or .48g walking-step tolerance.
 if(high-low>.4)return null;
 const ground=hits.filter(h=>h.height>=low-1e-8&&h.height<=high+.4);
 if(!ground.length||Math.max(...ground.map(h=>h.height))-Math.min(...ground.map(h=>h.height))>.4)return null;
 return ground.reduce((a,b)=>a.height>=b.height?a:b);
}
