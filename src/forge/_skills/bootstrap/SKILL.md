---
name: bootstrap
phase: bootstrap
description: >
  Give an existing repository a store it can trust: derive the facts, propose
  candidates with fan-out subagents, and walk a human through ratifying them.
requires-kernel: ["forge bootstrap derive", "forge bootstrap review", "forge bootstrap seal", "forge check"]
reads: from-dag
writes: ["docs/system/candidates/*.md", "docs/system/OVERVIEW.md"]
---

# bootstrap

## Announce

> Running `bootstrap`: deriving what a scan can see, then proposing candidates.

## What this does

Three passes over a repository that has no store yet. The point is not to
describe the system - it is to make the first change possible. A scan that
emits two hundred confident claims about architecture and invariants is
producing exactly the noise this harness exists to prevent.

## Pass 1 - derive

```bash
forge bootstrap derive
```

Deterministic, re-runnable, and it claims nothing. Read what it prints, and
read the "not derivable" list at the bottom especially: architecture is about
40% inferable, invariants about 25%, rationale about 5%, and pitfalls 0%.
Those four are where a bootstrap goes wrong, and knowing that before pass 2
is the difference between a useful baseline and a liability.

## Pass 2 - propose candidates

Fan out. One subagent per topic, each reading `docs/system/derived/` plus the
code in its area, each writing `docs/system/candidates/<topic>.md` directly.
Subagents do not return content to you - a summary of a summary loses exactly
the specifics that make a claim checkable.

**Front-load `PIT-` and `CON-`.** A pitfall is knowledge paid for by a
failure; a concept prevents a class of wrong code by fixing a word. Neither is
derivable, both are cheap for a human to confirm, and both make the first
`investigate` noticeably better. Eight concepts and six pitfalls beat forty
inferred component descriptions on day one.

Sources worth reading for those two, in order: **any rules the project already
wrote down** - `AGENTS.md`, `CONTRIBUTING.md`, a `docs/` tree, an architecture
note; then test names and assertion messages; then validation and guard
clauses; then commit messages containing "fix" with an explanation; comments
that say why rather than what; issue or PR text if the repository carries it.

The first entry was missing from this list until a monorepo that states its own
three most important rules in `AGENTS.md` was bootstrapped without them being
read. A rule somebody wrote down is a pitfall that has already cost them
something, stated in their own words, and it is the cheapest evidence there is.
A conformance test that exists to stop one mistake - `no-mock-in-bundle.test.ts`
- is the same thing with the evidence attached.

Each topic file ends with a `## Uncertain` section naming what the agent could
not determine. That section is the most valuable output of the pass - it is
where the scan says where to look, instead of quietly filling the gap.

Five rules, checked by `forge check --scope candidates`:

- **Anchors required**, every kind, including `concept`. A ratified concept
  may be unanchored once a human agrees it is real; a guessed one with
  nothing to point at cannot be confirmed or ever re-checked.
- **`confidence` required.** High means the code says so plainly; medium
  means inferred from behaviour; low means a pattern seen twice.
- **No invented rationale.** A "because" needs an `evidence-from:` line **in
  the prose, after the fence** - not inside the ```claim block, where the
  check does not look. Or write `rationale: unknown` and let it become an
  interview question. A guessed reason reads exactly like a remembered one
  six months later.
- **Keep the fence valid YAML.** A bare `:` inside an unquoted value - an
  `evidence-from` quoting `if not stream: r.content`, say - fails the parse,
  and the claim then reports as having no anchor and no confidence rather
  than as unparseable. Quote it, or use a `>` block.
- **An invariant names what enforces or proves it**, or it is not an
  invariant yet - it is a question. Whether a property is *required* or
  merely currently true is not in the code.

Cap the total at forty. The cap is not about repository size; it is about how
much one unattended scan may add to a store nobody has checked.

## Pass 3 - ratify

```bash
forge bootstrap review
```

That writes `docs/system/candidates/REVIEW.md`: candidates ordered pitfalls
and concepts first, batched eight at a time, every verdict prefilled
`reject`, and the `## Uncertain` questions collected at the end.

Walk the human through one batch at a time. For each candidate show the
claim, its anchors, and the evidence it was inferred from, then ask for one
of `ratify`, `edit`, `reject` or `defer`. Interleave the uncertain questions
where they bear on a candidate - a question that settles one is worth more
than the candidate.

Two things not to do:

- **Do not ask what a scan can answer.** The derived tier already knows the
  languages, the entry points, the test count and the dependency graph.
  Asking wastes the one resource a review has, which is the human's patience.
- **Do not argue for a candidate.** The default is reject, and that is the
  posture rather than a starting position to be negotiated up. Baseline
  completeness is not the goal; baseline trustworthiness is.

## Seal

```bash
forge bootstrap seal
forge sync derived
forge check
```

Seal writes the ratified claims with anchors stamped at HEAD and `reviewed`
set to today, an `OVERVIEW.md` whose first paragraph a human still has to
replace, and the baseline record in `ADR-0001` - including what was
deliberately *not* ratified. That last part matters: a store with no record
of its own gaps is ambiguous between "nothing to say here" and "nobody
looked", and those call for opposite responses from the next reader.

Unratified candidates stay where they are, readable and not citable.

## Exit

Report the numbers plainly: how many candidates were proposed, how many
ratified, and which kinds. Then say the thing that is easy to leave out - the
first change that touches an area will produce better knowledge about it than
this scan did, because that change will have a reason, a test, and a human
who cared.
