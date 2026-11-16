/** Source-bound access decisions. This module never changes physical road geometry.
 * `allowed` means usable for unconditional public travel in this game profile.
 * `basis` distinguishes source facts from gameplay defaults and legacy compatibility.
 */
export type TravelMode='motorcar'|'foot'|'bicycle'|'bus';
export type SourcePointOrder='osm-forward'|'osm-reversed';
export type SourceAccessTags=Readonly<Record<string,string>>;
export type AccessRoad={kind:string;oneway:boolean;sourceAccessTags?:SourceAccessTags};
export type AccessStatus='allowed'|'denied'|'restricted'|'unknown';
export type SourceEvidence='explicit'|'default'|'missing';
export type RoadAccessDecision={
 status:AccessStatus;allowed:boolean;mode:TravelMode;basis:string;evidence:SourceEvidence;
 sourceKey?:string;sourceValue?:string;baseStatus:AccessStatus;
 /** All source conditional tags are retained, including ones irrelevant to this mode. */
 conditional:Record<string,string>;
 /** Subset that could affect this mode and is not shadowed by a more specific base rule. */
 unresolved:Record<string,string>;
 /** Relevant qualifier keys / values that this small resolver does not interpret. */
 unhandled:Record<string,string>;
};
export type RoadDirectionDecision={
 status:'known'|'legacy'|'restricted'|'unknown';mode:TravelMode;pointOrder:SourcePointOrder;
 /** Relative to CURRENT road.points order. null requires caller policy, never means true. */
 forward:boolean|null;backward:boolean|null;
 sourceForward:boolean|null;sourceBackward:boolean|null;
 sourceKey?:string;sourceValue?:string;basis:string;
 conditional:Record<string,string>;unresolved:Record<string,string>;unhandled:Record<string,string>;
};
const ACCESS_KEYS:Record<TravelMode,readonly string[]>={
 motorcar:['motorcar','motor_vehicle','vehicle','access'],
 foot:['foot','access'],bicycle:['bicycle','vehicle','access'],
 bus:['bus','psv','motor_vehicle','vehicle','access'],
};
const DIRECTION_KEYS:Record<TravelMode,readonly string[]>={
 motorcar:['oneway:motorcar','oneway:motor_vehicle','oneway:vehicle','oneway'],
 foot:['oneway:foot'],bicycle:['oneway:bicycle','oneway:vehicle','oneway'],
 bus:['oneway:bus','oneway:psv','oneway:motor_vehicle','oneway:vehicle','oneway'],
};
const PUBLIC=new Set(['yes','designated','permissive','official']);
const DENIED=new Set(['no','private','permit']);
const RESTRICTED=new Set(['destination','customers','customer','delivery','agricultural','forestry','discouraged','dismount','use_sidepath']);
const MOTOR_HIGHWAYS=new Set(['motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','residential','unclassified','service','living_street','road','track']);
const NON_MOTOR_HIGHWAYS=new Set(['pedestrian','footway','cycleway','path','steps','bridleway','via_ferrata']);
const normal=(value:string)=>value.trim().toLowerCase();
const present=(tags:SourceAccessTags,key:string)=>Object.prototype.hasOwnProperty.call(tags,key)&&tags[key].trim()!=='';
function first(tags:SourceAccessTags,keys:readonly string[]){for(let index=0;index<keys.length;index++){const key=keys[index];if(present(tags,key))return {key,value:tags[key],index};}return undefined;}
function conditionals(tags:SourceAccessTags){return Object.fromEntries(Object.entries(tags).filter(([key])=>key.endsWith(':conditional')));}
function relevantConditionals(tags:SourceAccessTags,keys:readonly string[],selectedIndex:number){
 const result:Record<string,string>={};
 for(const [key,value] of Object.entries(tags)){
  if(!key.endsWith(':conditional'))continue;
  for(let i=0;i<keys.length&&i<=selectedIndex;i++)if(key===keys[i]+':conditional'||key.startsWith(keys[i]+':forward:')||key.startsWith(keys[i]+':backward:')||key.startsWith(keys[i]+':lanes:'))result[key]=value;
 }
 return result;
}
function accessQualifiers(tags:SourceAccessTags,keys:readonly string[],selectedIndex:number){
 const result:Record<string,string>={};
 for(const [key,value] of Object.entries(tags))for(let i=0;i<keys.length&&i<=selectedIndex;i++){
  if(key.endsWith(':conditional'))continue;
  if(key===keys[i]+':forward'||key===keys[i]+':backward'||key===keys[i]+':lanes'||key.startsWith(keys[i]+':lanes:'))result[key]=value;
 }
 return result;
}
function defaultAccess(kind:string,mode:TravelMode,tags:SourceAccessTags):{status:AccessStatus;basis:string}{
 // Deliberately small gameplay defaults, not a claim about every local traffic law.
 if(mode==='motorcar'||mode==='bus'){
  if(kind==='busway')return {status:mode==='bus'?'allowed':'denied',basis:'game-highway-default'};
  if(MOTOR_HIGHWAYS.has(kind))return {status:'allowed',basis:'game-highway-default'};
  if(NON_MOTOR_HIGHWAYS.has(kind))return {status:'denied',basis:'game-highway-default'};
 }else{
  if(kind==='motorway'||kind==='motorway_link'||normal(tags.motorroad??'')==='yes')return {status:'denied',basis:'game-motorroad-default'};
  if(mode==='bicycle'&&(kind==='steps'||kind==='via_ferrata'))return {status:'restricted',basis:'game-dismount-or-route-review'};
  if(MOTOR_HIGHWAYS.has(kind)||NON_MOTOR_HIGHWAYS.has(kind))return {status:'allowed',basis:'game-highway-default'};
 }
 return {status:'unknown',basis:'unsupported-highway-default'};
}
export function roadAllows(road:AccessRoad,mode:TravelMode):RoadAccessDecision{
 const tags=road.sourceAccessTags??{},kind=normal(tags.highway??road.kind),conditional=conditionals(tags);
 const result=(status:AccessStatus,basis:string,evidence:SourceEvidence,extra:Partial<RoadAccessDecision>={}):RoadAccessDecision=>({status,allowed:status==='allowed',mode,basis,evidence,baseStatus:status,conditional,unresolved:{},unhandled:{},...extra});
 if(kind==='construction'||kind==='proposed'||road.kind==='construction'||road.kind==='proposed')return result('denied','non-operational-highway',road.sourceAccessTags?'explicit':'default',{sourceKey:'highway',sourceValue:tags.highway??road.kind});
 if(road.sourceAccessTags===undefined)return result('allowed','legacy-gameplay-compatibility','missing');
 const keys=ACCESS_KEYS[mode],selected=first(tags,keys),index=selected?.index??keys.length;
 const unresolved=relevantConditionals(tags,keys,index),unhandled=accessQualifiers(tags,keys,index);
 let baseStatus:AccessStatus,basis:string;
 if(selected){
  const value=normal(selected.value);
  baseStatus=PUBLIC.has(value)?'allowed':DENIED.has(value)?'denied':RESTRICTED.has(value)?'restricted':'unknown';basis='source-access-tag';
  if(baseStatus==='unknown')unhandled[selected.key]=selected.value;
 }else {const fallback=defaultAccess(kind,mode,tags);baseStatus=fallback.status;basis=fallback.basis;}
 // An unconditional denial stays closed. A conditional may allow an exception,
 // but this resolver never grants it without an evaluator/authorized context.
 const pending=Object.keys(unresolved).length>0||Object.keys(unhandled).some(key=>key!==selected?.key);
 const status=baseStatus==='denied'?'denied':pending?'restricted':baseStatus;
 return result(status,pending&&baseStatus!=='denied'?'unresolved-access-conditions':basis,selected?'explicit':'default',{
  baseStatus,sourceKey:selected?.key,sourceValue:selected?.value,unresolved,unhandled,
 });
}
function parseDirection(value:string):[boolean,boolean]|null{
 switch(normal(value)){
  case 'yes':case '1':case 'true':return [true,false];
  case '-1':return [false,true];
  case 'no':case '0':case 'false':return [true,true];
  default:return null;
 }
}
/** Resolve raw OSM directions, then map once to the CURRENT prepared points.
 * For roads normalized from oneway=-1, pass 'osm-reversed'.
 * oneway:bicycle=-1 then maps to current forward; oneway:bicycle=yes maps to
 * current backward. oneway:bicycle=no remains bidirectional in either order.
 * Missing source tags returns legacy/null, so the caller can preserve its old
 * graph or geometric direction behavior. This function is separate from access.
 */
export function roadDirections(road:AccessRoad,mode:TravelMode,pointOrder:SourcePointOrder):RoadDirectionDecision{
 if(pointOrder!=='osm-forward'&&pointOrder!=='osm-reversed')throw new Error('Source point order must be explicit');
 const tags=road.sourceAccessTags??{},conditional=conditionals(tags),kind=normal(tags.highway??road.kind);
 const result=(status:RoadDirectionDecision['status'],basis:string,pair:[boolean,boolean]|null,extra:Partial<RoadDirectionDecision>={}):RoadDirectionDecision=>({
  status,mode,pointOrder,basis,forward:pair?(pointOrder==='osm-forward'?pair[0]:pair[1]):null,backward:pair?(pointOrder==='osm-forward'?pair[1]:pair[0]):null,
  sourceForward:pair?.[0]??null,sourceBackward:pair?.[1]??null,conditional,unresolved:{},unhandled:{},...extra,
 });
 if(road.sourceAccessTags===undefined)return result('legacy','legacy-direction-caller-policy',null);
 const keys=[...DIRECTION_KEYS[mode]];
 if(mode==='foot'&&(kind==='steps'||kind==='via_ferrata'))keys.push('oneway');
 const selected=first(tags,keys),index=selected?.index??keys.length,unresolved=relevantConditionals(tags,keys,index);
 if(Object.keys(unresolved).length)return result('restricted','unresolved-direction-conditions',null,{sourceKey:selected?.key,sourceValue:selected?.value,unresolved});
 if(selected){const pair=parseDirection(selected.value);return result(pair?'known':'unknown',pair?'source-direction-tag':'unsupported-direction-value',pair,{sourceKey:selected.key,sourceValue:selected.value,unhandled:pair?{}:{[selected.key]:selected.value}});}
 if(mode==='foot'){
  if((kind==='path'||kind==='footway')&&present(tags,'oneway:conditional'))return result('restricted','ambiguous-pedestrian-direction-conditions',null,{unresolved:{'oneway:conditional':tags['oneway:conditional']}});
  // OSM documents generic oneway on path/footway as ambiguous for walkers.
  if((kind==='path'||kind==='footway')&&present(tags,'oneway')&&normal(tags.oneway)!=='no'&&normal(tags.oneway)!=='0'&&normal(tags.oneway)!=='false')return result('unknown','ambiguous-pedestrian-oneway',null,{unhandled:{oneway:tags.oneway}});
  return result('known','pedestrian-street-default',[true,true]);
 }
 const implied=kind==='motorway'||normal(tags.junction??'')==='roundabout';
 return result('known',implied?'source-highway-implied-oneway':'no-source-oneway-recorded',implied?[true,false]:[true,true]);
}
