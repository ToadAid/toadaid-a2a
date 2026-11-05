import {test,expect,type Page} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';


type FirstControls = {theme:string|null;navigationColor:string;inputColor:string|null};
async function observeFirstControls(page:Page) {
 // Observe the first committed controls, not only the later settled theme.
 await page.addInitScript(() => {
  const target=window as typeof window & {__firstObservatoryRender?:FirstControls};
  const observer=new MutationObserver(() => {
   const tab=document.querySelector<HTMLElement>('[role="tab"]');
   if(!tab||target.__firstObservatoryRender)return;
   const input=document.querySelector<HTMLInputElement>('input[placeholder^="Search event"]');
   target.__firstObservatoryRender={theme:document.documentElement.getAttribute('data-theme'),navigationColor:getComputedStyle(tab).color,inputColor:input?getComputedStyle(input).color:null};
   observer.disconnect();
  });
  observer.observe(document,{childList:true,subtree:true});
 });
}

test('three public resources, headers, assets and reserved paths are truthful',async({request})=>{
 for(const [url,type] of [['/','text/html'],['/dashboard/?view=activity','text/html'],['/pond/guide.md','text/markdown']]){
  const response=await request.get(url);expect(response.status()).toBe(200);expect(response.headers()['content-type']).toContain(type);
  expect(response.headers()['x-content-type-options']).toBe('nosniff');expect(response.headers()['referrer-policy']).toBe('no-referrer');
  expect(response.headers()['content-security-policy']).toContain("connect-src 'none'");expect(response.headers()['set-cookie']).toBeUndefined();expect(response.headers()['access-control-allow-origin']).toBeUndefined();
 }
 const guide=await request.get('/pond/guide.md');expect(await guide.text()).toContain('# Welcome to ToadAid Agent Pond');expect(await guide.text()).not.toContain('<!doctype');
 for(const url of ['/missing/deep/','/dashboard/no-such-view/','/.well-known/agent-card.json','/pond/apply','/api/agents','/dashboard/assets/absent.js','/.env','/release-manifest.json'])expect((await request.get(url)).status(),url).toBe(404);
 for(const url of ['/pond/apply','/dashboard/','/api/messages'])expect((await request.post(url,{data:{role:'admin'}})).status()).toBe(405);
});

test('home is responsive, keyboard accessible and links to the complete journey',async({page},info)=>{
 const unexpected:string[]=[];page.on('request',request=>{if(new URL(request.url()).origin!==new URL(info.project.use.baseURL as string??'http://127.0.0.1:4389').origin)unexpected.push(request.url());});
 await page.goto('/');await expect(page.getByRole('heading',{level:1})).toContainText('Human sovereignty.');
 await expect(page.getByRole('img',{name:/Authentic Blue Toby/})).toBeVisible();
 const grove=page.getByRole('img',{name:/Living Grove landscape/});await expect(grove).toBeVisible();
 expect(await grove.evaluate((img:HTMLImageElement)=>img.complete&&img.naturalWidth>0)).toBe(true);
 expect(await page.locator('.hero .toby').count()).toBe(0);
 await expect(page.locator('.brand').first().getByRole('img',{name:/Authentic Blue Toby/})).toBeVisible();
 const hero=page.getByRole('region',{name:/One pond/});
 await expect(hero.getByRole('link',{name:/Visit ToadAid Portal/})).toHaveAttribute('href','https://portal.toadaid.org/');
 await expect(hero.getByRole('link',{name:/Explore A2A architecture/})).toHaveAttribute('href','https://portal.toadaid.org/a2a/');
 await expect(page.getByRole('link',{name:/Explore Observatory/}).first()).toHaveAttribute('href','/dashboard/');
 await expect(page.getByRole('link',{name:/Read participation guide/})).toHaveAttribute('href','/pond/guide.md');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
 if((info.project.use.viewport?.width??1440)<=720){await page.getByText('Explore the pond',{exact:true}).click();await expect(page.getByRole('navigation',{name:'Mobile'})).toBeVisible();await page.screenshot({path:`/tmp/observatory-contrast-home-menu-${info.project.name}.png`,fullPage:false});}
 const axe=await new AxeBuilder({page}).analyze();expect(axe.violations.filter(v=>['serious','critical'].includes(v.impact??''))).toEqual([]);
 await page.screenshot({path:`/tmp/observatory-contrast-home-${info.project.name}.png`,fullPage:true});expect(unexpected).toEqual([]);
});

test('all five synthetic views survive direct links, refresh, history and return navigation',async({page},info)=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 for(const [view,label] of [['overview','Observatory Overview'],['directory','Directory Preview'],['activity','Agent Activity'],['communication','Communication Vis'],['security','Security & Governance']]){
  await page.goto(`/dashboard/?view=${view}`);await expect(page.getByText('SYNTHETIC PREVIEW — NO LIVE AGENTS',{exact:true})).toBeVisible();
  await expect(page.locator(`[id="panel-${view}"]`)).toBeVisible();await page.reload();await expect(page.locator(`[id="panel-${view}"]`)).toBeVisible();
  if(view==='security'){await expect(page.getByText('A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY',{exact:true})).toBeVisible();}
 }
 await page.goto('/dashboard/');
 const desktop=(info.project.use.viewport?.width??1440)>=768;
 if(!desktop)await page.getByRole('button',{name:'Open all 5 views menu'}).click();
 await page.getByRole(desktop?'tab':'menuitem',{name:/Agent Activity/}).click();await expect(page).toHaveURL(/\/dashboard\/\?view=activity$/);await page.reload();await expect(page.locator('#panel-activity')).toBeVisible();
 await page.getByRole('navigation',{name:'Agent Pond destinations'}).getByRole('link',{name:/Agent Pond/}).click();await expect(page.getByRole('heading',{level:1})).toContainText('One pond.');
 await page.goto('/dashboard/?view=security');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const axe=await new AxeBuilder({page}).analyze();expect(axe.violations.filter(v=>['serious','critical'].includes(v.impact??''))).toEqual([]);
 await page.screenshot({path:`/tmp/observatory-contrast-observatory-${info.project.name}.png`,fullPage:true});
 if(!desktop){await page.getByRole('button',{name:'Open all 5 views menu'}).click();await page.screenshot({path:`/tmp/observatory-contrast-observatory-menu-${info.project.name}.png`,fullPage:false});}
 expect(errors).toEqual([]);
});

test('every synthetic view remains accessible in both supported themes',async({page})=>{
 test.setTimeout(60000);
 await observeFirstControls(page);
 const findings:unknown[]=[];
 for(const theme of ['light','dark'])for(const view of ['overview','directory','activity','communication','security']){
  await page.goto(`/dashboard/?theme=${theme}&view=${view}`);
  await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  const first=await page.evaluate(() => (window as typeof window & {__firstObservatoryRender?:FirstControls}).__firstObservatoryRender);
  expect(first,'The requested theme must precede the first committed controls').toEqual(expect.objectContaining({theme}));
  const axe=await new AxeBuilder({page}).analyze();
  findings.push(...axe.violations.filter(v=>['serious','critical'].includes(v.impact??'')).map(v=>({theme,view,id:v.id,nodes:v.nodes.map(n=>({html:n.html,failure:n.failureSummary}))})));
 }
 expect(findings).toEqual([]);
});

test('first Activity controls receive the requested dark theme before rendering',async({page})=>{
 await observeFirstControls(page);
 await page.addInitScript(() => localStorage.setItem('toadaid_theme','light'));
 await page.goto('/dashboard/?theme=dark&view=activity');
 await expect(page.locator('#panel-activity')).toBeVisible();
 const first=await page.evaluate(() => (window as typeof window & {__firstObservatoryRender?:FirstControls}).__firstObservatoryRender);
 expect(first,'Theme must precede the first controls even when saved preference conflicts').toEqual(expect.objectContaining({theme:'dark'}));
 expect(first?.navigationColor).not.toBe('rgb(0, 0, 0)');
 expect(first?.inputColor).not.toBeNull();expect(first?.inputColor).not.toBe('rgb(0, 0, 0)');
 await test.info().attach('first-themed-controls',{body:JSON.stringify(first),contentType:'application/json'});
});
