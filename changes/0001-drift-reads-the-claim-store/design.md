# Design - drift reads the claim store

## Approach

One new function in `anchor.py`, `classify_store`, which loads the store through the
existing `store.load_store`, walks each claim's anchors through the existing
`parse_anchor` and `classify`, and returns one record per claim carrying the worst
status among its anchors plus the anchors that produced it. The CLI renders it.

Reuse is the whole design. `parse_anchor` and `classify` are not re-implemented and not
copied; the store-wide entry point is a loop over the per-anchor engine that M1 already
measured. This is what keeps the `At risk` entry in `impact.md` from becoming real.

Three decisions worth stating:

**A claim is as stale as its worst anchor.** The human acts on claims, not anchors, so
reporting per anchor would make a five-anchor claim five findings and turn the report
into the wall of output that Q10 says kills the harness. The severity order already
exists in `anchor.Status`; the reducer picks the maximum and keeps the anchors that
justified it, so nothing is hidden - only re-grouped.

**Candidates are scanned but do not fail the command.** A proposed claim's staleness is
not yet anybody's obligation - nobody has agreed to it. Scanning them anyway is free and
tells the reviewer something useful at ratification time; failing on them would make the
candidate tier a liability instead of a staging area.

**A malformed anchor does not stop the scan.** `trace.py` already established this rule
for the index: whether an anchor is well-formed is a validation question that `forge
check` owns, and a scan that dies on one bad anchor reports nothing about the other
thirty-nine. A malformed anchor is reported as its own status and the walk continues.

## Alternatives rejected

**Make `--store` the default when no anchor is given.** Tempting, and it is what the
command will eventually want. Rejected for now because `forge drift <anchor>` is already
scripted against in this repository's own tests and measurement tools, and silently
changing what a bare invocation means is the kind of break that is discovered in
somebody's CI. `--store` is explicit; making it the default is a separate, deliberate
change with its own **BREAKING** marker.

**Report per anchor and let the caller group.** Rejected: it moves the reducer into
every consumer - the ledger, `forge verify`, the hook - and three copies of a severity
ordering is three chances to disagree about which status is worse.

**Compute `--changed` from the git diff inside `anchor.py`.** Rejected: `gitio` owns
every git call in this kernel, and an anchor module that shells out to git would be the
second place that knows how. `--changed` resolves its path set through `gitio` in the
CLI and passes it down as a filter.

## What this change does not decide

The drift **ledger** is not designed here. This change deliberately stops at producing
the signal, because deciding how a human records a verdict - a file, a schema, the four
verdicts' consequences - is a larger decision that deserves its own change and its own
ADR. Building the signal first also means the ledger's design can be informed by what
the scan actually reports on a real store, rather than by what SYSTEM_KNOWLEDGE.md
guessed it would report.

## ADR

None. This change adds a capability inside an architecture that is already decided; it
establishes no new constraint that a future change would need to know about. The ledger
change that follows will need one.

## A finding this change surfaced

Writing `impact.md` before any code exists means `forge impact` computes the claim-touch
set from an empty diff, and `trace.claim_touch_complete` - declared only at
`impact:post` - therefore verifies an account against nothing. The six warnings that
gate emitted say the accounted claims "are not in the computed touch set" and advise
checking whether the anchors point at the wrong files; the anchors are correct and the
advice is wrong. Nothing re-runs the check after implementation. This is recorded here
rather than fixed here, because it is a workflow-schema defect, not a drift defect, and
mixing the two would make this change unreviewable.
