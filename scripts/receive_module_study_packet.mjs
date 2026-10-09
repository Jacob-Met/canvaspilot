// Actual native CLI and offline browser receiving using existing installations.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const source = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.resolve(process.argv[2] || '');
if (process.argv.length !== 3 || fs.existsSync(out) || out === source || out.startsWith(source + path.sep)) {
  throw new Error('Usage: node scripts/receive_module_study_packet.mjs NEW_EXTERNAL_OUTPUT');
}
const python = process.env.CANVASPILOT_PYTHON || 'python3';
const executablePath = process.env.CANVASPILOT_CHROME;
const dependency = process.env.CANVASPILOT_PLAYWRIGHT_FROM;
if (!executablePath || !dependency) throw new Error('Set CANVASPILOT_CHROME and CANVASPILOT_PLAYWRIGHT_FROM to existing installations.');
const { chromium } = createRequire(path.resolve(dependency))('playwright');
fs.mkdirSync(out, { recursive: false });
const sha = value => createHash('sha256').update(value).digest('hex');
const checks = [], requests = [], browserRequests = [], errors = [];
const receipt = { schema: 'canvaspilot.module-study-packet.browser/1', accepted: false, checks, requests, browserRequests, errors };
const check = (name, actual, expected = true) => {
  const row = { name, actual, expected, pass: false }; checks.push(row);
  assert.deepEqual(actual, expected, name); row.pass = true;
};
const save = (name, bytes) => fs.writeFileSync(path.join(out, name), bytes, { flag: 'wx' });
const sourcePaths = ['src/canvaspilot/module_study_packet.py', 'src/canvaspilot/cli.py',
  'src/canvaspilot/api.py', 'src/canvaspilot/client.py', 'src/canvaspilot/page_export.py',
  'src/canvaspilot/calendar_export.py', 'src/canvaspilot/study_workspace.py',
  'scripts/receive_module_study_packet.mjs'];
const bind = name => ({ path: name, bytes: fs.statSync(path.join(source, name)).size,
  sha256: sha(fs.readFileSync(path.join(source, name))) });
const names = ['Start here', 'Read the field guide', 'Explain your method', 'Read the guide again',
  'Field attachment', 'Reading not returned', 'Locked reading', 'Empty reading', 'External practice', 'Future reference'];
const items = [
  { type: 'SubHeader' }, { type: 'Page', page_url: 'reading' },
  { type: 'Assignment', content_id: 1001 }, { type: 'Page', page_url: 'reading' },
  { type: 'File', content_id: 44 }, { type: 'Page', page_url: 'missing' },
  { type: 'Page', page_url: 'locked' }, { type: 'Page', page_url: 'empty' },
  { type: 'ExternalTool', external_url: 'https://example.invalid/never-opened' },
  { type: 'FutureKind', unknown: { retained: true, zero: 0, nil: null, large: '__LARGE_INTEGER__' } },
].map((item, i) => ({ id: i + 1, module_id: 7, position: i === 3 ? 3 : i + 1,
  title: names[i], completion_requirement: i === 1 ? { type: 'must_view', completed: false } : null, ...item }));
const selected = { id: 7, course_id: 42, name: 'Field methods — module study packet', items_count: items.length,
  state: 'started', requirement_type: 'one', require_sequential_progress: false, prerequisite_module_ids: [],
  unknown: { empty: '', missingIsNotNull: null } };
const pages = {
  reading: { page_id: 201, url: 'reading', title: 'Observe before interpreting', locked_for_user: false,
    editor: 'rce', body: '<h2>Record what you observe</h2><p>Keep observations separate from conclusions.</p>'
      + '<script>window.__moduleSourceExecuted=true</script><img src="https://example.invalid/tracker">'
      + '<p>Use your own examples &amp; explain your uncertainty.</p>' },
  missing: { page_id: 202, url: 'missing', title: 'Block editor observation', editor: 'block',
    block_editor_attributes: { original: 'Retained as source; no invented HTML' } },
  locked: { page_id: 203, url: 'locked', title: 'Later reading', locked_for_user: true,
    lock_explanation: 'The provider reports this reading opens later.', body: null },
  empty: { page_id: 204, url: 'empty', title: 'Empty reading', body: '' },
};
const assignment = { id: 1001, name: 'Explain your method', description: '<p>Describe an observation and its limits.</p>',
  due_at: null, points_possible: 0, submission_types: [], use_rubric_for_grading: false,
  rubric: [{ id: 'criterion-zero', description: 'Describe uncertainty', points: 0,
    ratings: [{ id: 'rating-zero', description: 'Observation recorded', points: 0 }] }],
  rubric_settings: { hide_score_total: true } };
let server, browser;
async function nativeCLI(base) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toLowerCase().endsWith('_proxy')));
  Object.assign(env, { PYTHONDONTWRITEBYTECODE: '1', PYTHONIOENCODING: 'utf-8', PYTHONPATH: path.join(source, 'src'),
    CANVAS_BASE_URL: base, CANVAS_API_TOKEN: 'module-browser-synthetic',
    CANVAS_PROFILE: path.join(out, 'unused-profile'), TEMP: out, TMP: out });
  const args = ['-B', '-m', 'canvaspilot.cli', 'export-module', '42', '7', '--out', path.join(out, 'packet.html')];
  const child = spawn(python, args, { cwd: out, env, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = [], stderr = [];
  child.stdout.on('data', data => stdout.push(data)); child.stderr.on('data', data => stderr.push(data));
  const exit = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { child.kill(); reject(new Error('Native CLI timed out')); }, 60000);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', code => { clearTimeout(timer); resolve(code); });
  });
  const result = { exit, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr) };
  save('cli.stdout', result.stdout); save('cli.stderr', result.stderr);
  receipt.native = { executable: python, args, exit, executableSha256: sha(fs.readFileSync(python)) };
  check('native CLI exit', exit, 0); check('native CLI stderr', result.stderr.toString(), '');
  return JSON.parse(result.stdout);
}
try {
  receipt.startedAt = new Date().toISOString(); receipt.sourceBefore = sourcePaths.map(bind);
  receipt.head = execFileSync('git', ['-C', source, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  save('synthetic-input.json', JSON.stringify({ selected, items, pages, assignment }, null, 2));
  server = createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    requests.push({ method: req.method, path: url.pathname, search: url.search,
      syntheticAuth: req.headers.authorization === 'Bearer module-browser-synthetic' });
    let value, next;
    if (req.method !== 'GET') { res.writeHead(405); res.end(); return; }
    if (url.pathname === '/api/v1/courses/42/modules') {
      value = url.searchParams.has('cursor') ? [{ id: 8, items_count: 0, items: [] }] : [selected];
      if (!url.searchParams.has('cursor')) next = '?cursor=more-modules';
    } else if (url.pathname === '/api/v1/courses/42/modules/7/items') {
      value = url.searchParams.has('cursor') ? items.slice(3) : items.slice(0, 3);
      if (!url.searchParams.has('cursor')) next = '?cursor=more-items';
    } else if (url.pathname.startsWith('/api/v1/courses/42/pages/')) value = pages[url.pathname.split('/').at(-1)];
    else if (url.pathname === '/api/v1/courses/42/assignments/1001') value = assignment;
    if (value === undefined) { res.writeHead(404); res.end(); return; }
    const data = Buffer.from(JSON.stringify(value).replaceAll('"__LARGE_INTEGER__"', '9223372036854775807'));
    save('response-' + requests.length + '.json', data);
    const headers = { 'Content-Type': 'application/json', 'Content-Length': data.length };
    if (next) headers.Link = '<http://127.0.0.1:' + server.address().port + url.pathname + next + '>; rel="next"';
    res.writeHead(200, headers); res.end(data);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const report = await nativeCLI('http://127.0.0.1:' + server.address().port);
  await new Promise(resolve => server.close(resolve)); server = null;
  check('complete native read sequence', requests.map(row => row.path), [
    '/api/v1/courses/42/modules', '/api/v1/courses/42/modules',
    '/api/v1/courses/42/modules/7/items', '/api/v1/courses/42/modules/7/items',
    '/api/v1/courses/42/pages/reading', '/api/v1/courses/42/assignments/1001',
    '/api/v1/courses/42/pages/missing', '/api/v1/courses/42/pages/locked', '/api/v1/courses/42/pages/empty',
  ]);
  check('only synthetic GETs', requests.every(row => row.method === 'GET' && row.syntheticAuth));
  check('profile absent', fs.existsSync(path.join(out, 'unused-profile')), false);
  check('all positions retained', report.items, 10); check('unique bodies', report.unique_resources, 5);
  const packet = fs.readFileSync(path.join(out, 'packet.html'));
  check('receipt HTML digest', sha(packet), report.sha256);
  browser = await chromium.launch({ executablePath, headless: true,
    args: ['--disable-background-networking', '--no-first-run'] });
  receipt.browser = { engine: await browser.version(), node: process.version,
    playwright: createRequire(path.resolve(dependency))('playwright/package.json').version,
    executablePath, executableSha256: sha(fs.readFileSync(executablePath)), offline: true };
  const context = await browser.newContext({ acceptDownloads: true, offline: true, viewport: { width: 1280, height: 950 } });
  const page = await context.newPage();
  page.on('request', request => { if (/^https?:/.test(request.url())) browserRequests.push(request.url()); });
  page.on('pageerror', error => errors.push(String(error)));
  page.on('dialog', dialog => { errors.push('Unexpected dialog: ' + dialog.message()); dialog.dismiss(); });
  await page.goto(pathToFileURL(path.join(out, 'packet.html')).href);
  check('actual item headings', await page.locator('article.item > h2').allTextContents(), names);
  check('no executable or remote elements', await page.locator('script,img,iframe,object,embed,form,link,video,audio').count(), 0);
  check('source script not executed', await page.evaluate(() => window.__moduleSourceExecuted === undefined));
  check('no persistent controls', await page.locator('input,textarea,button').count(), 0);
  const sourceLink = page.getByRole('link', { name: 'Download complete retained source JSON', exact: true });
  const href = await sourceLink.getAttribute('href');
  const sourceJSON = Buffer.from(href.split(',')[1], 'base64');
  check('retained JSON digest', sha(sourceJSON), report.source_json_sha256);
  check('retained JSON byte count', sourceJSON.length, report.source_json_bytes);
  check('large integer remains literal', sourceJSON.includes(Buffer.from('9223372036854775807')));
  check('raw script retained', sourceJSON.toString().includes('window.__moduleSourceExecuted=true'));
  check('missing body label', await page.getByText('Page body was not returned.', { exact: true }).count(), 1);
  check('null body label', await page.getByText('Page body is unavailable (null).', { exact: true }).count(), 1);
  check('empty body label', await page.getByText('The supplied page body is empty.', { exact: true }).count(), 1);
  check('reference-only count', await page.getByText('Reference only.', { exact: false }).count(), 4);
  await page.keyboard.press('Tab');
  check('first keyboard stop is source download', await sourceLink.evaluate(el => el === document.activeElement));
  const downloadPromise = page.waitForEvent('download');
  await page.keyboard.press('Enter'); const download = await downloadPromise;
  await download.saveAs(path.join(out, 'downloaded-source.json'));
  check('actual download bytes exact', fs.readFileSync(path.join(out, 'downloaded-source.json')).equals(sourceJSON));
  await page.keyboard.press('Tab');
  check('keyboard reaches contents', await page.evaluate(() => document.activeElement.getAttribute('href')), '#item-1');
  await page.keyboard.press('Enter');
  check('keyboard contents navigation', new URL(page.url()).hash, '#item-1');
  const disclosure = page.locator('#item-2 details.raw-source').first();
  await disclosure.locator('summary').focus(); await page.keyboard.press('Space');
  check('Space opens source', await disclosure.getAttribute('open'), '');
  check('inert original HTML visible', await disclosure.locator('pre').isVisible());
  await page.keyboard.press('Space');
  check('Space closes source', await disclosure.getAttribute('open'), null);
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 950 }); await page.evaluate(() => scrollTo(0, 0));
    check('document fits ' + width, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    check('heading fits ' + width, await page.locator('h1').evaluate(el => {
      const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.height > 0;
    }));
    await page.screenshot({ path: path.join(out, 'top-' + width + '.png'), animations: 'disabled' });
    await page.locator('#item-2').scrollIntoViewIfNeeded();
    check('reading fits ' + width, await page.locator('#item-2 .reading').evaluate(el => {
      const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.height > 0;
    }));
    await page.screenshot({ path: path.join(out, 'reading-' + width + '.png'), animations: 'disabled' });
  }
  await page.emulateMedia({ media: 'print' });
  check('print hides download', await sourceLink.isVisible(), false);
  check('print hides raw disclosures', await disclosure.isVisible(), false);
  check('print retains reading', await page.locator('#item-2 .reading').isVisible());
  await page.pdf({ path: path.join(out, 'packet-print.pdf'), format: 'A4', printBackground: true });
  check('actual print PDF', fs.readFileSync(path.join(out, 'packet-print.pdf')).subarray(0, 5).toString(), '%PDF-');
  check('no browser network request', browserRequests, []); check('browser errors', errors, []);
  check('source preserved', sourcePaths.map(bind), receipt.sourceBefore);
  receipt.accepted = true;
} catch (error) {
  receipt.failure = String(error.stack || error); process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  receipt.finishedAt = new Date().toISOString();
  save('requests.json', JSON.stringify(requests, null, 2));
  receipt.outputFiles = fs.readdirSync(out).filter(name => fs.statSync(path.join(out, name)).isFile()).sort().map(name => {
    const b = fs.readFileSync(path.join(out, name)); return { name, bytes: b.length, sha256: sha(b) };
  });
  const result = Buffer.from(JSON.stringify(receipt, null, 2) + '\n');
  save('result.json', result);
  console.log(JSON.stringify({ path: path.join(out, 'result.json'), sha256: sha(result), accepted: receipt.accepted,
    checks: checks.length, passed: checks.filter(row => row.pass).length, failure: receipt.failure || null }));
}
