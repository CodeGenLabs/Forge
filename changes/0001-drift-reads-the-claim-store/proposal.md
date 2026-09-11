# Proposal - drift reads the claim store

## Why

`forge drift` today classifies only the anchors typed on the command line, so the
question the harness exists to answer - *which of my claims describe code that has
moved?* - cannot be asked without first knowing the answer. Every consumer of drift
(the ledger, `forge verify`'s drift condition, a pre-commit hook) needs a store-wide
scan underneath it, and none of them can be built on an argv-only command.

## What changes

- `forge drift` accepts `--store`: read every anchor from every ratified claim in
  `docs/system/**`, classify each against its own recorded SHA, and report by claim.
- `forge drift` accepts `--changed`: the same scan narrowed to anchors whose path
  appears in the working diff. This is the form a pre-commit hook can afford.
- Both forms report per claim, not per anchor: a claim is as stale as its worst
  anchor, and the human acts on claims.
- Candidate claims are scanned but reported separately - an unratified claim's
  staleness is not yet anybody's obligation.
- No **BREAKING** change: the positional-anchor form keeps working unchanged, and
  `--store` is mutually exclusive with it.

## Capabilities

- Modified: `src/forge/anchor.py` - a store-wide classification entry point beside
  the existing per-anchor `classify`.
- Modified: `src/forge/cli.py` - the `drift` subparser and its rendering.
- Unchanged: `src/forge/store.py` is read from, not modified.

## Not in this change

The drift **ledger** (`docs/system/drift.md`, `forge drift resolve --verdict`) is
deliberately out of scope. This change produces the signal; recording a human verdict
about the signal is a separate decision with its own artifacts.
