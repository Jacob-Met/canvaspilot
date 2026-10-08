import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { chromium } from "/home/jacob/hamon-b890f0b1bfcd/browser-tools/node_modules/playwright/index.mjs";

const [manifestPath, output] = process.argv.slice(2);
assert(manifestPath && output, "usage: receive-discussion.mjs MANIFEST NEW_OUTPUT");
const digest = data => createHash("sha256").update(data).digest("hex");
const manifestBytes = await fs.readFile(manifestPath);
const manifest = JSON.parse(manifestBytes);
await fs.mkdir(output, { recursive: false });
const proof = {
  started: new Date().toISOString(), phase: "preflight", success: false,
  manifest: { path: manifestPath, sha256: digest(manifestBytes) },
  receiver: { path: new URL(import.meta.url).pathname, sha256: digest(await fs.readFile(new URL(import.meta.url))) },
  runtime: { node: process.version, playwright: "1.64.0", chromium: "/snap/bin/chromium" },
  preflight: [], reports: [], requests: [], externalRequests: [], pageErrors: [], consoleErrors: [],
  limitations: [
    "Synthetic fixture documents only; no live Canvas credentials, session, or source requests.",
    "Browser receiving consumes the independent CLI-produced full/unread HTML and exact normalized oracles.",
    "Print qualification covers readable thread and scope with metadata details closed; complete normalized data is qualified by actual download.",
    "Network observation covers page-context resource attempts, not operating-system Chromium background telemetry."
  ]
};
const pins = [
  proof.receiver,
  { path: manifestPath, sha256: digest(manifestBytes) },
  ...(manifest.sourcePins || []),
  ...manifest.reports.flatMap(report => [report.html, report.oracle])
];
let context;
const fact = async (scope, name) => JSON.parse(await scope.locator(':scope > dl.facts > dd[data-field="' + name + '"]').textContent());
try {
  for (const pin of pins) {
    const bytes = await fs.readFile(pin.path);
    assert.equal(digest(bytes), pin.sha256, "frozen input mismatch: " + pin.path);
    proof.preflight.push({ ...pin, bytes: bytes.length });
  }
  const capacity = await fs.statfs(output);
  proof.capacityBefore = { availableBytes: capacity.bavail * capacity.bsize };
  assert(proof.capacityBefore.availableBytes >= 128 * 1024 * 1024, "Insufficient bounded browser capacity");
  const profile = path.join(output, "browser-profile");
  await fs.mkdir(profile);
  proof.phase = "browser";
  context = await chromium.launchPersistentContext(profile, {
    headless: true, executablePath: "/snap/bin/chromium",
    viewport: { width: 1100, height: 900 }, acceptDownloads: true, timeout: 60000
  });
  proof.runtime.browser = context.browser()?.version() || null;
  proof.freshProfile = profile;
  await context.route("**/*", async route => {
    const url = route.request().url();
    if (/^(https?|wss?):/i.test(url)) {
      proof.externalRequests.push({ url, resourceType: route.request().resourceType() });
      await route.abort("blockedbyclient");
    } else await route.continue();
  });
  const page = context.pages()[0] || await context.newPage();
  page.setDefaultTimeout(30000);
  page.on("pageerror", error => proof.pageErrors.push(error.message));
  page.on("console", item => { if (item.type() === "error") proof.consoleErrors.push(item.text()); });
  page.on("request", request => proof.requests.push({ url: request.url(), resourceType: request.resourceType() }));
  for (const spec of manifest.reports) {
    const oracle = JSON.parse(await fs.readFile(spec.oracle.path, "utf8"));
    const receipt = { name: spec.name, html: spec.html, oracle: spec.oracle, rows: [], widths: [], downloads: {}, print: {} };
    proof.reports.push(receipt);
    await page.emulateMedia({ media: "screen" });
    await page.setViewportSize({ width: 1100, height: 900 });
    await page.goto(pathToFileURL(spec.html.path).href, { waitUntil: "load" });
    assert.equal(await page.locator("h1").textContent(), oracle.topic.title);
    assert.equal(await page.locator("article.entry").count(), oracle.entries.length);
    assert.deepEqual(await page.locator("article.entry").evaluateAll(nodes => nodes.map(node => node.id)), oracle.entries.map((_, index) => "entry-" + index), "DOM order equals returned source order");
    assert.equal(await page.locator("#entries-nav ol li").count(), oracle.entries.length);
    assert.equal(await page.locator("script,iframe,object,embed,img,audio,video,form").count(), 0, "source content must remain inert");
    const eventAttributes = await page.locator("*").evaluateAll(nodes => nodes.flatMap(node =>
      [...node.attributes].filter(attribute => /^on/i.test(attribute.name)).map(attribute => ({ tag: node.tagName, name: attribute.name }))));
    assert.deepEqual(eventAttributes, []);
    const scope = page.locator('section[aria-labelledby="scope-title"]');
    for (const [key, value] of Object.entries({ selection: oracle.selection, ...oracle.counts, unmatched_unread_entries: oracle.unmatched_unread_entries })) {
      assert.deepEqual(await fact(scope, key), value, "scope field " + key);
    }
    const warningText = await scope.textContent();
    for (const warning of oracle.warnings) assert(warningText.includes(warning), "reader warning visible");
    const bodyText = await page.locator("body").innerText();
    assert.match(bodyText, /cached, eventually consistent/);
    assert.match(bodyText, /Unknown read states stay unknown/);
    for (const [index, row] of oracle.entries.entries()) {
      const article = page.locator("#entry-" + index);
      assert.equal(await article.getAttribute("aria-labelledby"), "entry-" + index + "-title");
      const metadata = Object.fromEntries(Object.entries(row).filter(([key]) => !["entry", "message_text", "author"].includes(key)));
      for (const [key, value] of Object.entries(metadata)) assert.deepEqual(await fact(article, key), value, spec.name + " entry " + index + " " + key);
      const classes = (await article.getAttribute("class")).split(/\s+/);
      assert.equal(classes.includes("context"), row.context_only);
      assert.equal(await article.locator(".badge").first().textContent(), "Read state: " + row.read_state);
      const heading = await article.locator("h3").textContent();
      if (row.entry.deleted === true) assert.match(heading, /Author unavailable for this deleted entry/);
      else if (row.author === null) assert.match(heading, /Author unavailable or ambiguous/);
      else if (typeof row.author.display_name === "string" && row.author.display_name) assert(heading.endsWith(row.author.display_name));
      const actualBody = await article.locator(":scope > p.body-text").textContent();
      if (row.entry.deleted === true) assert.equal(actualBody, "Deleted entry; body text is unavailable.");
      else if (row.message_text === null) assert.equal(actualBody, "The reader returned no body text.");
      else if (row.message_text === "") assert.equal(actualBody, "The reader returned empty text.");
      else assert.equal(actualBody, row.message_text);
      const parentIndex = row.parent_path === null ? -1 : oracle.entries.findIndex(item => JSON.stringify(item.path) === JSON.stringify(row.parent_path));
      const parentLink = article.locator(':scope > p.muted > a[href^="#entry-"]');
      if (parentIndex >= 0) assert.equal(await parentLink.getAttribute("href"), "#entry-" + parentIndex);
      else assert.equal(await parentLink.count(), 0);
      const original = article.locator(":scope > details");
      assert.deepEqual(JSON.parse(await original.locator('dd[data-field="entry"]').textContent()), row.entry);
      assert.deepEqual(JSON.parse(await original.locator('dd[data-field="author"]').textContent()), row.author);
      receipt.rows.push({ ordinal: index, path: row.path, parent_path: row.parent_path, context_only: row.context_only, read_state: row.read_state, bodyKind: row.entry.deleted === true ? "deleted" : row.message_text === null ? "missing" : row.message_text === "" ? "empty" : "text", parentHref: parentIndex >= 0 ? "#entry-" + parentIndex : null });
    }
    const parentLink = page.locator('article.entry > p.muted > a[href^="#entry-"]').first();
    if (await parentLink.count()) {
      const target = await parentLink.getAttribute("href");
      await parentLink.click();
      assert.equal(new URL(page.url()).hash, target);
      receipt.parentNavigation = { clicked: target, reached: new URL(page.url()).hash };
    }
    const summary = page.locator("details > summary").first();
    await summary.focus();
    await page.keyboard.press("Enter");
    assert.equal(await summary.evaluate(node => node.parentElement.open), true);
    await page.keyboard.press("Enter");
    assert.equal(await summary.evaluate(node => node.parentElement.open), false);
    receipt.keyboardDisclosure = { openedWithEnter: true, closedWithEnter: true };
    await page.evaluate(() => scrollTo(0, 0));
    if (spec.name === "full") {
      const screenshot = path.join(output, "full-desktop.png");
      await page.screenshot({ path: screenshot, fullPage: true });
      receipt.desktopScreenshot = { path: screenshot, sha256: digest(await fs.readFile(screenshot)) };
    }
    const [download] = await Promise.all([page.waitForEvent("download"), page.locator("#download-report").click()]);
    assert.equal(download.suggestedFilename(), "discussion-thread.json");
    const downloadPath = path.join(output, spec.name + "-discussion-thread.json");
    await download.saveAs(downloadPath);
    assert.equal(await download.failure(), null);
    const downloaded = await fs.readFile(downloadPath);
    assert.deepEqual(JSON.parse(downloaded.toString("utf8")), oracle);
    assert.equal(digest(downloaded), (await page.locator("#json-sha256").textContent()).trim());
    if (spec.jsonSha256) assert.equal(digest(downloaded), spec.jsonSha256, "download digest equals accepted CLI metadata");
    receipt.downloads = { path: downloadPath, suggestedFilename: download.suggestedFilename(), bytes: downloaded.length, sha256: digest(downloaded), equalsNormalizedOracle: true };
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      for (const open of [false, true]) {
        await page.locator("details").evaluateAll((nodes, expanded) => nodes.forEach(node => node.open = expanded), open);
        const dimensions = await page.evaluate(() => ({ viewport: innerWidth, htmlWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth }));
        assert(dimensions.htmlWidth <= dimensions.viewport + 1 && dimensions.bodyWidth <= dimensions.viewport + 1, spec.name + " horizontal overflow at " + width + " details=" + open);
        receipt.widths.push({ width, detailsOpen: open, ...dimensions, noHorizontalOverflow: true });
      }
    }
    await page.locator("details").evaluateAll(nodes => nodes.forEach(node => node.open = false));
    await page.evaluate(() => scrollTo(0, 0));
    {
      const screenshot = path.join(output, spec.name + "-narrow.png");
      await page.screenshot({ path: screenshot, fullPage: true });
      receipt.narrowScreenshot = { path: screenshot, sha256: digest(await fs.readFile(screenshot)) };
    }
    await page.setViewportSize({ width: 1100, height: 900 });
    await page.emulateMedia({ media: "print" });
    assert.equal(await page.locator("#download-report").isVisible(), false);
    assert.equal(await page.locator("#entries-nav").isVisible(), false);
    assert.equal(await page.locator('section[aria-labelledby="scope-title"]').isVisible(), true);
    for (const [index] of oracle.entries.entries()) assert.equal(await page.locator("#entry-" + index + " > p.body-text").isVisible(), true);
    const pdfPath = path.join(output, spec.name + ".pdf");
    await page.pdf({ path: pdfPath, format: "A4", printBackground: true, margin: { top: "12mm", right: "12mm", bottom: "12mm", left: "12mm" } });
    const text = execFileSync("/usr/bin/pdftotext", ["-layout", pdfPath, "-"], { encoding: "utf8" });
    const pdfInfo = execFileSync("/usr/bin/pdfinfo", [pdfPath], { encoding: "utf8" });
    const flattened = text.replace(/\s+/g, " ");
    assert.match(flattened, /Reading scope/);
    assert.match(flattened, /cached, eventually consistent/);
    assert(!flattened.includes("WITHHELD_DELETED_TEXT"), "deleted raw text stays outside readable print when original metadata is closed");
    for (const [index, row] of oracle.entries.entries()) {
      assert(flattened.includes("Entry " + (index + 1)), "printed entry heading " + index);
      if (row.message_text && row.entry.deleted !== true) assert(flattened.replace(/\s/g, "").includes(row.message_text.replace(/\s/g, "")), "printed readable body " + index);
    }
    await fs.writeFile(path.join(output, spec.name + "-print.txt"), text, { flag: "wx" });
    await fs.writeFile(path.join(output, spec.name + "-pdfinfo.txt"), pdfInfo, { flag: "wx" });
    receipt.print = { pdf: pdfPath, bytes: (await fs.stat(pdfPath)).size, sha256: digest(await fs.readFile(pdfPath)), readableEntries: oracle.entries.length, metadataDetailsClosed: true, navigationAndDownloadHidden: true, pdfInfo };
    await page.emulateMedia({ media: "screen" });
  }
  assert.deepEqual(proof.externalRequests, []);
  assert.deepEqual(proof.pageErrors, []);
  assert.deepEqual(proof.consoleErrors, []);
  for (const pin of pins) assert.equal(digest(await fs.readFile(pin.path)), pin.sha256, "input changed during browser receiving");
  proof.inputsUnchanged = true;
  proof.success = true;
  proof.phase = "complete";
} catch (error) {
  proof.failure = { message: error.message, stack: error.stack };
  process.exitCode = 1;
} finally {
  if (context) {
    try { await context.close(); proof.contextClosed = true; }
    catch (error) { proof.closeError = error.message; proof.success = false; process.exitCode = 1; }
  }
  proof.finished = new Date().toISOString();
  await fs.writeFile(path.join(output, "receiving.json"), JSON.stringify(proof, null, 2) + "\n", { flag: "wx" });
  console.log(JSON.stringify({ success: proof.success, phase: proof.phase, reportCount: proof.reports.length, failure: proof.failure?.message, output }));
}
