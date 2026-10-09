# Read one module offline

Choose a module from `canvaspilot modules COURSE_ID`, then save a new file:

```bash
canvaspilot export-module 42 7 --out module-7.html
```

The packet keeps one selected module's returned item order, Page readings and Assignment briefs. A repeated reading is fetched once and shown at every original position. Files, quizzes, discussions, external tools and unknown item types remain labeled references; their bodies, attachments and media are not fetched.

Use the existing `--base-url`, `--token` and `--profile` options for your Canvas connection. Export requests use the existing readers and transport. They do not request submission, completion, quiz-attempt or read-state actions.

## Read, navigate and print

Open the saved HTML directly in a browser. **Contents in returned order** links to each item. Item identity, reported position and completion requirement remain visible, including duplicate positions. Module state, all-versus-one rule, sequential setting and prerequisite IDs are reported context. The packet does not calculate completion percentage, remaining work, grades, prerequisite satisfaction or accessibility.

Page sections show a plain-text projection and an **Original page HTML (inert text)** disclosure. Formatting and embedded media are not reproduced. Missing, null and explicitly empty bodies have different labels. Lock/editor metadata remain visible. A supplied nonempty body remains source content, without an inferred access decision. Withheld content is not sought at another URL. Block editor data stays in the complete source; no HTML is invented from it.

Assignment sections use the existing normalized brief: prompt, rubric, settings, advisory/grading flag and warnings. Zero points and false flags remain meaningful. An empty normalized prompt cannot establish whether original HTML was absent, null or empty. The brief carries requested identities; the exporter does not independently observe the original HTTP assignment identity. Rubric evidence is not a newly calculated grade or self-assessment workflow.

**Download complete retained source JSON** saves the selected normalized module and all returned Page objects/normalized briefs. Unknown fields, large integer identities and null/false/zero/empty values survive. Its SHA-256 and byte count are displayed. These are decoded source values, not original HTTP wire bytes.

The self-contained file has no scripts, automatic network requests, remote assets, browser storage or local notes. Contents, downloads and disclosures work with a keyboard. Printing includes readable content; raw-source disclosures and the download control are hidden from print but remain in the HTML.

## Selection and failure behavior

Course and module IDs must be positive ASCII decimal numbers. The destination must be new: existing files, directories, and live or dangling symlinks are refused before connection setup. A destination created during collection is preserved by the existing exclusive new-file writer.

The exporter reads the existing full module collection once, selects the exact module, validates item identities and preflights every Page/Assignment target. Pages use ModuleItem `page_url`, encoded as one course-local path segment; Page `content_id` and supplied item URLs do not select the API request. Returned Page locators must match; explicit foreign course identities are refused.

The selected module must have a nonnegative integer `items_count` matching its returned item array. This check uses the existing full reader's normalized result, after fallback and pagination. A reported zero count with no inline array is normalized by that reader to zero items without fetching its item route. A zero-item packet is explicitly labeled. Count correspondence does not prove raw upstream shape, an atomic snapshot, course-wide completeness or later changes.

Limits refuse excess without silent truncation:

- 100 selected items.
- 20 distinct Page/Assignment targets, counted before any body fetch.
- 512 KiB per Page body or serialized normalized brief.
- 4 MiB complete retained JSON and 16 MiB final HTML.

Malformed or ambiguous identities, unavailable required locators, count mismatch, HTTP/pagination failures, provider changes and exceeded bounds refuse the complete packet. Missing/null/empty Page bodies are explicit observations, not request failures. All output is prepared before publication. No successful partial file/receipt is emitted after a collection failure. If publication succeeds but temporary-file cleanup fails, the existing writer's cleanup warning is retained in the success receipt.

## Development checks

```bash
python -m pytest -q tests/test_module_study_packet.py tests/test_module_study_packet_cli.py
python -m ruff check src/canvaspilot/module_study_packet.py tests/test_module_study_packet.py tests/test_module_study_packet_cli.py
```

These use synthetic objects and disposable numeric-loopback HTTP servers, including actual CLI subprocesses and HTTPX. They do not use a school account or learner records.

The optional installed-browser check requires existing Node.js, Playwright and Chromium. Set `CANVASPILOT_PYTHON` to Python's executable, `CANVASPILOT_CHROME` to Chromium's executable and `CANVASPILOT_PLAYWRIGHT_FROM` to an existing package.json from which Playwright resolves. Then run:

```bash
node scripts/receive_module_study_packet.mjs /absolute/new-external-receipt-directory
```

It runs the real CLI against its own synthetic provider, stops the provider, and opens the saved file offline. It records actual request order, source download, keyboard navigation/disclosure, desktop/390-pixel layout and print output. Screenshots and raw receipts are saved for review. It installs nothing and is not wired to a new hosted workflow.
