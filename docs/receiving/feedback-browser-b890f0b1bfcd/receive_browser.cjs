'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const {chromium} = require('/home/jacob/hamon-b890f0b1bfcd/browser-tools/node_modules/playwright');
const input = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3]);
fs.mkdirSync(out, {recursive:false});
const expected = JSON.parse(fs.readFileSync(path.join(input,'expectations.json'),'utf8'));
const observations = {status:'running', playwright:require('/home/jacob/hamon-b890f0b1bfcd/browser-tools/node_modules/playwright/package.json').version, sandbox:true, groups:[], requests:[], exceptions:[], layouts:[], files:[], receiver_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex')};
const save = ()=>fs.writeFileSync(path.join(out,'browser-result.json'),JSON.stringify(observations,null,2)+'\n');
const check = (name,ok,detail={})=>{observations.groups.push({name,pass:!!ok,...detail});save();};
const sha = file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
(async()=>{
 let browser;
 try {
  browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,chromiumSandbox:true,args:['--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--disable-background-networking'],timeout:45000});
  observations.chromium=browser.version();
  const context=await browser.newContext({viewport:{width:1200,height:900},offline:true});
  const page=await context.newPage();
  page.on('pageerror',e=>observations.exceptions.push(String(e)));
  page.on('request',r=>observations.requests.push({url:r.url(),type:r.resourceType()}));
  for(const [name,e] of Object.entries(expected)) {
   const file=path.join(input,name+'.html');
   check(name+': exact producer HTML',sha(file)===e.html_sha256);
   await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:20000});
   const values=await page.evaluate(()=>({
    title:document.querySelector('h1').textContent,
    text:document.body.innerText,
    fields:Object.fromEntries([...document.querySelectorAll('[data-field]')].map(x=>[x.dataset.field,x.textContent])),
    criteria:[...document.querySelectorAll('article[id^="criterion-"] h3')].map(x=>x.textContent),
    articles:[...document.querySelectorAll('article h3')].map(x=>x.textContent),
    forbidden:[...document.querySelectorAll('script,img,iframe,object,embed,audio,video,link,base,form')].map(x=>x.tagName),
    anchors:[...document.querySelectorAll('a')].map(x=>({href:x.href,text:x.textContent,rel:x.rel})),
    injected:typeof window.injected,
   }));
   fs.writeFileSync(path.join(out,name+'-dom.json'),JSON.stringify(values,null,2)+'\n');
   check(name+': original visible identity and literal feedback',values.title===e.title && values.criteria[0]==='1. '+e.criterion && values.fields['comment.1.comment']===e.full_comment && values.fields['criterion.1.long_description']===e.literal && values.articles.includes('Unmatched assessment: '+e.unmatched));
   check(name+': zero unknown empty and attempt context',values.fields['submission.score']==='0' && values.fields['submission.grade']==='Returned empty text' && values.fields['submission.posted_at']==='Not returned' && values.fields['submission.attempt']==='3' && values.fields['submission.grader_id']==='-7' && values.text.includes('must not be treated as a grade for the current attempt.') && values.text.includes('Advisory rubric:') && values.fields['comment.1.author.display_name']==='Different recorded display' && values.fields['comment.1.author.id']==='28');
   const numeric=['criterion.1.points','criterion.1.rating.1.points','criterion.1.assessment.points','unmatched.1.points'];
   check(name+': independent rubric visibility',numeric.every(key=>e.hide_points ? !(key in values.fields) : key in values.fields) && ((e.hide_points||e.hide_total)? !('rubric.points_possible' in values.fields) : values.fields['rubric.points_possible']==='15') && values.fields['submission.score']==='0' && values.fields['assignment.points_possible']==='100' && values.fields['rubric.hide_outcome_results']==='true');
   check(name+': literal DOM and explicit link',values.forbidden.length===0 && values.injected==='undefined' && values.anchors.length===1 && values.anchors[0].href==='https://receiving.invalid/courses/61/assignments/902?view=feedback&literal=%3Cvalue%3E' && values.anchors[0].rel==='noreferrer noopener');
   for(const width of [1200,390]) {
    await page.setViewportSize({width,height:900});
    const layout=await page.evaluate(()=>({width:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,overflow:[...document.querySelectorAll('h1,h2,h3,dd,.literal')].filter(x=>x.scrollWidth>x.clientWidth+1).map(x=>({tag:x.tagName,field:x.dataset.field||null,text:x.textContent.slice(0,80),client:x.clientWidth,scroll:x.scrollWidth}))}));
    observations.layouts.push({case:name,...layout});
    check(name+': '+width+'px readable width',layout.scroll<=layout.client+1 && layout.overflow.length===0,{layout});
    if(name==='ordinary'||name==='long-headings') {
     await page.screenshot({path:path.join(out,name+'-'+width+'.png'),fullPage:true});
    }
   }
   if(name==='ordinary'||name==='long-headings') {
    await page.setViewportSize({width:1200,height:900});
    await page.keyboard.press('Tab');
    const focus=await page.evaluate(()=>({tag:document.activeElement.tagName,href:document.activeElement.getAttribute('href'),outline:getComputedStyle(document.activeElement).outlineStyle}));
    check(name+': keyboard assignment link focus',focus.tag==='A' && focus.href===values.anchors[0].href && focus.outline!=='none',{focus});
    const pdf=path.join(out,name+'.pdf');
    await page.pdf({path:pdf,format:'A4',printBackground:true,preferCSSPageSize:true});
    const result=spawnSync('/usr/bin/pdftotext',['-layout',pdf,path.join(out,name+'-print.txt')],{encoding:'utf8',timeout:15000});
    const printed=result.status===0?fs.readFileSync(path.join(out,name+'-print.txt'),'utf8'):'';
    const normal=x=>x.replace(/\s+/gu,'');
    check(name+': complete printed feedback and headings',result.status===0 && normal(printed).includes(normal(e.criterion)) && normal(printed).includes(normal(e.unmatched)) && normal(printed).includes(normal(e.full_comment)) && printed.includes('PRINTED_COMMENT_END'),{pdftotext_exit:result.status,pdf_sha256:sha(pdf),print_text_sha256:crypto.createHash('sha256').update(printed).digest('hex'),printed_characters:printed.length,pages:(printed.match(/\f/g)||[]).length});
   }
   check(name+': original file unchanged',sha(file)===e.html_sha256);
  }
  check('offline local resources only',observations.requests.every(r=>r.url.startsWith('file:') && r.type==='document'),{requests:observations.requests});
  check('no page exceptions',observations.exceptions.length===0,{exceptions:observations.exceptions});
  await context.close();
  observations.status=observations.groups.every(g=>g.pass)?'pass':'fail';
 }catch(e){observations.status='receiver-error';observations.error=String(e.stack||e);}
 finally{if(browser)await browser.close(); observations.browser_closed=true; save();}
 console.log(JSON.stringify({status:observations.status,passed:observations.groups.filter(g=>g.pass).length,total:observations.groups.length,failures:observations.groups.filter(g=>!g.pass).map(g=>g.name),error:observations.error}));
 process.exitCode=observations.status==='pass'?0:1;
})();
