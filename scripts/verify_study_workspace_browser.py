"""Exercise the exported study workspace in native Chromium using synthetic briefs.

Run from the repository's development environment:
  python scripts/verify_study_workspace_browser.py --output /new/evidence/path
No Canvas account is contacted. Browser contexts stay offline throughout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canvaspilot.study_workspace import build_study_workspace
from tests.test_study_workspace import envelope
from tests.test_study_workspace_cli import command, fixture_server

PATTERN = re.compile(
    r'(<script id="workspace-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def inventory():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return {
        name: digest(ROOT / name)
        for name in sorted(set(result.stdout.decode().strip("\0").split("\0")))
        if name and (ROOT / name).is_file()
    }


def escaped_json(value):
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    for char in ("<", ">", "&", "\u2028", "\u2029"):
        text = text.replace(char, "\\u" + format(ord(char), "04x"))
    return text


def revised_envelope(path, original, value):
    text, count = PATTERN.subn(
        lambda match: match[1] + escaped_json(value) + match[3],
        original.read_text(),
    )
    assert count == 1
    path.write_text(text)
    return path


class BrowserRun:
    def __init__(self, browser, output, receipt):
        self.browser = browser
        self.output = output
        self.receipt = receipt
        self.contexts = []

    def open(
        self,
        label,
        path,
        *,
        mobile=False,
        refused=False,
        pending=False,
        digest_error=False,
    ):
        from playwright.sync_api import expect

        context = self.browser.new_context(
            offline=True,
            accept_downloads=True,
            viewport={"width": 320, "height": 568}
            if mobile
            else {"width": 1280, "height": 960},
            is_mobile=mobile,
            has_touch=mobile,
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        self.contexts.append(context)
        if pending:
            context.add_init_script(
                "crypto.subtle.digest = () => new Promise(() => {});"
            )
        if digest_error:
            context.add_init_script(
                "crypto.subtle.digest = () => Promise.reject(new Error('controlled digest failure'));"
            )
        evidence = {
            "label": label,
            "file": path.name,
            "file_before": digest(path),
            "http_requests": [],
            "page_errors": [],
            "console_errors": [],
        }
        self.receipt["pages"].append(evidence)
        context.on(
            "request",
            lambda request: (
                evidence["http_requests"].append(
                    {"method": request.method, "url": request.url}
                )
                if request.url.startswith(("http://", "https://"))
                else None
            ),
        )
        page = context.new_page()
        page.on("pageerror", lambda error: evidence["page_errors"].append(str(error)))
        page.on(
            "console",
            lambda message: (
                evidence["console_errors"].append(message.text)
                if message.type == "error"
                else None
            ),
        )
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.goto(path.as_uri(), wait_until="load")
        if pending:
            expect(page.locator("#workspace")).to_be_hidden()
            expect(page.locator("#save-copy")).to_be_disabled()
            expect(page.locator("#print-copy")).to_be_disabled()
            expect(page.locator("article.assignment")).to_have_count(0)
        elif refused:
            expect(page.locator("#error")).to_be_visible()
            expect(page.locator("#workspace")).to_be_hidden()
            expect(page.locator("#save-copy")).to_be_disabled()
            expect(page.locator("#print-copy")).to_be_disabled()
        else:
            expect(page.locator("#workspace")).to_be_visible()
            expect(page.locator("#error")).to_be_hidden()
            expect(page.locator("#save-copy")).to_be_enabled()
        evidence["file_after_open"] = digest(path)
        assert evidence["file_after_open"] == evidence["file_before"]
        return page, evidence

    def save(self, page, name):
        with page.expect_download() as event:
            page.get_by_role("button", name="Save working copy", exact=True).click()
        download = event.value
        path = self.output / name
        download.save_as(path)
        assert download.failure() is None
        return path

    def passed(self, name, **details):
        self.receipt["cases"].append({"name": name, "passed": True, **details})
        print("PASS", name, flush=True)

    def finish(self):
        for context in self.contexts:
            context.close()
        for page in self.receipt["pages"]:
            assert not page["http_requests"], page
            assert not page["page_errors"], page
            assert not page["console_errors"], page


def exercise(browser, output, receipt):
    from playwright.sync_api import expect

    run = BrowserRun(browser, output, receipt)
    original = output / "selected-study.html"
    with fixture_server() as (base, requests):
        result = command(base, original)
    (output / "producer.stdout.txt").write_text(result.stdout)
    (output / "producer.stderr.txt").write_text(result.stderr)
    (output / "producer-requests.json").write_text(
        json.dumps(requests, indent=2) + "\n"
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert len(requests) == 3 and all(item["method"] == "GET" for item in requests)
    doc = envelope(original.read_bytes())
    source_before = doc["source"]
    run.passed("actual_cli_selected_three_gets", report=json.loads(result.stdout))

    page, _ = run.open("desktop", original)
    expect(page.locator("article.assignment")).to_have_count(3)
    expect(page.locator("#selection-summary")).to_have_text(
        "Course 17 · 3 selected assignments"
    )
    first = page.locator("#assignment-0")
    second = page.locator("#assignment-1")
    third = page.locator("#assignment-2")
    expect(first.locator("h2")).to_have_text("Research plan & evidence map")
    expect(first.locator(".assignment-meta")).to_contain_text("Assignment points: 0")
    expect(first.locator(".assignment-meta")).to_contain_text(
        "2026-11-20T15:30:00-08:00"
    )
    expect(first.locator(".prompt")).to_contain_text(
        "Literal notation: <claim> → evidence."
    )
    expect(first).to_contain_text("Criterion points: 5.5")
    expect(first).to_contain_text("Rating ranges enabled")
    expect(first).to_contain_text("Excluded from scoring (reported)")
    expect(first.locator(".notice")).to_be_visible()
    assert "17.5" not in first.inner_text()
    assert [
        node.strip() for node in first.locator(".rating-points").all_text_contents()
    ] == ["5.5 points", "2.5 points", "0 points"]
    expect(second).to_contain_text("this rubric is advisory")
    for hidden_points in ("987654.125", "876543.125", "765432.125"):
        assert hidden_points not in second.inner_text()
    expect(third.locator("h2")).to_have_text("Assignment 83")
    expect(third).to_contain_text("Assignment points: not supplied")
    expect(third).to_contain_text("No prompt text was supplied")
    expect(third).to_contain_text("empty rubric")
    assert "UNEXPORTED_" not in page.locator("body").inner_text()
    assert page.locator("img, iframe, object").count() == 0
    run.passed("brief_and_rubric_projection_no_inferred_scores")

    notes = (
        "Question: Which observation would change my conclusion?\n"
        "Plan: compare the two sources before choosing an example.\n"
        "Bring a draft evidence map to class; keep <claim> as literal notation."
    )
    page.locator("#assignment-0-notes").fill(notes)
    page.locator("#assignment-0-review").check()
    page.locator("#assignment-1-notes").fill(
        "Sketch the delay before describing the feedback loop."
    )
    expect(page.locator("#review-progress")).to_have_text("1 of 3 reviewed locally")
    expect(page.locator("#save-status")).to_contain_text("edits in this tab")
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=output / "desktop.png", full_page=True)
    working = run.save(page, "working-copy.html")
    saved = envelope(working.read_bytes())
    assert saved["source"] == source_before
    assert saved["source_sha256"] == doc["source_sha256"]
    assert saved["state"]["assignments"]["17:81"] == {"notes": notes, "reviewed": True}
    expect(page.locator("#save-status")).to_contain_text("Download requested")
    run.open("saved-copy-pending-verification", working, pending=True)
    run.passed("saved_copy_waits_for_snapshot_verification")
    digest_failed, _ = run.open(
        "saved-copy-digest-rejection", working, refused=True, digest_error=True
    )
    expect(digest_failed.locator("#error")).to_have_text("controlled digest failure")
    assert envelope(working.read_bytes())["state"] == saved["state"]
    run.passed("saved_copy_digest_rejection_keeps_notes_and_file")
    fresh, _ = run.open("working-reopen", working)
    expect(fresh.locator("#assignment-0-notes")).to_have_value(notes)
    expect(fresh.locator("#assignment-0-review")).to_be_checked()
    expect(fresh.locator("#review-progress")).to_have_text("1 of 3 reviewed locally")
    expect(fresh.locator("article.assignment")).to_have_count(3)
    fresh.locator("#assignment-2-review").check()
    second_copy = run.save(fresh, "second-working-copy.html")
    again, _ = run.open("second-generation", second_copy)
    expect(again.locator("article.assignment")).to_have_count(3)
    expect(again.locator("#review-progress")).to_have_text("2 of 3 reviewed locally")
    expect(again.locator("#assignment-0-notes")).to_have_value(notes)
    assert envelope(second_copy.read_bytes())["source"] == source_before
    run.passed(
        "download_and_two_fresh_offline_reopens", source_sha256=doc["source_sha256"]
    )

    fresh.evaluate(
        "() => { window.__printCalls = 0; window.print = () => { window.__printCalls += 1; }; }"
    )
    fresh.get_by_role("button", name="Print", exact=True).click()
    assert fresh.evaluate("window.__printCalls") == 1
    fresh.emulate_media(media="print")
    expect(fresh.locator("#assignment-0-notes")).to_be_hidden()
    expect(fresh.locator("#assignment-0 .print-notes")).to_have_text(notes)
    assert fresh.locator("#assignment-0 .print-notes").is_visible()
    fresh.pdf(path=output / "study-print.pdf", format="A4", print_background=True)
    fresh.emulate_media(media="screen")
    run.passed(
        "print_button_and_real_chromium_pdf", pdf=digest(output / "study-print.pdf")
    )

    long_notes = (
        "\n".join(
            f"Study line {index:03d}: compare evidence, identify uncertainty, and retain this complete sentence."
            for index in range(1, 121)
        )
        + "\nEND OF LONG STUDY NOTE"
    )
    fresh.locator("#assignment-0-notes").fill(long_notes)
    fresh.emulate_media(media="print")
    expect(fresh.locator("#assignment-0 .print-notes")).to_have_text(long_notes)
    fresh.pdf(path=output / "long-notes-print.pdf", format="A4", print_background=True)
    (output / "long-notes-expected.txt").write_text(long_notes)
    run.passed(
        "long_note_real_pdf_generated", pdf=digest(output / "long-notes-print.pdf")
    )

    phone, _ = run.open("mobile-touch", original, mobile=True)
    assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    save_box = phone.locator("#save-copy").bounding_box()
    assert save_box and save_box["height"] >= 44
    phone.locator("#assignment-1-notes").fill(
        "Mobile reminder: start with the feedback diagram."
    )
    phone.locator("#assignment-1-review").tap()
    expect(phone.locator("#review-progress")).to_have_text("1 of 3 reviewed locally")
    phone.locator("#assignment-1 .notes-area").screenshot(
        path=output / "mobile-notes.png"
    )
    phone.evaluate("window.scrollTo(0, 0)")
    phone.screenshot(path=output / "mobile-header.png")
    assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    run.passed("phone_320_touch_and_no_horizontal_overflow")

    keyboard, _ = run.open("keyboard", original)
    focus_path = []
    for _ in range(18):
        keyboard.keyboard.press("Tab")
        active = keyboard.evaluate(
            "({id:document.activeElement.id,tag:document.activeElement.tagName})"
        )
        focus_path.append(active)
        if active["id"] == "assignment-0-notes":
            break
    assert focus_path[-1]["id"] == "assignment-0-notes", focus_path
    keyboard.keyboard.insert_text("Keyboard-only study note.")
    keyboard.keyboard.press("Tab")
    assert keyboard.evaluate("document.activeElement.id") == "assignment-0-review"
    keyboard.keyboard.press("Space")
    expect(keyboard.locator("#assignment-0-review")).to_be_checked()
    for _ in range(18):
        keyboard.keyboard.press("Shift+Tab")
        if keyboard.evaluate("document.activeElement.id") == "save-copy":
            break
    assert keyboard.evaluate("document.activeElement.id") == "save-copy"
    with keyboard.expect_download() as event:
        keyboard.keyboard.press("Enter")
    event.value.save_as(output / "keyboard-working.html")
    key_doc = envelope((output / "keyboard-working.html").read_bytes())
    assert key_doc["state"]["assignments"]["17:81"] == {
        "notes": "Keyboard-only study note.",
        "reviewed": True,
    }
    run.passed("keyboard_notes_review_and_download", focus_path=focus_path)

    bad_values = []
    changed_source = json.loads(json.dumps(saved))
    changed_source["source"] = changed_source["source"].replace(
        "Research plan", "Revised plan", 1
    )
    bad_values.append(("changed-source", changed_source, "snapshot has changed"))
    wrong_hash = json.loads(json.dumps(doc))
    wrong_hash["state"]["source_sha256"] = "0" * 64
    bad_values.append(("foreign-notes", wrong_hash, "do not belong"))
    wrong_key = json.loads(json.dumps(doc))
    wrong_key["state"]["assignments"]["17:901"] = wrong_key["state"]["assignments"].pop(
        "17:81"
    )
    bad_values.append(("foreign-assignment", wrong_key, "do not belong"))
    wrong_type = json.loads(json.dumps(doc))
    wrong_type["state"]["assignments"]["17:81"]["reviewed"] = "yes"
    bad_values.append(("invalid-review-marker", wrong_type, "not valid"))
    too_long = json.loads(json.dumps(doc))
    too_long["state"]["assignments"]["17:81"]["notes"] = "x" * 50001
    bad_values.append(("oversized-note", too_long, "not valid"))
    for label, value, expected in bad_values:
        template = working if label == "changed-source" else original
        path = revised_envelope(output / (label + ".html"), template, value)
        before = digest(path)
        refused, _ = run.open(label, path, refused=True)
        expect(refused.locator("#error")).to_contain_text(expected)
        assert digest(path) == before
        run.passed(label + "_refused_with_file_preserved")

    source = json.loads(source_before)
    brief = source["assignments"][0]["brief"]
    title = "</script><script>window.__unexpected_execution=7</script> __STYLE__"
    literal = '<img src="https://unexpected.invalid/pixel" onerror="window.__unexpected_execution=8">'
    brief["title"] = title
    brief["prompt"] = literal
    brief["html_url"] = "javascript:window.__unexpected_execution=9"
    brief["rubric"][0]["description"] = (
        "<svg onload='window.__unexpected_execution=10'>"
    )
    content, _ = build_study_workspace(
        SimpleNamespace(assignment_brief=lambda *_: brief),
        "17",
        ["81"],
        source_base_url="https://canvas.fixture.invalid",
        exported_at="2026-10-08T00:00:00+00:00",
    )
    hostile = output / "literal-source.html"
    hostile.write_bytes(content)
    literal_page, _ = run.open("literal-source", hostile)
    expect(literal_page.locator("#assignment-0 h2")).to_have_text(title)
    expect(literal_page.locator("#assignment-0 .prompt")).to_have_text(literal)
    assert literal_page.locator("img, svg, .source-link").count() == 0
    assert literal_page.locator("script").count() == 2
    assert literal_page.evaluate("typeof window.__unexpected_execution") == "undefined"
    note = "</script><script>window.__unexpected_execution=11</script> & <img src=x>"
    literal_page.locator("#assignment-0-notes").fill(note)
    hostile_saved = run.save(literal_page, "literal-working.html")
    literal_again, _ = run.open("literal-notes-reopen", hostile_saved)
    expect(literal_again.locator("#assignment-0-notes")).to_have_value(note)
    assert literal_again.locator("img, svg, .source-link").count() == 0
    assert literal_again.evaluate("typeof window.__unexpected_execution") == "undefined"
    run.passed("literal_source_and_notes_remain_inert_after_reopen")

    failing, _ = run.open("download-failure", original)
    failing.locator("#assignment-0-notes").fill(
        "Keep this note after the controlled browser failure."
    )
    failing.evaluate("""() => {
      window.__realCreate = URL.createObjectURL.bind(URL);
      URL.createObjectURL = () => { throw new Error("controlled URL creation failure"); };
    }""")
    failing.get_by_role("button", name="Save working copy", exact=True).click()
    expect(failing.locator("#save-status")).to_contain_text("could not be prepared")
    expect(failing.locator("#assignment-0-notes")).to_have_value(
        "Keep this note after the controlled browser failure."
    )
    failing.evaluate("""() => {
      window.__created = []; window.__revoked = [];
      const revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = (blob) => {
        const value = window.__realCreate(blob); window.__created.push(value); return value;
      };
      URL.revokeObjectURL = (value) => { window.__revoked.push(value); revoke(value); };
      HTMLAnchorElement.prototype.click = () => { throw new Error("controlled download click failure"); };
    }""")
    failing.get_by_role("button", name="Save working copy", exact=True).click()
    expect(failing.locator("#save-status")).to_contain_text(
        "controlled download click failure"
    )
    assert failing.evaluate(
        "JSON.stringify(window.__created) === JSON.stringify(window.__revoked)"
    )
    assert failing.evaluate("window.__created.length") == 1
    assert failing.locator('a[href^="blob:"]').count() == 0
    expect(failing.locator("#assignment-0-notes")).to_have_value(
        "Keep this note after the controlled browser failure."
    )
    run.passed("two_controlled_download_failures_keep_notes_and_release_resources")
    run.finish()
    return original


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--chrome",
        type=Path,
        default=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = inventory()
    receipt = {
        "schema": "canvaspilot.study_workspace.browser_receiving/1",
        "scope": "Synthetic loopback CLI producer; native Chrome, file URLs, offline contexts",
        "python": sys.version,
        "source_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True
        ).strip(),
        "source_before": before,
        "cases": [],
        "pages": [],
        "passed": False,
    }
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(args.chrome), headless=True
            )
            receipt["browser_version"] = browser.version
            try:
                original = exercise(browser, output, receipt)
            finally:
                browser.close()
        receipt["original_after"] = digest(original)
        receipt["source_after"] = inventory()
        assert receipt["source_after"] == before
        receipt["passed"] = True
    except Exception:
        receipt["failure"] = traceback.format_exc()
        raise
    finally:
        receipt["artifacts"] = {
            str(path.relative_to(output)): digest(path)
            for path in sorted(output.rglob("*"))
            if path.is_file()
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "cases": len(receipt["cases"]),
                "pages": len(receipt["pages"]),
            }
        )
    )


if __name__ == "__main__":
    main()
