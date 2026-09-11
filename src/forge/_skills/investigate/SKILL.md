---
name: investigate
phase: investigate
description: >
  Read the code before changing it. Produces investigation notes and candidate
  claims with confidence, never edits to the ratified store.
requires-kernel: ["forge trace", "forge drift", "forge instructions", "forge status"]
reads: from-dag
writes: ["changes/${change}/investigation.md", "docs/system/candidates/*.md"]
---

# investigate

## Announce

> Running `investigate`: reading the system before changing it.

## What this does

Answers "how does this actually work here" from the code, and writes down what
was learned in two places with two different standards of proof: notes for
this change, and candidate claims for the store.

Run this in a fresh context. The point is to read the system rather than to
recall it, and a context already full of the request will find what it expects.

## 1. Start from what is already known

```bash
forge instructions investigate --change <n>
forge status
```

For every domain word in the request, check whether the store already defines
it:

```bash
forge trace CON-<word>
```

A claim that already exists is the cheapest possible answer and it has been
reviewed by a human. Reading the code to re-derive it is the most common way
an investigation burns its budget.

## 2. Read the code, in this order

1. **Entry points** - `docs/system/derived/inventory.json` lists them. Start
   where the system starts, not where the request points.
2. **The path the request touches**, followed end to end once.
3. **The tests around it.** They record what someone believed had to hold,
   which is often the only surviving statement of intent.
4. **The edges**: error paths, retries, transactions, anything concurrent.
   This is where the pitfalls live and where reading is hardest to replace.

Check the anchors of any claim you rely on:

```bash
forge drift "<path>#<Symbol>" --baseline <sha>
```

A claim whose anchor is stale is not a fact yet. Say so in the notes rather
than building on it.

## 3. Write the notes

`changes/<n>/investigation.md`, structured so the next phase can act on it:

- **How it works today** - the actual sequence, with file and symbol
  references. Not a summary of the code; the parts a reader could not guess.
- **Where the request lands** - the specific functions and files.
- **What surprised you.** The single most valuable section, and the one that
  disappears if you write the notes from memory at the end.
- **What you could not determine**, and what would settle it.

Cite claims by ID, never by paraphrase. `INV-refund-cap`, not "the refund
rule". That is what makes `grep -r INV-refund-cap` a complete answer later.

## 4. Write candidates, not claims

Anything learned that is worth keeping beyond this change goes to
`docs/system/candidates/<topic>.md` as a candidate:

```claim
kind: pitfall
status: proposed
truth-source: decision
anchors: ["src/pay/retry.py#send"]
confidence: medium
reviewed: <today>
```

Three rules, each with a reason:

- **`status: proposed` and a `confidence`, always.** A candidate is a
  plausible statement, and plausible-but-wrong knowledge is worse than none.
  The tier exists so "plausible" is a state rather than something laundered
  into truth.
- **Anchored, or not written.** An unanchored claim can never be checked and
  will rot silently. If you cannot point at code, it is a note, not a claim.
- **No invented rationale.** If you do not know *why* the code is like this,
  write what it does and mark the why unknown. A guessed reason reads exactly
  like a remembered one six months later.

Confidence is about your evidence, not your feeling: `high` means the code
says so plainly; `medium` means you inferred it from behaviour; `low` means it
is a pattern you noticed twice.

## 5. Highest value per line

Prefer `PIT-` and `CON-` candidates over anything restating structure.

A pitfall is knowledge that was paid for by a failure and cannot be derived
from anything. A concept prevents a class of wrong code by fixing a word.
Both are invisible to static analysis, and both are what generated
documentation never contains. A component claim that lists directories is
work the reader could have done with `ls`.

## Exit

Notes written, candidates written, and one paragraph to the user: what you
found, what you now recommend, and what is still unknown. Ratifying candidates
is a human action and belongs to `curate-knowledge`, not here.
