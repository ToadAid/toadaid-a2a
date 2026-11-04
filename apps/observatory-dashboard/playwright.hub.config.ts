import {defineConfig} from '@playwright/test';
const port=Number(process.env.AGENT_HUB_TEST_PORT??4389);
export default defineConfig({testDir:'./e2e',outputDir:process.env.AGENT_HUB_EVIDENCE??'/tmp/toadaid-agent-door-browser',workers:1,retries:0,reporter:'list',
 use:{baseURL:`http://127.0.0.1:${port}`,trace:'retain-on-failure',reducedMotion:'reduce'},
 webServer:{command:'node ../../tools/serve_public_hub_preview.mjs',url:`http://127.0.0.1:${port}`,reuseExistingServer:false,timeout:20000},
 projects:[{name:'mobile-320',use:{viewport:{width:320,height:740}}},{name:'mobile-390',use:{viewport:{width:390,height:844}}},{name:'tablet',use:{viewport:{width:768,height:1024}}},{name:'desktop',use:{viewport:{width:1440,height:1000}}}],
});
