import test from 'node:test';
import assert from 'node:assert/strict';
import {CITY_PROFILES} from '../src/city-profiles.generated.ts';
import {adaptCityStory,cityText} from '../src/city-narrative.ts';
import {CITY_STORY_CONTENT} from '../src/city-story-content.ts';
import {CareerGame,newCareerSave,type CareerPlaces} from '../src/city-career.ts';

const places:CareerPlaces={hub:[0,0],bay:[440,0],office:[280,50],park:[180,180],workshop:[280,100]};
test('Hangzhou story copy keeps every branch, reward, speaker and action',()=>{
 const source=structuredClone(CITY_STORY_CONTENT),hz=adaptCityStory(source,CITY_PROFILES.hangzhou);
 const logic=(content:typeof source)=>({schemaVersion:content.schemaVersion,id:content.id,firstStep:content.firstStep,reward:content.reward,
  steps:content.steps.map(s=>({id:s.id,place:s.place,action:s.action,next:s.next,terminal:s.terminal,speakers:s.lines.map(l=>l.speaker),choices:s.choices?.map(c=>({id:c.id,next:c.next}))}))});
 assert.deepEqual(logic(hz),logic(source));assert.deepEqual(source,CITY_STORY_CONTENT);
 assert.match(hz.steps[0].objective,/钱江生活驿站/);assert.match(hz.steps.find(s=>s.place==='park')!.objective,/世纪花园养护点/);
 assert.doesNotMatch(JSON.stringify(hz),/科苑|滨海|海湾/);
 assert.deepEqual(adaptCityStory(source,CITY_PROFILES.shenzhen),source);
});
test('city copy changes preserve all six contract mechanics and relationship costs',()=>{
 const sz=new CareerGame(places,newCareerSave(),CITY_PROFILES.shenzhen),hz=new CareerGame(places,newCareerSave(),CITY_PROFILES.hangzhou);
 const logic=(game:CareerGame)=>game.jobs.map(({title,description,pickupLine,arrivalLine,objectives,...job})=>({...job,objectives:objectives.map(({label,...o})=>o)}));
 assert.deepEqual(logic(hz),logic(sz));assert.equal(hz.jobs.length,6);assert.match(hz.jobs[0].description,/江边/);
 const save=newCareerSave();save.pendingChoice='alin-first';
 const a=new CareerGame(places,save,CITY_PROFILES.shenzhen).choice!,b=new CareerGame(places,save,CITY_PROFILES.hangzhou).choice!;
 assert.deepEqual(a.options.map(o=>[o.id,o.cost,o.relationship]),b.options.map(o=>[o.id,o.cost,o.relationship]));
 assert.match(b.line,/江边/);assert.equal(cityText('海边',CITY_PROFILES.shenzhen),'海边');
});
