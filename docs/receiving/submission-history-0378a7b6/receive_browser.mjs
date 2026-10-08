import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {chromium} from 'D:/Hamon/worktrees/surgeon-trails-0378a7b6-proof/browser-tools/node_modules/playwright-core/index.mjs';

const [proof]=process.argv.slice(2);
const candidate=path.join(proof,'candidate'), out=path.join(proof,'browser');
fs.mkdirSync(out);
const expected=JSON.parse(fs.readFileSync(path.join(candidate,'expected-normalized-report.json'),'utf8'));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const receipt={started:new Date().toISOString(),driver_sha256:hash(fs.readFileSync(new URL(import.meta.url))),checks:[],errors:[],externalRequests:[],artifacts:{}};
const context=await chromium.launchPersistentContext(path.join(out,'profile'),{
  executablePath:'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',headless:true,
  viewport:{width:1360,height:1050},acceptDownloads:true,downloadsPath:path.join(out,'downloads'),
  args:['--disable-background-networking']
});
try {
  await context.route('**/*',async route=>{
    const url=route.request().url();
    if(!/^(file:|data:|about:)/.test(url)){receipt.externalRequests.push(url);await route.abort();}
    else await route.continue();
  });
  const page=context.pages()[0]??await context.newPage();
  page.on('pageerror',error=>receipt.errors.push(String(error)));
  page.on('console',message=>{if(message.type()==='error')receipt.errors.push(message.text());});
  page.on('request',request=>{if(/^https?:/.test(request.url()))receipt.externalRequests.push(request.url());});
  await page.goto(pathToFileURL(path.join(candidate,'submission-history.html')).href);
  async function facts(selector) {
    return page.locator(selector+' > dl.fields > .field').evaluateAll(nodes=>Object.fromEntries(nodes.map(node=>[
      JSON.parse(node.querySelector('dt code').textContent),JSON.parse(node.querySelector('dd pre').textContent)
    ])));
  }
  assert.deepEqual(await facts('#assignment-record'),expected.assignment);
  assert.deepEqual(await facts('#current-record'),expected.current_submission);
  assert.match(await page.locator('#current-grade-context').innerText(),/earlier attempt/i);
  receipt.checks.push('Current submission and assignment retain exact fields; false current-grade match is visibly qualified');
  const records=page.locator('.history-record');
  assert.equal(await records.count(),expected.history.records.length);
  for(let i=0;i<expected.history.records.length;i++) {
    assert.deepEqual(await facts('#history-record-'+(i+1)),expected.history.records[i]);
    assert.match(await records.nth(i).locator('h3').innerText(),new RegExp('Returned record '+(i+1)+'\\b'));
  }
  receipt.checks.push('All returned records appear once in original 2,1,2,missing-attempt order; zero, null, false, missing fields and nested comments remain original');
  const comments=page.locator('.top-comment');
  assert.equal(await comments.count(),expected.submission_comments.length);
  for(let i=0;i<expected.submission_comments.length;i++)assert.deepEqual(await facts('#top-comment-'+(i+1)),expected.submission_comments[i]);
  assert.match(await page.locator('#comments-context').innerText(),/not assigned/i);
  receipt.checks.push('Top-level comments remain in their own ordered section, separate from nested and current record data');
  assert.equal(await page.locator('script,iframe,img,link,form,input,button,video,audio,object,embed').count(),0);
  const hrefs=await page.locator('a[href]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
  assert.ok(hrefs.every(href=>href.startsWith('#')||href.startsWith('data:application/json;base64,')));
  receipt.checks.push('Provider markup and URL metadata stay literal; no active embedded content or external link is created');
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const nav=page.locator('nav a').last();
  await nav.focus();await page.keyboard.press('Enter');
  assert.ok(page.url().endsWith('#history-record-4'));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth),false);
  receipt.checks.push('Native keyboard anchor reaches the fourth record and the390px report has no horizontal overflow');
  await page.locator('#download-history').focus();
  const awaited=page.waitForEvent('download');
  await page.keyboard.press('Enter');
  const download=await awaited;
  const destination=path.join(out,'downloaded-history.json');
  await download.saveAs(destination);
  const downloaded=fs.readFileSync(destination);
  assert.deepEqual(JSON.parse(downloaded),expected);
  assert.equal((await page.locator('#json-sha256').innerText()).trim(),hash(downloaded));
  receipt.checks.push('Actual keyboard download preserves the complete original normalized JSON and its displayed checksum');
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  await page.pdf({path:path.join(out,'submission-history.pdf'),format:'A4',printBackground:true});
  assert.ok(fs.readFileSync(path.join(out,'submission-history.pdf')).subarray(0,5).equals(Buffer.from('%PDF-')));
  receipt.checks.push('Native print pipeline generates a PDF; visual/text interpretation is recorded separately');
  for(const [name,pattern] of [['unavailable',/unavailable/i],['empty',/empty/i]]) {
    await page.goto(pathToFileURL(path.join(candidate,name+'.html')).href);
    assert.match(await page.locator('#history-availability').innerText(),pattern);
    assert.equal(await page.locator('.history-record').count(),0);
    assert.match(await page.locator('#comments-availability').innerText(),pattern);
  }
  receipt.checks.push('Unavailable history/comments and returned empty history/comments have distinct visible messages');
  assert.deepEqual(receipt.errors,[]);assert.deepEqual(receipt.externalRequests,[]);
  receipt.checks.push('Zero observed runtime or console errors and zero observed external requests');
  for(const name of ['desktop.png','mobile.png','downloaded-history.json','submission-history.pdf']) {
    const bytes=fs.readFileSync(path.join(out,name));receipt.artifacts[name]={bytes:bytes.length,sha256:hash(bytes)};
  }
  receipt.passed=true;
} catch(error){receipt.passed=false;receipt.failure=String(error?.stack??error);throw error;}
finally {
  await context.close();receipt.finished=new Date().toISOString();
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  process.stdout.write(JSON.stringify({passed:receipt.passed,checks:receipt.checks,receipt:path.join(out,'receipt.json')})+'\n');
}
