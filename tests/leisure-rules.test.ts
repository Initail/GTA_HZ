import test from 'node:test';
import assert from 'node:assert/strict';
import {LeisureBoat,LeisureFishing,readFishJournal,type LeisurePose} from '../src/city-leisure.ts';
const p:LeisurePose={x:0,z:0,yaw:0,height:0};
const dock={id:'test',land:{...p,x:-1.4,height:.4},berth:{...p}};
const keys=(...v:string[])=>new Set(v);
function boat(){return new LeisureBoat(dock,(x,z)=>Math.abs(x)<15&&Math.abs(z)<20);}
const atDock={...dock.land};
test('boarding checks real distance, height, land clearance and hull footprint',()=>{
 const b=boat();assert.equal(b.board({...atDock,x:100},()=>true),'away');assert.equal(b.board({...atDock,height:9},()=>true),'away');assert.equal(b.board(atDock,()=>false),'blocked');assert.equal(b.active,false);assert.equal(b.board(atDock,()=>true),'ok');
 const blocked=new LeisureBoat(dock,(x)=>x<.4);assert.equal(blocked.board(atDock,()=>true),'blocked');
});
test('normal paddling moves the boat, keeps its own distance, and limits speed',()=>{
 const b=new LeisureBoat(dock,()=>true);b.board(atDock,()=>true);for(let i=0;i<500;i++)b.step(keys('KeyW'),.05);assert.equal(b.speed,3.2);assert.ok(b.pose.z>40);assert.ok(b.distance>40);assert.equal(b.pose.x,0);
});
test('a long frame cannot teleport and inactive controls cannot move a parked boat',()=>{
 const b=boat();b.step(keys('KeyW'),1000);assert.equal(b.distance,0);b.board(atDock,()=>true);b.step(keys('KeyW'),1000);assert.ok(b.pose.z<.01);for(const dt of [NaN,Infinity,-1,0])b.step(keys('KeyW'),dt);assert.ok(Number.isFinite(b.pose.z));
});
test('hull stops before shore, then can reverse away',()=>{
 const b=new LeisureBoat(dock,(_,z)=>z<4);b.board(atDock,()=>true);for(let i=0;i<150;i++)b.step(keys('KeyW'),.05);assert.ok(b.blocked);assert.ok(b.pose.z+1.75<4);assert.equal(b.speed,0);const z=b.pose.z;for(let i=0;i<60;i++)b.step(keys('KeyS'),.05);assert.ok(b.pose.z<z);
});
test('a corner touching land rejects the move even with the centre on water',()=>{
 const b=new LeisureBoat(dock,(x,z)=>!(x>.6&&z>2.1));b.board(atDock,()=>true);for(let i=0;i<100;i++)b.step(keys('KeyW'),.05);assert.ok(b.blocked);assert.ok(b.pose.z<=.35);
});
test('braking and turning use boat rules without replacing original car handling',()=>{
 const b=boat();b.board(atDock,()=>true);for(let i=0;i<30;i++)b.step(keys('KeyW','KeyD'),.05);assert.ok(b.pose.x>0&&b.pose.yaw>0);for(let i=0;i<30;i++)b.step(keys('Space'),.05);assert.equal(b.speed,0);
});
test('disembark requires a still boat at its berth and a safe land target',()=>{
 const b=boat();b.board(atDock,()=>true);b.speed=1;assert.equal(b.disembark(()=>true),null);b.speed=0;b.pose.z=5;assert.equal(b.disembark(()=>true),null);b.pose.z=0;assert.equal(b.disembark(()=>false),null);assert.deepEqual(b.disembark(()=>true),atDock);assert.equal(b.active,false);
});
function fishing(){return new LeisureFishing(p,readFishJournal(null),()=>0);}
function tick(f:LeisureFishing,n:number,hold=false){for(let i=0;i<n;i++)f.tick(.05,hold,p,true);}
test('cast requires walking beside the correct spot and cannot restart an active cast',()=>{
 const f=fishing();assert.equal(f.cast({...p,x:3},true),false);assert.equal(f.cast(p,false),false);assert.equal(f.cast(p,true),true);assert.equal(f.cast(p,true),false);assert.equal(f.hook(),false);assert.equal(f.castId,1);
});
test('bite and missed window are driven by elapsed simulation time',()=>{
 const f=fishing();f.cast(p,true);tick(f,41);assert.equal(f.phase,'bite');tick(f,38);assert.equal(f.phase,'escaped');assert.equal(f.hook(),false);assert.equal(f.journal.released,0);assert.equal(f.cast(p,true),true);
});
test('holding too long breaks the line without a reward',()=>{
 const f=fishing();f.cast(p,true);tick(f,41);f.hook();tick(f,40,true);assert.equal(f.phase,'escaped');assert.equal(f.release(),null);assert.equal(f.journal.released,0);
});
test('balanced hold/release lands a fish; explicit release records it exactly once',()=>{
 const f=fishing();f.cast(p,true);tick(f,41);assert.equal(f.hook(),true);
 for(let i=0;i<350&&f.phase==='reeling';i++)f.tick(.05,f.tension<.6,p,true);
 assert.equal(f.phase,'landed');assert.equal(f.journal.released,0);assert.equal(f.release(),18);assert.equal(f.journal.released,1);assert.equal(f.journal.bestCm,18);assert.equal(f.release(),null);assert.equal(f.journal.released,1);
});
test('moving away, boarding, cancelling, or reloading cannot settle an unfinished cast',()=>{
 for(const action of ['away','boat','cancel']){const f=fishing();f.cast(p,true);tick(f,41);f.hook();if(action==='away')f.tick(.05,false,{...p,x:8},true);else if(action==='boat')f.tick(.05,false,p,false);else f.cancel();assert.equal(f.release(),null);assert.equal(f.phase,'idle');}
 const f=fishing();f.cast(p,true);const recovered=new LeisureFishing(p,readFishJournal(JSON.parse(JSON.stringify(f.journal))));assert.equal(recovered.phase,'idle');assert.equal(recovered.release(),null);
});
test('only a bounded versioned leisure journal survives reload; bad saves recover safely',()=>{
 assert.deepEqual(readFishJournal({version:1,released:3,bestCm:35}),{version:1,released:3,bestCm:35});
 for(const v of [null,{}, {version:2,released:3,bestCm:35},{version:1,released:Infinity,bestCm:20},{version:1,released:1.5,bestCm:20},{version:1,released:-1,bestCm:20},{version:1,released:1,bestCm:900}])assert.deepEqual(readFishJournal(v),{version:1,released:0,bestCm:0});
});
