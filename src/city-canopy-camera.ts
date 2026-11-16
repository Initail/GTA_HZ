export type CameraPoint={x:number;y:number;z:number};
export type CanopyTriangleSoup={positions:ArrayLike<number>;indices:ArrayLike<number>;min:CameraPoint;max:CameraPoint};
type Instance={parts:readonly CanopyTriangleSoup[];matrix:Float32Array;offset:number};
/** Actual currently visible LOD geometry, with the renderer's float32 transform. */
export class CanopyCameraCollision {
 private cells=new Map<string,Instance[]>();private size=32;
 clear(){this.cells.clear();}
 add(parts:readonly CanopyTriangleSoup[],matrix:Float32Array,offset:number){
  const m=matrix,o=offset,points:CameraPoint[]=[];
  for(const p of parts)for(const x of [p.min.x,p.max.x])for(const y of [p.min.y,p.max.y])for(const z of [p.min.z,p.max.z])points.push({x:m[o]*x+m[o+8]*z+m[o+12],y:m[o+5]*y+m[o+13],z:m[o+2]*x+m[o+10]*z+m[o+14]});
  if(!points.length)return;const xs=points.map(p=>p.x),zs=points.map(p=>p.z),instance={parts,matrix,offset};
  for(let x=Math.floor(Math.min(...xs)/this.size);x<=Math.floor(Math.max(...xs)/this.size);x++)for(let z=Math.floor(Math.min(...zs)/this.size);z<=Math.floor(Math.max(...zs)/this.size);z++){const key=x+','+z,list=this.cells.get(key)??[];list.push(instance);this.cells.set(key,list);}
 }
 fraction(from:CameraPoint,to:CameraPoint,padding=.22){
  if(![from.x,from.y,from.z,to.x,to.y,to.z,padding].every(Number.isFinite)||padding<0)throw Error('Invalid camera segment');
  const length=Math.hypot(to.x-from.x,to.y-from.y,to.z-from.z);if(length<1e-6)return 1;
  let best=1,hit=false;const seen=new Set<Instance>();
  for(let x=Math.floor(Math.min(from.x,to.x)/this.size);x<=Math.floor(Math.max(from.x,to.x)/this.size);x++)for(let z=Math.floor(Math.min(from.z,to.z)/this.size);z<=Math.floor(Math.max(from.z,to.z)/this.size);z++)for(const item of this.cells.get(x+','+z)??[]){
   if(seen.has(item))continue;seen.add(item);const m=item.matrix,o=item.offset,det=m[o]*m[o+10]-m[o+8]*m[o+2];if(Math.abs(det)<1e-12||!m[o+5])continue;
   const local=(p:CameraPoint)=>{const dx=p.x-m[o+12],dz=p.z-m[o+14];return {x:(dx*m[o+10]-dz*m[o+8])/det,y:(p.y-m[o+13])/m[o+5],z:(dz*m[o]-dx*m[o+2])/det};};
   const a=local(from),b=local(to),d={x:b.x-a.x,y:b.y-a.y,z:b.z-a.z};
   for(const part of item.parts){if(!segmentBounds(a,b,part.min,part.max))continue;const p=part.positions,ix=part.indices;
    for(let i=0;i<ix.length;i+=3){const A=ix[i]*3,B=ix[i+1]*3,C=ix[i+2]*3;
     const e1x=p[B]-p[A],e1y=p[B+1]-p[A+1],e1z=p[B+2]-p[A+2],e2x=p[C]-p[A],e2y=p[C+1]-p[A+1],e2z=p[C+2]-p[A+2];
     const px=d.y*e2z-d.z*e2y,py=d.z*e2x-d.x*e2z,pz=d.x*e2y-d.y*e2x,den=e1x*px+e1y*py+e1z*pz;if(Math.abs(den)<1e-12)continue;
     const tx=a.x-p[A],ty=a.y-p[A+1],tz=a.z-p[A+2],u=(tx*px+ty*py+tz*pz)/den;if(u< -1e-9||u>1+1e-9)continue;
     const qx=ty*e1z-tz*e1y,qy=tz*e1x-tx*e1z,qz=tx*e1y-ty*e1x,v=(d.x*qx+d.y*qy+d.z*qz)/den;if(v< -1e-9||u+v>1+1e-9)continue;
     const t=(e2x*qx+e2y*qy+e2z*qz)/den;if(t>= -1e-9&&t<=best+1e-9){best=Math.min(best,Math.max(0,t));hit=true;}
    }
   }
  }
  return hit?Math.max(0,best-padding/length):1;
 }
}
function segmentBounds(a:CameraPoint,b:CameraPoint,min:CameraPoint,max:CameraPoint){let low=0,high=1;for(const k of ['x','y','z'] as const){const d=b[k]-a[k];if(Math.abs(d)<1e-12){if(a[k]<min[k]||a[k]>max[k])return false;continue;}let t0=(min[k]-a[k])/d,t1=(max[k]-a[k])/d;if(t0>t1)[t0,t1]=[t1,t0];low=Math.max(low,t0);high=Math.min(high,t1);if(low>high)return false;}return true;}
export function canopyTriangleSoup(positions:ArrayLike<number>,indices:ArrayLike<number>):CanopyTriangleSoup{
 if(positions.length%3||indices.length%3)throw Error('Invalid canopy triangle layout');const min={x:Infinity,y:Infinity,z:Infinity},max={x:-Infinity,y:-Infinity,z:-Infinity};
 for(let i=0;i<positions.length;i+=3)for(const [k,j]of [['x',0],['y',1],['z',2]] as const){const p=positions[i+j];if(!Number.isFinite(p))throw Error('Invalid canopy position');min[k]=Math.min(min[k],p);max[k]=Math.max(max[k],p);}
 for(let i=0;i<indices.length;i++)if(!Number.isInteger(indices[i])||indices[i]<0||indices[i]*3>=positions.length)throw Error('Invalid canopy index');return {positions,indices,min,max};
}
