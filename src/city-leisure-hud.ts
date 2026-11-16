import type {CityLeisureSession} from './city-leisure-session.ts';
import './city-leisure-hud.css';
export function createCityLeisureHud(parent:HTMLElement,session:()=>CityLeisureSession|null,focus:()=>void){
 const root=document.createElement('section');root.className='leisure-hud';root.hidden=true;root.setAttribute('aria-label','湖畔休闲');
 root.innerHTML='<small>湖畔休闲 · 游戏改编</small><strong></strong><p></p><div class="leisure-meters" hidden><label>收线 <progress data-progress max="1" value="0"></progress></label><label>张力 <progress data-tension max="1" value="0"></progress></label></div><div class="leisure-actions"><button data-interact>交谈 / 靠岸 <kbd>E</kbd></button><button data-fish>抛竿 / 收竿 <kbd>Q</kbd></button><button data-reel>提竿 / 按住收线</button></div><span></span>';
 parent.append(root);const title=root.querySelector('strong')!,copy=root.querySelector('p')!,summary=root.querySelector('span')!,meters=root.querySelector<HTMLElement>('.leisure-meters')!,progress=root.querySelector<HTMLProgressElement>('[data-progress]')!,tension=root.querySelector<HTMLProgressElement>('[data-tension]')!;
 const talk=root.querySelector<HTMLButtonElement>('[data-interact]')!,fish=root.querySelector<HTMLButtonElement>('[data-fish]')!,reel=root.querySelector<HTMLButtonElement>('[data-reel]')!;let held=false;
 talk.onclick=()=>{session()?.interact();focus();};fish.onclick=()=>{session()?.toggleFishing();focus();};
 reel.onpointerdown=e=>{held=true;reel.setPointerCapture(e.pointerId);session()?.hook();e.preventDefault();};reel.onpointerup=reel.onpointercancel=reel.onlostpointercapture=()=>{held=false;};window.addEventListener('blur',()=>{held=false;});
 return {get reeling(){return held;},update(hidden:boolean){const s=session(),prompt=s?.prompt();root.hidden=hidden||!s||!prompt;if(root.hidden){held=false;return;}const f=s!.fishing;
  title.textContent=s!.boat.active?'湖上划行':s!.fishingActive?'湖畔垂钓':'湖畔服务';copy.textContent=prompt!;summary.textContent=`休闲手账 · 已放流 ${f.journal.released} 尾 · 最长 ${f.journal.bestCm} cm`;
  meters.hidden=f.phase!=='reeling';progress.value=f.progress;tension.value=f.tension;tension.classList.toggle('tense',f.tension>.78);
  talk.textContent=f.phase==='landed'?'放流并记录 · E':s!.boat.active?'停稳靠岸 · E / F':'交谈 / 登船 · E';fish.hidden=s!.boat.active;reel.hidden=!['bite','reeling'].includes(f.phase);
 },dispose(){root.remove();}};
}
