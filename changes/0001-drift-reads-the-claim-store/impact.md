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

> The three `PIT-` claims below are reported by the kernel as having had "their own
> definition edited", because this change appends one new claim to the end of
> `docs/system/pitfalls.md` and that test is file-level (`impact.py:207`). Their
> definitions were not touched. They stay here, under the heading that is true, and
> the change stays blocked rather than being unblocked by writing `Updated` about
> claims nobody updated. Filing a claim under a heading to satisfy a checker is the
> exact rubber-stamping OPEN_QUESTIONS.md Q3 asks about.

- CON-claim - the change reads `Claim` objects through the existing loader and adds no
  field, so the shape this claim describes is untouched.
- INV-regeneration-is-a-no-op - retired, and anchored to `derive.py#write_json`, which
  this change does not reach; a drift scan writes nothing, so the derived tier is not
  involved at all.
- PIT-derived-self-reference - about a census counting its own output; a drift scan
  produces no file, so it cannot count itself.
- PIT-regex-across-newlines - no new multi-line regex is introduced by this change.
- PIT-markdown-bullet-is-not-a-diff - no diff parsing is added by this change.

### Updated

- CON-anchor - anchored to `src/forge/anchor.py#parse_anchor`. The file is edited and
  the claim's prose gains nothing new, but the anchor's SHA must be restamped once the
  edit lands, and the claim is the natural home for the store-wide scan's existence.

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
