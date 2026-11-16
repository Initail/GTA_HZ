/** Small local checkpoint only: records the last started phase, not a causal
 * crash verdict. No world data, save contents, timers, or network requests. */
export function createStartupTrace(storage:Pick<Storage,'setItem'>|null,key:string,clock=()=>performance.now()){
 const start=clock();let previous=start;
 const phases:{label:string;startedMs:number;previousPhaseMs:number}[]=[];
 return (label:string)=>{
  const now=clock();phases.push({label:label.slice(0,160),startedMs:Math.round(now-start),previousPhaseMs:Math.round(now-previous)});previous=now;
  if(phases.length>64)phases.shift();
  try{storage?.setItem(key,JSON.stringify({version:1,status:label==='ready'?'ready':label==='failed'?'error':'loading',phases}));}catch{}
 };
}
