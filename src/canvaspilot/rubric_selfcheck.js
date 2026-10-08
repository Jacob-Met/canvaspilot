(() => {
"use strict";
const SCHEMA = "canvaspilot.rubric_selfcheck/1";
const MAX_SOURCE = 4 * 1024 * 1024, MAX_STATE = 2 * 1024 * 1024;
const LABELS = {unreviewed: "Unreviewed", "needs-work": "Needs work", checked: "Checked locally"};
const enc = new TextEncoder();
const data = document.getElementById("selfcheck-data");
const workspace = document.getElementById("workspace");
const save = document.getElementById("save-copy"), print = document.getElementById("print-copy");
const message = document.getElementById("status"), error = document.getElementById("error");
const summary = document.getElementById("summary");
let envelope, source, state, expected, rows;
const exact = (v, keys) => v !== null && typeof v === "object" && !Array.isArray(v)
  && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
function fail(text) { throw new Error(text); }
function validateSource(doc) {
  if (!exact(doc, ["schema_id", "course_id", "source_base_url", "exported_at", "reader", "source_boundary", "assignments"])
      || doc.schema_id !== SCHEMA || typeof doc.course_id !== "string" || !/^[1-9][0-9]{0,18}$/.test(doc.course_id)
      || !Array.isArray(doc.assignments) || doc.assignments.length < 1 || doc.assignments.length > 25) fail("Unsupported source snapshot.");
  const keys = [], assignments = new Set(); let ratings = 0;
  for (const item of doc.assignments) {
    if (!exact(item, ["key", "brief"]) || !item.brief || typeof item.brief !== "object") fail("Invalid assignment source.");
    const b = item.brief;
    if (b.course_id !== doc.course_id || typeof b.assignment_id !== "string" || !/^[1-9][0-9]{0,18}$/.test(b.assignment_id)
        || item.key !== doc.course_id + ":" + b.assignment_id || assignments.has(item.key)) fail("Mismatched assignment identity.");
    assignments.add(item.key);
    if (b.rubric !== null && !Array.isArray(b.rubric)) fail("Invalid supplied rubric.");
    for (const [i, criterion] of (b.rubric || []).entries()) {
      if (criterion === null || typeof criterion !== "object" || Array.isArray(criterion)) fail("Invalid supplied criterion.");
      if (criterion.ratings != null && (!Array.isArray(criterion.ratings) || criterion.ratings.some(r => r === null || typeof r !== "object" || Array.isArray(r)))) fail("Invalid supplied ratings.");
      ratings += criterion.ratings?.length || 0;
      keys.push(item.key + ":" + i);
      if (keys.length > 500 || ratings > 5000) fail("The source exceeds the self-check limits.");
    }
  }
  return keys;
}
function validateState(value) {
  if (!exact(value, ["source_sha256", "criteria"]) || value.source_sha256 !== envelope.source_sha256
      || !exact(value.criteria, expected)) fail("Self-checks do not belong to this exact source.");
  for (const key of expected) {
    const item = value.criteria[key];
    if (!exact(item, ["status", "notes"]) || !Object.hasOwn(LABELS, item.status)
        || typeof item.status !== "string" || typeof item.notes !== "string" || item.notes.length > 5000) fail("Invalid local status or evidence note.");
    // Refuse lone surrogates instead of letting UTF-8 replacement change a note.
    if (item.notes.isWellFormed && !item.notes.isWellFormed()) fail("An evidence note contains an unsupported Unicode surrogate.");
  }
  if (enc.encode(JSON.stringify(value)).length > MAX_STATE) fail("Local notes exceed the 2 MiB limit. Shorten them before saving; nothing was truncated.");
  return value;
}
function reflect(key) {
  const row = rows.get(key), item = state.criteria[key];
  row.querySelector('[data-role="print-status"]').textContent = LABELS[item.status];
  row.querySelector('[data-role="print-notes"]').textContent = item.notes || "No evidence note recorded.";
  row.querySelector('[data-role="count"]').textContent = item.notes.length.toLocaleString() + " / 5,000 note units";
}
function summarize() {
  const counts = {unreviewed: 0, "needs-work": 0, checked: 0};
  for (const x of Object.values(state.criteria)) if (Object.hasOwn(counts, x.status)) counts[x.status]++;
  summary.textContent = expected.length + " criteria · " + counts.checked + " checked locally · " + counts["needs-work"] + " need work · " + counts.unreviewed + " unreviewed";
}
function capture() {
  const result = {source_sha256: envelope.source_sha256, criteria: {}};
  for (const [key, row] of rows) result.criteria[key] = {
    status: row.querySelector('[data-role="status"]').value,
    notes: row.querySelector('[data-role="notes"]').value
  };
  return validateState(result);
}
function embedded(value) {
  return JSON.stringify(value).replaceAll("&", "\\u0026").replaceAll("<", "\\u003c").replaceAll(">", "\\u003e")
    .replaceAll("\u2028", "\\u2028").replaceAll("\u2029", "\\u2029");
}
function saveCopy() {
  let url = null, anchor = null;
  try {
    const captured = capture();
    const copy = document.documentElement.cloneNode(true);
    copy.querySelector("#selfcheck-data").textContent = embedded({...envelope, state: captured});
    copy.querySelector("#workspace").hidden = true;
    copy.querySelector("#error").hidden = true;
    for (const el of copy.querySelectorAll("button,select,textarea")) el.disabled = true;
    copy.querySelector("#summary").textContent = "Checking the saved source and local notes…";
    const bytes = "<!doctype html>\n" + copy.outerHTML + "\n";
    url = URL.createObjectURL(new Blob([bytes], {type: "text/html;charset=utf-8"}));
    anchor = document.createElement("a"); anchor.href = url; anchor.download = "rubric-selfcheck-working.html";
    document.body.append(anchor); anchor.click();
    state = captured;
    message.textContent = "Working-copy download requested. Confirm that the file was saved before closing; this tab does not autosave.";
    const held = url; setTimeout(() => URL.revokeObjectURL(held), 60000); url = null;
  } catch (e) {
    message.textContent = "Working copy was not prepared: " + e.message + " Your work remains in this tab.";
  } finally { anchor?.remove(); if (url) URL.revokeObjectURL(url); }
}
async function open() {
  try {
    envelope = JSON.parse(data.textContent);
    if (!exact(envelope, ["schema_id", "source", "source_sha256", "state"]) || envelope.schema_id !== SCHEMA
        || typeof envelope.source !== "string" || !/^[a-f0-9]{64}$/.test(envelope.source_sha256)) fail("Unsupported working copy.");
    if (enc.encode(envelope.source).length > MAX_SOURCE) fail("The saved source exceeds 4 MiB.");
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(envelope.source))), x => x.toString(16).padStart(2, "0")).join("");
    if (digest !== envelope.source_sha256) fail("The saved source checksum does not match.");
    source = JSON.parse(envelope.source); expected = validateSource(source);
    const cards = Array.from(workspace.querySelectorAll("[data-criterion-key]"));
    if (!same(cards.map(x => x.dataset.criterionKey), expected)) fail("The displayed criteria do not match the saved source order.");
    rows = new Map(cards.map(row => [row.dataset.criterionKey, row]));
    state = structuredClone(validateState(envelope.state));
    for (const [key, row] of rows) {
      const status = row.querySelector('[data-role="status"]'), notes = row.querySelector('[data-role="notes"]');
      status.value = state.criteria[key].status; notes.value = state.criteria[key].notes;
      if (status.value !== state.criteria[key].status || notes.value !== state.criteria[key].notes) fail("The browser could not restore an exact self-check value.");
      status.disabled = notes.disabled = false;
      status.addEventListener("change", () => { state.criteria[key].status = status.value; reflect(key); summarize(); message.textContent = "Unsaved changes in this tab. Save a working copy to keep them."; });
      notes.addEventListener("input", () => { state.criteria[key].notes = notes.value; reflect(key); message.textContent = "Unsaved changes in this tab. Save a working copy to keep them."; });
      reflect(key);
    }
    summarize(); workspace.hidden = false; save.disabled = print.disabled = false;
    save.addEventListener("click", saveCopy);
    print.addEventListener("click", () => {
      try { state = capture(); for (const key of expected) reflect(key); window.print(); }
      catch (e) { message.textContent = "Print was not prepared: " + e.message + " Your work remains in this tab."; }
    });
    window.addEventListener("beforeprint", () => { for (const key of expected) reflect(key); });
    message.textContent = "Source and self-checks verified. Changes stay in this tab until you save a working copy.";
  } catch (e) {
    workspace.hidden = true; save.disabled = print.disabled = true;
    error.textContent = "This working copy could not be opened: " + e.message + " The file has not been changed.";
    error.hidden = false; summary.textContent = "Working copy unavailable";
  }
}
open();
})();
