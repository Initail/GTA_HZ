import {Color3} from '@babylonjs/core/Maths/math.color.js';
import {Vector3} from '@babylonjs/core/Maths/math.vector.js';
import {DynamicTexture} from '@babylonjs/core/Materials/Textures/dynamicTexture.js';
import {StandardMaterial} from '@babylonjs/core/Materials/standardMaterial.js';
import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {MeshBuilder} from '@babylonjs/core/Meshes/meshBuilder.js';
import {TransformNode} from '@babylonjs/core/Meshes/transformNode.js';
import {VertexData} from '@babylonjs/core/Meshes/mesh.vertexData.js';
import {type Scene} from '@babylonjs/core/scene.js';
import type {CityLeisureSession,LeisureSite} from './city-leisure-session.ts';
import type {LeisurePose} from './city-leisure.ts';import type {SiteSurface} from './city-site-surfaces.ts';
export type CityLeisureSite=LeisureSite&{floors:SiteSurface[];solidSlabs:(SiteSurface&{thicknessGame:number})[];arrival:{point:[number,number];roadId:string;yaw:number}};
/** Small game-authored furnishings. No extra water plane or image-derived texture. */
export function createCityLeisureView(scene:Scene,site:CityLeisureSite){
 const root=new TransformNode('leisure:'+site.id,scene);
 const mat=(name:string,color:string)=>{const m=new StandardMaterial('leisure:'+name,scene);m.diffuseColor=Color3.FromHexString(color);m.specularColor.set(.06,.06,.06);m.maxSimultaneousLights=8;return m;};
 const wood=mat('wood','#76543c'),plank=mat('plank','#b59970'),stone=mat('path','#acaa98'),dark=mat('dark','#263c3f'),cream=mat('cream','#e9dec1'),blue=mat('keeper','#386d8b'),green=mat('volunteer','#57876c'),skin=mat('skin','#cba47e'),orange=mat('lifejacket','#d59340');
 function box(name:string,x:number,y:number,z:number,w:number,h:number,d:number,m:StandardMaterial,parent=root){const b=MeshBuilder.CreateBox('leisure:'+name,{width:w,height:h,depth:d},scene);b.position.set(x,y,z);b.material=m;b.parent=parent;b.receiveShadows=true;return b;}
 function ball(name:string,x:number,y:number,z:number,d:number,m:StandardMaterial,parent=root){const b=MeshBuilder.CreateSphere('leisure:'+name,{diameter:d,segments:8},scene);b.position.set(x,y,z);b.material=m;b.parent=parent;return b;}
 // Render the very same upward surface triangles used by walking and collision.
 for(const [name,groups,material] of [['paths',site.floors.filter(f=>!f.id.includes('marina-deck')),stone],['pier',site.floors.filter(f=>f.id.includes('marina-deck')),plank]] as const){
  const positions:number[]=[],indices:number[]=[];
  for(const g of groups)for(const t of g.triangles){const n=positions.length/3;for(const p of t)positions.push(p[0],p[2],p[1]);indices.push(n,n+2,n+1);}
  const mesh=new Mesh('leisure:'+name,scene),vd=new VertexData(),normals:number[]=[];VertexData.ComputeNormals(positions,indices,normals);vd.positions=positions;vd.indices=indices;vd.normals=normals;vd.applyToMesh(mesh);mesh.material=material;mesh.parent=root;mesh.receiveShadows=true;mesh.freezeWorldMatrix();
 }
 // Slab side walls close the visible deck perimeter, keeping collision thickness visible.
 for(const g of site.solidSlabs.filter(g=>g.id.includes('marina-deck'))){const positions:number[]=[],indices:number[]=[];const t=g.triangles,ring=[t[0][0],t[0][1],t[0][2],t[1][2]];for(let i=0;i<4;i++){const a=ring[i],b=ring[(i+1)%4],n=positions.length/3;positions.push(a[0],a[2],a[1],b[0],b[2],b[1],a[0],a[2]-g.thicknessGame,a[1],b[0],b[2]-g.thicknessGame,b[1]);indices.push(n,n+1,n+2,n+2,n+1,n+3);}const mesh=new Mesh('leisure:pier-sides',scene),vd=new VertexData(),normals:number[]=[];VertexData.ComputeNormals(positions,indices,normals);vd.positions=positions;vd.indices=indices;vd.normals=normals;vd.applyToMesh(mesh);mesh.material=wood;mesh.parent=root;wood.backFaceCulling=false;}
 function person(name:string,color:StandardMaterial,hat:boolean,seated=false){const p=new TransformNode('leisure:'+name,scene);p.parent=root;
  box(name+'-body',0,seated?.64:.95,0,.42,.56,.26,color,p);ball(name+'-head',0,seated?1.1:1.42,0,.31,skin,p);
  for(const x of [-.13,.13]){box(name+'-thigh',x,seated?.32:.4,seated?.18:0,.16,seated?.16:.65,seated?.5:.18,dark,p);if(seated)box(name+'-shin',x,.12,.4,.15,.35,.16,dark,p);box(name+'-shoe',x,seated?-.03:.06,seated?.46:.08,.18,.12,.28,dark,p);}
  for(const x of [-.28,.28]){const arm=box(name+'-arm',x,seated?.62:.88,seated?.14:0,.12,.45,.14,color,p);if(seated)arm.rotation.x=-.65;ball(name+'-hand',x,seated?.44:.61,seated?.29:.03,.13,skin,p);}
  if(hat){box(name+'-hat',0,1.58,0,.43,.06,.39,cream,p);box(name+'-hat-top',0,1.65,0,.28,.14,.27,cream,p);}return p;
 }
 const place=(node:TransformNode,p:LeisurePose)=>{node.position.set(p.x,p.height,p.z);node.rotation.y=p.yaw;};
 const keeper=person('boatkeeper',blue,true),volunteer=person('volunteer',green,false);place(keeper,site.keeper);place(volunteer,site.volunteer);
 // White vest and cap distinguish the two roles without cloning the same outfit.
 box('volunteer-vest',0,1.0,-.145,.35,.44,.03,cream,volunteer);box('volunteer-cap',0,1.58,.04,.33,.08,.34,green,volunteer);
 const boat=new TransformNode('leisure:rowboat',scene);boat.parent=root;const hull=new Mesh('leisure:boat-hull',scene),ps:number[]=[],ix:number[]=[];
 const stations=[[-1.8,.07],[-1.35,.52],[-.6,.66],[.6,.66],[1.35,.48],[1.8,.05]];
 for(const [z,w]of stations)ps.push(-w,.28,z,-w*.58,-.17,z,w*.58,-.17,z,w,.28,z);
 for(let j=0;j<5;j++)for(let s=0;s<3;s++){const a=j*4+s,b=a+4;ix.push(a,b,a+1,a+1,b,b+1);}
 const vd=new VertexData(),normals:number[]=[];VertexData.ComputeNormals(ps,ix,normals);vd.positions=ps;vd.indices=ix;vd.normals=normals;vd.applyToMesh(hull);hull.material=wood;hull.parent=boat;
 box('floor',0,-.08,0,.7,.08,2.6,plank,boat);for(const z of [-.7,.65])box('seat',0,.22,z,1.05,.09,.32,plank,boat);
 const oars=[-1,1].map(s=>{const p=new TransformNode('leisure:oar',scene);p.parent=boat;p.position.set(s*.62,.36,0);box('oar-shaft',s*.9,0,0,1.9,.045,.055,wood,p);box('oar-blade',s*1.75,0,0,.55,.06,.22,plank,p);return p;});
 const rower=person('rower',orange,false,true);rower.parent=boat;rower.position.set(0,.23,-.65);rower.rotation.y=Math.PI;
 function sign(text:string,p:LeisurePose){const r=new TransformNode('leisure:sign',scene);r.parent=root;place(r,p);box('post',0,.7,0,.075,1.4,.075,wood,r);const mesh=MeshBuilder.CreatePlane('leisure:sign-face',{width:2.4,height:.62},scene);mesh.parent=r;mesh.position.set(0,1.55,0);const tx=new DynamicTexture('leisure:lettering',{width:1024,height:256},scene,false);tx.drawText(text,null,155,'bold 60px sans-serif','#f7f1d8','#315c50',true);const m=mat('sign','#ffffff');m.diffuseTexture=tx;m.emissiveColor.set(.16,.16,.16);m.backFaceCulling=false;mesh.material=m;}
 sign('游船 · 沿栈桥登船',{...site.keeper,x:site.keeper.x+.9});sign('垂钓体验 · 游戏改编',{...site.volunteer,x:site.volunteer.x+1.0});
 const rod=new TransformNode('leisure:fishing-rod',scene);rod.parent=root;box('rod',0,1.1,1.05,.035,.035,2.3,wood,rod);const bob=ball('float',0,0,3,.13,orange,rod);const line=MeshBuilder.CreateLines('leisure:line',{points:[new Vector3(0,1.1,2.2),new Vector3(0,-.6,3)],updatable:true},scene);line.color=Color3.FromHexString('#eee9ce');line.parent=rod;
 const lineVertices=new Float32Array([0,1.1,2.2,0,-.6,3]);
 let phase=0;return {root,
  peopleBlocked(x:number,z:number,height:number){return [site.keeper,site.volunteer].some(p=>Math.hypot(p.x-x,p.z-z)<.38&&height<p.height+1.75&&height+1.6>p.height);},
  update(session:CityLeisureSession,dt:number,paused:boolean){if(!paused)phase+=dt;const b=session.boat;place(boat,b.pose);rower.setEnabled(b.active);const near=Math.hypot(b.pose.x-site.dock.berth.x,b.pose.z-site.dock.berth.z)<5;for(const [i,o]of oars.entries()){o.rotation.y=near?Math.PI/2:Math.sin(phase*2.5)*.35*Math.min(1,Math.abs(b.speed));o.rotation.z=near?0:Math.cos(phase*2.5)*.16*(i?1:-1);}
   const f=session.fishing;rod.setEnabled(session.fishingActive);const fisher=session.fishingActor;place(rod,fisher);bob.position.y=site.dock.berth.height-fisher.height+(f.phase==='bite'?-.06:.06)+Math.sin(phase*3)*.025;lineVertices[4]=bob.position.y;line.updateVerticesData('position',lineVertices);
  },dispose(){root.dispose(false,true);}
 };
}
