# Run 2 — the whole lifecycle on a repository nobody here had read

> `requests` 2.34.2, obtained as the published sdist and committed to a fresh git
> repository. Run on 2026-09-11, after the five repairs of `5ad73f0`. The question
> this run existed to answer: **did those repairs actually clear the path, or did
> they only clear it on the repository that produced them?**

The answer is yes for four of the five, no for one, and the run found eighteen more
things — including one that makes the lifecycle unfinishable on any repository.

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

Archive blocks on a verdict of `unproven`. `unproven` is produced by three conditions
the **kernel** owes — `DRIFT.md`, `DEBT.md`, and a baseline test run — which no user
action can satisfy. The suggested fix, `forge verify --change 1`, yields the same
verdict forever.

This is why the spec fold had never been executed by anyone: the only route to it is
`--force`, which is documented as recording blockers rather than as the normal path.
Forcing it immediately found G17.

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
| **G16** | **`forge archive` is unreachable on any repository today** |
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
