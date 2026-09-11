---
name: curate-knowledge
phase: sync
description: >
  Write what this change taught into the claim store: the claim-touch account,
  claim edits, candidate ratification, and drift evidence.
requires-kernel: ["forge impact", "forge trace", "forge check", "forge drift", "forge archive"]
reads: from-dag
writes: ["changes/${change}/impact.md", "docs/system/*.md", "docs/system/decisions/*.md"]
---

# curate-knowledge

## Announce

> Running `curate-knowledge`: accounting for the claims this change touched.

## What this does

Turns what the change learned into the permanent tier, and accounts for every
claim it touched. This write outlives the change, which is why it has its own
skill and its own gate.

## 1. Compute the set

```bash
forge impact --change <n>
```

That prints every claim the diff reaches: through an anchor, through a
component boundary glob, through an evidence file, or because the claim's own
definition was edited. The set is computed, so it is not a matter of opinion
and not something to argue down.

## 2. Account for every member

`changes/<n>/impact.md`:

```markdown
## Claims touched

### Unaffected
- CMP-payments - the new function lands inside the existing boundary; the
  component's responsibility is unchanged

### Updated
- INV-refund-cap - the bound now accumulates across partial refunds; it was
  per-refund

### Superseded
- ARC-3 -> ADR-0021 - the domain may now read the projection cache
```

One heading per claim, exactly one, and one honest sentence each.

`Unaffected` is cheap but not free, and the price is the point: it is what
keeps the claim count low, because every claim taxes every change that
touches its files. A store of forty good claims is worth more than four
hundred, and this is what makes that true economically rather than as advice.

Two things the kernel will refuse:

- a claim whose own definition this change edited, filed as `Unaffected`.
  Editing a claim and calling it unaffected is the move the rule exists to
  stop;
- `Superseded` without an ADR that exists. Superseding a claim is a decision,
  and a decision with no record is a preference.

## 3. Edit the claims

Edit the claim text in place, in its kind's file. Then, before showing
anyone, read each edit against three questions:

- **Does it say something the code cannot?** A claim whose prose is the
  identifiers of its own anchors rearranged into English is restatement. Say
  why it is this way and what breaks otherwise.
- **Is it anchored?** An unanchored claim can never be checked and will rot
  silently. `concept` and `constraint` are the only kinds exempt.
- **If `status: enforced`, does the named evidence still resolve?**
  `forge check --scope store` answers this; a test that was renamed leaves
  the claim claiming enforcement nothing provides.

Set `reviewed:` to today only where you actually re-read the prose and agreed
with it. It feeds review-debt reporting, and a date stamped by habit makes
that reporting useless.

## 4. Ratify candidates

```bash
forge trace <ID>
```

A candidate becomes a claim by being moved into its kind's file with the
`confidence` field dropped and `reviewed` set - and that is a human decision,
shown as a line item, not a batch. Anything not ratified stays a candidate;
it is still readable and still honest about what it is.

## 5. Retiring

A claim may be retired on exactly four grounds, and the ground is recorded:

1. stale or incorrect - the referent is gone, or it was never true;
2. mechanically enforced - a check now fails the violation it names, and the
   check is recorded. A tool that merely covers the topic does not count;
3. harmful or contradictory;
4. the human approved this specific deletion, asked as a line item.

Explicitly **not** grounds: brevity, nothing having failed lately, "the agent
could derive it", and the one that empties good files - "it is discoverable
somewhere in the repository".

Retired claims stay in the file, excluded from checks and budgets, so the
history of what we used to believe survives.

## 6. Drift

When `forge drift` reports a stale anchor on a claim, present the evidence and
stop:

- the fingerprint diff and which anchors moved;
- whether the discharging test still passes;
- whether the conformance rule still passes;
- what the commits in the range say they were doing.

Propose a verdict **only when a mechanical signal narrows it**: a now-failing
rule means V1 or V3 and never V2 or V4; a change that arrived through a
`forge` change with an ADR is V3, already accounted. With no such signal,
present the evidence and let the human classify.

The reason is measured rather than stylistic. Models detect documentation
faults well when the prose changed and badly when only the implementation
did - 21 to 43 points worse, which is the case drift always is - and their
confidence does not separate their correct judgements from their wrong ones.
A confident wrong proposal is worse than none, because it anchors the reader.

## 7. Gate G5 - the knowledge delta

Show the user the literal diff of the store, the folded spec, and one ledger
line per claim. Not a summary of intent - the actual text. One interaction,
and it is the difference between a curated store and an accreted one.

## Exit

```bash
forge check
forge archive --change <n>
```

`forge check` clean, G5 recorded, and the change archived with its spec delta
folded. Anything still only recorded in the archive is gone in practice - the
archive is never an input to any phase - so if it matters, it is in the
permanent tier by now.
