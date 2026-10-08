# Independent PR45 provider-page receiving

Reviewed published head: 1748e52ed1533c102e04525f96c3d76d4141d30c.
Parent: a03a8637efad8ff22103a0c5018c93f7ecbb7d8d.
Independent receiver: estate-49f845d0dece/source_coordination.

## Result

The proposed calendar helper faithfully mirrors fixture/token/session transport
precedence and fixes the four published configured-provider identity cases.
It does not establish that the selected browser page belongs to the configured
provider. The unchanged broker selects the first page containing instructure.com
and runs relative assignment requests there. Its health response independently
reports STATE.base_url.

Three fresh native CLI processes reproduced the stable mismatch on the exact
five production source hashes from PR45:

1. Configured A / page A -> report A and UID A.
2. Configured A / page B -> exit 0, artifact URL B, report A and the same UID A.
3. Configured B / page B -> report B and a different UID B.

No concurrent switch is required. This is an existing broker routing defect,
not a new patch regression; it remains consequential for complete actual-provider
identity acceptance. The lead and author received the exact evidence before
integration. Their source ownership remains unchanged.

## Exact boundary

Production CLI, CanvasAPI, CanvasClient, broker Handler, _call, job queue,
_canvas_page and _run_job execute unchanged. Only the terminal Page object is
authored. It records the selected page, relative path, navigation decisions and
production evaluation-script hash, and supplies synthetic JSON at the page
boundary. urllib.parse.urljoin records the relative fetch origin. No actual
browser, login, school, account, external HTTP request or credential is used.

The receiver is NOT real-browser or live-provider qualification. Matching-host
controls, one event independently parsed by icalendar per command, unchanged
source hashes, zero navigation, exact request count and no profile creation
bound the counterexample. Native stdout says counterexample_reproduced; exit 0
means those receiving preconditions and the witness held, not product acceptance.

## Reproduce

Use the retained existing calendar virtual environment and an empty output path:

    python receive_provider_page.py --source /path/to/PR45-source --output /new/output

The harness refuses before import if any of five frozen production SHA-256
pins differs. It writes no source files and the child commands receive an
explicit empty token, isolated nonexistent profile path and local broker port.
Raw stdout/stderr, all three .ics files and receipt.json are retained.

The original broader receiver and its 14 current-main pagination failures were
not rerun or changed. No implementation repair was made by this reviewer.
