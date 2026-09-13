# Handover - the remaining work, and how to hand it back

Written 2026-09-12 by the agent that did M1-M7 and the Q1 measurements, for whoever picks
this up next. The author is out of budget, not out of opinions, so this says what to do,
why, and - more usefully - the specific ways this project has already gone wrong.

**Read [ROADMAP.md](ROADMAP.md) R9, R10, R11 first.** They are the three most recent
measurements and everything below follows from them. Then read
[OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) Q1 and Q3.

---

## Ground rules

These are not style preferences. Each one exists because breaking it produced a defect that
is recorded somewhere in `docs/measurements/`.

1. **Repository artifacts in English.** Code, docs, commit messages. Chat with the user in
   Vietnamese - that is their stated preference.
2. **Every finished piece of work ends with a proposed next step.** Standing instruction
   from the user.
3. **Fix the plan and the scoring rubric in a commit *before* running the thing you are
   measuring.** This is what made Q1 credible: the null condition was written down before
   a single agent ran, so the null result could not be reinterpreted afterwards. A
   measurement whose criteria were chosen after seeing the data is not a measurement.
4. **A null result is a result. Report it.** [RESEARCH.md](../RESEARCH.md)'s third finding
   is that the projects with the most machinery have the least evidence it helps. Q1 is
   the honest answer to that for this project, and it went against the design.
5. **Correct your own overclaims in place, struck through, not rewritten.** There are three
   examples already: G16 in run 2, the `redact.ts` normalisation test, and the correction
   at the end of `q1c`. A quiet rewrite loses the thing worth reading.
6. **Do not modify `D:/git/studio-monorepo`.** It is the user's real project. Work on a
   clone; deliver a patch and let them apply it.
7. **Spawning subagents costs the user money.** W2 below needs six runs. Ask first.

---

## Environment

- Windows 11, PowerShell and Git Bash both available. Console is cp1252 - the CLI already
  survives this via `_survive_the_console()`, but any new printing of test-runner output
  can still break.
- `.venv/Scripts/python.exe` is the interpreter. **`python -m forge` does not work** (no
  `__main__`); use:
  ```bash
  .venv/Scripts/python.exe -c "from forge.cli import main; raise SystemExit(main(['check']))"
  ```
- The full test suite is **794 passed, 7 skipped** and takes ~4 minutes alone, ~20 minutes
  if you run several pytest processes at once. Run it in the background, once, and wait.
- `forge check` currently reports **0 errors, 3 warnings**. The three warnings are
  `trace.claim_touch_extra` on the open change `0001` - claims accounted for that the diff
  came *near* but did not reach. They are advisory by design. Do not "fix" them.

### Traps that cost the previous agent real time

- **Never put Python containing backslash escapes inside a bash heredoc.** `\b` became a
  literal backspace and silently broke a regex; `\n` became a real newline and broke an
  f-string; this happened *repeatedly*, including twice on the last day. Use the `Write`
  tool, or write a `.py` file and run it.
- **`forge sync derived` must run *after* the content commit, not before.** The tier is
  generated from HEAD; syncing with tracked content still uncommitted produces a tier that
  is stale the moment it is written. The CLI now warns about this (`fix(sync)`, commit
  `826bdbe`) - believe the warning.
- **Clone with `--no-hardlinks`.** A local `git clone` of the user's monorepo repo shared
  objects by hardlink and the clone's object store corrupted mid-session. The original was
  verified healthy afterwards, but do not repeat it.
- **Do not trust an error message over the code.** The G16 finding in run 2 was diagnosed
  backwards because the blocker's wording lumped `pending` conditions under "failing". Read
  the code that produces the verdict.
- **Write a test that can actually go red.** The first `SECRET_TERMS` test passed with the
  fix reverted, because `client_secret` normalises to `clientsecret`, which already
  contains `secret`. Prove a new test fails before you believe it.

---

## The three jobs, in priority order

### W1 - Does a stale report change what anybody does? **(highest value, no subagents)**

This is now the top open question. R10 and R11 both land on it:

> A comment, a runtime warning, a changelog line and a conformance test all state their
> knowledge perfectly well, and not one of them knows when the code underneath moved.
> Staleness is the only thing on the list that only this harness does - and it is
> unmeasured.

M1 measured whether anchors *survive* refactoring (false positives). Q1c measured what an
anchor *fails to cover* (false negatives, 7 of 18). **Nobody has measured whether the
report, when it fires correctly, changes an outcome.**

**Do not start by writing code. Start by writing the plan and committing it**, per ground
rule 3. Two designs were considered and neither was chosen - pick one, or a better one, and
argue for it in the plan:

- **(a) The rubber-stamp rate.** For every stale detection this project can produce, ask:
  could the reader discharge it *without reading the claim*? If the available action is
  `forge drift confirm` and a restamp, the report is a ritual and Q3 in OPEN_QUESTIONS is
  answered badly. This is deterministic and needs no humans.
- **(b) Information content of the report.** Replay commits in the three M1 repositories,
  collect every stale detection, and classify what the report gives a maintainer: does it
  name the commit, the author, the symbol and a candidate verdict, or only "stale"?
  `forge reconcile` already does attribution - the question is whether the attribution is
  the part that makes it actionable.

**Data available.** This repository's own `docs/system/DRIFT.md` has exactly **one** entry
(D-001), so n is tiny here - say so. The requests and monorepo runs produced their own
ledgers in clones that no longer exist; `docs/measurements/run2-requests-lifecycle.md` and
`run3-monorepo-lifecycle.md` record what happened in prose and are the honest secondary
source. The M1 replay findings are summarized in `docs/measurements/M1-anchor-stability.md`.

**State the limits.** n is small, the author designs the task, and behaviour cannot be
observed without users. If the honest answer is "this cannot be measured yet", **say that
and stop** - that is a better outcome than a number nobody should believe.

### W2 - The inverse experiment **(needs the user's go-ahead: six agent runs)**

Q1 found the store added nothing because the trap already had four written homes. The
inverse is a trap whose record exists **only** in the store. Q1b found exactly one such
trap, by census, and it is unusually good:

> `PIT-adapter-prefix-is-a-raw-string-prefix` (requests): mounting an adapter on
> `https://example.com` also captures `https://example.com.other.com`, because
> `Session.get_adapter` matches with `str.startswith`.

Verified by inspection to be stated **nowhere**: not in `mount`'s docstring, not in
`get_adapter`'s, not in `HISTORY.md`, and not in the tests.
`test_session_get_adapter_prefix_matching` *looks* like it covers the case and does not -
its negative example is `https://another.example.com/`, a **sub**domain, which does not
start with the prefix. `test_transport_adapter_ordering` makes the hazard derivable by a
careful reader. Nobody states it. That gap is the best description of what a store is for
that these repositories produced.

**Design, mirroring Q1 exactly so the two are comparable:**

- Same two arms: **A** told to read `docs/system/` then the code; **B** told to read the
  code. Nothing forbids B from reading anything. Three agents each.
- A task where a bare-prefix mount is the obvious answer - e.g. "a user wants an adapter
  used for one specific host; say what you would change and why". A written proposal, not
  code, so the reasoning is visible.
- Binary rubric, **committed before running**: does the proposal notice that a bare prefix
  over-matches sibling domains, or not?
- Record tool-call counts and what each agent cited, the same as Q1.

**The repository.** requests 2.34.2, from the sdist. The store from run 2 is what arm A
reads. Re-create it rather than trusting a stale copy; `docs/measurements/run2-requests-lifecycle.md`
says how the original was set up.

**Declare the null condition in advance**, as Q1 did: if arm B sees it at the same rate,
the store lost on a trap chosen to favour it, and that is a much stronger negative result
than Q1's. Say so before you know.

### W3 - The monorepo patch **(deliverable to the user, not to this repo)**

Three things were found in the user's repository while measuring forge. None has been
delivered. Produce **one patch file** against `D:/git/studio-monorepo`, on a clone, and
hand it over - do not apply it.

1. **A conformance test for the `apply*` rule.** `PIT-apply-takes-only-the-token` says
   `apply*` must accept nothing but the preview token, which is what keeps the SQL shown
   from differing from the SQL run. Every `apply*` that exists is enforced by its own Zod
   `params` schema - **this was overstated once, read the correction in
   `docs/measurements/q1c-what-an-anchor-does-not-cover.md` before repeating it.** What is
   unenforced is the rule across methods: a new `ddl.applyIndex` declared with
   `{ previewToken, sql }` passes every check in that repository. The fix is the pattern
   monorepo already uses twice - `tools/__tests__/no-mock-in-bundle.test.ts` and
   `no-dev-credential-in-image.test.ts`: iterate every contract method whose name matches
   `apply` and assert its params are exactly the token.
2. **The driver-registry conformance test** from run 3 (`PIT-seeded-driver-must-be-registered`):
   every `driverId` in the seed profile must resolve to a registered driver. The existing
   seed test asserted the profile listed eight engines and said nothing about whether any
   could be opened; a real commit had already shipped that gap.
3. **The `SECRET_TERMS` normalisation fix** (`PIT-secret-term-must-be-normalised`). This
   closes a real silent gap: a badly-spelled term in the list is dead and still looks
   covered. The test must assert the property that *can* fail - that each term equals
   itself after normalisation - not `isSecretKey(term)`, which passes vacuously.

---

## What you must produce

One file: **`docs/measurements/handover-report.md`**, committed. Its first section is
fixed, because the person reviewing it is on a small budget and needs to know in fifteen
lines whether to read further.

```markdown
# Handover report - <date>

## Review block

| job | status | one-line outcome |
|---|---|---|
| W1 | done / partial / not attempted / refused | ... |
| W2 | ... | ... |
| W3 | ... | ... |

**Where I disagreed with the handover brief:** ...
**What I could not verify:** ...
**What I would do next:** ...
```

Then, per job attempted:

- **The question you actually answered**, stated plainly, and the commit that fixed the
  rubric before you ran anything.
- **The result, including a null or negative one.**
- **The limits**, including the ones no care removes.
- **Anything you got wrong and corrected**, struck through rather than rewritten.
- **What shipped** - files and commits - separately from what was merely measured.

## How this will be reviewed

The reviewer will read the review block, then the *limits* sections, then the diffs. What
they are checking:

1. **Was the rubric committed before the run?** `git log` will show it. If not, the result
   does not count, however good it looks.
2. **Does a negative result appear anywhere?** Three of the last three measurements went
   against the design. A handover report where everything worked is the thing to be
   suspicious of.
3. **Did you disagree with this brief?** The brief was written by someone who was wrong
   twice in the last two hours and corrected both in place. "I disagreed with nothing" is
   a finding about the report, not about the brief.
4. **Is anything claimed about the user's repository verified twice?** The one gap named in
   W3 was overstated on first reading because the schema was two files away. Read it twice.
