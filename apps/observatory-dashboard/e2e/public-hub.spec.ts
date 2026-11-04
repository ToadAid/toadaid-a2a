import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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
 await expect(page.getByRole('link',{name:/Explore Observatory/}).first()).toHaveAttribute('href','/dashboard/');
 await expect(page.getByRole('link',{name:/Read participation guide/})).toHaveAttribute('href','/pond/guide.md');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
 if((info.project.use.viewport?.width??1440)<=720){await page.getByText('Explore the pond',{exact:true}).click();await expect(page.getByRole('navigation',{name:'Mobile'})).toBeVisible();await page.screenshot({path:`/tmp/agent-door-home-menu-${info.project.name}.png`,fullPage:false});}
 const axe=await new AxeBuilder({page}).analyze();expect(axe.violations.filter(v=>['serious','critical'].includes(v.impact??''))).toEqual([]);
 await page.screenshot({path:`/tmp/agent-door-home-${info.project.name}.png`,fullPage:true});expect(unexpected).toEqual([]);
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
 await page.screenshot({path:`/tmp/agent-door-observatory-${info.project.name}.png`,fullPage:true});
 if(!desktop){await page.getByRole('button',{name:'Open all 5 views menu'}).click();await page.screenshot({path:`/tmp/agent-door-observatory-menu-${info.project.name}.png`,fullPage:false});}
 expect(errors).toEqual([]);
});

test('every synthetic view remains accessible in both supported themes',async({page})=>{
 test.setTimeout(60000);
 const findings:unknown[]=[];
 for(const theme of ['light','dark'])for(const view of ['overview','directory','activity','communication','security']){
  await page.goto(`/dashboard/?theme=${theme}&view=${view}`);
  await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  const axe=await new AxeBuilder({page}).analyze();
  findings.push(...axe.violations.filter(v=>['serious','critical'].includes(v.impact??'')).map(v=>({theme,view,id:v.id,nodes:v.nodes.map(n=>({html:n.html,failure:n.failureSummary}))})));
 }
 expect(findings).toEqual([]);
});
