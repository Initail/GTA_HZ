import test from 'node:test';import assert from 'node:assert/strict';
import {CityTraffic} from '../src/traffic.ts';import {CAR_BODY,vehicleContact} from '../src/city-vehicle-contact.ts';
function make(){
 const graph={nodes:[[0,0],[0,100]],edges:[new Map([[1,100]]),new Map([[0,100]])]};
 const traffic=new CityTraffic(graph as any,[],null as any);
 const c={from:0,to:1,t:.2,speed:10,x:1.15,z:20,yaw:0,group:0,actualSpeed:10};traffic.cars=[c];
 return {traffic,c};
}
test('struck NPC visibly moves and dissipates impulse, then rejoins its original lane',()=>{
 const {traffic,c}=make();traffic.applyImpact(c,6,0);traffic.update(.05,0,20);
 assert.ok(c.x>1.4);assert.equal(c.t,.2,'impact must not simultaneously drive along its old route');
 for(let i=0;i<120;i++)traffic.update(.05,0,20);
 assert.ok(Math.abs(c.x-1.15)<.001);assert.ok(c.z>30);assert.equal(c.speed,10,'original cruise calibration is retained');
});
test('impulse substeps never push the NPC past a shore or structural obstruction',()=>{
 const {traffic,c}=make();traffic.contactBlocked=body=>body.x+body.halfWidth>=2.4;traffic.applyImpact(c,20,0);
 for(let i=0;i<30;i++){traffic.update(.05,0,20);assert.ok(c.x+CAR_BODY.halfWidth<2.4);}
});
test('NPC stops for the player car rather than running through it',()=>{
 const {traffic,c}=make();const player={x:1.15,z:26,yaw:0,groundY:0,...CAR_BODY};traffic.vehicleObstacle=()=>player;
 for(let i=0;i<30;i++)traffic.update(.05,0,20);
 assert.ok(!vehicleContact({...c,groundY:0,...CAR_BODY},player));assert.equal(c.actualSpeed,0);
});
test('NPC movement keeps bridge levels separate',()=>{
 const {traffic,c}=make();traffic.vehicleObstacle=()=>({x:1.15,z:26,yaw:0,groundY:8,...CAR_BODY});
 for(let i=0;i<30;i++)traffic.update(.05,0,20);assert.ok(c.z>30);
});
test('red-light stop and resume retain the original signal contract',()=>{
 const {traffic,c}=make();traffic.signalHold=()=>3;traffic.update(.05,0,20);assert.equal(c.z,20);
 traffic.signalHold=()=>null;traffic.update(.05,0,20);assert.ok(c.z>20);
});
test('contact cannot accumulate a hidden offset while blocked by the player',()=>{
 const {traffic,c}=make();const player={x:4,z:20,yaw:0,groundY:0,...CAR_BODY};traffic.vehicleObstacle=()=>player;
 traffic.applyImpact(c,20,0);for(let i=0;i<30;i++){traffic.update(.05,0,20);assert.ok(!vehicleContact({...c,groundY:0,...CAR_BODY},player));}
 traffic.vehicleObstacle=()=>null;const before=c.x;traffic.update(.05,0,20);assert.ok(Math.abs(c.x-before)<.2);
});

test('an immediately blocked lateral impact leaves no deferred sideways motion',()=>{
 const {traffic,c}=make();traffic.vehicleObstacle=()=>({x:4,z:20,yaw:0,groundY:0,...CAR_BODY});
 traffic.applyImpact(c,20,0);traffic.update(.05,0,20);assert.equal(c.x,1.15);
 traffic.vehicleObstacle=()=>null;traffic.update(.05,0,20);assert.equal(c.x,1.15);
});
