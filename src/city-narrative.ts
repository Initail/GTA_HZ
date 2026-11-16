import {CITY_CONFIG,type CityProfile} from './city-config.ts';
import type {CityStoryContent} from './city-story-contract.ts';

/** Translate display copy only. Identifiers, positions and gameplay numbers stay intact. */
export function cityText(text:string,city:CityProfile=CITY_CONFIG):string {
 for(const [from,to] of city.narrative.replacements)text=text.replaceAll(from,to);
 return text;
}

export function adaptCityStory(content:CityStoryContent,city:CityProfile=CITY_CONFIG):CityStoryContent {
 const t=(text:string)=>cityText(text,city);
 return {...content,title:t(content.title),synopsis:t(content.synopsis),
  people:Object.fromEntries(Object.entries(content.people).map(([id,p])=>[id,{name:t(p.name),role:t(p.role)}])) as CityStoryContent['people'],
  steps:content.steps.map(step=>({...step,title:t(step.title),objective:t(step.objective),
   lines:step.lines.map(line=>({...line,text:t(line.text)})),
   ...(step.choices?{choices:step.choices.map(choice=>({...choice,label:t(choice.label),consequence:t(choice.consequence)}))}:{})
  }))};
}
