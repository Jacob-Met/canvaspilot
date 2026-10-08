/* Local study state only. No network, Canvas mutations, or browser storage. */
"use strict";
(() => {
  const SCHEMA = "canvaspilot.study_workspace/1";
  const MAX_NOTES = 50000;
  const $ = (id) => document.getElementById(id);
  const plain = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const fail = (message) => { throw new Error(message); };
  const text = (value, fallback = "") => typeof value === "string" ? value : fallback;
  function element(tag, value, className) {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = value;
    if (className) node.className = className;
    return node;
  }
  function sameKeys(value, expected) {
    return plain(value) && Object.keys(value).length === expected.length
      && expected.every((key) => Object.hasOwn(value, key));
  }
  function escapedJSON(value) {
    return JSON.stringify(value).replace(/[<>&\u2028\u2029]/g, (char) =>
      "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"));
  }
  function checkState(state, digest, assignments) {
    if (!sameKeys(state, ["source_sha256", "assignments"]) || state.source_sha256 !== digest
        || !sameKeys(state.assignments, assignments.map((item) => item.key))) {
      fail("The saved notes do not belong to this assignment snapshot.");
    }
    for (const item of assignments) {
      const local = state.assignments[item.key];
      if (!sameKeys(local, ["notes", "reviewed"]) || typeof local.notes !== "string"
          || local.notes.length > MAX_NOTES || typeof local.reviewed !== "boolean") {
        fail("A saved note or review marker is not valid. The original file has not been changed.");
      }
    }
  }
  function pointLabel(value) {
    if (typeof value === "number" && Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER) {
      return String(value);
    }
    if (typeof value === "string" && value.trim() !== "") return value;
    return null;
  }
  function safeCanvasLink(value, base) {
    try {
      const target = new URL(value);
      const origin = new URL(base);
      return ["http:", "https:"].includes(target.protocol) && target.origin === origin.origin
        && !target.username && !target.password ? target.href : null;
    } catch { return null; }
  }
  function addRubric(container, brief) {
    const settings = plain(brief.rubric_settings) ? brief.rubric_settings : {};
    const heading = element("h3", "Rubric");
    container.append(heading);
    if (text(settings.title)) container.append(element("p", settings.title, "rubric-intro"));
    const grading = brief.use_rubric_for_grading === true
      ? "Canvas reports that this rubric is used for grading."
      : brief.use_rubric_for_grading === false
        ? "Canvas reports that this rubric is advisory."
        : "Whether this rubric is used for grading was not reported.";
    container.append(element("p", grading, "rubric-intro"));
    if (brief.rubric === null) {
      container.append(element("p", "A rubric was not supplied in this brief. Check Canvas for current requirements.", "rubric-intro"));
    } else if (brief.rubric.length === 0) {
      container.append(element("p", "The brief supplied an empty rubric.", "rubric-intro"));
    } else {
      const unknownHidePoints = settings.hide_points != null && typeof settings.hide_points !== "boolean";
      const unknownHideTotal = settings.hide_score_total != null && typeof settings.hide_score_total !== "boolean";
      const hidePoints = settings.hide_points === true || unknownHidePoints;
      const hideTotal = hidePoints || settings.hide_score_total === true || unknownHideTotal;
      if (hidePoints) container.append(element("p", unknownHidePoints
        ? "The rubric point-display setting is unavailable; point labels are omitted."
        : "Rubric point labels are hidden by the supplied display settings.", "rubric-intro"));
      if (!hidePoints && hideTotal) container.append(element("p", "The rubric total is not displayed.", "rubric-intro"));
      if (settings.free_form_criterion_comments === true) {
        container.append(element("p", "Free-form rubric comments are enabled (reported by Canvas).", "rubric-intro"));
      }
      brief.rubric.forEach((criterion, index) => {
        if (!plain(criterion)) fail("A rubric criterion is not a valid snapshot record.");
        const card = element("section", undefined, "criterion");
        card.append(element("h4", text(criterion.description) || "Criterion " + (index + 1)));
        if (text(criterion.long_description)) card.append(element("p", criterion.long_description, "long-text"));
        const metadata = [];
        const points = pointLabel(criterion.points);
        if (!hidePoints && points !== null) metadata.push("Criterion points: " + points);
        if (criterion.criterion_use_range === true) metadata.push("Rating ranges enabled");
        if (criterion.ignore_for_scoring === true) metadata.push("Excluded from scoring (reported)");
        if (metadata.length) card.append(element("p", metadata.join(" · "), "criterion-meta"));
        if (Array.isArray(criterion.ratings) && criterion.ratings.length) {
          const ratings = element("ul", undefined, "ratings");
          criterion.ratings.forEach((rating, ratingIndex) => {
            if (!plain(rating)) fail("A rubric rating is not a valid snapshot record.");
            const li = element("li", undefined, "rating");
            li.append(element("strong", text(rating.description) || "Rating " + (ratingIndex + 1)));
            if (text(rating.long_description)) li.append(element("p", rating.long_description, "long-text"));
            const ratingPoints = pointLabel(rating.points);
            if (!hidePoints && ratingPoints !== null) li.append(element("span", ratingPoints + " points", "rating-points"));
            ratings.append(li);
          });
          card.append(ratings);
        } else {
          card.append(element("p", Array.isArray(criterion.ratings)
            ? "The criterion supplied an empty ratings list."
            : "Rating details were not supplied.", "criterion-meta"));
        }
        container.append(card);
      });
      const total = pointLabel(settings.points_possible);
      if (!hideTotal && total !== null) container.append(element("p", "Reported rubric total: " + total + " points", "rubric-intro"));
    }
    if (Array.isArray(brief.rubric_warnings) && brief.rubric_warnings.length) {
      const details = element("details", undefined, "notice");
      details.open = true;
      details.append(element("summary", "Some rubric details were unavailable"));
      const list = element("ul");
      brief.rubric_warnings.forEach((warning) => list.append(element("li", text(warning))));
      details.append(list);
      container.append(details);
    }
  }
  async function openWorkspace() {
    const envelope = JSON.parse($("workspace-data").textContent);
    if (!sameKeys(envelope, ["schema_id", "source", "source_sha256", "state"])
        || envelope.schema_id !== SCHEMA || typeof envelope.source !== "string"
        || !/^[0-9a-f]{64}$/.test(envelope.source_sha256)) fail("This is not a supported study workspace.");
    const bytes = new TextEncoder().encode(envelope.source);
    if (bytes.length > 4 * 1024 * 1024) fail("The assignment snapshot exceeds the supported size.");
    if (!globalThis.crypto?.subtle) fail("This browser cannot verify the snapshot. Open this file in a modern browser with Web Crypto support.");
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
      .map((byte) => byte.toString(16).padStart(2, "0")).join("");
    if (digest !== envelope.source_sha256) fail("The assignment snapshot has changed. Your file and notes have not been changed.");
    const source = JSON.parse(envelope.source);
    if (source.schema_id !== SCHEMA || typeof source.course_id !== "string"
        || !Array.isArray(source.assignments) || source.assignments.length < 1
        || source.assignments.length > 25) fail("The assignment selection is not valid.");
    const keys = new Set();
    for (const item of source.assignments) {
      if (!plain(item) || !plain(item.brief) || typeof item.brief.assignment_id !== "string"
          || item.brief.course_id !== source.course_id
          || item.key !== source.course_id + ":" + item.brief.assignment_id || keys.has(item.key)
          || !(item.brief.rubric === null || Array.isArray(item.brief.rubric))) {
        fail("The assignment snapshot contains an ambiguous selection.");
      }
      keys.add(item.key);
    }
    const state = envelope.state;
    checkState(state, digest, source.assignments);
    const nav = $("assignment-nav");
    const main = $("assignments");
    nav.replaceChildren();
    main.replaceChildren();
    const localViews = new Map();
    let changedSinceDownload = false;
    function updateReviewProgress() {
      let reviewed = 0;
      for (const item of source.assignments) {
        const yes = state.assignments[item.key].reviewed;
        if (yes) reviewed += 1;
        const view = localViews.get(item.key);
        view.navState.textContent = yes ? "Reviewed locally" : "Still to review";
        view.reviewState.textContent = yes ? "My review marker: reviewed locally." : "My review marker: not reviewed locally.";
      }
      $("review-progress").textContent = reviewed + " of " + source.assignments.length + " reviewed locally";
    }
    function changed() {
      changedSinceDownload = true;
      $("save-status").textContent = "You have edits in this tab. Save a working copy to keep them.";
    }
    source.assignments.forEach((item, index) => {
      const brief = item.brief;
      const local = state.assignments[item.key];
      const title = text(brief.title) || "Assignment " + brief.assignment_id;
      const sectionId = "assignment-" + index;
      const navItem = element("li");
      const navLink = element("a");
      navLink.href = "#" + sectionId;
      navLink.append(element("span", String(index + 1).padStart(2, "0") + "  " + title, "nav-title"));
      const navState = element("span", "", "nav-state");
      navLink.append(navState);navItem.append(navLink);nav.append(navItem);
      const article = element("article", undefined, "assignment");article.id = sectionId;
      article.setAttribute("aria-labelledby", sectionId + "-title");
      article.append(element("p", "Assignment " + brief.assignment_id, "eyebrow"));
      const heading = element("h2", title);heading.id = sectionId + "-title";article.append(heading);
      const metadata = element("div", undefined, "assignment-meta");
      metadata.append(element("span", "Due (reported): " + (text(brief.due_at) || "not supplied")));
      const points = pointLabel(brief.points_possible);
      metadata.append(element("span", "Assignment points: " + (points === null ? "not supplied" : points)));
      const types = Array.isArray(brief.submission_types) ? brief.submission_types.join(", ") || "empty list supplied" : "not supplied";
      metadata.append(element("span", "Submission types: " + types));
      article.append(metadata, element("h3", "Prompt"));
      article.append(element("div", text(brief.prompt) || "No prompt text was supplied by this brief.", "prompt"));
      const link = safeCanvasLink(brief.html_url, source.source_base_url);
      if (link) {
        const a = element("a", "Open the assignment in Canvas", "source-link");
        a.href = link;a.target = "_blank";a.rel = "noopener noreferrer";article.append(a);
      }
      addRubric(article, brief);
      const notes = element("section", undefined, "notes-area");
      const label = element("label", "My study notes", "notes-label");label.htmlFor = sectionId + "-notes";
      const help = element("p", "Questions, plans, and reminders in your own words. Save a working copy before closing this tab.", "notes-help");
      help.id = sectionId + "-notes-help";
      const textarea = element("textarea");textarea.id = sectionId + "-notes";textarea.rows = 7;textarea.maxLength = MAX_NOTES;textarea.value = local.notes;
      textarea.setAttribute("aria-describedby", help.id);
      const printNotes = element("div", local.notes || "No study notes entered.", "print-notes");
      const toggleLabel = element("label", undefined, "review-toggle");
      const checkbox = element("input");checkbox.type = "checkbox";checkbox.checked = local.reviewed;
      checkbox.id = sectionId + "-review";toggleLabel.htmlFor = checkbox.id;
      toggleLabel.append(checkbox, element("span", "I have reviewed this assignment locally"));
      const reviewState = element("p", "", "review-state");
      notes.append(label, help, textarea, printNotes, toggleLabel, reviewState);article.append(notes);main.append(article);
      localViews.set(item.key, {navState, reviewState});
      textarea.addEventListener("input", () => {local.notes = textarea.value;printNotes.textContent = local.notes || "No study notes entered.";changed();});
      checkbox.addEventListener("change", () => {local.reviewed = checkbox.checked;changed();updateReviewProgress();});
    });
    updateReviewProgress();
    $("selection-summary").textContent = "Course " + source.course_id + " · " + source.assignments.length + " selected assignment" + (source.assignments.length === 1 ? "" : "s");
    $("snapshot-provenance").textContent = "Exported " + text(source.exported_at, "at an unreported time") + " · Snapshot " + digest.slice(0, 16);
    $("snapshot-provenance").title = "SHA-256 " + digest;
    $("save-status").textContent = "Edits stay in this tab until you save a working copy.";
    $("workspace").hidden = false;
    $("error").hidden = true;
    $("save-copy").disabled = false;
    $("print-copy").disabled = false;
    $("print-copy").addEventListener("click", () => window.print());
    $("save-copy").addEventListener("click", () => {
      let url = null;
      let link = null;
      try {
        checkState(state, digest, source.assignments);
        const copy = document.documentElement.cloneNode(true);
        // Every downloaded copy starts closed until its source and notes verify.
        copy.querySelector("#workspace").hidden = true;
        for (const id of ["assignment-nav", "assignments", "review-progress", "snapshot-provenance", "error"]) {
          copy.querySelector("#" + id).textContent = "";
        }
        copy.querySelector("#snapshot-provenance").removeAttribute("title");
        copy.querySelector("#error").hidden = true;
        copy.querySelector("#save-copy").disabled = true;
        copy.querySelector("#print-copy").disabled = true;
        copy.querySelector("#selection-summary").textContent = "Opening snapshot…";
        copy.querySelector("#save-status").textContent = "Edits stay in this tab until you save a working copy.";
        copy.querySelector("#workspace-data").textContent = escapedJSON({
          schema_id: SCHEMA, source: envelope.source, source_sha256: digest, state,
        });
        url = URL.createObjectURL(new Blob(["<!doctype html>\n" + copy.outerHTML], {type: "text/html;charset=utf-8"}));
        link = element("a");
        link.href = url;link.download = "canvaspilot-study-" + source.course_id + "-" + digest.slice(0, 12) + "-working.html";
        document.body.append(link);link.click();link.remove();link = null;
        const revoke = url;setTimeout(() => URL.revokeObjectURL(revoke), 1000);url = null;
        changedSinceDownload = false;
        $("save-status").textContent = "Download requested. Keep the downloaded working copy and reopen it to continue later.";
      } catch (error) {
        if (link) link.remove();
        if (url) URL.revokeObjectURL(url);
        $("save-status").textContent = "The working copy could not be prepared. Your notes are still in this tab. " + error.message;
      }
    });
    window.addEventListener("beforeunload", (event) => {
      if (changedSinceDownload) {event.preventDefault();event.returnValue = "";}
    });
  }
  openWorkspace().catch((error) => {
    $("workspace").hidden = true;
    $("save-copy").disabled = true;
    $("print-copy").disabled = true;
    $("error").textContent = error.message || "This workspace could not be opened. The file has not been changed.";
    $("error").hidden = false;
    $("selection-summary").textContent = "Workspace unavailable";
    $("save-status").textContent = "Keep this file while you restore an earlier working copy or a fresh export.";
  });
})();
