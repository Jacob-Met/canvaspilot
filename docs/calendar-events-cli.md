# Read calendar events from the CLI

`canvaspilot calendar-events` exposes the existing read-only calendar-event reader. It prints the original returned event records as JSON, including their supplied fields and values. It follows the existing client's pagination and refusal behavior. It does not create or edit events, infer missing dates, or turn assignments into calendar events.

```sh
canvaspilot calendar-events
canvaspilot calendar-events --start-date 2026-10-08 --end-date 2026-10-15
canvaspilot calendar-events --context-code course_123 --context-code user_456
```

The command uses the normal `--base-url`, `--profile` and `--token` options and existing authentication behavior. Use your established connection. There is no new credential store or login flow.

`--start-date` and `--end-date` pass their strings to the existing reader as `start_date` and `end_date`. Omitted values preserve Canvas defaults; the CLI does not choose a date window. An explicitly empty date also omits that filter, matching the existing reader. Use the portable equals form `--start-date=` or `--end-date=` if needed.

Repeat `--context-code` to provide multiple existing context codes. Their order, repetitions and literal values are preserved as repeated `context_codes[]` parameters. The CLI does not guess a course from a label or validate what contexts you may access. An empty context value is forwarded if explicitly supplied as `--context-code=`; omit the option to leave context filtering to the existing reader and Canvas.

The output describes the records the server returned under those filters and defaults. It is not a promise that every event or assignment in your account is present. `export-calendar` remains the separate assignment-deadline export, and `agenda` retains its existing course-agenda behavior.

A successful call emits JSON on stdout. An authentication, pagination or HTTP failure exits1, emits one structured JSON error on stderr, and does not print a partial event collection. Invalid or incomplete options are refused by the ordinary argument parser before a request. No live school data is needed for the synthetic local receiving tests.
