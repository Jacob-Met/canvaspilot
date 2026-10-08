# Announcement text search: qualification

The new `find-announcements` command finds a literal phrase in the full titles
and cleaned messages returned for selected courses. Its [public guide](../../announcement-search.md)
describes the JSON result and complete-read behavior. Source ownership is recorded
in [issue #74](https://github.com/Jacob-Met/canvaspilot/issues/74).

## Frozen source

- Candidate: `2239de20e604318feccd82b1eec3db4553e7c0e7`, tree `aa8c890ed82177024cf9bf35a13635974ed59c26`.
- Current parent: `f618c3ed13f191ea58642283c1f9cd45a0c1ca81`, including page-packet PR #71.
- Original author baseline: `1bafdaa31f7789d8e561680cb6001bbe38b2da64`.
- Six product leaves: the new search helper, additive CLI spans, two dedicated tests, a guide, and an appended README pointer.

Removing the three search additions restores every current CLI byte. Removing the
README suffix restores every current README byte. All 18 other current runtime
modules and all 1,331 unselected current tree leaves remain exact, including the
page exporter, API, client, existing commands, tests, dependencies, and workflow.
[Current source closure](current-source-closure.json) records the exact additions.
The full 20-module [candidate archive](candidate-source.zip) has SHA256
`fb96edaf741668547fb62e7bdbc06695d3a7642d42e3a3ac9d6b4b083004ef37`.

## Observed checks

| Stage | Result | Scope |
| --- | --- | --- |
| Original baseline | Three existing controls pass; the missing search command fails as expected | Actual full and compact readers, later-page refusal, and absent new command |
| First author source | 17 methods pass, with no test failures or errors | 21 actual CLI processes and six actual CLI/logger HTTP calls, plus semantic controls |
| Focused author correction | Nine methods and all five Ruff checks pass | Two malformed-container exception categories, test formatting, four contributed Python files, and an original CLI control |
| Current parent composition | Full source and tree closure pass | Page-packet owner bytes preserved; identical public search additions |
| Independent current-source receiving | Pending in its separate receipt | Frozen external oracle and actual current 20-module package |
| Maintained hosted CI | Pending | Normal repository Ruff and pytest workflow |

The initial lint result is retained. Its two helper container exceptions now use
`TypeError`; new-test formatting is corrected. The local stdin lint adapter
explicitly supplies the project's Python 3.11 floor and `canvaspilot` first-party
classification because this run has no physical source directory. It suppresses
no rules and changes no existing source. Full hosted lint remains a separate gate.

## Complete evidence

[author-native.tar.gz](author-native.tar.gz) is 442,024 bytes, SHA256
`05e869121df10211044cec4bff31964dfbac5528cbd98c77c19709d7067180fa`.
Its 48 members include 47 payload files and a manifest; every member was read back
against its exact input bytes before sealing. It retains the original and candidate
source stages, complete executed scripts, raw output, all assertions, native
runtime metadata, and the original preparation and lint failures.
[author-receiving.json](author-receiving.json) binds the archive and stage results.

Local storage was full, so standard Python zipimport loaded the complete actual
package from sealed Linux memory files within an owned process tree. The source
origin and hash checks exclude the stale editable donor. Fixtures use real HTTPX
against an owned numeric-loopback server with synthetic credentials and content.
No school account, session broker, installed service, live provider, installation,
or deployment is involved. This describes the receiving setup; the product itself
has no memory-file or Linux-specific dependency.

The first seal-constant and process-path preparations stopped before product
execution. Their setup-only successors and exact original failures are retained.
No product success is inferred from either failed preparation.
