# Impact - drift reads the claim store

## Blast radius

`forge impact` computes 0 changed files and 0 reached by import, because on track C
this artifact is written before any code exists. The set below is therefore a
**forecast**, made by reading the change, not a computation. That gap is itself a
finding of this change and is recorded in `design.md`.

Forecast, by reading the proposal:

- `src/forge/anchor.py` - a new store-wide classification entry point beside `classify`.
- `src/forge/cli.py` - the `drift` subparser gains `--store` and `--changed`, and a
  per-claim renderer.
- `src/forge/store.py` - read only. No edit expected.
- `tests/test_anchor_store.py` - new.

Reached by import: `cli.py` imports `anchor`, `store` and `gitio`; nothing imports
`cli.py` except the console-script entry point, so the import closure stops there.

## Claims touched

Computed set: empty, for the reason above. The entries below are the claims whose
anchor paths the forecast intersects, accounted for by hand.

### Unaffected

> This note used to cover three `PIT-` claims and now covers none of them. It said
> they were reported as having "their own definition edited" only because this change
> appends a new claim to the end of `docs/system/pitfalls.md` and that test is
> file-level - a false positive, refused rather than rubber-stamped, with the change
> left blocked. **Two of the three have since been edited for real**, by Q1c, and have
> moved to `Updated`. The note is kept because the reasoning was right when it was
> written and because it is worth seeing a refusal survive long enough to be overtaken
> by the thing it refused to pretend had happened.

- CON-claim - the change reads `Claim` objects through the existing loader and adds no
  field, so the shape this claim describes is untouched.
- INV-regeneration-is-a-no-op - retired, and anchored to `derive.py#write_json`, which
  this change does not reach; a drift scan writes nothing, so the derived tier is not
  involved at all.

### Updated

- CON-anchor - anchored to `src/forge/anchor.py#parse_anchor`. The file is edited and
  the claim's prose gains nothing new, but the anchor's SHA must be restamped once the
  edit lands, and the claim is the natural home for the store-wide scan's existence.
- PIT-regex-across-newlines - the rule it states is untouched and still holds. It moved
  here from `Unaffected` because this change's own ledger flagged it: its anchor is
  whole-file on `src/forge/impact.py`, the G14 edit made it stale, and
  `forge drift confirm D-001` restamped the anchor and the review date. A restamp is a
  claim edit, the claim-touch rule said so, and the rule was right - which is the first
  time in this project the ledger and the account have argued with each other and the
  account lost.

- PIT-derived-self-reference - the rule it states is untouched: a drift scan produces
  no file, so it still cannot count itself. The definition gained an `evidence:` block
  naming the two tests that already enforced it, under the rule Q1c added - a claim
  that names no enforcer is a claim nothing catches when it breaks, and this one had
  two and said neither. A claim edit is a claim edit; the account says so.
- PIT-markdown-bullet-is-not-a-diff - same edit, same reason, naming
  `test_markdown_bullets_are_not_diff_markers`. No diff parsing is added by this
  change and the rule is unchanged.

### New

- PIT-bullet-continuation-lines - not about this change's code, but found by running
  this change through the lifecycle: `tasks.md` entries lose any `REQ-` id written on
  a wrapped line, which is the same defect M5 found in `## Uncertain` and fixed in
  `bootstrap.py#_bullets` without recording it. It recurred because it was never
  written down, which is the argument for the claim store in one line.

The store-wide scan itself gets no claim. It is a capability, recorded as
`REQ-drift-store-scan` in the spec delta, and it establishes no invariant that a
future change would trip over.

### Superseded

None. No ADR is retired by this change.

### At risk

None. The risk this section first recorded - that the store-wide entry point would
reimplement `parse_anchor`'s tolerance for malformed anchors rather than reuse it -
was retired in `design.md`, which makes reuse the whole approach, and is held by
`tests/test_anchor_store.py::test_a_malformed_anchor_does_not_abort_the_walk`.

CON-anchor was listed here as well as under Updated. The claim-touch rule rejected
that, correctly: a claim accounted for twice is a claim accounted for under whichever
heading the reader happens to see first. Recorded rather than silently deleted,
because the rule only caught it *after* implementation - see `design.md`.
