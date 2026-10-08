// Actual native CLI -> saved file -> installed Chrome receiving. No browser stubs.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.resolve(process.argv[2] || '');
const baseline = path.resolve(process.argv[3] || '');
if (process.argv.length !== 4 || out === root || out.startsWith(root + path.sep) || fs.existsSync(out)) {
  throw new Error('Usage: node scripts/receive_agenda_view.mjs NEW_EXTERNAL_OUTPUT IMMUTABLE_BASELINE');
}
fs.mkdirSync(out, { recursive: false });
const receipt = { schema: 'canvaspilot-agenda-view-browser/1', accepted: false, artifacts: [],
  native: [], browser: [], pageErrors: [], externalRequests: [] };
const sha = data => createHash('sha256').update(data).digest('hex');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const git = (source, ...args) => execFileSync('git', ['-C', source, ...args], { encoding: 'utf8' }).trim();
const sourcePins = source => Object.fromEntries(execFileSync('git', ['-C', source, 'ls-files', '-z'], { encoding: 'utf8' })
  .split('\0').filter(Boolean).sort().map(name => [name, sha(fs.readFileSync(path.join(source, name)))]));
const save = (name, data) => {
  fs.writeFileSync(path.join(out, name), data, { flag: 'wx' });
  receipt.artifacts.push({ name, bytes: Buffer.byteLength(data), sha256: sha(data) });
};
async function until(condition, label, timeout = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const value = await condition();
    if (value) return value;
    await sleep(50);
  }
  throw new Error(`Timed out: ${label}`);
}

let server, chrome, profile, socket, serial = 0, chromeLog = '';
const pending = new Map();
const loaded = new Map();
function command(method, params = {}, sessionId) {
  const id = ++serial;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 8000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}
async function page(targetId, { scripts = true, width = 1280 } = {}) {
  const { sessionId } = await command('Target.attachToTarget', { targetId, flatten: true });
  const send = (method, params) => command(method, params, sessionId);
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });
  await send('Emulation.setDeviceMetricsOverride', { width, height: 950, deviceScaleFactor: 1, mobile: false });
  if (!scripts) await send('Emulation.setScriptExecutionDisabled', { value: true });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const key = async (keyName, code = keyName, virtual = 0, modifiers = 0) => {
    const text = keyName === 'Enter' ? { text: '\r', unmodifiedText: '\r' } : {};
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: keyName, code, windowsVirtualKeyCode: virtual, nativeVirtualKeyCode: virtual, modifiers, ...text });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: keyName, code, windowsVirtualKeyCode: virtual, nativeVirtualKeyCode: virtual, modifiers });
  };
  const click = async selector => {
    const point = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) throw new Error('Missing control'); e.scrollIntoView({block:'center'}); const r=e.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...point });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 });
  };
  return { targetId, sessionId, send, evaluate, key, click };
}

async function cli(source, commandName, name, base, output) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([name]) => !name.toLowerCase().endsWith('_proxy')));
  env.PYTHONDONTWRITEBYTECODE = '1';
  env.PYTHONPATH = path.join(source, 'src') + path.delimiter + (env.PYTHONPATH || '');
  const args = ['-B', '-m', 'canvaspilot.cli', commandName, '42', '77', '--start', '2026-10-08', '--end', '2026-10-15',
    '--base-url', base, '--token', 'authored-agenda-view-browser', '--profile', path.join(out, 'unused-profile')];
  if (output) args.push('--out', output);
  const child = spawn(process.env.CANVASPILOT_PYTHON || 'python3', args, { cwd: source, env, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = [], stderr = [];
  child.stdout.on('data', data => stdout.push(data)); child.stderr.on('data', data => stderr.push(data));
  const exit = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error('Native CLI timed out')); }, 25000);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', code => { clearTimeout(timer); resolve(code); });
  });
  const result = { exit, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr) };
  save(`${name}.stdout`, result.stdout); save(`${name}.stderr`, result.stderr);
  receipt.native.push({ name, command: commandName, exit, stdoutSHA256: sha(result.stdout), stderrSHA256: sha(result.stderr) });
  return result;
}

async function main() {
  receipt.source = { head: git(root, 'rev-parse', 'HEAD'), tree: git(root, 'rev-parse', 'HEAD^{tree}'), parents: git(root, 'show', '-s', '--format=%P', 'HEAD').split(' '), githubSHA: process.env.GITHUB_SHA || null };
  if (receipt.source.githubSHA) assert.equal(receipt.source.head, receipt.source.githubSHA);
  assert.equal(git(root, 'status', '--porcelain'), '');
  assert.equal(git(baseline, 'rev-parse', 'HEAD'), '0480cbce421bae532e3e909899fc8fb83789e878');
  assert.equal(git(baseline, 'status', '--porcelain'), '');
  const before = sourcePins(root), oldBefore = sourcePins(baseline);
  save('source-before.json', JSON.stringify(before, null, 2) + '\n');
  save('baseline-source-before.json', JSON.stringify(oldBefore, null, 2) + '\n');
  const fixtureBytes = fs.readFileSync(path.join(root, 'tests/fixtures/agenda_view_calendar.json'));
  assert.equal(sha(fixtureBytes), '0a72127b1de5f4f9836c30fd8dd5bbd762e63e5805111e64db8a918c7ee14f19');
  const records = JSON.parse(fixtureBytes), requests = [];
  server = createServer((request, response) => {
    const url = new URL(request.url, 'http://127.0.0.1');
    const kind = url.searchParams.get('type');
    requests.push({ method: request.method, path: url.pathname, query: [...url.searchParams] });
    if (request.method !== 'GET' || url.pathname !== '/api/v1/calendar_events' || !(kind in records)) {
      response.writeHead(404); response.end(); return;
    }
    const body = JSON.stringify(records[kind]);
    response.writeHead(200, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }); response.end(body);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const old = await cli(baseline, 'agenda', 'original-native', base);
  assert.equal(old.exit, 0); assert.equal(old.stderr.length, 0); assert.equal(requests.length, 2);
  assert.equal(sha(old.stdout), '1d47bb539939336ab70bea45068635d57196a5e45d1660abddd5bcfcc17811ce');
  requests.length = 0;
  const absent = await cli(baseline, 'export-agenda', 'original-missing-view', base, path.join(out, 'absent-original.html'));
  assert.equal(absent.exit, 2); assert.match(absent.stderr.toString(), /invalid choice/); assert.equal(requests.length, 0);
  assert.equal(fs.existsSync(path.join(out, 'absent-original.html')), false);
  const current = await cli(root, 'agenda', 'current-native', base);
  assert.equal(current.exit, 0); assert.deepEqual(current.stdout, old.stdout); assert.equal(requests.length, 2);
  requests.length = 0;
  const htmlPath = path.join(out, 'agenda.html');
  const exported = await cli(root, 'export-agenda', 'current-export', base, htmlPath);
  assert.equal(exported.exit, 0, exported.stderr.toString()); assert.equal(exported.stderr.length, 0);
  assert.equal(requests.length, 2);
  for (const request of requests) {
    assert.equal(request.method, 'GET');
    const query = new URLSearchParams(request.query);
    assert.deepEqual(query.getAll('context_codes[]'), ['course_42', 'course_77']);
    assert.equal(query.get('start_date'), '2026-10-08'); assert.equal(query.get('end_date'), '2026-10-15');
    assert.equal(query.get('per_page'), '50');
  }
  receipt.nativeRequests = requests;
  const native = JSON.parse(current.stdout), html = fs.readFileSync(htmlPath), exportReceipt = JSON.parse(exported.stdout);
  assert.deepEqual(native.counts, { total: 4, timed: 2, all_day: 1, timing_unavailable: 1 });
  assert.equal(exportReceipt.html_sha256, sha(html)); assert.equal(exportReceipt.native_report_sha256, sha(current.stdout));
  receipt.savedFile = { bytes: html.length, sha256: sha(html), nativeBytes: current.stdout.length, nativeSHA256: sha(current.stdout) };
  server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); server = null;
  assert.equal(fs.existsSync(path.join(out, 'unused-profile')), false);

  const executable = [process.env.CANVASPILOT_CHROMIUM_BIN, '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/opt/google/chrome/chrome', '/usr/bin/chromium'].find(file => file && fs.existsSync(file));
  if (!executable) throw new Error('Actual installed Chrome is required; no download or simulated acceptance.');
  receipt.runtime = { node: process.version, chrome: execFileSync(executable, ['--version'], { encoding: 'utf8' }).trim(), executable };
  profile = fs.mkdtempSync(path.join(os.tmpdir(), 'canvas-agenda-view-chrome-'));
  chrome = spawn(executable, ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
  chrome.stderr.on('data', data => { chromeLog += data; });
  const active = path.join(profile, 'DevToolsActivePort');
  await until(() => fs.existsSync(active), 'installed Chrome startup');
  const [port, endpoint] = fs.readFileSync(active, 'utf8').trim().split('\n');
  socket = new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const request = pending.get(message.id); pending.delete(message.id); clearTimeout(request.timer);
      if (message.error) request.reject(new Error(JSON.stringify(message.error))); else request.resolve(message.result || {});
    } else if (message.method === 'Page.loadEventFired') loaded.set(message.sessionId, (loaded.get(message.sessionId) || 0) + 1);
    else if (message.method === 'Runtime.exceptionThrown') receipt.pageErrors.push(message.params.exceptionDetails);
    else if (message.method === 'Network.requestWillBeSent') {
      const url = message.params.request.url;
      if (!url.startsWith('file:') && !url.startsWith('data:') && url !== 'about:blank') receipt.externalRequests.push(url);
    }
  });
  const downloads = path.join(out, 'downloads'); fs.mkdirSync(downloads);
  await command('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: downloads, eventsEnabled: true });
  const target = await command('Target.createTarget', { url: 'about:blank' });
  const view = await page(target.targetId);
  await view.send('Page.navigate', { url: pathToFileURL(htmlPath).href });
  await until(() => view.evaluate("document.readyState === 'complete' && document.getElementById('view-tools')?.hidden === false"), 'real saved view ready');
  const observed = async label => {
    const state = await view.evaluate(`(() => ({count:document.getElementById('view-count').textContent,context:document.getElementById('view-context').textContent,entries:[...document.querySelectorAll('.agenda-entry:not([hidden])')].map(e=>({course:e.dataset.course,group:e.dataset.group,date:e.dataset.date,title:e.querySelector('h3').textContent,source:JSON.parse(e.querySelector('.source-details pre').textContent)}))}))()`);
    receipt.browser.push({ label, ...state }); return state;
  };
  const all = await observed('complete offline saved agenda');
  assert.equal(all.count, 'Showing 4 of 4 saved entries');
  assert.deepEqual(all.entries.map(e => e.source), [...native.timed, ...native.all_day, ...native.timing_unavailable]);
  assert.equal(await view.evaluate("document.querySelectorAll('img,iframe,object').length"), 0);
  assert.equal(await view.evaluate('localStorage.length + sessionStorage.length'), 0);

  async function chooseCourse(index) {
    await view.evaluate("document.getElementById('course-filter').focus()");
    await view.key('Home', 'Home', 36);
    for (let i = 0; i < index; i += 1) await view.key('ArrowDown', 'ArrowDown', 40);
    await view.key('Enter', 'Enter', 13);
    await until(() => view.evaluate(`document.getElementById('course-filter').selectedIndex === ${index}`), 'native course select');
  }
  // Date controls use their real browser value setter and bubbling input event;
  // course/search/reset/links/disclosures below use actual mouse/key input.
  async function chooseDate(value) {
    await view.evaluate(`(() => {const e=document.getElementById('date-filter');e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  }
  await chooseCourse(1);
  assert.deepEqual((await observed('Course 42')).entries.map(e => e.source.record.id), ['evt-07', 'pending']);
  await chooseDate('2026-10-09');
  assert.deepEqual((await observed('Course 42 unknown timing retained through date')).entries.map(e => e.source.record.id), ['pending']);
  await chooseCourse(2);
  assert.deepEqual((await observed('Course 77 all-day source date')).entries.map(e => e.source.record.id), [0]);
  await chooseDate('2026-10-08');
  assert.deepEqual((await observed('Course 77 timed source date')).entries.map(e => e.source.record.id), [901]);
  await chooseDate('2026-10-15');
  assert.equal((await observed('explicit empty matching view')).count, 'Showing 0 of 4 saved entries');
  await view.click('button[type="reset"]');
  await until(() => view.evaluate("document.getElementById('view-count').textContent === 'Showing 4 of 4 saved entries'"), 'reset complete view');
  await view.click('#search-filter'); await view.send('Input.insertText', { text: '<poster>' });
  assert.deepEqual((await observed('literal text search')).entries.map(e => e.source.record.id), ['evt-07']);
  assert.equal(await view.evaluate("document.querySelectorAll('poster,img').length"), 0);
  await chooseCourse(2);
  assert.equal((await observed('intersecting course and search')).entries.length, 0);
  await view.click('button[type="reset"]');
  await until(() => view.evaluate("document.getElementById('view-count').textContent === 'Showing 4 of 4 saved entries'"), 'second reset');

  await view.click('#download-native');
  const downloaded = path.join(downloads, 'course-agenda.json');
  await until(() => fs.existsSync(downloaded), 'actual original JSON download');
  assert.deepEqual(fs.readFileSync(downloaded), current.stdout);
  receipt.download = { actualFile: 'downloads/course-agenda.json', bytes: fs.statSync(downloaded).size, sha256: sha(fs.readFileSync(downloaded)) };

  const previousLoads = loaded.get(view.sessionId) || 0;
  await view.send('Page.reload');
  await until(() => (loaded.get(view.sessionId) || 0) > previousLoads, 'actual reload completed');
  await until(() => view.evaluate("document.getElementById('view-tools')?.hidden === false"), 'fresh keyboard view');
  const focus = [];
  for (let i = 0; i < 14; i += 1) {
    await view.key('Tab', 'Tab', 9);
    focus.push(await view.evaluate(`(() => {const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,id:e.id,text:e.textContent.trim().slice(0,80),outline:s.outlineStyle,width:parseFloat(s.outlineWidth)};})()`));
    if (focus.at(-1).text === 'Reset view') break;
  }
  receipt.keyboard = focus;
  // Native date widgets may expose multiple keyboard segments inside one input.
  const stops = focus.filter((entry, i) => !i || entry.id !== focus[i - 1].id || entry.text !== focus[i - 1].text);
  assert.equal(stops[0].text, 'Skip to agenda');
  assert.deepEqual(stops.slice(1,6).map(e => e.id), ['download-native', 'print-agenda', 'course-filter', 'date-filter', 'search-filter']);
  assert.equal(stops[6].text, 'Reset view'); assert.equal(stops.length, 7);
  assert.ok(focus.every(e => e.width >= 2 && e.outline !== 'none'));
  await view.key('Tab', 'Tab', 9);
  assert.equal(await view.evaluate('document.activeElement.tagName'), 'SUMMARY');
  await view.key('Enter', 'Enter', 13);
  assert.equal(await view.evaluate("document.querySelector('.source-details').open"), true);

  async function layout(width, name) {
    await view.send('Emulation.setDeviceMetricsOverride', { width, height: 950, deviceScaleFactor: 1, mobile: false });
    await view.evaluate('window.scrollTo(0,0)');
    const measured = await view.evaluate(`(() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,panels:[...document.querySelectorAll('.page-header,.view-tools,.agenda-entry:not([hidden])')].map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width};}),controls:[...document.querySelectorAll('button:not([hidden]),select,input')].map(e=>({height:e.getBoundingClientRect().height}))}))()`);
    assert.equal(measured.width, width); assert.ok(measured.scrollWidth <= width + 1);
    assert.ok(measured.panels.every(p => p.left >= -1 && p.right <= width + 1));
    assert.ok(measured.controls.every(c => c.height >= 43));
    receipt.browser.push({ label: name, layout: measured });
    save(`${name}.png`, Buffer.from((await view.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })).data, 'base64'));
  }
  await layout(1280, 'desktop-complete');
  await layout(390, 'narrow-complete');
  await chooseCourse(1); await chooseDate('2026-10-09');
  await observed('narrow filtered unknown timing');
  await layout(390, 'narrow-filtered');

  await view.send('Emulation.setEmulatedMedia', { media: 'print' });
  const printState = await view.evaluate(`(() => ({tools:getComputedStyle(document.getElementById('view-tools')).display,actions:getComputedStyle(document.querySelector('.actions')).display,visible:[...document.querySelectorAll('.agenda-entry')].filter(e=>getComputedStyle(e).display!=='none').map(e=>JSON.parse(e.querySelector('pre').textContent).record.id),context:document.getElementById('view-context').textContent,preOverflow:getComputedStyle(document.querySelector('.agenda-entry:not([hidden]) pre')).overflowY}))()`);
  assert.equal(printState.tools, 'none'); assert.equal(printState.actions, 'none');
  assert.deepEqual(printState.visible, ['pending']); assert.match(printState.context, /Course 42.*2026-10-09/);
  assert.equal(printState.preOverflow, 'visible'); receipt.print = printState;
  await view.evaluate(`window.addEventListener('beforeprint',()=>{window.agendaReceivingPrint=[...document.querySelectorAll('.agenda-entry:not([hidden])')].map(e=>({id:JSON.parse(e.querySelector('pre').textContent).record.id,sourceOpen:e.querySelector('details').open}));})`);
  const printed = Buffer.from((await view.send('Page.printToPDF', { printBackground: true, preferCSSPageSize: true })).data, 'base64');
  assert.equal(printed.subarray(0,5).toString(), '%PDF-'); save('filtered-print.pdf', printed);
  receipt.print.beforePrint = await view.evaluate('window.agendaReceivingPrint');
  assert.deepEqual(receipt.print.beforePrint, [{ id: 'pending', sourceOpen: true }]);
  await view.send('Emulation.setEmulatedMedia', { media: '' });

  const noScriptTarget = await command('Target.createTarget', { url: 'about:blank' });
  const noScript = await page(noScriptTarget.targetId, { scripts: false });
  await noScript.send('Page.navigate', { url: pathToFileURL(htmlPath).href });
  await until(() => noScript.evaluate("document.readyState === 'complete' && !!document.getElementById('agenda')"), 'script-disabled complete source');
  const noScriptState = await noScript.evaluate(`({visible:[...document.querySelectorAll('.agenda-entry')].filter(e=>getComputedStyle(e).display!=='none').length,toolsHidden:document.getElementById('view-tools').hidden,download:document.getElementById('download-native').getAttribute('href'),text:document.body.textContent})`);
  assert.equal(noScriptState.visible, 4); assert.equal(noScriptState.toolsHidden, true);
  assert.match(noScriptState.text, /complete saved agenda is shown/);
  assert.deepEqual(Buffer.from(noScriptState.download.split(',')[1], 'base64'), current.stdout);
  receipt.scriptDisabled = { visible: noScriptState.visible, toolsHidden: true, exactOriginalJSON: true };
  assert.deepEqual(receipt.pageErrors, []); assert.deepEqual(receipt.externalRequests, []);
  assert.equal(fs.existsSync(path.join(out, 'unused-profile')), false);
  const after = sourcePins(root), oldAfter = sourcePins(baseline);
  assert.deepEqual(after, before); assert.deepEqual(oldAfter, oldBefore);
  assert.equal(git(root, 'status', '--porcelain'), ''); assert.equal(git(baseline, 'status', '--porcelain'), '');
  assert.deepEqual(fs.readFileSync(htmlPath), html);
  save('source-after.json', JSON.stringify(after, null, 2) + '\n');
  receipt.sourcePreservation = { currentFiles: Object.keys(after).length, baselineFiles: Object.keys(oldAfter).length, clean: true, unchanged: true, htmlUnchanged: true };
  receipt.accepted = true;
}

main().catch(error => {
  receipt.error = { name: error.name, message: error.message, stack: error.stack }; process.exitCode = 1;
}).finally(async () => {
  receipt.protocolCommands = serial;
  process.stdout.write('AGENDA_VIEW_MAIN_RESULT\n' + JSON.stringify(receipt, null, 2) + '\n');
  receipt.cleanupErrors = [];
  try { save('receiving-before-cleanup.json', JSON.stringify(receipt, null, 2) + '\n'); }
  catch (error) { receipt.cleanupErrors.push({ operation: 'write-main-receipt', message: error.message }); }
  for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error('Browser closing')); }
  pending.clear(); if (socket) socket.close();
  let stopped = !chrome?.pid || chrome.exitCode !== null || chrome.signalCode !== null;
  if (!stopped) {
    try {
      await new Promise((resolve, reject) => {
        let finalTimer;
        const timer = setTimeout(() => { chrome.kill('SIGKILL'); finalTimer = setTimeout(() => reject(new Error('Exclusive Chrome did not exit')), 3000); }, 3000);
        chrome.once('exit', () => { clearTimeout(timer); clearTimeout(finalTimer); resolve(); });
        chrome.kill('SIGTERM');
      }); stopped = true;
    } catch (error) { receipt.cleanupErrors.push({ operation: 'stop-chrome', message: error.message }); }
  }
  if (profile && stopped) {
    try { await fs.promises.rm(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 100 }); }
    catch (error) { receipt.cleanupErrors.push({ operation: 'remove-profile', message: error.message }); }
  }
  if (server) {
    try { server.closeAllConnections(); await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())); }
    catch (error) { receipt.cleanupErrors.push({ operation: 'close-fixture', message: error.message }); }
  }
  if (receipt.cleanupErrors.length) { receipt.accepted = false; process.exitCode = 1; }
  try { save('chrome-stderr.log', chromeLog); save('receiving.json', JSON.stringify(receipt, null, 2) + '\n'); }
  catch (error) { receipt.evidenceWriteError = error.message; receipt.accepted = false; process.exitCode = 1; }
  process.stdout.write('AGENDA_VIEW_FINAL_RESULT\n' + JSON.stringify(receipt, null, 2) + '\n');
});
