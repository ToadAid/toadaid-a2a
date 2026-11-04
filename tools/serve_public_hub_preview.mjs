// A2A-P0C-DOOR-A1: test-only static preview on an explicitly assigned loopback port.
import {mkdtempSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawn,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'..');
const output=path.join(mkdtempSync(path.join(tmpdir(),'toadaid-agent-preview-')),'release');
const built=spawnSync('python3',['-m','agent_web.public_hub','build','--output',output,'--release-id',`agent-preview-${process.pid}`],{cwd:root,stdio:'inherit'});
if(built.status!==0)process.exit(built.status??1);
const sha=createHash('sha256').update(readFileSync(path.join(output,'release-manifest.json'))).digest('hex');
const child=spawn('python3',['-I',path.join(output,'runtime/public_hub.py'),'serve','--release',output,'--manifest-sha256',sha,'--port',process.env.AGENT_HUB_TEST_PORT??'4389','--preview'],{cwd:root,stdio:'inherit',env:{PATH:'/usr/bin:/bin'}});
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>process.exit(code??1));
