import type {Scene} from '@babylonjs/core/scene.js';
import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {VertexData} from '@babylonjs/core/Meshes/mesh.vertexData.js';
import {StandardMaterial} from '@babylonjs/core/Materials/standardMaterial.js';
import {Color3} from '@babylonjs/core/Maths/math.color.js';
import {RawTexture} from '@babylonjs/core/Materials/Textures/rawTexture.js';
import {Texture} from '@babylonjs/core/Materials/Textures/texture.js';
import type {SitePathPlan} from './city-site-path-plan.ts';
export function createCitySitePaths(scene:Scene,plans:SitePathPlan[]){
 const materials=new Map<string,StandardMaterial>(),meshes:Mesh[]=[];
 // Original procedural grey stone, not a photo texture or a claim of surveyed
 // slab dimensions. One tiny mipmapped atlas is shared by every path group.
 const pixels=new Uint8Array(128*128*4);for(let y=0;y<128;y++)for(let x=0;x<128;x++){
  const course=Math.floor(y/64),xx=(x+course*32)%64,joint=xx<2||y%64<2;
  const grain=((x*73856093^y*19349663)>>>0)%13,shade=joint?103:184+grain,at=(y*128+x)*4;pixels.set([shade,shade,shade,255],at);
 }
 const stone=plans.length?RawTexture.CreateRGBATexture(pixels,128,128,scene,true,false,Texture.TRILINEAR_SAMPLINGMODE):null;
 if(stone){stone.name='site-path:original-stone';stone.wrapU=stone.wrapV=Texture.WRAP_ADDRESSMODE;stone.anisotropicFilteringLevel=4;}
 for(const p of plans){
  const key=p.color.join(',');let material=materials.get(key);
  if(!material){material=new StandardMaterial('site-path:'+key,scene);material.diffuseColor=Color3.FromArray(p.color);material.diffuseTexture=stone;material.specularColor=Color3.Black();materials.set(key,material);}
  const mesh=new Mesh('site-path:'+p.id,scene),v=new VertexData(),normals:number[]=[];VertexData.ComputeNormals(p.positions,p.indices,normals);
  const uvs:number[]=[],ox=Math.floor(p.bounds.min[0]/.72)*.72,oz=Math.floor(p.bounds.min[1]/.36)*.36;
  for(let i=0;i<p.positions.length;i+=3)uvs.push((p.positions[i]-ox)/.72,(p.positions[i+2]-oz)/.36);
  v.positions=p.positions;v.indices=p.indices;v.normals=normals;v.uvs=uvs;v.applyToMesh(mesh);mesh.material=material;mesh.isPickable=false;mesh.receiveShadows=true;mesh.freezeWorldMatrix();
  mesh.metadata={sourceIds:p.sourceIds,castsShadows:false};meshes.push(mesh);
 }
 let disposed=false;
 return {meshes,update(x:number,z:number){if(disposed)return;plans.forEach((p,i)=>{const dx=Math.max(p.bounds.min[0]-x,0,x-p.bounds.max[0]),dz=Math.max(p.bounds.min[1]-z,0,z-p.bounds.max[1]);meshes[i].setEnabled(Math.hypot(dx,dz)<900);});},
  dispose(){if(disposed)return;disposed=true;meshes.forEach(m=>m.dispose());materials.forEach(m=>m.dispose());stone?.dispose();},
  stats:{groups:plans.length,triangles:plans.reduce((n,p)=>n+p.indices.length/3,0),materials:materials.size,texturePixels:stone?128*128:0,source:'same physical walking triangles; geographic scale already applied; original procedural stone, dimensions estimated'}};
}
