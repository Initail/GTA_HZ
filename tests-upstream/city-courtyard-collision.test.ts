import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CityCollision} from '../src/driving.ts';
import type {CityData,V2} from '../src/city-types.ts';

const rectangle=(a:number,b:number,c:number,d:number):V2[]=>[[a,b],[c,b],[c,d],[a,d]];
function courtyard(){
 const data:CityData={meta:{counts:{},extent:[-100,-100,200,200],horizontalScale:.6},land:[[rectangle(-100,-100,200,200)]],coast:[],roads:[],water:[],green:[],landmarks:[],spawn:{x:0,z:0,yaw:0,road:''},buildings:[{rings:[rectangle(10,10,89.8,89.8),rectangle(30,30,70,70)],height:12,style:'office'}]};
 return {data,collision:new CityCollision(data)};
}
test('a mapped courtyard remains open while its surrounding wings block movement',()=>{
 const {collision}=courtyard();
 assert.equal(collision.blocked(50,50),false);
 assert.equal(collision.blocked(20,50),true);
 assert.equal(collision.blocked(70.5,50),true);
 assert.equal(collision.blocked(30.5,50),true,'inner wall clearance stays 1.15');
 assert.equal(collision.blocked(31.2,50),false);
});
test('building wall clearance extends into an adjacent collision grid cell',()=>{
 const {collision}=courtyard();
 assert.equal(collision.blocked(90.5,50),true);
 assert.equal(collision.blocked(91,50),false);
 assert.equal(collision.blocked(9.5,50),true,'unclosed final edge also blocks');
});
test('an independent building placed in a courtyard still blocks movement',()=>{
 const {data}=courtyard();
 data.buildings.push({rings:[rectangle(45,45,55,55)],height:6,style:'office'});
 const collision=new CityCollision(data);
 assert.equal(collision.blocked(50,50),true);
 assert.equal(collision.blocked(40,40),false);
});
test('road priority and islands within water retain upstream behavior',()=>{
 const {data}=courtyard();
 data.roads.push({id:'road',name:'入口路',kind:'service',width:6,oneway:false,grade:'0',points:[[0,50],[25,50]]});
 data.water.push({name:'水体',rings:[rectangle(95,20,140,80),rectangle(110,40,125,60)]});
 const collision=new CityCollision(data);
 assert.equal(collision.blocked(20,50),false);
 assert.equal(collision.blocked(100,50),true);
 assert.equal(collision.blocked(115,50),false);
});
