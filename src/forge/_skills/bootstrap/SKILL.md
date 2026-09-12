---
name: bootstrap
phase: bootstrap
description: >
  Give an existing repository a store it can trust: derive the facts, propose
  candidates one topic at a time, and walk a human through ratifying them.
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

Work one topic at a time, and **write each topic's file directly** -
`docs/system/candidates/<topic>.md`, from whoever read the code. Content must
not be summarised back to a coordinator and re-written: a summary of a summary
loses exactly the specifics that make a claim checkable, which is the anchor,
the symbol and the line that proves it.

If this host can run agents in parallel, one per topic is the fast way to do
it. If it cannot, do the topics in sequence - the requirement is the direct
write, not the fan-out. This skill names no host feature anywhere else, and
should not name one here either.

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

**Then ask where the knowledge already lives.** A rule the project wrote down
is the best source for a candidate and the worst reason to keep one: an agent
that finds the document gets the knowledge without the claim. Measured -
`docs/measurements/q1-does-the-store-help.md` - three agents pointed at a
claim store and three pointed only at the code avoided the same trap at the
same rate, and every agent in the second arm found the rules file unaided and
cited the exact section the claim had been derived from.

So for each candidate drawn from a document, answer one question before
writing it: **what does the claim add that its source does not?** Two answers
are good ones. An **anchor** is real added value - prose does not know when
the code under it moved, and that is the one thing a claim does that a rules
document cannot. **Reach** is the other - knowledge whose record is nowhere
near the work, where a reader editing that file would never think to look.

If the answer is neither - if the claim is a shorter restatement of a section
an agent reads anyway - do not write it. Put the pointer in `OVERVIEW.md`
instead and spend the cap on something with no written home.

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

A candidate whose evidence names a document in this repository carries a
`restates:` line. It is not a defect - it is where good candidates come from -
but it is the fact most worth weighing, and the sheet asks the question
plainly: would a reader find that document anyway? If yes and the claim adds
no anchor the document lacks, `reject` is the right verdict and the store is
better for it.

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
