# M1 — Anchor stability measurement

**Date:** 2026-09-10 · **Verdict:** **PASS** — 0.61% false positives, 0% false negatives; proceed to M2 (§5)
· **Gate:** [MVP.md](../../MVP.md) M1 · **Follow-up:** the residual 0.61% was closed at the start of M2 (§3.2)

[MVP.md](../../MVP.md) makes M1 a stop condition: before building M2–M5, measure whether
anchor-based staleness detection is quiet enough to be read. The bet the whole design rests on is that
a claim anchored to `path#Symbol@sha` can be checked mechanically without drowning a reviewer in false
positives. If a routine refactor produces fifteen spurious drift entries, the ledger becomes noise and
gets ignored — and an ignored ledger is worse than none, because it looks like coverage.

Reproduce:

```bash
python tools/measure_anchors.py --repo <repo> --commits 200 --anchors 30 --json out.json
```

```bash
python tools/perturb_anchors.py --repo <repo> --samples 25 --json out.json
```

---

## 1. Method

Two experiments, because one is not enough.

### 1.1 Observational replay (`tools/measure_anchors.py`)

Place 30 anchors on real declarations at a commit 200 commits back, then walk the mainline
(`--first-parent`) one commit at a time. At each step the baseline is the *previous* commit, so a
verdict describes one step of the project's history. An anchor is evaluated only when the commit touches
its file (both sides of a rename count). When an anchor reports `missing` it is retired from the replay
and the reason recorded.

Anchor selection is **biased toward files that change during the window**. Anchoring only to quiet code
would make every verdict `fresh` and the false-positive rate trivially zero. The bias is stated here
rather than buried: this measures the population a real claim store cares about.

A cumulative view is also reported — baseline fixed at the start, head at the end — because that is what
a ledger actually sees when the baseline is the last human confirmation, many commits back.

### 1.2 Controlled perturbation (`tools/perturb_anchors.py`)

The replay measures *volume*. It cannot measure the *false-positive rate*, and the reason is itself a
finding: **across 600 replayed commits in three repositories there were zero pure renames (`R100`) and
zero formatting-only commits.** These projects run formatters continuously, so the two failure modes the
design most fears never appear as isolated commits in recent history. An empty population yields no rate,
and reporting "0 false positives" from an empty population would be dishonest.

So the second experiment borrows the method from arXiv:2604.03447 — the same TRACE paper cited in
[RESEARCH.md](../../RESEARCH.md) for the opposite finding: take real code, inject perturbations whose
ground truth is known by construction, measure. Perturbations are applied *through tree-sitter*, so
"rewrite every comment" edits exactly the comment nodes and nothing else, which is what makes the label
defensible.

| Family | Ground truth | A wrong answer is |
|---|---|---|
| **neutral** — comment rewrite, uniform reindent, blank lines, trailing whitespace, CRLF conversion, quote swap, pure file move, move + comment rewrite | behaviour unchanged | a **false positive** (noise) |
| **substantive** — flip an operator inside the symbol, delete a statement from its body, rename the declaration | behaviour changed | a **false negative** (a lie) |

### 1.3 What is deliberately not measured

There is no mechanical ground truth for these, so they are excluded from the rates rather than guessed:

- comment-only edits *inside* an otherwise-changed file;
- semantically neutral refactors an author would call cosmetic (extract variable, reorder independent
  statements, rename a local);
- whether the *claim* attached to an anchor is still true. Nothing measures that, which is the entire
  reason the design requires a human verdict (SYSTEM_KNOWLEDGE.md §6).

### 1.4 Subjects

| Repository | Language | Commits available | Why |
|---|---|---|---|
| `Fission-AI/OpenSpec` | TypeScript | 400 | Heavy real refactoring, including a documented monolith-to-modules split |
| `SWE-agent/mini-swe-agent` | Python | 528 | Small, actively edited, hot files |
| `oasdiff/oasdiff` | Go | 712 | Third grammar; large mature codebase |

Shallow clones (`--depth 400`), replay confined inside the window.

---

## 2. Observational results

600 commits replayed, 90 anchors, 826 evaluations, **0 errors**.

| Repository | Commits | Touching an anchor | Evaluations | fresh | shifted | stale | missing |
|---|---|---|---|---|---|---|---|
| OpenSpec (TS) | 200 | 115 | 401 | 300 | 76 | 24 | 1 |
| mini-swe-agent (Py) | 200 | 80 | 170 | 117 | 35 | 12 | 6 |
| oasdiff (Go) | 200 | 88 | 255 | 187 | 65 | 1 | 2 |
| **Total** | **600** | **283** | **826** | **604** (73.1%) | **176** (21.3%) | **37** (4.5%) | **9** (1.1%) |

### 2.1 Noise volume

| Repository | `stale+missing` per touching commit | `shifted` per touching commit |
|---|---|---|
| OpenSpec | 0.217 | 0.661 |
| mini-swe-agent | 0.225 | 0.438 |
| oasdiff | 0.034 | 0.739 |
| **Combined** | **0.163** | **0.622** |

Per *replayed* commit (not just touching ones) the hard-signal rate is 46/600 = **0.077**.

### 2.2 The headline number

**73.1% of the time that a commit touched an anchored file, the anchored symbol was unchanged.**

That is the precision symbol-level anchoring buys over file-level anchoring, and it is the single most
consequential number here. A file-level anchor — which is what every prose-based approach in the corpus
effectively has — would have raised all 826 evaluations as drift. Symbol-level anchoring raises 46 hard
ones: an **18× reduction in ledger volume**, before any judgement is applied.

The `shifted`/`stale` split earns its keep too. Of the 222 non-fresh verdicts, 176 (79%) are body-only
changes. Surfacing those by default would quadruple the ledger; suppressing them by default leaves 46
entries across 600 commits of three real projects.

### 2.3 The same story in one command

Four anchors on OpenSpec, baseline 120 commits back:

```
$ forge drift \
    "src/core/artifact-graph/schema.ts#parseSchema" \
    "src/core/artifact-graph/state.ts#detectCompleted" \
    "src/core/validation/task-numbering.ts#findTaskNumberingIssues" \
    "src/core/artifact-graph/" \
    --repo ../OpenSpec --baseline 1da6dfa

src/core/artifact-graph/schema.ts#parseSchema                  fresh     symbol parseSchema (function_declaration)
src/core/artifact-graph/state.ts#detectCompleted               fresh     symbol detectCompleted (function_declaration)
src/core/validation/task-numbering.ts#findTaskNumberingIssues  missing   ... did not exist at the baseline; the anchor postdates its @sha
src/core/artifact-graph/                                       stale     tree hash comparison
```

The directory anchor — which is what a prose map or a component glob amounts to — reports `stale`,
because *something* under `src/core/artifact-graph/` changed in 120 commits. The two symbol anchors
inside that same directory report `fresh`, because the specific functions a claim would be about did
not. A reviewer following the directory anchor reads a diff and finds nothing to decide; a reviewer
following the symbol anchors is not called at all. That is the 18× in §2.2, in four lines.

The third anchor is the other useful behaviour: an anchor whose target did not exist at its own
baseline is an authoring bug, and it is reported as such rather than as drift.

Rename following was also checked against a **real** rename rather than only synthetic fixtures.
OpenSpec commit `39bebef` ("feat(cli): merge init and experimental commands") moves
`src/commands/experimental/*` to `src/commands/workflow/*` at `R100` — byte-identical content. An
anchor still written with the old path resolves cleanly across it:

```
src/commands/experimental/instructions.ts   fresh   whole-file comparison
                                                    [moved src/commands/experimental/instructions.ts
                                                     -> src/commands/workflow/instructions.ts]
```

### 2.4 Cumulative view (fixed baseline, 200 commits later)

| Repository | fresh | shifted | stale | missing |
|---|---|---|---|---|
| OpenSpec | 16 | 10 | 3 | 1 |
| mini-swe-agent | 7 | 9 | 9 | 5 |
| oasdiff | 10 | 17 | 1 | 2 |
| **Total (90 anchors)** | **33** (37%) | **36** (40%) | **13** (14%) | **8** (9%) |

Read that as review debt: if nobody re-anchors for 200 commits, about a third of anchors are still
verified, 40% need a glance, and roughly a quarter (23%) need real attention. That is a workable
maintenance load for a store of a few dozen claims, and it is an argument for re-anchoring per change
(which `forge sync` does) rather than in periodic sweeps.

### 2.5 Retirements

9 anchors reported `missing` mid-replay (1 OpenSpec, 6 mini-swe-agent, 2 oasdiff) and were retired.
Spot-checking the recorded reasons, these are genuine deletions and renames of the declaration, not
tooling failures — but note this is the one figure in §2 resting on inspection rather than ground truth.

---

## 3. Perturbation results

75 sampled declarations, 656 cases.

| | Neutral cases | False positives | Substantive cases | False negatives |
|---|---|---|---|---|
| OpenSpec (TS) | 166 | **0** | 52 | **0** |
| mini-swe-agent (Py) | 169 | **0** | 60 | **0** |
| oasdiff (Go) | 159 | **3** | 50 | **0** |
| **Total** | **494** | **3** (0.61%) | **162** | **0** (0.00%) |

Per neutral perturbation:

| Perturbation | Cases | Verdicts |
|---|---|---|
| rewrite every comment | 56 | all `fresh` |
| uniform reindent | 57 | all `fresh` |
| insert blank lines | 75 | all `fresh` |
| trailing whitespace | 75 | all `fresh` |
| convert to CRLF | 75 | all `fresh` |
| swap quote style | 25 | all `fresh` |
| pure file move | 75 | all `fresh` |
| move + rewrite comments | 56 | 53 `fresh`, **3 `missing`** |

Per substantive perturbation:

| Perturbation | Cases | Verdicts |
|---|---|---|
| flip an operator in the body | 50 | 30 `stale`, 20 `shifted` |
| delete a statement from the body | 37 | 37 `shifted` |
| rename the declaration | 75 | 39 `missing`, 36 `stale` |

Reading these:

- **Formatting is fully absorbed.** Reindentation, blank lines, trailing whitespace, CRLF conversion and
  quote-style swaps produced not one false verdict across three languages. This is the property the
  whole mechanism depends on, because formatters touch every file routinely.
- **Pure moves are fully absorbed.** 75/75 `fresh`, and rename following was separately confirmed
  against a real `R100` rename in OpenSpec's history (§2.3).
- **Nothing real was missed.** 162 substantive perturbations, zero `fresh` verdicts. Every operator
  flip, deleted statement and renamed declaration was surfaced.
- **`rename_declaration` splits 39 `missing` / 36 `stale`** because the perturbation renames only the
  declaration and leaves its call sites, so the old name is still present in the file and the verdict
  degrades to a whole-file comparison. Both are non-fresh, so neither is a false negative; a real
  refactor would rename the call sites too and the split would move toward `missing`.

### 3.1 The three remaining false positives

All three are the same case: **move + rewrite comments** on a Go file, reported `missing` instead of
`fresh`. Diagnosed rather than guessed.

The perturbation collapses every comment to `// rewritten`. On a comment-heavy Go file — and Go style
means most exported identifiers carry several lines of doc comment — that shrinks the file
dramatically. In a reproduction, 510 bytes became 161, and `git diff --find-renames` measured the
similarity at **13%**, well under its 50% default. Git therefore reports add + delete rather than a
rename, the anchor cannot follow the move, and the verdict is `missing`.

Two things follow, and they point in opposite directions:

- **The perturbation is more violent than reality.** A 68% size reduction from a comment edit is not
  what a real comment rewrite looks like, so 3/159 over-states the rate a real repository would see.
- **The limitation is real anyway.** Any move combined with a large edit can fall below git's rename
  threshold, and the resulting verdict is `missing` — the *blocking* status, which is the worst kind of
  false positive to have.

**Lowering the threshold was considered and rejected.** `--find-renames=10%` recovers this exact case,
but a global 10% threshold invites spurious rename matches between unrelated files, which would trade a
visible false positive for an invisible wrong answer. Tuning the knob until the number looks better is
gaming the measurement.

The right fix is the one this measurement produced evidence for:
**content-addressed relocation** — when a path is gone at head, look for a declaration at head whose
fingerprint matches the baseline's, and follow that. This is option **B** in
[OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) Q2, which I had dismissed as unnecessary before measuring.
It was implemented at the start of M2 and the case is closed — see §3.2.

### 3.2 Follow-up: the residual defect, closed in M2

*Added 2026-09-10, after the M1 verdict. The numbers above are left exactly as measured — a measurement
report that gets edited to look better is not a record of anything.*

Content-addressed relocation was implemented at the start of M2 (`_relocate` in `src/forge/anchor.py`)
and oasdiff was re-measured on the same samples and seed:

| | Neutral cases | False positives |
|---|---|---|
| oasdiff, at the M1 verdict | 159 | 3 |
| oasdiff, after relocation | 159 | **0** |
| **All three repositories** | **494** | **0** (was 3) |

False negatives stayed at 0/162.

How it works, and what it deliberately refuses to do: when a path is absent at head, the anchored
symbol's name is looked up with `git grep` at head, each candidate is parsed, and a match is accepted
**only on identical fingerprint** — content identity, not git's similarity heuristic. A match is
accepted only when it is unique; two equally good candidates report `missing` with the count, because
silently re-anchoring a claim to the wrong code is worse than asking. A same-named symbol with a
different body or signature is not a match.

This keeps the earlier rejection intact: the fix is not "lower git's rename threshold and hope", which
would trade a visible false positive for invisible wrong matches. It is a narrower, stricter search
that runs only in the case git has already given up on.

### 3.3 Three defects the perturbation harness found in its own labels

Before the numbers above, two earlier runs reported 17/171, 14/182 and 3/159 false positives. **Every
one of those was a bug in the harness's ground truth, not in the detector** — a "neutral" perturbation
that actually changed behaviour:

1. **Whitespace edits inside multi-line literals.** A template literal, a docstring or a Go raw string
   carries its own whitespace as content. Fixed by making the line-based perturbations literal-aware.
2. **Requoting triple-quoted strings.** `text[1:-1]` on `"""Doc."""` yields `'""Doc.""'` — a different
   string. Fixed by excluding them.
3. **Reindenting around a protected literal.** Doubling a `def` line while holding its docstring back
   produced code CPython rejects with *"expected an indented block after function definition"*.
   Tree-sitter is error-tolerant and parsed it anyway. Fixed by skipping files with multi-line literals.

Rather than only fixing the three, the harness now **discards** any neutral case whose perturbed source
fails to parse — tree-sitter for every language, plus CPython for Python, because tree-sitter's
error tolerance is exactly what hid defect 3. A future ground-truth bug therefore shows up as a
shrinking population, not as a fabricated defect. In the final run that guard discarded nothing, which
is the intended state: the fixes are at the source, not behind the net.

That the harness's own bugs outnumbered the detector's is worth stating plainly. It is also the reason
to trust the final number more than the first one.

---

## 4. Defects the measurement found

Both were found by the perturbation harness, not by the replay, and neither would have shown up as a
crash — they would have shown up as ledger noise, which is exactly the failure this milestone exists to
catch. Both now have regression tests.

### 4.1 Formatter noise flipped the fingerprint

The first fingerprint hashed every node of the *concrete* syntax tree. A trailing comma added by a
formatter, or an added semicolon, changed the digest. Since prettier and gofmt do this routinely, every
formatting pass would have marked every anchor in the file stale.

**Fix:** hash the *abstract* tree — drop punctuation-only anonymous nodes, keep every named node, keep
anonymous nodes that fill a named field (tree-sitter exposes operators as the `operator` field, so
`a + b` and `a - b` still differ), and keep anonymous leaves containing a word character (keywords such
as `number`, `async` and `true` are anonymous leaves under a wrapper node). An intermediate version that
dropped *all* anonymous nodes erased the difference between `a: number` and `a: string`, which the tests
now pin.

### 4.2 Quote style was absorbed in TypeScript and reported as drift in Python

Python's grammar exposes string delimiters as **named** nodes (`string_start`, `string_end`); TypeScript
leaves them anonymous. So the same reformatting — a formatter switching quote style — was invisible in
one language and drift in the other. The perturbation harness caught this at a 2-in-3 false-positive
rate on Python samples.

**Fix:** normalise `string_start` / `string_end` by stripping quote characters while keeping any prefix,
so `'` and `"` collapse but `f"` and `rb"` stay distinguishable from `"`.

### 4.3 A renamed declaration hid behind a substring test

`symbol_appears_textually` separates "the symbol is gone" (blocking `missing`) from "our declaration
table cannot parse this form" (degrade to a whole-file comparison). It used a substring test, so
renaming `handler` to `handlerV2` still "found" `handler` and the verdict was downgraded from `missing`
to `stale`. Right family, wrong status, and it would have hidden renames.

**Fix:** match on word boundaries.

---

## 5. Verdict against the stop condition

**PASS — proceed to M2 as designed, with one deferred fix.**

MVP.md's table:

| Result | Action |
|---|---|
| < 0.5 spurious `stale` per commit | proceed as designed |
| 0.5–2 | proceed, but suppress `shifted` by default and revisit anchor granularity |
| > 2 | **stop** and redesign per OPEN_QUESTIONS.md Q2 |

Two clarifications the measurement forced on that table:

1. The replay measures **total** hard-signal volume (0.077 per replayed commit, 0.163 per touching
   commit), not *spurious* volume. Volume alone does not discharge the gate.
2. The *spurious* rate can only come from the perturbation experiment, because recent history in these
   repositories contains none of the relevant cases.

Against both readings the result is inside the first band by a wide margin:

| Measure | Value | Band |
|---|---|---|
| Hard signals per replayed commit (total, not spurious) | 0.077 | < 0.5 |
| Hard signals per commit touching an anchored file | 0.163 | < 0.5 |
| Spurious verdicts per behaviour-preserving change | **0.0061** | < 0.5 by ~80× |
| Missed behaviour-changing edits | **0.0000** | — |

**Consequences accepted with this verdict:**

- `shifted` is **suppressed by default** in the ledger, and only `stale` and `missing` demand a verdict.
  That is not a concession to the second band — it is the design decision the data supports, since
  body-only edits are 79% of non-fresh verdicts and every one of them is a true positive that a
  reviewer usually does not need.
- Content-addressed relocation (§3.1) was deferred to M2 as a named follow-up. It has since been
  implemented and the floor is now 0.00% (§3.2).
- The residual risk is unchanged and unmeasured: semantically neutral refactors (§1.3, §6). The true
  false-positive rate is higher than 0.61% by an unknown margin, and no experiment here bounds it.

**What this does not establish.** That anchored claims are *useful* — only that they are quiet enough
to be read. Whether the claim attached to an anchor is worth having, and whether the whole lifecycle
improves outcomes, remains [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) Q1, and nothing here touches it.

---

## 6. Limitations

- **Anchor selection is biased toward churn** (§1.1). The false-positive rates are therefore pessimistic
  relative to a store anchored to stable code, and the volume figures are optimistic relative to nothing
  at all.
- **Only declarations with a body were perturbed.** `tools/perturb_anchors.py` samples symbols that have
  a `body` field and span more than 120 bytes, i.e. functions, methods and classes. Interfaces, type
  aliases, enums and `const` declarations — the forms an `API-` or `DAT-` claim would most likely anchor
  to — are covered by unit tests but not by the perturbation rates. They have no body, so `shifted` can
  never apply to them and every real change reads as `stale`; that is more conservative, not less, but it
  is unmeasured on real code.
- **Three languages, three repositories.** No C, C++, Java, Rust, Ruby or SQL. Repositories without a
  tree-sitter grammar take the coarse path, which absorbs trailing whitespace and line endings but *not*
  a reflow across lines — a documented and tested limit.
- **Shallow clones.** Rename following across the `--depth 400` boundary is untested.
- **Mainline only.** `--first-parent` skips side-branch commits, so a squash-merge project is
  well modelled and a merge-heavy one is not.
- **No human labelling.** Semantically neutral refactors are not in the false-positive rate, so the true
  rate is *higher* than reported here. How much higher is unknown and is the main residual risk.
- **One measurement, one author.** The numbers were produced by the same code they evaluate. The
  regression tests in `tests/` are the guard against that, not a substitute for independent replication.
