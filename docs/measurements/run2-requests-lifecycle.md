# Run 2 — the whole lifecycle on a repository nobody here had read

> `requests` 2.34.2, obtained as the published sdist and committed to a fresh git
> repository. Run on 2026-09-11, after the five repairs of `5ad73f0`. The question
> this run existed to answer: **did those repairs actually clear the path, or did
> they only clear it on the repository that produced them?**

The answer is yes for four of the five, no for one, and the run found twenty more
things. One of those — G16 — I got wrong, and the correction is recorded in place
rather than quietly edited away, because the mistake is instructive: I read an error
message instead of the code that produced the verdict.

---

## 1. What ran

| Pass | Result |
|---|---|
| `forge init` | clean |
| `forge bootstrap derive` | 95 files, 88 import edges, 20 cycles, 345 tests, 35 Python files, 11,526 lines |
| `forge bootstrap` pass 2 | 14 candidates (6 `PIT-`, 8 `CON-`) + 14 `## Uncertain` questions, from two subagents |
| `forge check --scope candidates` | **5 errors** in candidates both subagents reported as clean |
| `forge bootstrap review` / `seal` | 12 ratified, 2 rejected → trimmed to **10** under budget pressure |
| Track C change, `0001-content-may-be-none` | all five gates passed |
| `forge verify` | **zero failing conditions** — the first time anywhere |
| `forge archive` | blocked; reachable only with `--force` |
| Final `forge check` | **0 errors**, 9 warnings |

Derivation reproduced the M5 numbers **exactly**, five days and one machine apart.
That is the derived tier's central promise, now observed twice rather than asserted.

---

## 2. The change

`Response.content` is annotated `-> bytes`, assigns `None` when `status_code == 0` or
`raw is None`, and `test_empty_response_has_content_none` pins that. The annotation
was wrong about a value the library returns on purpose, so a type checker reported the
correct handling of that value as dead code.

The change annotates it `bytes | None`, documents when `None` happens, and adds
`test_response_content_annotation_admits_none`, which reads the annotation itself with
`typing.get_type_hints` — pinning the *agreement* between behaviour and declared type,
which is the pair that had drifted.

629 tests still pass. `ruff` is clean.

---

## 3. Did the repairs hold?

| Repair | On requests |
|---|---|
| **F15** per-claim edit detection | **held.** Only `CON-content-text-json` was flagged as having its definition edited, though nine claims share `domain.md` |
| **F16** provisional requirements | **held.** `forge trace REQ-content-absent-is-typed` named the delta defining it, the test discharging it, and the change |
| **F10/F13** command resolution | **held, and paid for itself.** `'pytest' is not on PATH, but .venv/Scripts/pytest.exe exists` on the first run, against the ~25 minutes of suite time run 1 spent discovering the same thing |
| **F5** wrapped tasks | held; no recurrence |
| **F2** artifact templates | **did not hold — it introduced G17a.** `--write NAME` writes `spec/NAME.md`, but the fold expects `spec/<capability>/spec.md` |

Four of five. The fifth was a defect I shipped three hours earlier, found by the first
attempt to use it on unfamiliar code.

---

## 4. The two findings that change the roadmap

### G14 — the claim-touch set is matched against the blast radius, not the diff

[impact.py:218](../../src/forge/impact.py:218) tests `path in radius`, where
`radius = changed | reverse_deps`. [SYSTEM_KNOWLEDGE.md §9.2](../../SYSTEM_KNOWLEDGE.md)
defines `claim_touch_set(D)` on the **diff** `D`.

A one-line annotation change to `models.py` touched **10 claims out of 10**. Eight are
anchored to `sessions.py` and `utils.py`, which the diff never opened; they are in the
set because those files import `models.py`. On a library with 88 import edges and 20
cycles, every change touches every claim.

`impact.md` for this change therefore carries nine `Unaffected` sentences, each honest
and each about code the change could not have reached. `Unaffected` is meant to cost
one sentence, and that price is the point — but the price is supposed to be paid for
claims the diff actually touched. The first thing a new user learns here is that the
account is a formality, which is precisely the rubber-stamping
[OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) Q3 names.

The blast radius answers *what might this affect?* and is a reading aid. The touch set
answers *what must you account for?* and is an obligation. Conflating them makes the
obligation unbounded.

This is the same failure as F15 through a second door: F15 fixed
claims-sharing-a-definition-file, and this is claims-sharing-an-import-graph.

### G16 — `forge archive` is unreachable on any repository today

> **This finding is wrong, and the correction is more useful than the original.**
> Probed on 2026-09-11 by re-running the same change with `build` and `typecheck`
> declared: the verdict reached `pass` and `forge archive` went through the
> verification gate. `pending` conditions do **not** block the verdict —
> [verify.py:301](../../src/forge/verify.py:301) computes `unproven` from
> `unavailable` only. I read the blocker's error message, which lists pending
> conditions among the "failing" ones, and did not check the code that produces the
> verdict. Struck through below; what it got right is separated out as G19 and G20.

~~Archive blocks on a verdict of `unproven`. `unproven` is produced by three conditions
the **kernel** owes — `DRIFT.md`, `DEBT.md`, and a baseline test run — which no user
action can satisfy.~~

What was actually in the way, on `requests`:

- **G19 — a project cannot say "not applicable".** The verdict was `unproven` because
  `commands.build` and `commands.typecheck` were undeclared, and `unavailable` blocks
  `pass`. A library with no build step has no way to record that, so it must either
  declare a fake command or never reach `pass`. The distinction the report needs is
  between *this project owes us a command* and *this project has no such step*.
- **G20 — `forge verify` invalidates its own freshness condition.** It writes
  `verification.json`, a tracked file, which changes `inventory.json`, which makes
  `derived_fresh` fail — in the very report that just created the file. Reaching
  `pass` takes `verify` → `sync derived` → commit → `verify` again, and nothing says
  so. Both earlier green runs had done that sequence by accident.

The blocker's message is worth fixing too: it lists every condition whose status is
not `pass`, which puts the three `pending` ones in a line headed "failing" — the
misreading that produced this finding.

The fold really had never been executed before this run, but `--force` was not the
only route to it; a passing verdict was.

---

## 5. Every finding

| # | Finding |
|---|---|
| G1 | `forge doctor` takes no `--repo`, though it is the first command the README tells a new user to run |
| G2 | `bootstrap derive` prints `stack` as a raw Python dict repr — quotes, `None`, nested braces |
| G3 | Derivation reproduced the M5 numbers exactly (positive) |
| G4 | `check --scope candidates` reports the *consequences* of an unparseable claim (no anchor, no confidence) and not the cause. The cause appears only under the full `forge check`, which the bootstrap skill does not tell you to run |
| G5 | `evidence-from` is accepted in the claim fence and honoured only in the prose. Nothing documents which, so a candidate citing CVE-2024-47081 and a named regression test is told to "add `evidence-from:`" |
| G6 | The linter found 5 defects in candidates both subagents reported as clean (positive) |
| G7 | `bootstrap seal` produces a store `forge check` immediately rejects — 467 always-loaded lines against a budget of 400 |
| G8 | `store.placeholder` cannot tell a placeholder from a quotation: two errors on text quoting a `TODO:` that exists in `src/requests/adapters.py`, inside a code span, inside a question *about* it |
| G9 | `store.derivable_smell` agreed with a human reviewer twice, unprompted (positive) |
| G10 | There is no way to un-ratify. Seal removes a ratified candidate from `candidates/`, so deleting it from the store leaves ADR-0001 dangling; recovery was `git show` and a hand edit |
| G11 | The dangling-reference error prints its location as `unknown`, though `forge trace` names the referrer in one command |
| G12 | `bootstrap seal` copies the candidates' `## Uncertain` section into the always-loaded store — 79 lines of open questions costing budget in every agent context forever. Moving them to ADR-0001 took the store from 3 errors to 0, and was the real cause of G7 |
| G13 | The spec template titles the file with the change name, not the capability |
| **G14** | **The claim-touch set is matched against the blast radius, not the diff** |
| G15 | `__pycache__/*.pyc` appears in the blast radius |
| ~~G16~~ | ~~`forge archive` is unreachable on any repository today~~ — **wrong**, see the correction in §4 |
| **G19** | **A project cannot declare a step inapplicable, so a library with no build never reaches `pass`** |
| **G20** | **`forge verify` writes a tracked file and thereby fails its own `derived_fresh` condition** |
| G17 | (a) `--write NAME` writes a spec layout the fold cannot read — a defect introduced by F2. (b) `capability_of` returns `""` silently, folding every unplaceable delta into `specs/spec.md` titled `# capability` |
| G18 | Eight things that worked, listed in §3 and the positives above |

---

## 6. What this run did not measure

**Whether the store helped.** Ten claims now exist for `requests` and one change was
made with them present; nobody has yet made a change *without* them on the same
codebase to compare. Q1 remains unanswered and this run does not touch it.

**A second agent host.** Everything ran through one CLI from one session. The claim in
[OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) Q12 — that a second host costs a manifest
rather than a port — is still untested.

**Drift.** No claim went stale during the run, so `forge drift --store` classified ten
fresh claims and nothing else. The mechanism that makes this project novel remains
unexercised on real decay.


---

## 7. Postscript: G14 repaired, and re-measured on the same change

Fixed the same day. Obligations are now computed against the diff; claims reached only
through the import graph are reported under a `Nearby` heading that says plainly no
account is owed, so the reading value of the blast radius survives without becoming an
obligation.

Re-run against the identical change, `0001-content-may-be-none`:

| | before | after |
|---|---|---|
| Claims **touched** (a sentence owed each) | 10 | **5** |
| Claims **nearby** (reading only) | - | 5 |

The five that moved are the ones anchored to `sessions.py` and `utils.py`, which the
diff never opened.

**The five that remain are still too many, and the reason is worth writing down.** All
five are anchored to `src/requests/models.py`, which the diff did change - but they are
anchored to *symbols* in it: `models.py#PreparedRequest`, `models.py#Response.next`,
`models.py#Response.iter_content`. The diff touched only `Response.content`. Matching
is still at file level on the anchor side, so a change to one method taxes every claim
about every other method in the same module.

The machinery to fix it already exists: `fingerprint.find_symbol` locates a symbol's
span, which is how the anchor engine has classified drift since M1, and
`gitio.changed_line_ranges` is what R1 added. Intersecting the two would take this
change from five to one. That is the next narrowing, and it is deliberately not done
here: symbol resolution fails on coarse files and on languages with no grammar
installed, and deciding what a *failed* resolution should mean - fall back to the file,
or report nothing - is a decision that deserves its own change rather than a footnote
in this one.


---

## 8. Postscript 2: the narrowing finished, 10 → 5 → 1

The symbol-level narrowing §7 deferred was built the same day, once the drift ledger
made the cost concrete: the very first entry that ledger ever opened existed *only*
because an anchor was file-level. One root cause, two symptoms.

A symbol anchor is now touched when the diff's hunks intersect that symbol's own line
span, found with the `find_symbol` the drift engine has used since M1. A **file** anchor
is unchanged — a claim that points at a whole file is making a claim about the whole
file. Every way of not knowing falls back to the file: no grammar, a declaration form
the table does not cover, a symbol renamed away, a file gone from the working tree.

Re-run a third time against the identical change:

| | run 2 | after G14 | after the symbol narrowing |
|---|---|---|---|
| Claims **touched** | 10 | 5 | **1** |
| Claims **nearby** | — | 5 | 9 |

The one is `CON-content-text-json`, the only claim in the store that describes
`Response.content`. The nine are listed under `Nearby` with the reason each is there —
five because their file merely imports the diff, four because the diff opened their file
and changed a different part of it.

**What this cost, and what to watch.** Two tests in the existing suite had encoded the
file-level rule: both appended an unrelated function to `src/pay.py` and expected the
invariant anchored to `src/pay.py#refundable` to be taxed for it. Under the new rule it
is not, and that is the intended answer — but it is worth being plain that this run
loosened an obligation, and the thing to watch for is a claim that needed re-reading and
now sits quietly under `Nearby`. The `Nearby` list exists so that failure is visible
rather than silent; whether anyone actually reads it is not something this run measured.
