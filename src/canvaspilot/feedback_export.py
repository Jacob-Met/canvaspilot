"""Save the existing submission-feedback reader's result as a local HTML sheet."""

from __future__ import annotations

import hashlib
import html
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI


_STYLE = """:root { color-scheme: light; color: #182a3a; background: #f3f5f6; }
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.55 system-ui, -apple-system, sans-serif; }
main { max-width: 72rem; margin: 3rem auto; padding: 0 1.5rem; }
header { padding: 0 0 1.8rem; border-bottom: 2px solid #23465c; }
.eyebrow { margin: 0 0 .5rem; font-size: .78rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: #3e637b; }
h1 { margin: 0 0 .8rem; font: 700 clamp(2rem, 5vw, 3rem)/1.15 Georgia, serif; }
h2 { margin: 0 0 1rem; font-size: 1.35rem; }
h3 { margin: 0 0 .8rem; font-size: 1.05rem; }
p { margin: .6rem 0; }
section { margin: 1.8rem 0; }
article, .panel { padding: 1.3rem; margin: 1rem 0; background: white;
  border: 1px solid #d6dfe4; border-radius: .6rem; }
.notice { padding: 1rem 1.2rem; background: #e7f0f5; border-left: 4px solid #44718b; }
.prior { background: #fff3d9; border-color: #a16a12; }
.muted, dt, footer { color: #506370; }
dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: .8rem 1.5rem; margin: .8rem 0; }
dl > div { min-width: 0; }
dt { font-size: .8rem; font-weight: 650; }
dd { margin: .2rem 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.wide { grid-column: 1 / -1; }
.ratings { padding-left: 1.2rem; }
.ratings li { margin: .7rem 0; }
.ratings dl { margin: .3rem 0; }
.literal { white-space: pre-wrap; overflow-wrap: anywhere; }
a { color: #164e75; overflow-wrap: anywhere; }
a:focus-visible { outline: 3px solid #b16b11; outline-offset: 3px; }
footer { border-top: 1px solid #c4d0d8; padding: 1.2rem 0; font-size: .85rem; }
@media (max-width: 36rem) {
  main { margin: 1.5rem auto; padding: 0 1rem; }
  article, .panel { padding: 1rem; }
  dl { grid-template-columns: 1fr; }
}
@media print {
  @page { margin: 16mm; }
  :root { background: white; }
  main { margin: 0; padding: 0; max-width: none; }
  h1, h2, h3 { break-after: avoid; }
  article, .panel { border-radius: 0; }
  a { color: inherit; }
}
"""


def _value(value: Any) -> str:
    if value is None:
        return '<span class="muted">Not returned</span>'
    if value == "":
        return '<span class="muted">Returned empty text</span>'
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False)
    return html.escape(text, quote=True)


def _field(label: str, value: Any, key: str, *, wide: bool = False) -> str:
    css = ' class="wide"' if wide else ""
    return (f"<div{css}><dt>{html.escape(label)}</dt>"
            f'<dd data-field="{html.escape(key, quote=True)}">{_value(value)}</dd></div>')


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        # Malformed Canvas data uses the public ValueError refusal contract.
        raise ValueError(f"Cannot render malformed {name}")  # noqa: TRY004
    return value


def _positive_id(value: int | str, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        # All invalid IDs use one ValueError contract, including wrong types.
        raise ValueError(f"{name} must be a positive numeric Canvas ID")  # noqa: TRY004
    text = str(value)
    if not text.isascii() or not text.isdigit() or int(text) <= 0:
        raise ValueError(f"{name} must be a positive numeric Canvas ID")
    return int(text)


def _saved_at(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("captured_at must be a timezone-aware datetime")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _assignment_link(value: Any) -> str:
    if isinstance(value, str) and value and not any(ord(char) < 33 for char in value):
        try:
            parsed = urlsplit(value)
            if (parsed.scheme.lower() in {"http", "https"} and parsed.hostname
                    and parsed.username is None and parsed.password is None):
                escaped = html.escape(value, quote=True)
                return f'<a href="{escaped}" rel="noreferrer noopener">{escaped}</a>'
        except ValueError:
            pass
    return _value(value)


def _assessment(value: Any, prefix: str, hide_points: bool) -> str:
    if value is None:
        return '<p class="muted">No assessment was returned for this criterion.</p>'
    value = _mapping(value, "rubric assessment")
    if not value:
        return '<p class="muted">Canvas returned an empty assessment.</p>'
    fields = ""
    if not hide_points:
        fields += _field("Reported assessment points", value.get("points"), prefix + ".points")
    fields += _field("Reported rating ID", value.get("rating_id"), prefix + ".rating_id")
    fields += _field("Criterion feedback", value.get("comments"), prefix + ".comments", wide=True)
    return "<dl>" + fields + "</dl>"


def _criteria(value: Any, hide_points: bool) -> str:
    if value is None:
        return '<p class="muted">Rubric criteria were not returned; their presence is unknown.</p>'
    if not isinstance(value, list):
        # Malformed Canvas data uses the public ValueError refusal contract.
        raise ValueError("Cannot render malformed rubric criteria")  # noqa: TRY004
    if not value:
        return '<p class="muted">Canvas returned an empty criterion list.</p>'
    cards = []
    for index, row in enumerate(value, 1):
        row = _mapping(row, "rubric row")
        criterion = _mapping(row.get("criterion"), "rubric criterion")
        prefix = f"criterion.{index}"
        fields = _field("Criterion ID", criterion.get("id"), prefix + ".id")
        if not hide_points:
            fields += _field("Criterion possible points", criterion.get("points"), prefix + ".points")
        fields += _field("Range-based ratings", criterion.get("criterion_use_range"), prefix + ".criterion_use_range")
        fields += _field("Excluded from scoring", criterion.get("ignore_for_scoring"), prefix + ".ignore_for_scoring")
        if "learning_outcome_id" in criterion:
            fields += _field("Learning outcome ID", criterion["learning_outcome_id"], prefix + ".learning_outcome_id")
        if "long_description" in criterion:
            fields += _field("Criterion detail", criterion["long_description"], prefix + ".long_description", wide=True)
        ratings = criterion.get("ratings")
        if ratings is None:
            scale = '<p class="muted">Rating scale was not returned.</p>'
        elif not isinstance(ratings, list):
            raise ValueError("Cannot render malformed rubric ratings")
        elif not ratings:
            scale = '<p class="muted">Canvas returned an empty rating scale.</p>'
        else:
            entries = []
            for number, rating in enumerate(ratings, 1):
                rating = _mapping(rating, "rubric rating")
                key = prefix + f".rating.{number}"
                detail = _field("Rating ID", rating.get("id"), key + ".id")
                if not hide_points:
                    detail += _field("Rating points", rating.get("points"), key + ".points")
                if "long_description" in rating:
                    detail += _field("Rating detail", rating["long_description"], key + ".long_description", wide=True)
                entries.append(f'<li><div class="literal">{_value(rating.get("description"))}</div><dl>{detail}</dl></li>')
            scale = '<ul class="ratings">' + "".join(entries) + "</ul>"
        cards.append(
            f'<article id="criterion-{index}"><h3>{index}. {_value(criterion.get("description"))}</h3>'
            f"<dl>{fields}</dl><h4>Returned rating scale</h4>{scale}"
            f'<h4>Returned assessment</h4>{_assessment(row.get("assessment"), prefix + ".assessment", hide_points)}</article>'
        )
    return "".join(cards)


def _comments(value: Any) -> str:
    if value is None:
        return '<p class="muted">Submission comments were not returned; their presence is unknown.</p>'
    if not isinstance(value, list):
        # Malformed Canvas data uses the public ValueError refusal contract.
        raise ValueError("Cannot render malformed submission comments")  # noqa: TRY004
    if not value:
        return '<p class="muted">Canvas returned an empty comment list.</p>'
    cards = []
    for index, comment in enumerate(value, 1):
        comment = _mapping(comment, "submission comment")
        prefix = f"comment.{index}"
        fields = "".join(_field(label, comment.get(key), prefix + "." + key) for key, label in (
            ("id", "Comment ID"), ("author_name", "Reported author name"),
            ("author_id", "Author ID"), ("created_at", "Created"), ("edited_at", "Edited"),
        ))
        author = comment.get("author")
        if isinstance(author, dict):
            if "display_name" in author and author["display_name"] != comment.get("author_name"):
                fields += _field("Author record display name", author["display_name"], prefix + ".author.display_name")
            if "id" in author and author["id"] != comment.get("author_id"):
                fields += _field("Author record ID", author["id"], prefix + ".author.id")
        fields += _field("Comment", comment.get("comment"), prefix + ".comment", wide=True)
        media = comment.get("media_comment")
        if media is not None:
            media = _mapping(media, "media comment")
            fields += _field("Media type (not downloaded)", media.get("media_type"), prefix + ".media.type")
            fields += _field("Media ID", media.get("media_id"), prefix + ".media.id")
            if "display_name" in media:
                fields += _field("Media name", media["display_name"], prefix + ".media.name")
        attachments = comment.get("attachments")
        if attachments is None:
            attachment_text = '<p class="muted">Attachment list was not returned.</p>'
        elif not isinstance(attachments, list):
            raise ValueError("Cannot render malformed comment attachments")
        elif not attachments:
            attachment_text = '<p class="muted">Canvas returned an empty attachment list.</p>'
        else:
            entries = []
            for number, attachment in enumerate(attachments, 1):
                attachment = _mapping(attachment, "comment attachment")
                key = prefix + f".attachment.{number}"
                detail = _field("Attachment ID", attachment.get("id"), key + ".id")
                detail += _field("File name", attachment.get("display_name", attachment.get("filename")), key + ".name")
                if "content-type" in attachment:
                    detail += _field("Content type", attachment["content-type"], key + ".type")
                entries.append("<li><dl>" + detail + "</dl></li>")
            attachment_text = '<p>Attachments (not downloaded):</p><ul>' + "".join(entries) + "</ul>"
        cards.append(f'<article id="comment-{index}"><h3>Comment {index}</h3><dl>{fields}</dl>{attachment_text}</article>')
    return f"<p>{len(value)} returned comments, in Canvas response order.</p>" + "".join(cards)


def render_feedback_document(
    feedback: dict[str, Any], *, course_id: int | str, assignment_id: int | str,
    captured_at: datetime,
) -> bytes:
    """Render received feedback without inferring grades or fetching resources.

    The native reader remains responsible for joining criterion IDs. This view
    renders those joins as returned and keeps unmatched assessments separate.
    Optional absent/null values and explicit empty containers remain distinct.
    """
    course_id = _positive_id(course_id, "course_id")
    assignment_id = _positive_id(assignment_id, "assignment_id")
    saved = _saved_at(captured_at)
    # An HTML sheet must not turn NaN/Infinity into plausible score text.
    json.dumps(feedback, ensure_ascii=False, allow_nan=False)
    feedback = _mapping(feedback, "feedback document")
    assignment = _mapping(feedback.get("assignment"), "assignment")
    submission = _mapping(feedback.get("submission"), "submission")
    rubric = _mapping(feedback.get("rubric"), "rubric")
    for value, expected, name in (
        (assignment.get("id"), assignment_id, "assignment.id"),
        (assignment.get("course_id"), course_id, "assignment.course_id"),
        (submission.get("assignment_id"), assignment_id, "submission.assignment_id"),
    ):
        if value is not None and _positive_id(value, name) != expected:
            raise ValueError(f"Returned {name} does not match the requested assignment")

    settings = rubric.get("settings")
    if settings is None:
        settings_note = "Rubric settings were not returned."
    else:
        settings = _mapping(settings, "rubric settings")
        settings_note = "Canvas returned an empty rubric settings object." if not settings else ""
    settings = settings if settings is not None else {}
    for flag in ("hide_points", "hide_score_total", "hide_outcome_results"):
        if settings.get(flag) is not None and not isinstance(settings[flag], bool):
            raise ValueError(f"Cannot interpret non-boolean rubric {flag}")
    hide_points = settings.get("hide_points") is True
    hide_total = settings.get("hide_score_total") is True

    flag = submission.get("grade_matches_current_submission")
    if flag is False:
        notice = "Canvas reports that grading preceded the latest resubmission. The displayed grade must not be treated as a grade for the current attempt."
    elif flag is True:
        notice = "Canvas reports that the grade matches the current submission."
    else:
        notice = "Canvas did not establish whether the grade matches the current submission."
    use_for_grading = rubric.get("use_rubric_for_grading")
    if use_for_grading is False:
        rubric_notice = "Advisory rubric: Canvas says it is not used for grading."
    elif use_for_grading is True:
        rubric_notice = "Canvas says this rubric is used for grading."
    else:
        rubric_notice = "Whether the rubric is used for grading was not established by Canvas."

    assignment_fields = _field("Requested course ID", course_id, "requested.course_id")
    assignment_fields += _field("Requested assignment ID", assignment_id, "requested.assignment_id")
    assignment_fields += _field("Returned course ID", assignment.get("course_id"), "assignment.course_id")
    assignment_fields += _field("Returned assignment ID", assignment.get("id"), "assignment.id")
    assignment_fields += _field("Assignment due", assignment.get("due_at"), "assignment.due_at")
    assignment_fields += _field("Saved at (UTC)", saved, "captured_at")
    submission_fields = "".join(_field(label, submission.get(key), "submission." + key) for key, label in (
        ("attempt", "Current submission attempt"), ("workflow_state", "Submission state"),
        ("score", "Reported submission score"), ("grade", "Reported submission grade"),
        ("submitted_at", "Submitted"), ("graded_at", "Graded"), ("posted_at", "Grade posted"),
        ("submission_type", "Submission type"), ("user_id", "Submitting user ID"),
        ("grader_id", "Reported grader ID"), ("excused", "Excused"), ("late", "Late"),
        ("missing", "Missing"), ("redo_request", "Revision requested"),
    ))
    submission_fields += _field("Assignment possible points", assignment.get("points_possible"), "assignment.points_possible")
    rubric_fields = _field("Rubric title", settings.get("title"), "rubric.title")
    if not hide_points and not hide_total:
        rubric_fields += _field("Rubric possible points (as supplied)", settings.get("points_possible"), "rubric.points_possible")
    rubric_fields += _field("Free-form criterion comments", settings.get("free_form_criterion_comments"), "rubric.free_form_criterion_comments")
    rubric_fields += _field("Assessment object returned", rubric.get("assessment_returned"), "rubric.assessment_returned")
    rubric_fields += _field("Withhold outcome results from Learning Mastery Gradebook", settings.get("hide_outcome_results"), "rubric.hide_outcome_results")
    visibility = ""
    if hide_points:
        visibility += "<p>Rubric points are hidden by the returned Canvas setting.</p>"
    if hide_total:
        visibility += "<p>The rubric total is hidden by the returned Canvas setting.</p>"
    criteria_html = _criteria(rubric.get("criteria"), hide_points)
    unmatched = rubric.get("unmatched_assessments")
    if unmatched is None:
        unmatched_html = '<p class="muted">No assessment mapping was returned; unmatched feedback is unknown.</p>'
    else:
        unmatched = _mapping(unmatched, "unmatched rubric assessments")
        if not unmatched:
            unmatched_html = '<p class="muted">The returned assessment mapping has no unmatched entries.</p>'
        else:
            unmatched_html = "<p>These entries have no unique matching rubric criterion. They remain separate.</p>"
            for index, (key, assessment) in enumerate(unmatched.items(), 1):
                unmatched_html += f'<article><h3>Unmatched assessment: {_value(key)}</h3>{_assessment(assessment, f"unmatched.{index}", hide_points)}</article>'

    title = _value(assignment.get("name"))
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>CanvasPilot · Feedback review</title><style>{_STYLE}</style></head>
<body><main>
<header><p class="eyebrow">CanvasPilot · Saved feedback</p><h1 class="literal">{title}</h1>
<p>Submission comments, rubric feedback and the attempt context returned by Canvas.</p>
<dl>{assignment_fields}</dl><p>Assignment link returned by Canvas: {_assignment_link(assignment.get("html_url"))}</p></header>
<section aria-labelledby="submission-heading"><h2 id="submission-heading">Submission and grading</h2>
<p class="notice{' prior' if flag is False else ''}">{notice}</p><div class="panel"><dl>{submission_fields}</dl></div></section>
<section aria-labelledby="rubric-heading"><h2 id="rubric-heading">Rubric feedback</h2>
<p class="notice">{rubric_notice}</p><div class="panel"><p class="muted">{settings_note}</p><dl>{rubric_fields}</dl>{visibility}
<p class="muted">No rubric score is summed or used to calculate a grade in this sheet.</p></div>{criteria_html}
<h3>Unmatched assessments</h3>{unmatched_html}</section>
<section aria-labelledby="comments-heading"><h2 id="comments-heading">Submission comments</h2>
<p>Authors are shown as returned; comments are not assumed to come from an instructor.</p>{_comments(feedback.get("submission_comments"))}</section>
<footer><p>This is a saved copy of the returned feedback. It does not refresh. Source timestamps retain their reported timezone notation.</p>
<p>Media and attachments are listed when returned, but their contents are not downloaded. Open the assignment in Canvas to review them.</p>
<p>Open this file in a browser to read it, or use the browser’s Print command.</p></footer>
</main></body></html>
"""
    return document.encode("utf-8")


def build_feedback_document(
    api: CanvasAPI, course_id: int | str, assignment_id: int | str,
    *, captured_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read once through the native API and prepare a complete snapshot in memory."""
    course_id = _positive_id(course_id, "course_id")
    assignment_id = _positive_id(assignment_id, "assignment_id")
    if captured_at is not None:
        _saved_at(captured_at)
    feedback = api.submission_feedback(course_id, assignment_id)
    captured_at = captured_at if captured_at is not None else datetime.now(UTC)
    content = render_feedback_document(feedback, course_id=course_id, assignment_id=assignment_id,
                                       captured_at=captured_at)
    return content, {"course_id": course_id, "assignment_id": assignment_id,
                     "captured_at": _saved_at(captured_at),
                     "sha256": hashlib.sha256(content).hexdigest()}


def write_feedback_document(path: Path, content: bytes) -> None:
    """Publish completed bytes to a new file, preserving any existing entry.

    Follow the native calendar writer's same-directory hard-link publication
    pattern. No alternate overwrite path is used on unsupported filesystems.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="." + path.name + ".", suffix=".tmp",
                                         dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
