import test from 'node:test';
import assert from 'node:assert/strict';
import {roadAllows,roadDirections,type AccessRoad,type SourceAccessTags,type TravelMode,type AccessStatus,type SourcePointOrder} from '../src/road-access.ts';
const road=(sourceAccessTags:SourceAccessTags={},kind='service'):AccessRoad=>({kind,oneway:false,sourceAccessTags});
const modes:TravelMode[]=['motorcar','foot','bicycle','bus'];
const status=(tags:SourceAccessTags,mode:TravelMode)=>roadAllows(road(tags),mode).status;

test('legacy roads preserve gameplay while saying source evidence is missing',()=>{
 for(const mode of modes){const value=roadAllows({kind:'service',oneway:true},mode);assert.equal(value.allowed,true);assert.equal(value.evidence,'missing');assert.equal(value.basis,'legacy-gameplay-compatibility');}
});
test('bound roads with no access key report a gameplay default, not confirmed public access',()=>{
 const value=roadAllows(road({highway:'service',name:'园区内部道路'}),'motorcar');
 assert.equal(value.allowed,true);assert.equal(value.evidence,'default');assert.equal(value.sourceKey,undefined);assert.equal(value.basis,'game-highway-default');
});
test('names alone never fabricate a gate or private access',()=>{
 for(const name of ['菜鸟','阿里园区','灵隐寺入口'])assert.equal(status({highway:'service',name},'motorcar'),'allowed');
});
test('access=no plus foot=designated permits walking only',()=>{
 for(const mode of modes)assert.equal(status({access:'no',foot:'designated'},mode),mode==='foot'?'allowed':'denied');
});
test('more specific motorcar tags override generic motor_vehicle and access restrictions',()=>{
 assert.equal(status({access:'no',vehicle:'no',motor_vehicle:'no',motorcar:'yes'},'motorcar'),'allowed');
 assert.equal(status({access:'yes',vehicle:'yes',motor_vehicle:'yes',motorcar:'no'},'motorcar'),'denied');
});
test('motorcar=no alone does not ban bus, foot, or bicycle modes',()=>{
 for(const mode of modes)assert.equal(status({highway:'unclassified',motorcar:'no',name:'白堤'},mode),mode==='motorcar'?'denied':'allowed');
});
test('vehicle restriction applies to motorcar, bicycle and bus but not foot',()=>{
 for(const mode of modes)assert.equal(status({vehicle:'no'},mode),mode==='foot'?'allowed':'denied');
});
test('motor_vehicle restriction leaves bicycle and foot unaffected',()=>{
 for(const mode of modes)assert.equal(status({motor_vehicle:'no'},mode),mode==='motorcar'||mode==='bus'?'denied':'allowed');
});
test('bus and psv exceptions override motor_vehicle while motorcar does not override bus',()=>{
 assert.equal(status({motor_vehicle:'no',bus:'yes'},'bus'),'allowed');
 assert.equal(status({access:'no',psv:'yes'},'bus'),'allowed');
 assert.equal(status({access:'no',psv:'yes',bus:'no'},'bus'),'denied');
 assert.equal(status({motor_vehicle:'no',motorcar:'yes'},'bus'),'denied');
});
for(const value of ['no','private','permit'])test(`${value} denies unconditional public use`,()=>{
 for(const mode of modes){const result=roadAllows(road({access:value}),mode);assert.equal(result.status,'denied');assert.equal(result.allowed,false);assert.equal(result.sourceKey,'access');assert.equal(result.sourceValue,value);}
});
for(const value of ['destination','customers','customer','delivery','agricultural','forestry','dismount','use_sidepath'])test(`${value} remains restricted rather than unrestricted public access`,()=>{
 const result=roadAllows(road({access:value}),'motorcar');assert.equal(result.status,'restricted');assert.equal(result.allowed,false);assert.equal(result.sourceValue,value);
});
test('unrecognized access values remain unknown and retain the raw value',()=>{
 for(const value of ['unknown','something-new','yes;private']){const result=roadAllows(road({access:value}),'motorcar');assert.equal(result.status,'unknown');assert.equal(result.allowed,false);assert.equal(result.unhandled.access,value);}
});
for(const kind of ['construction','proposed'])test(`${kind} is nonoperational even with an explicit yes`,()=>{
 for(const mode of modes){assert.equal(roadAllows(road({highway:kind,access:'yes'},kind),mode).allowed,false);assert.equal(roadAllows({kind,oneway:false},mode).allowed,false);}
});
test('explicit mode access overrides highway defaults but never nonoperational status',()=>{
 assert.equal(roadAllows(road({highway:'footway'},'footway'),'motorcar').allowed,false);
 assert.equal(roadAllows(road({highway:'footway',motorcar:'yes'},'footway'),'motorcar').allowed,true);
 assert.equal(roadAllows(road({highway:'motorway'},'motorway'),'bicycle').allowed,false);
 assert.equal(roadAllows(road({highway:'motorway',bicycle:'yes'},'motorway'),'bicycle').allowed,true);
});
test('unknown road classification is not silently public',()=>{
 const result=roadAllows(road({highway:'future-highway'},'future-highway'),'motorcar');assert.equal(result.status,'unknown');assert.equal(result.allowed,false);
});
test('access conditional is retained and prevents unconditional public access',()=>{
 const result=roadAllows(road({access:'yes','access:conditional':'no @ (Mo-Fr 07:00-21:00)'}),'motorcar');
 assert.equal(result.status,'restricted');assert.equal(result.baseStatus,'allowed');assert.equal(result.allowed,false);assert.equal(result.unresolved['access:conditional'],'no @ (Mo-Fr 07:00-21:00)');
});
test('a conditional exception does not silently open a private road',()=>{
 const result=roadAllows(road({access:'private','access:conditional':'yes @ (21:00-07:00)'}),'motorcar');
 assert.equal(result.status,'denied');assert.equal(result.allowed,false);assert.equal(result.unresolved['access:conditional'],'yes @ (21:00-07:00)');
});
test('a specific unconditional foot rule shadows generic access conditional',()=>{
 const result=roadAllows(road({access:'no',foot:'designated','access:conditional':'yes @ (Sa-Su)'}),'foot');
 assert.equal(result.allowed,true);assert.deepEqual(result.unresolved,{});assert.equal(result.conditional['access:conditional'],'yes @ (Sa-Su)');
});
test('mode-specific conditional overrides no broad default without an evaluator',()=>{
 const result=roadAllows(road({access:'yes','bicycle:conditional':'no @ (Mo-Fr)'}),'bicycle');assert.equal(result.allowed,false);assert.equal(result.status,'restricted');
 assert.equal(roadAllows(road({access:'yes','bicycle:conditional':'no @ (Mo-Fr)'}),'foot').allowed,true);
});
test('non-access conditional tags are retained but do not close a road',()=>{
 const result=roadAllows(road({'maxspeed:conditional':'30 @ (wet)'}),'motorcar');assert.equal(result.allowed,true);assert.equal(result.conditional['maxspeed:conditional'],'30 @ (wet)');assert.deepEqual(result.unresolved,{});
});
test('direction-qualified access is not misreported as unconditionally public',()=>{
 const result=roadAllows(road({'motorcar:backward':'no'}),'motorcar');assert.equal(result.status,'restricted');assert.equal(result.unhandled['motorcar:backward'],'no');
});
test('empty more-specific values do not override a meaningful parent restriction',()=>{
 const result=roadAllows(road({access:'no',motorcar:'  '}),'motorcar');assert.equal(result.status,'denied');assert.equal(result.sourceKey,'access');
});

// Fixed-source negative controls; no network or whole-city fixture is needed.
const sourceCases:{id:string;tags:SourceAccessTags;checks:Partial<Record<TravelMode,AccessStatus>>}[]=[
 {id:'way/4326974 白堤',tags:{highway:'unclassified',motorcar:'no',cycleway:'yes',name:'白堤'},checks:{motorcar:'denied',bicycle:'allowed',foot:'allowed',bus:'allowed'}},
 {id:'way/159467531 烈士纪念馆路',tags:{highway:'service',access:'permit'},checks:{motorcar:'denied',foot:'denied'}},
 {id:'way/926280678',tags:{highway:'unclassified',motor_vehicle:'permit',bicycle:'yes',foot:'yes'},checks:{motorcar:'denied',bus:'denied',bicycle:'allowed',foot:'allowed'}},
 {id:'way/331789764',tags:{highway:'service',access:'destination'},checks:{motorcar:'restricted'}},
 {id:'way/588262375 西园路',tags:{highway:'secondary',bicycle:'no',foot:'no',oneway:'-1'},checks:{bicycle:'denied',foot:'denied',motorcar:'allowed'}},
 {id:'way/463092538',tags:{highway:'path',vehicle:'no',bicycle:'designated',foot:'designated'},checks:{motorcar:'denied',bicycle:'allowed',foot:'allowed'}},
 {id:'way/331177507 文晖路',tags:{highway:'secondary',motor_vehicle:'no',bus:'yes',oneway:'yes'},checks:{motorcar:'denied',bus:'allowed'}},
];
for(const sample of sourceCases)test(`fixed OSM tags: ${sample.id}`,()=>{for(const [mode,expected] of Object.entries(sample.checks))assert.equal(status(sample.tags,mode as TravelMode),expected);});

test('legacy directions defer to the caller instead of changing Shenzhen behavior',()=>{
 const result=roadDirections({kind:'service',oneway:true},'motorcar','osm-forward');assert.equal(result.status,'legacy');assert.equal(result.forward,null);assert.equal(result.backward,null);
});
const directionCases:{name:string;tags:SourceAccessTags;mode:TravelMode;order:SourcePointOrder;expected:[boolean,boolean]}[]=[
 {name:'raw forward oneway',tags:{oneway:'yes'},mode:'motorcar',order:'osm-forward',expected:[true,false]},
 {name:'raw reverse oneway before normalization',tags:{oneway:'-1'},mode:'motorcar',order:'osm-forward',expected:[false,true]},
 {name:'normalized oneway=-1 allows current forward',tags:{oneway:'-1'},mode:'motorcar',order:'osm-reversed',expected:[true,false]},
 {name:'normalized -1 with bicycle=no is bidirectional for bicycle',tags:{oneway:'-1','oneway:bicycle':'no'},mode:'bicycle',order:'osm-reversed',expected:[true,true]},
 {name:'normalized -1 with bicycle=-1 allows current forward',tags:{oneway:'-1','oneway:bicycle':'-1'},mode:'bicycle',order:'osm-reversed',expected:[true,false]},
 {name:'normalized -1 with bicycle=yes allows current backward',tags:{oneway:'-1','oneway:bicycle':'yes'},mode:'bicycle',order:'osm-reversed',expected:[false,true]},
 {name:'raw forward road with bicycle=-1 permits source reverse',tags:{oneway:'yes','oneway:bicycle':'-1'},mode:'bicycle',order:'osm-forward',expected:[false,true]},
 {name:'real way/373719035 bicycle contraflow',tags:{highway:'service',oneway:'yes','oneway:bicycle':'no'},mode:'bicycle',order:'osm-forward',expected:[true,true]},
 {name:'normal street oneway does not restrict walking',tags:{highway:'service',oneway:'-1'},mode:'foot',order:'osm-reversed',expected:[true,true]},
 {name:'explicit foot reverse is mapped to current point order',tags:{highway:'service','oneway:foot':'-1'},mode:'foot',order:'osm-reversed',expected:[true,false]},
 {name:'bus exception overrides generic direction',tags:{oneway:'yes','oneway:psv':'no'},mode:'bus',order:'osm-forward',expected:[true,true]},
 {name:'explicit no overrides motorway implication',tags:{highway:'motorway',oneway:'no'},mode:'motorcar',order:'osm-forward',expected:[true,true]},
 {name:'roundabout implies forward for vehicles',tags:{junction:'roundabout'},mode:'motorcar',order:'osm-forward',expected:[true,false]},
 {name:'specific bicycle no shadows generic direction conditional',tags:{oneway:'yes','oneway:bicycle':'no','oneway:conditional':'-1 @ (Mo-Fr)'},mode:'bicycle',order:'osm-forward',expected:[true,true]},
];
for(const sample of directionCases)test(`directions: ${sample.name}`,()=>{
 const result=roadDirections(road(sample.tags),sample.mode,sample.order);assert.equal(result.status,'known');assert.deepEqual([result.forward,result.backward],sample.expected);
});
test('uninterpreted conditional direction never silently grants a direction',()=>{
 const result=roadDirections(road({oneway:'yes','oneway:bicycle:conditional':'no @ (Sa-Su)'}),'bicycle','osm-forward');
 assert.equal(result.status,'restricted');assert.equal(result.forward,null);assert.equal(result.backward,null);assert.equal(result.unresolved['oneway:bicycle:conditional'],'no @ (Sa-Su)');
});
test('reversible and unknown direction values remain unresolved',()=>{
 for(const value of ['reversible','alternating','maybe']){const result=roadDirections(road({oneway:value}),'motorcar','osm-forward');assert.equal(result.status,'unknown');assert.equal(result.forward,null);assert.equal(result.unhandled.oneway,value);}
});
test('generic pedestrian path direction is marked ambiguous rather than guessed',()=>{
 const result=roadDirections(road({highway:'path',oneway:'yes'},'path'),'foot','osm-forward');assert.equal(result.status,'unknown');assert.equal(result.forward,null);
 const conditional=roadDirections(road({highway:'path','oneway:conditional':'yes @ (Sa-Su)'},'path'),'foot','osm-forward');assert.equal(conditional.status,'restricted');
});
test('conditional source object and raw tags are never mutated',()=>{
 const tags=Object.freeze({access:'yes','access:conditional':'no @ (Mo-Fr)',oneway:'-1','oneway:bicycle':'no'});const before=JSON.stringify(tags);
 roadAllows(road(tags),'motorcar');roadDirections(road(tags),'bicycle','osm-reversed');assert.equal(JSON.stringify(tags),before);
});

test('invalid runtime point order cannot silently mean reversed',()=>{
 assert.throws(()=>roadDirections(road({oneway:'-1'}),'motorcar','unknown' as SourcePointOrder),/point order must be explicit/);
});
