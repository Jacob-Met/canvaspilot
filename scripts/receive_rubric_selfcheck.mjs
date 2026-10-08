// Independent native receiver transport. Adapted from the accepted RecallWeave
// tools/check_browser.mjs at d8a9ff81. Uses an isolated headless Chrome profile.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdir,mkdtemp,readFile,writeFile,rm,stat} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

export const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export async function until(check,label,milliseconds=12000){
  const end=Date.now()+milliseconds;let last;
  while(Date.now()<end){try{const value=await check();if(value)return value;}catch(error){last=error;}await pause(100);}
  throw new Error('Timed out: '+label+(last?' ('+last.message+')':''));
}
export async function openBrowser(output,executable='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'){
  output=resolve(output);await mkdir(output,{recursive:true});
  const profile=await mkdtemp(join(output,'profile-'));
  const downloads=join(output,'downloads');await mkdir(downloads,{recursive:true});
  const child=spawn(executable,['--headless=new','--disable-gpu','--disable-background-networking',
    '--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check',
    '--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
    {stdio:['ignore','ignore','pipe']});
  let log='',launchError,socket,sessionId,sequence=0;
  const pending=new Map(),events=[],errors=[],requests=[],downloadsStarted=[],downloadsCompleted=new Map();
  child.stderr.on('data',bytes=>{log=(log+bytes.toString()).slice(-12000);});
  child.on('error',error=>{launchError=error;});
  function command(method,params={},scoped=true){
    const id=++sequence;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},10000);
      pending.set(id,{resolve,reject,timer});
      socket.send(JSON.stringify({id,method,params,...(scoped&&sessionId?{sessionId}:{})}));
    });
  }
  async function evaluate(expression){
    const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);
    return r.result.value;
  }
  async function key(name){
    const codes={Enter:13,Tab:9,Home:36,End:35,ArrowRight:39,ArrowLeft:37};
    for(const type of ['keyDown','keyUp'])await command('Input.dispatchKeyEvent',{
      type,key:name,code:name,windowsVirtualKeyCode:codes[name]??0,nativeVirtualKeyCode:codes[name]??0,
      ...(name==='Enter'&&type==='keyDown'?{text:'\r',unmodifiedText:'\r'}:{})
    });
  }
  async function activate(selector){
    assert.ok(await evaluate('!!document.querySelector('+JSON.stringify(selector)+')'),'missing '+selector);
    await evaluate('document.querySelector('+JSON.stringify(selector)+').focus()');await key('Enter');
  }
  async function close(){
    if(socket?.readyState===1){try{await command('Browser.close',{},false);}catch{}socket.close();}
    for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('browser closed'));}pending.clear();
    if(child.exitCode===null){await Promise.race([new Promise(r=>child.once('exit',r)),pause(2000)]);}
    if(child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),pause(1000)]);}
    await writeFile(join(output,'browser-stderr.log'),log);
    if(child.exitCode!==null||child.signalCode!==null)await rm(profile,{recursive:true,force:true});
  }
  try{
    const [port,endpoint]=await until(async()=>{
      if(launchError)throw launchError;
      if(child.exitCode!==null)throw new Error('browser exited '+child.exitCode+': '+log);
      const fields=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).trim().split('\n');
      return fields[0]&&fields[1]?fields:false;
    },'Chrome startup',90000);
    socket=new WebSocket('ws://127.0.0.1:'+port+endpoint);
    socket.addEventListener('message',event=>{
      const m=JSON.parse(event.data);
      if(m.id){const p=pending.get(m.id);if(!p)return;pending.delete(m.id);clearTimeout(p.timer);
        if(m.error)p.reject(new Error(m.error.message));else p.resolve(m.result);return;}
      events.push(m);
      if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description??m.params.exceptionDetails.text);
      if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);
      if(m.method==='Browser.downloadWillBegin')downloadsStarted.push(m.params);
      if(m.method==='Browser.downloadProgress')downloadsCompleted.set(m.params.guid,m.params);
    });
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
    const version=await command('Browser.getVersion',{},false);
    const {targetId}=await command('Target.createTarget',{url:'about:blank'},false);
    ({sessionId}=await command('Target.attachToTarget',{targetId,flatten:true},false));
    await command('Page.enable');await command('Runtime.enable');await command('Network.enable');
    await command('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:downloads,eventsEnabled:true},false);
    await command('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
    return {version,command,evaluate,key,activate,close,errors,requests,events,
      async viewport(width,height=1000){await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});},
      async navigate(path,width=1280,height=1000){
        errors.length=0;requests.length=0;
        await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
        const url=pathToFileURL(resolve(path)).href;await command('Page.navigate',{url});
        await until(()=>evaluate('document.URL === '+JSON.stringify(url)+' && document.readyState === "complete"'),'report document load');
      },
      async screenshot(name){
        const {cssContentSize:s}=await command('Page.getLayoutMetrics');
        const {data}=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,
          clip:{x:0,y:0,width:s.width,height:Math.min(s.height,7000),scale:1}});
        const bytes=Buffer.from(data,'base64');const path=join(output,name);await writeFile(path,bytes);
        return {path,sha256:sha256(bytes),bytes:bytes.length};
      },
      async download(selector){
        const count=downloadsStarted.length;await activate(selector);
        const start=await until(()=>downloadsStarted[count],'download start');
        const completed=await until(()=>{const p=downloadsCompleted.get(start.guid);if(p?.state==='canceled')throw new Error('download canceled');return p?.state==='completed'?p:false;},'download completion');
        const path=join(downloads,start.guid);await until(async()=>{try{return(await stat(path)).isFile();}catch{return false;}},'download file');
        const bytes=await readFile(path);return {path,bytes,suggestedFilename:start.suggestedFilename,sha256:sha256(bytes),completed};
      }
    };
  }catch(error){await close();throw error;}
}


import {createServer} from 'node:http';
import {fileURLToPath} from 'node:url';
import {copyFile} from 'node:fs/promises';

const sourceRoot=resolve(fileURLToPath(new URL('..',import.meta.url)));
const output=resolve(process.argv[2]??'');
if(!process.argv[2])throw new Error('Usage: node scripts/receive_rubric_selfcheck.mjs NEW_OUTPUT [PYTHON] [CHROMIUM]');
const python=process.argv[3]??'python3', chrome=process.argv[4]??'/snap/bin/chromium';
await mkdir(output,{recursive:false});
const fixture=JSON.parse(await readFile(join(sourceRoot,'tests/fixtures/study_workspace_assignments.json'),'utf8'));
fixture['81'].rubric[1].id=fixture['81'].rubric[0].id;
fixture['81'].rubric[0].long_description+=' Literal markup <img src="https://outside.invalid/pixel" onerror="alert(1)"> and __DATA__.';
fixture['84']={id:84,name:'Missing rubric',description:'<p>Ask for the rubric when needed.</p>',rubric:null};
const requests=[];let base;
const server=createServer((req,res)=>{
 requests.push({method:req.method,url:req.url});
 const url=new URL(req.url,base), id=url.pathname.split('/').at(-1);
 if(req.method!=='GET'||!url.pathname.startsWith('/api/v1/courses/17/assignments/')||!fixture[id]||req.headers.authorization!=='Bearer selfcheck-fixture-token'){
  res.writeHead(400,{'Content-Type':'application/json'});res.end('{"error":"unexpected fixture request"}');return;
 }
 const row=structuredClone(fixture[id]);row.html_url=base+'/courses/17/assignments/'+id;
 const raw=JSON.stringify(row);res.writeHead(200,{'Content-Type':'application/json','Content-Length':Buffer.byteLength(raw)});res.end(raw);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));base='http://127.0.0.1:'+server.address().port;
async function processRun(command,args,options={}){
 return await new Promise((resolve,reject)=>{
  const child=spawn(command,args,{...options,stdio:['ignore','pipe','pipe']});let stdout='',stderr='';
  child.stdout.on('data',x=>stdout+=x);child.stderr.on('data',x=>stderr+=x);child.on('error',reject);
  const timer=setTimeout(()=>{child.kill('SIGTERM');reject(new Error('Native child timed out'));},90000);
  child.on('close',code=>{clearTimeout(timer);resolve({code,stdout,stderr});});
 });
}
let b;const groups=[],downloads=[],captures=[],allRequests=[],allErrors=[];
const result={schema:'canvaspilot.rubric-selfcheck-browser/1',started_at:new Date().toISOString(),groups,downloads,captures};
const record=(name,details={})=>{groups.push({name,...details});};
const parseEnvelope=bytes=>JSON.parse(bytes.toString().match(/<script id="selfcheck-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const encode=value=>JSON.stringify(value).replaceAll('&','\\u0026').replaceAll('<','\\u003c').replaceAll('>','\\u003e');
async function load(path,width=1360,height=980){
 if(b){allRequests.push(...b.requests);allErrors.push(...b.errors);}
 await b.navigate(path,width,height);
 await until(()=>b.evaluate('!document.querySelector("#save-copy").disabled || !document.querySelector("#error").hidden'),'source admission');
}
const text=()=>b.evaluate('document.body.innerText');
const statuses=()=>b.evaluate('Array.from(document.querySelectorAll("[data-role=status]"),x=>x.value)');
async function choose(selector,index){
 await b.evaluate('document.querySelector('+JSON.stringify(selector)+').focus()');
 for(const [key,code] of [['Home',36],...Array.from({length:index},()=>['ArrowDown',40])]){
  for(const type of ['rawKeyDown','keyUp'])await b.command('Input.dispatchKeyEvent',{type,key,code:key,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});
 }
 await b.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
 assert.equal(await b.evaluate('document.querySelector('+JSON.stringify(selector)+').selectedIndex'),index);
 await b.key('Tab');
}
async function note(selector,value){
 await b.evaluate('document.querySelector('+JSON.stringify(selector)+').focus()');
 await b.command('Input.insertText',{text:value});
 assert.equal(await b.evaluate('document.querySelector('+JSON.stringify(selector)+').value'),value);
}
async function altered(name,change){
 const e=structuredClone(original);change(e);
 const path=join(output,name+'.html');
 const alteredText=page.toString().replace(/(<script id="selfcheck-data" type="application\/json">)[\s\S]*?(<\/script>)/,(_,a,z)=>a+encode(e)+z);
 await writeFile(path,alteredText);return path;
}
let page,original;
try{
 const env={...process.env,PYTHONPATH:join(sourceRoot,'src'),PYTHONDONTWRITEBYTECODE:'1'};
 const initial=join(output,'selfcheck.html');
 const cli=await processRun(python,['-m','canvaspilot.cli','export-selfcheck','17','81','82','83','84','--base-url',base,'--token','selfcheck-fixture-token','--out',initial],{cwd:sourceRoot,env});
 await writeFile(join(output,'cli.json'),JSON.stringify({base,requests,...cli},null,2)+'\n');
 assert.equal(cli.code,0,cli.stderr);assert.equal(requests.length,4);assert.ok(requests.every(x=>x.method==='GET'));
 await new Promise(r=>server.close(r));
 page=await readFile(initial);original=parseEnvelope(page);
 record('actual CLI captures exactly four selected normalized briefs without writes',{requests:requests.length,html_sha256:sha256(page)});
 b=await openBrowser(join(output,'browser'),chrome);result.browser=b.version;
 await load(initial);assert.equal(await b.evaluate('document.querySelector("#workspace").hidden'),false);
 assert.deepEqual(await statuses(),['unreviewed','unreviewed','unreviewed']);
 const initialText=await text();assert.ok(initialText.includes('The supplied rubric is empty')&&initialText.includes('Rubric unavailable'));
 assert.equal(await b.evaluate('document.querySelectorAll("img").length'),0);
 assert.ok(!initialText.includes('876543.125')&&!initialText.includes('765432.125')&&!initialText.includes('987654.125'));
 record('initial unreviewed controls, empty/unavailable rubric and hidden point labels remain literal');
 const noteA='Evidence <script>window.__should_not_run=1</script> & __DATA__\nA concrete example 🌿';
 const noteB='Needs a clearer counterexample.\nKeep the limitation explicit.';
 await choose('#criterion-17-81-0-status',2);await note('#criterion-17-81-0-notes',noteA);
 await choose('#criterion-17-81-1-status',1);await note('#criterion-17-81-1-notes',noteB);
 assert.match(await b.evaluate('document.querySelector("#summary").textContent'),/1 checked locally · 1 need work · 1 unreviewed/);
 assert.equal(await b.evaluate('window.__should_not_run'),undefined);
 record('actual keyboard changes keep duplicate-ID criteria independent and notes literal');
 const first=await b.download('#save-copy');downloads.push({sha256:first.sha256,bytes:first.bytes.length,name:first.suggestedFilename,path:first.path});
 assert.equal(first.suggestedFilename,'rubric-selfcheck-working.html');
 const saved=parseEnvelope(first.bytes);assert.equal(saved.source,original.source);assert.equal(saved.source_sha256,original.source_sha256);
 assert.deepEqual(saved.state.criteria['17:81:0'],{status:'checked',notes:noteA});
 assert.deepEqual(saved.state.criteria['17:81:1'],{status:'needs-work',notes:noteB});
 const firstPath=join(output,'working-copy-1.html');await writeFile(firstPath,first.bytes);
 await load(firstPath);assert.deepEqual(await statuses(),['checked','needs-work','unreviewed']);
 assert.equal(await b.evaluate('document.querySelector("#criterion-17-81-0-notes").value'),noteA);
 record('first actual working-copy download reopens exact source, statuses and multiline Unicode notes',{sha256:first.sha256});
 await choose('#criterion-17-82-0-status',2);await note('#criterion-17-82-0-notes','A traced feedback cycle, with a delayed response.');
 const second=await b.download('#save-copy');downloads.push({sha256:second.sha256,bytes:second.bytes.length,name:second.suggestedFilename,path:second.path});
 const saved2=parseEnvelope(second.bytes);assert.equal(saved2.source,original.source);assert.deepEqual(saved2.state.criteria['17:81:0'],saved.state.criteria['17:81:0']);
 const secondPath=join(output,'working-copy-2.html');await writeFile(secondPath,second.bytes);
 await load(secondPath);assert.deepEqual(await statuses(),['checked','needs-work','checked']);
 assert.equal(sha256(await readFile(firstPath)),first.sha256);assert.equal(sha256(await readFile(initial)),sha256(page));
 record('second saved generation preserves earlier work and both input files');
 await b.evaluate('document.querySelectorAll("details").forEach(x=>x.open=true)');
 captures.push(await b.screenshot('desktop.png'));
 await b.viewport(390,844);
 assert.equal(await b.evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
 captures.push(await b.screenshot('phone.png'));
 record('desktop and390px reflow; criterion controls stay within viewport');
 await b.viewport(1360,980);await b.evaluate('document.querySelectorAll("details").forEach(x=>x.open=false)');
 await b.command('Emulation.setEmulatedMedia',{media:'print'});
 const pdf=await b.command('Page.printToPDF',{printBackground:true,preferCSSPageSize:true});
 const pdfPath=join(output,'selfcheck.pdf');await writeFile(pdfPath,Buffer.from(pdf.data,'base64'));
 const pdfText=await processRun('pdftotext',['-layout',pdfPath,'-']);
 await writeFile(join(output,'selfcheck-print.txt'),pdfText.stdout);
 assert.equal(pdfText.code,0);assert.ok(pdfText.stdout.includes('Clear connection')&&pdfText.stdout.includes('Concrete example'));
 assert.ok(pdfText.stdout.includes('Needs a clearer counterexample.')&&pdfText.stdout.includes('Checked locally'));
 assert.ok(!pdfText.stdout.includes('765432.125')&&!pdfText.stdout.includes('876543.125'));
 await b.command('Emulation.setEmulatedMedia',{media:''});
 record('actual PDF includes closed rating details, complete notes and local statuses without hidden point labels',{pdf_sha256:sha256(Buffer.from(pdf.data,'base64'))});
 await b.evaluate('window.__originalBlobURL=URL.createObjectURL;URL.createObjectURL=()=>{throw new Error("deliberate receiving refusal")};');
 const beforeFailed=await b.evaluate('document.querySelector("#criterion-17-81-0-notes").value');
 await b.activate('#save-copy');assert.match(await b.evaluate('document.querySelector("#status").textContent'),/not prepared.*deliberate receiving refusal/);
 assert.equal(await b.evaluate('document.querySelector("#criterion-17-81-0-notes").value'),beforeFailed);
 await b.evaluate('URL.createObjectURL=window.__originalBlobURL');
 record('controlled download preparation failure preserves current work');
 await b.evaluate('const n=document.querySelector("#criterion-17-81-0-notes");n.value="x".repeat(5001);n.dispatchEvent(new Event("input",{bubbles:true}));');
 await b.activate('#save-copy');assert.match(await b.evaluate('document.querySelector("#status").textContent'),/not prepared.*Invalid local/);
 assert.equal(await b.evaluate('document.querySelector("#criterion-17-81-0-notes").value.length'),5001);
 record('oversized controlled note refuses download without truncation');
 const badCases=[
  ['damaged-source',e=>{e.source+=' ';},'checksum'],
  ['foreign-key',e=>{e.state.criteria['17:999:0']={status:'checked',notes:''};},'belong'],
  ['bad-status',e=>{e.state.criteria['17:81:0'].status='graded';},'Invalid local'],
  ['wrong-binding',e=>{e.state.source_sha256='0'.repeat(64);},'belong'],
  ['bad-note',e=>{e.state.criteria['17:81:0'].notes=42;},'Invalid local'],
  ['oversized-state',e=>{e.state.criteria['17:81:0'].notes='x'.repeat(5001);},'Invalid local']
 ];
 for(const [name,change,errorText] of badCases){
  const path=await altered(name,change);const before=sha256(await readFile(path));await load(path);
  assert.equal(await b.evaluate('document.querySelector("#workspace").hidden'),true);
  assert.match(await b.evaluate('document.querySelector("#error").textContent'),new RegExp(errorText));
  assert.equal(sha256(await readFile(path)),before);
 }
 record('six malformed or foreign saved states refuse opening and preserve files',{cases:badCases.map(x=>x[0])});
 await load(secondPath);allRequests.push(...b.requests);allErrors.push(...b.errors);
 assert.ok(allRequests.every(url=>url.startsWith('file:')));assert.deepEqual(allErrors,[]);
 record('all received pages stay offline with zero runtime exceptions',{document_requests:allRequests.length});
 result.accepted=true;
}catch(error){
 result.accepted=false;result.failure={name:error.name,message:error.message,stack:error.stack};
 throw error;
}finally{
 if(server.listening)await new Promise(r=>server.close(r));
 if(b){allRequests.push(...b.requests);allErrors.push(...b.errors);await b.close();}
 result.finished_at=new Date().toISOString();result.requests=allRequests;result.runtime_errors=allErrors;
 await writeFile(join(output,'receipt.json'),JSON.stringify(result,null,2)+'\n');
}
