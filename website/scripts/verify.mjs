import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const base=process.env.VW_URL || 'http://127.0.0.1:4201';
const {readFile}=await import('node:fs/promises');
const library=JSON.parse(await readFile(new URL('../app/data/variable-width-library.json',import.meta.url),'utf8'));
const b=await chromium.launch({channel:'chrome'});
const ctx=await b.newContext({permissions:['clipboard-read','clipboard-write']});
const p=await ctx.newPage(); const errors=[],bad=[],escaped=[];
p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)bad.push([r.status(),r.url()]);});p.on('request',r=>{if(r.url().startsWith(base)&&!new URL(r.url()).pathname.startsWith('/variable-width')&&!new URL(r.url()).pathname.startsWith('/cdn-cgi/'))escaped.push(r.url());});
for(const path of ['/variable-width','/variable-width/icons','/variable-width/docs']){
 const response=await p.goto(base+path);assert.equal(response.status(),200);await p.waitForTimeout(700);
 assert.equal(await p.locator('meta[name="robots"]').getAttribute('content'),'index, follow');
 assert.equal(await p.locator('link[rel="canonical"]').getAttribute('href'),'https://weihuasongguo.com'+path);
 const broken=await p.locator('img').evaluateAll(imgs=>imgs.filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.src));assert.deepEqual(broken,[]);
}
await p.goto(base+'/variable-width');
assert.equal(await p.locator('#figures [data-cursor="enlarge"]').count(),36);
const homeImages=await p.locator('img[src*="variable-width-library"]').evaluateAll(imgs=>imgs.map(i=>new URL(i.src).pathname.split('/').pop().replace('.svg','')));assert.ok(homeImages.every(name=>library.includes(name)));
await p.getByRole('button',{name:'Copy command',exact:true}).click();await p.getByRole('button',{name:'copied',exact:true}).waitFor();assert.match(await p.evaluate(()=>navigator.clipboard.readText()),/^npm install/);
await p.getByRole('link',{name:'Icons',exact:true}).click();await p.waitForURL('**/variable-width/icons');
await p.locator('[data-cursor="enlarge"]').first().click();await p.getByRole('button',{name:'Copy SVG',exact:true}).click();await p.getByRole('button',{name:'copied',exact:true}).waitFor();assert.match(await p.evaluate(()=>navigator.clipboard.readText()),/<svg/);await p.keyboard.press('Escape');
await p.getByRole('button',{name:'Switch to dark mode',exact:true}).click();assert.equal(await p.locator('html').getAttribute('data-mode'),'dark');
await p.getByRole('tab',{name:'中文',exact:true}).click();await p.getByRole('link',{name:'文档',exact:true}).click();await p.waitForURL('**/variable-width/docs');await p.getByRole('button',{name:'更新记录',exact:true}).click();await p.getByText('0.1.0 · 2026-10-13 · 首个公开实验版本',{exact:true}).waitFor();
await p.setViewportSize({width:390,height:844});assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));

assert.deepEqual(errors,[]);assert.deepEqual(bad,[]);assert.deepEqual(escaped,[]);
await p.goto(base+'/variable-width?ref=verification');assert.equal(await p.locator('link[rel="canonical"]').getAttribute('href'),'https://weihuasongguo.com/variable-width');
console.log('PASS: 3 routes, SEO, image loading, navigation, command/SVG copy, theme, language, changelog, mobile; no errors or root-level requests.');
await b.close();
