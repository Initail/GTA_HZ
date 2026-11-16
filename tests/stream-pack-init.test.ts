import {test} from 'node:test';import assert from 'node:assert/strict';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';import {Scene} from '@babylonjs/core/scene.js';
import {AssetContainer} from '@babylonjs/core/assetContainer.js';import {Mesh} from '@babylonjs/core/Meshes/mesh.js';import {VertexData} from '@babylonjs/core/Meshes/mesh.vertexData.js';
import {CityBaseStream,type BaseStreamSources} from '../src/city-base-stream.ts';
import {CityStreamGlbLoader} from '../src/city-stream-glb.ts';
import {packFixture} from './stream-pack-manifest.test.ts';

// Real CityBaseStream -> catalog -> metadata -> residency -> parent mask ->
// world hook. Only HTTP and the actual GLB decoder are fixtures. These checks
// explicitly do not claim to render the full world or decode real pack assets.
function setup(){
 const fixture=packFixture(),engine=new NullEngine(),scene=new Scene(engine);
 const originalFetch=globalThis.fetch,originalLoad=CityStreamGlbLoader.prototype.load,originalLocation=Object.getOwnPropertyDescriptor(globalThis,'location');
 Object.defineProperty(globalThis,'location',{configurable:true,value:new URL('http://pack.test/')});globalThis.fetch=fixture.fetcher;
 fixture.root.sourceManifests={};
 const sources:BaseStreamSources={decoderUrl:'/decoder.js'} as BaseStreamSources;
 for(const tile of fixture.tiles){
  const role=tile.role,doc={schemaVersion:1,role,source:{sha256:tile.sha256},tileSizeGame:640,tiles:[tile],textures:role==='roads'?fixture.textures:[],totals:{tiles:1,bytes:tile.bytes,logicalBytes:tile.logicalBytes,triangles:tile.triangles}};
  const record=fixture.put(role+'/manifest.json',doc);fixture.root.sourceManifests[role]=record.sha256;
  sources[role]={manifestUrl:'http://pack.test/'+record.file,manifestBytes:record.bytes,manifestSha256:record.sha256,sourceSha256:tile.sha256};
 }
 sources.packs=fixture.seal();
 const close=()=>{scene.dispose();engine.dispose();globalThis.fetch=originalFetch;CityStreamGlbLoader.prototype.load=originalLoad;if(originalLocation)Object.defineProperty(globalThis,'location',originalLocation);else delete (globalThis as any).location;};
 return {fixture,scene,sources,close};
}
test('actual base init loads all source identities before one pack reaches the world and unloads it once',async()=>{
 const f=setup();let attached=0,detached=0,disposed=0;
 try{
  CityStreamGlbLoader.prototype.load=async function(pack:any,signal:AbortSignal){
   signal.throwIfAborted();assert.equal(f.fixture.requested.length,6,'three original manifests, index, shard and metadata precede decoding');
   const container=new AssetContainer(f.scene),root=new Mesh('__root__',f.scene);root.setEnabled(false);container.meshes.push(root);
   for(const binding of f.fixture.meta.nodes){const mesh=new Mesh(binding.name,f.scene),data=new VertexData();data.positions=[0,0,0,1,0,0,0,1,0];data.indices=[0,1,2];data.applyToMesh(mesh);mesh.parent=root;mesh.freezeWorldMatrix();container.meshes.push(mesh);}
   const detach=(this as any).hooks.attach(pack,container,[{}]);let released=false;
   return {container,setVisible:(visible:boolean)=>root.setEnabled(visible),dispose:()=>{if(released)return;released=true;disposed++;detach();container.dispose();}};
  };
  const stream=new CityBaseStream(f.scene,f.sources,{attach:()=>{throw Error('single-role path used');},attachPack:(pack,container,materials,metadata)=>{
   attached++;assert.equal(pack.id,'near-0-0');assert.equal(materials.length,metadata.materialOrigins.length);assert.equal(container.transformNodes.length,3);return ()=>detached++;
  }});
  await stream.init({x:0,z:0,overview:false});assert.equal(stream.stats.ready,true);assert.equal(stream.stats.sourceTiles,3);assert.equal(stream.stats.residency!.resident,1);assert.equal(attached,1);
  assert(stream.meshes.filter(m=>m.getTotalVertices()>0).every(m=>m.isEnabled()));
  await stream.request({x:20000,z:20000,overview:false});assert.equal(stream.stats.residency!.resident,0);assert.equal(detached,1);assert.equal(disposed,1);
  stream.dispose();assert.equal(detached,1);assert.equal(f.scene.meshes.length,0);assert.equal(f.scene.transformNodes.length,0);
 }finally{f.close();}
});
test('disposing during actual per-pack metadata transfer cancels it before decode or world attach',async()=>{
 const f=setup();let started!:()=>void,aborted=false,decodes=0,attachments=0;
 const began=new Promise<void>(resolve=>started=resolve);
 try{
  globalThis.fetch=async(url,options)=>{
   if(String(url).includes('/metadata/'))return new Promise<Response>((_resolve,reject)=>{
    options!.signal!.addEventListener('abort',()=>{aborted=true;reject(options!.signal!.reason);},{once:true});started();
   });
   return f.fixture.fetcher(url,options);
  };
  CityStreamGlbLoader.prototype.load=async()=>{decodes++;throw Error('must not decode after metadata cancellation');};
  const stream=new CityBaseStream(f.scene,f.sources,{attach:()=>()=>{},attachPack:()=>{attachments++;return ()=>{};}});
  const initializing=stream.init({x:0,z:0,overview:false});await began;stream.dispose();await initializing;
  assert.equal(aborted,true);assert.equal(decodes,0);assert.equal(attachments,0);assert.equal(stream.stats.ready,false);assert.equal(stream.meshes.length,0);
 }finally{f.close();}
});
test('actual init replaces the parent with child sources before planning, masking and world attach',async()=>{
 const f=setup();let attached=0,detached=0;
 try{
  const parent=f.fixture.tiles[2],children=['a','b'].map((name,i)=>({...parent,id:parent.id+'/'+name,parentSourceId:parent.id,file:'groups/'+name+'/group.glb',bytes:70,sha256:String(i+8).repeat(64),logicalBytes:100,triangles:10,bounds:{min:[i*320,0,0],max:[(i+1)*320,10,640]}}));
  f.fixture.root.sourcePartitions=[f.fixture.put('partitions/buildings-0-0.json',{schemaVersion:1,kind:'city-base-source-partition',parent:{id:parent.id,sha256:parent.sha256},children,geometryCoverage:{file:'coverage.json',bytes:50,sha256:'c'.repeat(64)}})];
  f.fixture.raw.members=f.fixture.raw.members.slice(0,2).concat(children.map(t=>({id:t.id,quality:'near',referenceSha256:t.sha256})));
  f.fixture.meta.members=f.fixture.raw.members.map((m:any)=>({...m,role:m.id.split(':')[0],sourceSha256:m.referenceSha256}));
  f.fixture.meta.nodes=f.fixture.meta.nodes.slice(0,2).concat(children.map(t=>({name:'block_0_0_plaster__'+t.id.at(-1),member:t.id,role:'buildings',quality:'near'})));
  f.fixture.root.totals.nearMembers=4;f.fixture.root.totals.representations=4;f.sources.packs=f.fixture.seal();
  CityStreamGlbLoader.prototype.load=async function(pack:any,signal:AbortSignal){
   signal.throwIfAborted();const container=new AssetContainer(f.scene),root=new Mesh('__root__',f.scene);root.setEnabled(false);container.meshes.push(root);
   for(const binding of f.fixture.meta.nodes){const mesh=new Mesh(binding.name,f.scene),data=new VertexData();data.positions=[0,0,0,1,0,0,0,1,0];data.indices=[0,1,2];data.applyToMesh(mesh);mesh.parent=root;container.meshes.push(mesh);}
   const detach=(this as any).hooks.attach(pack,container,[{}]);let disposed=false;
   return {container,setVisible:(v:boolean)=>root.setEnabled(v),dispose:()=>{if(disposed)return;disposed=true;detach();container.dispose();}};
  };
  const stream=new CityBaseStream(f.scene,f.sources,{attach:()=>{throw Error('original source decoder must not be used');},attachPack:(pack,container)=>{attached++;assert.equal(container.transformNodes.length,4);assert.equal(pack.members.filter(m=>m.parentSourceId===parent.id).length,2);return ()=>detached++;}});
  await stream.init({x:0,z:0,overview:false});assert.equal(stream.stats.ready,true);assert.equal(stream.stats.sourceTiles,4);assert.equal(attached,1);assert.equal(stream.meshes.filter(m=>m.getTotalVertices()>0&&m.isEnabled()).length,4);
  stream.dispose();assert.equal(detached,1);assert.equal(f.scene.meshes.length,0);assert.equal(f.scene.transformNodes.length,0);
 }finally{f.close();}
});
