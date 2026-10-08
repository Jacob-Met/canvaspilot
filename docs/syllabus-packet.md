# Save a syllabus reading packet

Use the native terminal to save the syllabus bodies returned for explicitly selected courses:

```sh
canvaspilot export-syllabus 42 57 --out syllabi.html
```

Open `syllabi.html` directly in a browser. Reading, the course contents list, source previews, exact source-text downloads and printing work without CanvasPilot or a network connection. The document has no scripts, automatic external resource loads, local storage or service requirement. A link you deliberately follow can leave the file and may require Canvas sign-in.

Use the existing `--base-url`, `--profile` and `--token` options or the existing configuration/authentication route. This command does not introduce a separate login or transport. Successful stdout is JSON containing `ok`, the output path, ordered course IDs, per-course syllabus states, capture time and byte counts.

## Selection and source

Select 1–10 unique positive course IDs. The complete selection is checked before any course request. Courses are fetched in the requested order through the unchanged `CanvasAPI.get_course`, which requests `syllabus_body`, `term` and `total_scores` from the existing single-course endpoint. The packet uses only the returned course identity, name, course code and syllabus body; it does not turn grade or term fields into a new report.

Every returned course must be an object whose positive integer or decimal-string ID matches the requested ID. A course name can be a caller's Canvas nickname, so the packet labels it as a returned name. A missing, null or empty name/code remains explicit instead of becoming an invented title.

The configured Canvas URL supplies context for course links and relative links. It is **not proof of the response's origin**: the unchanged client can use a session broker or follow redirects. Every original supplied link destination remains visible. No new provider-identity, authentication, broker, pagination or MCP behavior is introduced.

Reads happen sequentially. The capture timestamp identifies the packet creation, not an atomic cross-course snapshot, a last-modified time or a promise that an instructor's policies are still current.

## Empty, unavailable and refused input

These states remain different:

| Canvas response | Packet state |
| --- | --- |
| No `syllabus_body` key | Not supplied; contents are unknown |
| `syllabus_body: null` | Unavailable; contents are unknown |
| `syllabus_body: ""` | Explicitly empty source, zero bytes |
| Nonempty HTML string, including markup with no visible text | Supplied source; never relabelled explicitly empty |
| Failed course fetch, wrong response/body type or mismatched/missing course ID | Whole export refused |

Missing or null bodies can appear as visible unavailable entries alongside supplied courses. This is useful evidence about what the reader actually returned; it does not mean there are no course policies elsewhere.

Each HTML body is limited to **512 KiB of UTF-8 source**, and all selected bodies together to **2 MiB**. Supplied names and codes are limited to 4 KiB each. The reading projection allows up to 20,000 start tags and 256 nested elements per syllabus. Table column spans must be whole values from 1 to 1,000; row spans may be 0–65,534, with 0 retaining HTML's remaining-row-group meaning. The complete generated file is limited to 32 MiB. These are admission limits, not truncation rules. The inherited HTTP client receives and parses its response before these content limits can be applied.

Invalid command-line syntax or a nonpositive course ID is an argparse error, normally exit 2. Duplicate/too many IDs, source/read failures and output refusals return exit 1 and a structured JSON error on stderr, with no successful report on stdout. Read or rendering failure publishes no packet. The command collects all selected sources and renders the whole file before publication.

## What the reading projection preserves

The packet rebuilds passive text, headings, paragraphs, emphasis, quotations, preformatted code, ordered/unordered lists, definition lists and tables. Ordered-list numbering values, supported table spans/header associations, text direction and language are retained. Numbering values stay escaped in their native HTML attributes so the browser applies its normal integer rules; later duplicate attributes are discarded as HTML requires. Source styling, event attributes and interactive behavior are not copied. Unsupported or malformed HTML can have a different layout; this is a reading projection, not an exact visual reproduction of Canvas.

Original link text and destinations are retained. Ordinary HTTP(S) targets can be followed deliberately; relative targets resolve against the configured course syllabus URL. Unsafe or unsupported schemes stay inert text. Nothing follows links during export or downloads their contents.

Images, audio/video, frames, SVG/MathML, embedded objects, forms and similar interactive resources become explicit omission markers, with supplied alternative text, title or destination where available. Script/style contents are not executed or presented as course prose. A marker is not the resource: instructions that exist only inside an image, iframe, linked file or interactive content have **not** been reproduced offline. The packet's general notice makes this boundary visible even when a custom HTML element cannot expose its resource structure.

Canvas's separately generated course-summary list of assignments and calendar events is not part of the supplied `syllabus_body` and is outside this packet. Existing agenda, assignment, course-page and module reports remain separate consumers.

## Exact source and printing

Each supplied body, including an explicitly empty body, has an escaped source preview and a **text/plain download** named `course-ID-syllabus-source.txt`. That internally generated data download preserves the exact supplied UTF-8 bytes and records their byte count and SHA-256. It is not an executable HTML attachment.

Use the download for byte-exact reuse or comparison. Browser display and clipboard behavior can normalize line endings and control characters in a preview. Absent and null bodies have no invented source download.

Printing includes the readable courses, states, link destinations and omission notices. The navigation controls, raw-source previews/download controls and generated navigation footer are omitted from print. Instructor-authored footer text remains part of the reading. This reduces raw-markup clutter while preserving the reading limitation on paper.

## New files only

`--out` is required. Its parent directory must already exist. Any existing file, directory or symlink is protected; the command does not replace it, including when a destination appears while course reads are in progress.

After complete rendering, the command writes a temporary file beside the destination, flushes it, and publishes it with an atomic new-name hard link, following the established calendar-export convention. Unsupported filesystems fail safely; there is no overwrite fallback. Only the command's own staging file is cleaned up. The packet contains saved course material, so the temporary-file mechanism's private file permissions are retained.

Choose a different output name when you want a later observation. No course policy, assignment, submission, grade, completion or read-state mutation is made.

## Primary references

- [Canvas Courses API: Course object and single-course request](https://developerdocs.instructure.com/services/canvas/resources/courses) — `syllabus_body` is supplied HTML; names may be user nicknames; the separately generated course summary is a different setting.
- [HTML parsing standard](https://html.spec.whatwg.org/multipage/parsing.html#attribute-name-state) — later duplicate attributes are discarded; the first destination or numbering value retains its identity.
- [Python HTMLParser documentation](https://docs.python.org/3.12/library/html.parser.html) — callback-based source parsing is tolerant of invalid markup and does not itself enforce matching tags. The packet emits only its own passive allowlist.
- [Python file operations](https://docs.python.org/3.12/library/os.html#os.link) — native hard-link publication follows the project's existing new-file export pattern.

Qualification and source pins for this contribution live in its dedicated receiving packet. Synthetic native/independent receiving does not claim a school account, real student data, a deployed service or a learner outcome.
