// Optional production smoke test. Uses an isolated Chrome profile and software
// WebGL to avoid measuring or stressing the user's normal GPU/browser session.
import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('..',import.meta.url));
const output=new URL('../artifacts/validation/browser/',import.meta.url);
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const result={renderer:'software WebGL / isolated Chrome',performanceAcceptance:false,checks:[],errors:[]};
const page=await browser.newPage({viewport:{width:960,height:640}});
page.on('pageerror',error=>result.errors.push(error.message));
page.on('response',response=>{if(response.status()>=400)result.errors.push(response.status()+' '+response.url());});
try{
 await page.goto(process.env.GTA_HZ_URL??'http://127.0.0.1:5241/',{waitUntil:'domcontentloaded'});
 await page.getByRole('button',{name:'进入杭州'}).waitFor();
 assert.equal(await page.evaluate(()=>!!window.__SHENCHENGJI_CITY__),false);
 result.checks.push('manual welcome does not boot the game');
 await page.screenshot({path:new URL('welcome.png',output).pathname});
 await page.getByRole('button',{name:'进入杭州'}).click();
 await page.waitForFunction(()=>window.__SHENCHENGJI_CITY__?.ready,{},{timeout:90000});
 await page.waitForFunction(()=>!document.querySelector('#city-loading'),{},{timeout:30000});
 await page.locator('#game').click({position:{x:480,y:420}});
 result.checks.push('current production main city initialized');
 const before=await page.evaluate(()=>window.__SHENCHENGJI_CITY__.state);
 await page.keyboard.down('w');await page.waitForTimeout(1800);await page.keyboard.up('w');
 const after=await page.evaluate(()=>window.__SHENCHENGJI_CITY__.state);
 result.driving={before,after};
 assert.ok(after.distance>before.distance||Math.hypot(after.x-before.x,after.z-before.z)>.05);
 result.checks.push('real keyboard input changes car position');
 await page.keyboard.down('Space');
 await page.waitForFunction(()=>Math.abs(window.__SHENCHENGJI_CITY__.state.speed)<.5,{},{timeout:15000});
 await page.keyboard.up('Space');result.checks.push('keyboard braking stops the car before exit');
 await page.keyboard.press('m');await page.screenshot({path:new URL('map.png',output).pathname});await page.keyboard.press('m');
 await page.keyboard.press('f');
 await page.waitForFunction(()=>window.__SHENCHENGJI_CITY__?.stats.walking?.active,{},{timeout:20000});
 assert.equal(await page.evaluate(()=>window.__SHENCHENGJI_CITY__.stats.rider.loaded),true);
 result.checks.push('car exit loads public original rider and activates walking');
 await page.screenshot({path:new URL('walking.png',output).pathname});
 result.stats=await page.evaluate(()=>({rider:window.__SHENCHENGJI_CITY__.stats.rider,mode:window.__SHENCHENGJI_CITY__.stats.controlMode}));
 assert.deepEqual(result.errors,[],'no missing assets or uncaught browser errors');
 result.status='passed';
}catch(error){result.status='failed';result.failure=String(error);await page.screenshot({path:new URL('failure.png',output).pathname}).catch(()=>{});process.exitCode=1;}
finally{await fs.writeFile(new URL('result.json',output),JSON.stringify(result,null,2)+'\n');await browser.close();}
console.log(JSON.stringify(result));
