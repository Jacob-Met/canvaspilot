import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {spawn, execFileSync} from "node:child_process";

const root = "/home/jacob/canvaspilot-grade-review-export-926c3dc2605e";
const out = path.join(root, "docs/receiving/grade-review-export-926c3dc2605e");
const htmlPath = path.join(out, "synthetic-review.html");
const normalPath = path.join(out, "synthetic-normalized.json");
const profile = fs.mkdtempSync("/home/jacob/grade-export-browser-926c3dc2605e-");
const downloadPath = path.join(profile, "downloads");
fs.mkdirSync(downloadPath);
const log = fs.openSync(path.join(out, "chromium.log"), "w");
const sha = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const until = async (predicate, description) => {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) { if (await predicate()) return; await pause(80); }
  throw new Error("Timed out: " + description);
};
const receipt = {synthetic: true, started_at: new Date().toISOString(), browser_profile: profile,
  html_sha256: sha(fs.readFileSync(htmlPath)), normalized_sha256: sha(fs.readFileSync(normalPath)),
  requests: [], exceptions: [], checks: {}};
let ws, child, pending = new Map(), nextId = 0, sessionId;
const check = (name, condition, detail) => {
  receipt.checks[name] = {passed: Boolean(condition), detail};
  if (!condition) throw new Error("Receiving assertion: " + name);
};
try {
  child = spawn("/snap/bin/chromium", [
    "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--disable-background-networking", "--disable-component-update",
    "--disable-domain-reliability", "--disable-sync", "--no-pings",
    "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank"
  ], {stdio: ["ignore", log, log]});
  await until(() => fs.existsSync(path.join(profile, "DevToolsActivePort")), "isolated browser startup");
  const [port, endpoint] = fs.readFileSync(path.join(profile, "DevToolsActivePort"), "utf8").trim().split("\n");
  ws = new WebSocket("ws://127.0.0.1:" + port + endpoint);
  await new Promise((resolve, reject) => { ws.addEventListener("open", resolve, {once:true}); ws.addEventListener("error", reject, {once:true}); });
  ws.addEventListener("message", event => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const {resolve,reject,timer} = pending.get(msg.id); pending.delete(msg.id); clearTimeout(timer);
      if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
    } else if (msg.method === "Network.requestWillBeSent") {
      receipt.requests.push({url: msg.params.request.url, method: msg.params.request.method});
    } else if (msg.method === "Runtime.exceptionThrown") receipt.exceptions.push(msg.params.exceptionDetails);
  });
  const call = (method, params = {}, sid) => new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error("CDP timeout: "+method));}, 15000);
    pending.set(id,{resolve,reject,timer});
    ws.send(JSON.stringify({id,method,params,...(sid ? {sessionId:sid} : {})}));
  });
  receipt.browser = await call("Browser.getVersion");
  const target = await call("Target.createTarget", {url:"about:blank"});
  ({sessionId} = await call("Target.attachToTarget", {targetId:target.targetId,flatten:true}));
  const page = (method, params = {}) => call(method, params, sessionId);
  const evaluate = async expression => {
    const r = await page("Runtime.evaluate", {expression,returnByValue:true,awaitPromise:true});
    if (r.exceptionDetails) throw new Error("Inspection failed: "+JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  await page("Page.enable"); await page("Runtime.enable"); await page("Network.enable");
  await page("Page.bringToFront"); await page("Emulation.setFocusEmulationEnabled", {enabled:true});
  await page("Network.setBlockedURLs", {urls:["http://*","https://*","ws://*","wss://*"]});
  await call("Browser.setDownloadBehavior", {behavior:"allow",downloadPath,eventsEnabled:true});
  await page("Emulation.setDeviceMetricsOverride", {width:1100,height:900,deviceScaleFactor:1,mobile:false});
  await page("Page.navigate", {url:"file://"+htmlPath});
  await until(() => evaluate('document.readyState === "complete" && document.querySelectorAll("article.assignment").length === 4'), "complete local report");
  const desktop = await evaluate('({title:document.querySelector("h1").textContent,cards:document.querySelectorAll("article.assignment").length,scrollWidth:document.documentElement.scrollWidth,width:innerWidth,hasWarning:document.body.innerText.includes("does not match the current submission"),details:[...document.querySelectorAll("details")].map(d=>d.open),headings:[...document.querySelectorAll("h2")].map(x=>x.textContent)})');
  check("desktop_content",desktop.title==="Synthetic Linear Algebra" && desktop.cards===4 && desktop.hasWarning,desktop);
  check("desktop_width",desktop.scrollWidth<=desktop.width,desktop);
  check("details_initially_closed",desktop.details.length===4&&desktop.details.every(x=>!x),desktop.details);
  const saveScreen = async name => {
    const {data}=await page("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});
    fs.writeFileSync(path.join(out,name),Buffer.from(data,"base64"));
  };
  await saveScreen("desktop.png");
  await evaluate('document.querySelector("article.assignment").scrollIntoView({block:"start"})');
  await saveScreen("desktop-assignments.png");
  await evaluate("window.scrollTo(0,0)");
  let keyboard;
  for(let n=0;n<24;n++){
    await page("Input.dispatchKeyEvent",{type:"keyDown",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
    await page("Input.dispatchKeyEvent",{type:"keyUp",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
    keyboard=await evaluate('({tag:document.activeElement.tagName,text:document.activeElement.textContent})');
    if(keyboard.tag==="SUMMARY")break;
  }
  check("keyboard_reaches_details",keyboard.tag==="SUMMARY",keyboard);
  await page("Input.dispatchKeyEvent",{type:"rawKeyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  await page("Input.dispatchKeyEvent",{type:"char",key:"Enter",code:"Enter",text:"\r",unmodifiedText:"\r",windowsVirtualKeyCode:13});
  await page("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  await until(() => evaluate('document.activeElement.parentElement.open'), "keyboard disclosure open");
  const opened=await evaluate('document.activeElement.parentElement.open');
  check("keyboard_opens_details",opened,opened);
  await page("Input.dispatchKeyEvent",{type:"rawKeyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  await page("Input.dispatchKeyEvent",{type:"char",key:"Enter",code:"Enter",text:"\r",unmodifiedText:"\r",windowsVirtualKeyCode:13});
  await page("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  await until(() => evaluate('!document.activeElement.parentElement.open'), "keyboard disclosure closed");
  check("keyboard_closes_details",!(await evaluate('document.activeElement.parentElement.open')));
  await page("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate("window.scrollTo(0,0)");
  const mobile=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
  check("mobile_width",mobile.scrollWidth<=mobile.width,mobile);
  await saveScreen("mobile.png");
  await evaluate('document.querySelector("article.assignment").scrollIntoView({block:"start"})');
  await saveScreen("mobile-assignments.png");
  await page("Emulation.setDeviceMetricsOverride",{width:1100,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate('document.querySelector("#download-report").scrollIntoView({block:"center"})');
  const link=await evaluate('(()=>{const a=document.querySelector("#download-report"),r=a.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,download:a.download}})()');
  await page("Input.dispatchMouseEvent",{type:"mouseMoved",x:link.x,y:link.y});
  await page("Input.dispatchMouseEvent",{type:"mousePressed",x:link.x,y:link.y,button:"left",clickCount:1});
  await page("Input.dispatchMouseEvent",{type:"mouseReleased",x:link.x,y:link.y,button:"left",clickCount:1});
  const downloaded=path.join(downloadPath,"course-grade-review.json");
  await until(()=>fs.existsSync(downloaded),"actual JSON download");
  const bytes=fs.readFileSync(downloaded);
  fs.writeFileSync(path.join(out,"downloaded-course-grade-review.json"),bytes);
  const expected=JSON.parse(fs.readFileSync(normalPath,"utf8"));
  check("actual_download_exact_report",JSON.stringify(JSON.parse(bytes.toString("utf8")))===JSON.stringify(expected),{download:link.download,bytes:bytes.length,sha256:sha(bytes)});
  check("actual_download_matches_displayed_hash",sha(bytes)===(await evaluate('document.querySelector("#json-sha256").textContent')));
  const stillClosed=await evaluate('[...document.querySelectorAll("details")].every(d=>!d.open)');
  check("details_closed_before_print",stillClosed);
  const pdf=await page("Page.printToPDF",{printBackground:true,preferCSSPageSize:true});
  const pdfPath=path.join(out,"print-review.pdf");
  fs.writeFileSync(pdfPath,Buffer.from(pdf.data,"base64"));
  const printText=execFileSync("/usr/bin/pdftotext",["-layout",pdfPath,"-"],{encoding:"utf8"});
  fs.writeFileSync(path.join(out,"print-review.txt"),printText);
  check("print_includes_closed_details",printText.includes("201") && printText.includes("submission_state") && printText.includes("not_returned") && printText.includes("assignment_group_id"),{containsAssignment201:printText.includes("201"),containsFullSubmission:printText.includes("submission_state")});
  receipt.pdf_info=execFileSync("/usr/bin/pdfinfo",[pdfPath],{encoding:"utf8"});
  check("no_external_page_requests",!receipt.requests.some(r=>/^https?:|^wss?:/.test(r.url)),receipt.requests);
  check("no_runtime_exceptions",receipt.exceptions.length===0,receipt.exceptions);
  receipt.passed=true;
  await call("Browser.close");
} catch(error) {
  receipt.passed=false;receipt.error=String(error.stack||error);
  process.exitCode=1;
} finally {
  for(const {timer,reject} of pending.values()){clearTimeout(timer);reject(new Error("Browser closed"));}
  pending.clear(); if(ws)ws.close();
  if(child && child.exitCode===null){child.kill("SIGTERM");await pause(700);if(child.exitCode===null)child.kill("SIGKILL");}
  fs.closeSync(log);
  receipt.finished_at=new Date().toISOString();
  receipt.artifacts=Object.fromEntries(["synthetic-review.html","synthetic-normalized.json","desktop.png","desktop-assignments.png","mobile.png","mobile-assignments.png","downloaded-course-grade-review.json","print-review.pdf","print-review.txt","browser-receiving.mjs"].filter(n=>fs.existsSync(path.join(out,n))).map(n=>[n,{bytes:fs.statSync(path.join(out,n)).size,sha256:sha(fs.readFileSync(path.join(out,n)))}]));
  fs.writeFileSync(path.join(out,"browser-receipt.json"),JSON.stringify(receipt,null,2)+"\n");
  if(child && child.exitCode!==null)fs.rmSync(profile,{recursive:true,force:true});
  console.log(JSON.stringify({passed:receipt.passed,checks:receipt.checks,error:receipt.error},null,2));
}
