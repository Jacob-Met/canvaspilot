# Module-progress source and receiving evidence

This packet qualifies the course module-progress checklist exposed by Python `CanvasAPI.module_progress`, CLI `canvaspilot module-progress`, and MCP `canvas_module_progress`. It preserves prior results at their exact source revisions.

## Product boundary

Canvas-declared module state and item requirements/completion remain authoritative. Missing or unsupported fields stay unknown; one-of alternatives are not presented as remaining work after Canvas declares a module completed. Counts cover returned rows, whole-course completeness remains unknown, and item access is not inferred. Reads never mark items done/read, submit work, or alter grades.

The adapter validates the **normalized output** of `CanvasAPI.list_modules(detail="full")`. It does not see or certify raw HTTP response shape. Existing singleton-page wrapping and inline-item fallback remain owned by the existing reader. The final report explicitly exposes `reader_source` and `upstream_response_shape: "not_observed"`; the independent review preserves the concrete earlier boundary counterexamples.

## Exact native stages

| Stage | Native source | Qualification |
| --- | --- | --- |
| Original implementation | `a8ba4be26d09d287304ca12808a1867483efd040` on `72357053` |263 passing tests; original192-test baseline and initial failed harness/lint attempts retained |
| Feedback composition | `51609ba3f93d20f69616b357c3c6bee19732dfd4` on `e8cd1aec` |288 passing tests; old shared bodies and182 unrelated parent leaves preserved |
| Reader-boundary clarification | `96e4f3d37b4e2e222e30ff34a0bab96bed95b8cd` |70 focused tests, including three real CLI/MCP normalized-response cases; Ruff/source whitespace pass |
| Current calendar composition | `5173b24285e9e3e2dda6b1d8158adea74e03bd52` on `a03a8637` |Two actual CLI/MCP receiving groups, calendar parser and Ruff pass;284 unrelated parent leaves preserved |

The current composition retains all eight unchanged reviewed source leaves exactly. CLI was reconstructed from the current canonical parent plus the two exact module-progress blocks; removing those blocks reproduces the complete parent file byte for byte. README preserves the current calendar guide and module-progress additions. The module reader, client, broker and dependency configuration are unchanged.

The independent reviewer adds original CLI/MCP counterexamples, all-versus-one/lock/unknown/completeness/failure/identity controls, and two exact-projection checks of the clarified output markers. Its immutable packet and final verdict are under `independent/`.

## Interpretation

Each stage has separate manifests, source pins and raw logs. These results are not summed into a claimed new full-suite run: hosted PR CI is the whole current-composition gate. No live Canvas account, another student's identity, learner mutation, real-school session, installed deployment or package release is part of these fixtures.

Raw historical patches and failure logs are retained exactly, including whitespace that makes an unrestricted full-evidence `git diff --check` report findings. Source-only whitespace checks passed. This does not convert retained artifact text into an unclaimed clean full-tree whitespace result.
