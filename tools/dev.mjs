import {spawnSync,spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const build=spawnSync(process.execPath,['tools/build.mjs'],{cwd:root,stdio:'inherit'});
if(build.status!==0)process.exit(build.status??1);
// Serve only production output, never the source checkout or credentials.
const child=spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','5241','--strictPort',...process.argv.slice(2)],{cwd:root,stdio:'inherit'});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>process.exit(code??0));
