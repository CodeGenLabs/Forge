# Tasks - drift reads the claim store

Each task is one physical line. `Change.tasks()` reads a single line per bullet, so a
REQ- id on a continuation line is invisible to `trace.requirement_task_coverage` - see
`design.md`, "A finding this change surfaced", and the second finding recorded there.

- [x] REQ-drift-store-scan: add `ClaimDrift` and `classify_store` to `src/forge/anchor.py` - walk every claim's anchors through the existing `parse_anchor` and `classify`, reduce to the worst status per claim, keep the anchors that justified it.
- [x] REQ-drift-changed-only: give `classify_store` an optional path filter so a caller can narrow the scan to anchors under a given set of files.
- [x] REQ-drift-never-rewrites: assert in tests that a scan over a store containing a stale claim leaves every store file byte-identical.
- [x] REQ-drift-store-scan, REQ-drift-changed-only: add `--store` and `--changed` to the `drift` subparser in `src/forge/cli.py`, mutually exclusive with the positional anchors, with `--changed` resolving its path set through `gitio`.
- [x] REQ-drift-store-scan: render per claim - id, worst status, and the anchors that caused it - with ratified and candidate claims in separate blocks, exiting 1 when any ratified claim is not fresh and 0 otherwise.
- [x] REQ-drift-store-scan, REQ-drift-changed-only: tests in `tests/test_anchor_store.py` covering all-fresh, one-stale, worst-of-several, stale-candidate-does-not-fail, changed-filter-hits, changed-filter-misses, and malformed-anchor-does-not-abort.
- [x] Chore: correct the scope note in the `cli.py` module docstring, which says the store-reading `forge drift` does not exist.
- [x] Chore: make `commands.test` in `.forge/config.yaml` resolvable without an activated virtualenv - bootstrap detected the bare `pytest`, which `forge verify` cannot run, so verification reported red for an environment reason while the suite passed.
