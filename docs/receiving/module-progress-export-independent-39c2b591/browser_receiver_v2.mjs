import fs from "node:fs";
import path from "node:path";
import {spawn} from "node:child_process";
import {pathToFileURL} from "node:url";
import {createHash} from "node:crypto";
import assert from "node:assert/strict";

const config = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = config.out;
fs.mkdirSync(out);
const sha = value => createHash("sha256").update(value).digest("hex");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label, timeout=15000) {
  const start=Date.now();
  while(Date.now()-start<timeout) { const value=await fn(); if(value) return value; await delay(75); }
  throw new Error("Timed out: "+label);
}
class CDP {
  constructor(ws) {
    this.ws=ws; this.next=1; this.pending=new Map(); this.events=[];
    ws.addEventListener("message", event=>{
      const data=JSON.parse(String(event.data));
      if(data.id) { const p=this.pending.get(data.id); if(!p)return; this.pending.delete(data.id);
        data.error?p.reject(new Error(JSON.stringify(data.error))):p.resolve(data.result); }
      else this.events.push(data);
    });
  }
  call(method,params={},sessionId) {
    const id=this.next++;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error("CDP timeout: "+method));},20000);
      this.pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});
      this.ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
    });
  }
}
let chrome, cdp, session;
const receipt={qualification:"Independent actual browser consumption of native saved module report",
  config,nodeVersion:process.version,checks:[],started:new Date().toISOString(),sourceExecuted:false};
function check(name, value) { assert.ok(value,name); receipt.checks.push({name,pass:true}); }
async function evaluate(expression) {
  const result=await cdp.call("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true},session);
  if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function inspectPage(label, htmlPath, expectedPath, viewport) {
  const expected=JSON.parse(fs.readFileSync(expectedPath,"utf8"));
  await cdp.call("Emulation.setDeviceMetricsOverride",{...viewport,deviceScaleFactor:1,mobile:false},session);
  const response=await cdp.call("Page.navigate",{url:pathToFileURL(htmlPath).href},session);
  assert.ok(!response.errorText,response.errorText);
  await until(()=>evaluate("document.readyState === 'complete'"),label+" document");
  const state=await evaluate(`(()=>{
    const links=[...document.querySelectorAll("a[download]")].map(a=>({text:a.textContent,href:a.href,download:a.download}));
    const inlineHandlers=[...document.querySelectorAll("*")].flatMap(n=>[...n.attributes].filter(a=>a.name.toLowerCase().startsWith("on")).map(a=>({tag:n.tagName,attribute:a.name})));
    const externalResources=[...document.querySelectorAll("[src],link[rel=stylesheet]")].map(n=>({tag:n.tagName,url:n.getAttribute("src")||n.getAttribute("href")}));
    const headings=[...document.querySelectorAll("h1,h2,h3,h4")].map(n=>({tag:n.tagName,text:n.textContent}));
    const facts=dl=>Object.fromEntries([...dl.querySelectorAll(":scope > dd[data-field]")].map(dd=>[dd.dataset.field,JSON.parse(dd.textContent)]));
    const reportFacts=[...document.querySelectorAll('section[aria-labelledby="overview-title"] > dl.facts')].map(facts);
    const visibleModules=[...document.querySelectorAll("section.module")].map(module=>({
      id:module.id,title:module.querySelector(":scope > h2").textContent,
      badge:module.querySelector(":scope > .badge").textContent,
      facts:[...module.querySelectorAll(":scope > dl.facts")].map(facts),
      diagnostics:[...module.querySelectorAll(":scope > ul > li")].map(li=>li.textContent),
      items:[...module.querySelectorAll(":scope > ol.items > li.item")].map(item=>({id:item.id,
        title:item.querySelector(":scope > h3").textContent,values:facts(item.querySelector(":scope > dl.facts"))}))
    }));
    const navigation=[...document.querySelectorAll('nav[aria-label="Modules in returned order"] a')].map(a=>({text:a.textContent,href:a.getAttribute("href")}));
    const displayedJsonSha256=document.querySelector("#json-sha256")?.textContent;
    return {title:document.title,text:document.body.innerText,headings,links,inlineHandlers,externalResources,
      reportFacts,visibleModules,navigation,displayedJsonSha256,
      scripts:document.scripts.length,forms:document.forms.length,iframes:document.querySelectorAll("iframe").length,
      images:document.images.length,width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
      contentHeight:document.documentElement.scrollHeight,
      inventedScriptValue:globalThis.notAllowed ?? null};
  })()`);
  fs.writeFileSync(path.join(out,label+"-dom.json"),JSON.stringify(state,null,2)+"\n");
  check(label+": no script/form/iframe/event-handler/external-resource execution surface",
    state.scripts===0 && state.forms===0 && state.iframes===0 && state.inlineHandlers.length===0 &&
    state.externalResources.length===0 && state.inventedScriptValue===null);
  check(label+": no horizontal document overflow",state.scrollWidth<=state.width);
  let previous=-1;
  for(const module of expected.modules) {
    const index=state.text.indexOf(module.name);
    assert.ok(index>previous,label+": original module order and complete literal name");previous=index;
    for(const item of module.items)assert.ok(state.text.includes(item.title),label+": complete literal item title "+item.id);
  }
  check(label+": all literal module/item names in returned order",true);
  const {modules,module_state_counts,...scope}=expected;
  assert.deepEqual(state.reportFacts,[scope,module_state_counts]);
  assert.deepEqual(state.navigation,modules.map((m,i)=>({text:m.name,href:"#module-"+i})));
  assert.equal(state.visibleModules.length,modules.length);
  for(let i=0;i<modules.length;i++) {
    const {items,item_coverage,requirement_counts,remaining_work,diagnostics,...core}=modules[i];
    const actual=state.visibleModules[i];
    assert.equal(actual.id,"module-"+i);
    assert.equal(actual.title,modules[i].name);
    assert.equal(actual.badge,"Reported module state: "+modules[i].state);
    assert.deepEqual(actual.facts,[core,item_coverage,requirement_counts,remaining_work]);
    assert.deepEqual(actual.diagnostics,diagnostics);
    assert.deepEqual(actual.items,items.map((item,j)=>({id:"module-"+i+"-item-"+j,title:item.title,values:item})));
  }
  check(label+": every visible scope/module/item fact, diagnostic and navigation association equals the original observation",true);
  const jsonLinks=state.links.filter(a=>a.href.startsWith("data:application/json")&&a.href.includes(";base64,"));
  assert.equal(jsonLinks.length,1,label+": exact one normalized JSON download");
  const encodedBytes=Buffer.from(jsonLinks[0].href.split(";base64,")[1],"base64");
  assert.deepEqual(JSON.parse(encodedBytes.toString("utf8")),expected,label+": complete normalized observation embedded");
  assert.equal(state.displayedJsonSha256,sha(encodedBytes));
  fs.writeFileSync(path.join(out,label+"-embedded.json"),encodedBytes);
  check(label+": exact normalized observation embedded",true);
  const screenshot=await cdp.call("Page.captureScreenshot",{format:"png",captureBeyondViewport:true,
    clip:{x:0,y:0,width:viewport.width,height:Math.min(state.contentHeight,12000),scale:1}},session);
  fs.writeFileSync(path.join(out,label+".png"),Buffer.from(screenshot.data,"base64"));
  return {state,encodedBytes,jsonLink:jsonLinks[0],expected};
}
try {
  const stat=fs.statfsSync(out);
  const free=Number(stat.bavail)*Number(stat.bsize);
  receipt.capacityBeforeBrowser=free;
  assert.ok(free>=512*1024*1024,"512 MiB required for own disposable Chrome profile and evidence");
  const profile=path.join(out,"owned-chrome-profile");
  const downloads=path.join(out,"downloads");fs.mkdirSync(downloads);
  const stderr=fs.openSync(path.join(out,"chrome.stderr"),"w");
  const stdout=fs.openSync(path.join(out,"chrome.stdout"),"w");
  const flags=["--headless=new","--remote-debugging-port=0","--user-data-dir="+profile,
    "--no-first-run","--no-default-browser-check","--disable-background-networking",
    "--disable-component-update","--disable-sync","--disable-extensions","--mute-audio",
    "--metrics-recording-only","about:blank"];
  receipt.chromeCommand=[config.chrome,...flags];
  chrome=spawn(config.chrome,flags,{stdio:["ignore",stdout,stderr]});
  receipt.ownedChromePid=chrome.pid;
  fs.closeSync(stderr);fs.closeSync(stdout);
  const active=path.join(profile,"DevToolsActivePort");
  const lines=await until(()=>fs.existsSync(active)?fs.readFileSync(active,"utf8").trim().split("\n"):null,"owned Chrome debugger");
  const ws=new WebSocket("ws://127.0.0.1:"+lines[0]+lines[1]);
  await new Promise((resolve,reject)=>{ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true});});
  cdp=new CDP(ws);
  receipt.browser=await cdp.call("Browser.getVersion");
  const target=await cdp.call("Target.createTarget",{url:"about:blank"});
  ({sessionId:session}=await cdp.call("Target.attachToTarget",{targetId:target.targetId,flatten:true}));
  await cdp.call("Page.enable",{},session);
  await cdp.call("Runtime.enable",{},session);
  await cdp.call("Network.enable",{},session);
  await cdp.call("Network.emulateNetworkConditions",{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0},session);
  await cdp.call("Emulation.setScriptExecutionDisabled",{value:true},session);
  await cdp.call("Browser.setDownloadBehavior",{behavior:"allowAndName",downloadPath:downloads,eventsEnabled:true});
  receipt.sourceExecuted=true;
  const all=await inspectPage("all-desktop",config.all_html,config.expected_all,{width:1280,height:900});
  const before=cdp.events.length;
  const box=await evaluate(`(()=>{
    const link=[...document.querySelectorAll("a[download]")].find(a=>a.href.startsWith("data:application/json"));
    link.scrollIntoView({block:"center"});const r=link.getBoundingClientRect();
    return {x:r.x+r.width/2,y:r.y+r.height/2};
  })()`);
  await cdp.call("Input.dispatchMouseEvent",{type:"mouseMoved",...box},session);
  await cdp.call("Input.dispatchMouseEvent",{type:"mousePressed",...box,button:"left",clickCount:1},session);
  await cdp.call("Input.dispatchMouseEvent",{type:"mouseReleased",...box,button:"left",clickCount:1},session);
  const began=await until(()=>cdp.events.slice(before).find(e=>e.method==="Browser.downloadWillBegin"),"real JSON download");
  await until(()=>cdp.events.slice(before).find(e=>e.method==="Browser.downloadProgress"&&e.params.guid===began.params.guid&&e.params.state==="completed"),"download completed");
  const actualPath=path.join(downloads,began.params.guid);
  const actual=fs.readFileSync(actualPath);
  assert.deepEqual(actual,all.encodedBytes);
  assert.deepEqual(actual,fs.readFileSync(config.original_cli_stdout));
  assert.deepEqual(JSON.parse(actual.toString("utf8")),all.expected);
  fs.renameSync(actualPath,path.join(out,"actual-normalized-download.json"));
  receipt.download={guid:began.params.guid,suggestedFilename:began.params.suggestedFilename,
    bytes:actual.length,sha256:sha(actual),path:path.join(out,"actual-normalized-download.json")};
  check("Real pointer-initiated complete JSON download matches embedded bytes and original native observation",true);
  await inspectPage("all-phone",config.all_html,config.expected_all,{width:390,height:844});
  const focusBefore=await evaluate("({tag:document.activeElement.tagName,href:document.activeElement.getAttribute('href')})");
  for(let i=0;i<all.expected.modules.length;i++) {
    await cdp.call("Input.dispatchKeyEvent",{type:"keyDown",key:"Tab",code:"Tab",windowsVirtualKeyCode:9},session);
    await cdp.call("Input.dispatchKeyEvent",{type:"keyUp",key:"Tab",code:"Tab",windowsVirtualKeyCode:9},session);
  }
  const focusedHref=await evaluate("document.activeElement.getAttribute('href')");
  assert.equal(focusedHref,"#module-3");
  await cdp.call("Input.dispatchKeyEvent",{type:"keyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13},session);
  await cdp.call("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13},session);
  await until(()=>evaluate("location.hash === '#module-3'"),"ordinary keyboard local navigation");
  const navigationState=await evaluate("({hash:location.hash,top:document.querySelector('#module-3').getBoundingClientRect().top,scrollY,active:document.activeElement.tagName})");
  fs.writeFileSync(path.join(out,"phone-keyboard-navigation.json"),JSON.stringify({focusBefore,focusedHref,...navigationState,focus_seeded_by_receiver:false},null,2)+"\n");
  const phoneViewport=await cdp.call("Page.captureScreenshot",{format:"png"},session);
  fs.writeFileSync(path.join(out,"phone-unknown-module-viewport.png"),Buffer.from(phoneViewport.data,"base64"));
  check("Ordinary Tab/Enter reaches the exact fourth returned module at phone width",true);
  await inspectPage("selected-desktop",config.selected_html,config.expected_selected,{width:1280,height:900});
  await cdp.call("Emulation.setEmulatedMedia",{media:"print"},session);
  const printState=await evaluate("({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,text:document.body.innerText})");
  fs.writeFileSync(path.join(out,"selected-print-media.json"),JSON.stringify(printState,null,2)+"\n");
  check("Selected report remains readable without overflow in print media",printState.scrollWidth<=printState.width&&printState.text.includes(all.expected.modules[1].name));
  const attempts=cdp.events.filter(e=>e.method==="Network.requestWillBeSent"&&/^https?:/.test(e.params.request.url));
  check("Offline saved report attempted no HTTP resource request",attempts.length===0);
  receipt.pass=true;
} catch(error) {
  receipt.pass=false;receipt.error=String(error);receipt.stack=error.stack;
} finally {
  if(cdp) {
    fs.writeFileSync(path.join(out,"cdp-events.json"),JSON.stringify(cdp.events,null,2)+"\n");
    try {await cdp.call("Browser.close");} catch(error) {receipt.closeError=String(error);}
    cdp.ws.close();
  }
  if(chrome && chrome.exitCode===null) {
    await Promise.race([new Promise(resolve=>chrome.once("exit",resolve)),delay(2500)]);
    if(chrome.exitCode===null) {chrome.kill("SIGTERM");receipt.ownedChildTerminated=true;}
  }
  receipt.finished=new Date().toISOString();
  fs.writeFileSync(path.join(out,"RECEIPT.json"),JSON.stringify(receipt,null,2)+"\n");
  console.log(JSON.stringify({pass:receipt.pass,checks:receipt.checks.length,error:receipt.error,out},null,2));
}
process.exitCode=receipt.pass?0:1;
