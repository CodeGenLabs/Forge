# Roadmap

> Written after the first real change was taken through the lifecycle
> (`changes/0001-drift-reads-the-claim-store`). Every item below is ordered by what
> that run measured, not by what the design documents predicted. Where the two
> disagree, the run wins, and the disagreement is recorded.

The goal this roadmap serves: **forge applied to other repositories** - a new project,
a project already underway, an investigation, a bug fix - driven from whichever coding
agent is at hand.

---

## 1. What the first real change found

The MVP's definition of done ([MVP.md](../MVP.md) section 5) called criteria 4 and 5
"the real ones", because they are the two behaviours no existing tool has. Running one
change end to end tested them for the first time.

**Criterion 5 passed, and passed hard.** A claim's account was wrong in three separate
ways across the run - a claim filed under two headings, an account written before the
diff existed, a claim filed under a heading that had become untrue - and the
claim-touch rule caught all three. It also refused to archive. The mechanism works.

**Criterion 4 could not be tested**, because the drift ledger does not exist.

**The verdict can never be `pass` on this repository**, for three independent reasons
found only by running it. They are items R1, R3 and R5 below.

The run produced sixteen findings, and repairing them surfaced a seventeenth. Eleven are
defects in the kernel, three are gaps in the design, and three are friction. The ones
that change this roadmap's order:

| # | Finding | Where |
|---|---|---|
| F15 | "its own definition was edited" is decided at **file** level, so appending one claim to `pitfalls.md` demanded three unrelated claims be re-filed as `Updated`. `Claim.line`/`end_line` exist for exactly this and are unused | [impact.py:207](../src/forge/impact.py:207) |
| F11 | `requirement_cover` needs `@covers` tags that `exclude_id_scan: ["tests/*"]` guarantees will never be harvested. No requirement can ever be discharged here | [.forge/config.yaml](../.forge/config.yaml) |
| F14 | The verify timeout is a hardcoded 900s with no flag and no config key, and a timeout is recorded as `"status": "fail"` - "we do not know" collapsed into "it failed" | [verify.py:130](../src/forge/verify.py:130) |
| F3 | `trace.claim_touch_complete` is gated at `impact:post`, which on track C runs **before** implementation, against an empty diff. It passed a file that `forge verify` later failed. (`verify` does recompute it - the settlement exists, the gate is just premature) | [gates.py:48](../src/forge/gates.py:48) |
| F5 | `Change.tasks()` reads one physical line per bullet, so a `REQ-` id on a wrapped line is invisible. Same defect M5 found in `## Uncertain` and fixed in `bootstrap.py#_bullets` **without recording it** | [change.py:198](../src/forge/change.py:198) |
| F10/F13 | `commands.test` is handed to the host shell verbatim. Bootstrap detected the bare `pytest`, unresolvable without an activated venv; the fix needed backslashes for `cmd.exe`. Three verify runs, ~25 minutes of suite time, and none of the three failures was a test | [verify.py:85](../src/forge/verify.py:85) |
| F2 | `template:` is declared for five artifacts, parsed, validated - and read by nothing. No template files exist | [schema.py:308](../src/forge/schema.py:308) |
| F6 | `classify` compares committed revisions, so `--changed` selects by the working diff and still classifies against HEAD. A file edited and uncommitted is reported fresh | [anchor.py](../src/forge/anchor.py) |
| F8 | The one gate at `implement:task:post` says "Owed by: M4". M4 shipped and did not bring it | [gates.py:58](../src/forge/gates.py:58) |
| F1 | `forge change show 1` is positional; every other change-scoped command takes `--change`. `change show` prints the flag form in its own "Next:" line | [cli.py](../src/forge/cli.py) |
| F16 | The trace index takes `REQ-` **definitions** only from `docs/system/specs/**`, so every open change with new requirements reports them as dangling references on `forge status` until it is archived. An in-progress change makes the status screen look broken | [trace.py:168](../src/forge/trace.py:168) |
| F17 | `CHANGING = ("Updated", "Superseded")` omits `New`, so a change that **adds** a claim can never satisfy the claim-touch rule - and adding a claim is the single most common knowledge action there is. Found while fixing F15; [WORKFLOW.md](../WORKFLOW.md) §3.4's own worked example files a new invariant under `New` | [impact.py:57](../src/forge/impact.py:57) |

F5 is the one to read twice. A defect was found, fixed, and never written down, so the
same line-based match was written again three days later in a different file. It is now
`PIT-bullet-continuation-lines`, and it is the entire argument for the claim store
stated in one incident.

---

## 2. R1-R3: make the harness able to finish

Nothing else matters until a change can reach a verdict.

> **Done 2026-09-11**, in one pass rather than through the lifecycle, because every item
> below blocks the lifecycle itself: R1, R3, and the small repairs F5, F2 and F16.
> Fixing them surfaced **F17** — `CHANGING` omitted `New`, so the claim-touch rule
> rejected every change that recorded a new claim, which is the single most common thing
> a change should do. Both errors are recorded in
> [SYSTEM_KNOWLEDGE.md](../SYSTEM_KNOWLEDGE.md) §9.2 where the original was wrong.
> What remains open here is **R2**, and R5 below.

### R1 - Per-claim edit detection **(P0, done)**

Fix F15. Use `Claim.line` and `Claim.end_line` against the diff's hunk line ranges
instead of `claim.file in radius`. `gitio` needs one new call returning changed line
ranges per path.

Shipped as `gitio.changed_line_ranges` and `impact._overlaps`. A claim with no recorded
`end_line` falls back to its heading line alone, never to the whole file: falling back to
the file would quietly restore the behaviour this replaces, in exactly the case where the
parser already knows something is wrong.

Why first: this is the failure mode [OPEN_QUESTIONS.md Q3](../OPEN_QUESTIONS.md) names -
`Unaffected` accounting degrading into rubber-stamping - and it arrived on the first
change. A rule whose only ways through are to lie or to split every claim into its own
file will be routed around, and a routed-around rule is worse than no rule, because the
gate still prints `pass`.

**Stop condition:** if hunk-range mapping proves unreliable across renames, fall back to
"the claim's heading line is inside a changed hunk" and say so - do not keep file-level.

### R2 - Move the claim-touch gate to where the diff exists **(P0, done)**

Fix F3. `trace.claim_touch_complete` is now declared twice: advisory at `impact:post`,
blocking at `sync:pre`. Eleven gates at nine points, and the count went up by adding a
decision point rather than a check.

By `sync:pre` the code exists, so the computed set is the real one - which is where
[MVP.md](../MVP.md) §5 criterion 5 is enforced, or nowhere. At `impact:post` on track C
the diff holds the change's artifacts and no code, so blocking there means blocking on a
forecast; it still reports everything it finds, because `blocking` decides the exit code
and never whether the reader is told.

The wrong advice is fixed too, and split three ways: a claim under `Nearby` is told
nothing is owed, an account written against an empty diff is told it is a forecast that
`sync:pre` will check, and only a genuinely unreachable claim is told its anchors may
point at the wrong place. One message for three situations was wrong for two of them.

### R3 - A verification that can distinguish "unknown" from "failed" **(P0, done)**

Fix F14 and F10/F13. Shipped:

- `commands.timeout` in config and a `--timeout` flag, over a `DEFAULT_TIMEOUT` of 900.
- A timed-out or unresolvable command records `unavailable`, not `fail`. `unavailable`
  already meant "the project owes this" and blocks the verdict without claiming the suite
  ran and lost, which is the one thing this report must never say.
- `verify.resolve_command` checks the first token before the shell sees it, and names the
  project's own `.venv` binary in the message when it finds one. Anything containing a
  separator, quote, operator or `=` is handed to the shell untouched.

Still open: `forge doctor` should check that every `commands.*` line resolves, and say so.
That is where a new project should meet this problem, rather than twenty minutes into its
first verification.

---

## 3. R4-R5: close the drift loop

### R4 - The drift ledger **(P0, was "M6")**

`forge drift --store` and `--changed` now exist (change 0001). What is still missing is
everything the design advertises around them:

- `docs/system/drift.md`, the ledger, with an entry per finding and a proposed verdict.
- `forge drift resolve --verdict V1|V2|V3|V4`, with the consequences
  [SYSTEM_KNOWLEDGE.md section 6](../SYSTEM_KNOWLEDGE.md) specifies: V2 requires
  `--evidence`, V3 requires `--adr`, V4 requires a new `enforced` status or an explicit
  recorded flag.
- `forge drift waive`, and the three `pending` conditions in `forge verify` wired to the
  ledger instead of to a string saying it does not exist.
- Fix F6 on the way: classify against the **index** under `--changed`, or a hook built on
  it checks the wrong thing.

Until this lands, [README.md](../README.md) advertises a mechanism that is not there. The
README should say so today, regardless of when R4 happens.

### R5 - Decide the `@covers` / `exclude_id_scan` collision **(P1, done 2026-09-12)**

Fix F11. This repository's test suite is built out of the strings the scanner looks for -
366 ID mentions, including literal `@covers INV-7` inside fixtures - so the exclusion was
necessary and made `requirement_cover` permanently unsatisfiable. The M5 postscript found
the same collision for `INV-` claims; it generalises to requirements.

**Resolved (Option 2):** `build_tests` and `build_backrefs` now harvest `@covers` and
`forge:<ID>` exclusively from AST-confirmed comments (using Python stdlib `tokenize` and
Tree-sitter cursor traversal for TypeScript/Go), safely ignoring string literals and test
fixtures. This allowed `tests/*` and `tools/*` to be removed from `exclude_id_scan` in
`.forge/config.yaml`, restoring requirement and invariant coverage to this repository.
The config template in `src/forge/scaffold.py` now explicitly documents that excluding a
test directory surrenders requirement coverage.

---

## 4. R6-R7: survive a repository you did not start

This is the "project đang làm dở" case, and it is the one
[OPEN_QUESTIONS.md Q10](../OPEN_QUESTIONS.md) predicts will kill the harness.

### R6 - `forge hooks install` **(P1)**

A pre-commit hook running `forge check --scope store` and `forge drift --changed`, and
running `forge sync derived` so the derived tier is committed with the code rather than
in a trailing `chore:` commit - this repository's own history has eight of those.

Blocked on R4's index-aware classification (F6): a hook that reports every
about-to-be-committed file as fresh is worse than no hook.

**Measure and record:** the runtime of `forge drift --changed` on a large diff. Q10 says
this number is unknown and it decides whether the hook is viable.

### R7 - `forge reconcile <range>` **(P2)**

The recovery path for when the hook is bypassed: classify the commits in a range, produce
one batch of ledger entries, review them in a single flow. Build it after R4 and after the
hook has been bypassed at least once in real use - its shape should be decided by what
actually accumulates, not by what we imagine will.

---

## 5. R8-R9: reach the other agents

The kernel is a CLI, so it already runs under Claude Code, Codex, Antigravity and zcode
alike. The skills are plain markdown with no host-specific syntax, which
[Q12](../OPEN_QUESTIONS.md) says is the thing that keeps a second host cheap. What is
missing is only the delivery.

### R8 - `forge install --host <name>` **(P1, done 2026-09-12)**

A manifest, never a port. Write the packaged skills to where each host reads them
(`.claude/skills/`, `AGENTS.md`, and so on), and nothing else. The rule that makes this
stay cheap: **no skill may depend on a host-specific feature** - not a subagent API, not a
hook type, not a tool name. Every mechanism lives in the kernel, and the kernel is a
command.

**Shipped:**
- `forge install --host <name>` added as a top-level CLI command (aliasing `_cmd_skill_export`).
- Shipped hosts configured in `src/forge/hosts.py`:
  - `claude`: `.claude/skills` (`copy`)
  - `antigravity`: `.agent/skills` (`copy`)
  - `codex`: `AGENTS.md` (`pointer`)
  - `agents-md`: `AGENTS.md` (`pointer`)
  - `forge`: `.forge/skills` (`copy`)
- Verified with unit tests in `tests/test_hosts.py` for each host and CLI command.

### R9 - Distribution **(P2, done 2026-09-12)**

Publish to PyPI so `pipx install forge-harness` works; pin the kernel version in
`.forge/config.yaml` so a repository can detect skew ([Q11](../OPEN_QUESTIONS.md)).

**Shipped:**
- `kernel_version` field added to `.forge/config.yaml`, `src/forge/config.py`, and scaffold template in `src/forge/scaffold.py`.
- Zero-dependency version skew detection (`detect_kernel_skew` in `src/forge/config.py`) supporting exact (`"0.0.1"`), minimum (`">=0.0.1"`), and compatible (`"~=0.0.1"`, `"^0.0.1"`) version specs.
- `forge check` emits `WARNING store.kernel_skew` when running kernel does not satisfy repository pin.
- `forge doctor` reports running `kernel` version and `kernel_pin` skew/match status.
- Added `readme = "README.md"` to `pyproject.toml` and verified distribution build.
- Unit tests added in `tests/test_config.py`.

---

## 6. R10-R12: the smaller repairs

- **R10 - Artifact templates (P2, done).** Fix F2. `forge instructions <artifact> --change
  N --write` scaffolds the declared template; `--write NAME` names the file for an
  artifact generating a glob, because `spec/**/*.md` is a shape and guessing the
  capability would produce `spec/spec.md` on every change. Each template opens with
  `<!-- forge:template -->`, and an artifact still carrying that line is **not** complete -
  otherwise scaffolding a change would walk it straight to "done" and every gate
  downstream would run against boilerplate. `verification.json` deliberately has no
  template: it is generated, and a template for it would be a place to write a result by
  hand.
- **R11 - CLI consistency (P3, done).** Fix F1: `forge change show --change 1`, keeping the
  positional form as an alias (shipped in `src/forge/cli.py:_named_change`, tested in
  `tests/test_lifecycle_repairs.py`).
- **R12 - Honest debt labels (P3, done).** Fix F8: `task.scope_and_covers` is owed by nobody
  now that M4 has shipped. Either schedule it or say it is unscheduled (shipped as
  "unscheduled" in `src/forge/gates.py:PENDING`, tested in `tests/test_lifecycle_repairs.py`).
- **R13 - Open deltas define their requirements (P2, done).** Fix F16. `trace` now indexes
  `REQ-` from open changes' spec deltas, marked `provisional`; a permanent spec always
  wins, so a stale delta cannot move a folded requirement back. `REMOVED` defines nothing,
  and the archive is not a definition.
- **R14 - A task is a bullet, not a line (P1, done).** Fix F5, and the reason
  `PIT-bullet-continuation-lines` exists. `Change.tasks()` joins indented continuation
  lines; the indent requirement is what stops a closing paragraph being swallowed into the
  last task.

---

## 7. `bugfix.yaml` - the "fix bug" case **(P2, done 2026-09-12)**

[MVP.md](../MVP.md) section 4 deferred this to M6. A bug fix can now run under the
dedicated `bugfix` workflow schema (`forge change new <name> --workflow bugfix`), which
adds one mandatory artifact - `reproduce` (`reproduce.md`) - holding a failing test
written **before** the fix, which then becomes the `evidence:` of whatever claim the bug
produces.

**Shipped:**
- Built-in `bugfix` workflow schema in `src/forge/schema.py` declaring `reproduce` as the root mandatory artifact for tracks B and C, blocking `proposal` and downstream tasks until reproduction is established.
- `_T_REPRODUCE` template added to `src/forge/scaffold.py:CHANGE_TEMPLATES` for `forge instructions reproduce --change N --write`.
- `forge init` scaffolds both `feature.yaml` and `bugfix.yaml` under `.forge/schema/`.
- Validated with unit tests in `tests/test_schema.py` (structure and track requirements) and `tests/test_change.py` (end-to-end change lifecycle and template unblocking).

---

## 8. What stays deferred, and why

Unchanged from [MVP.md](../MVP.md) section 4. Nothing in the first real change argued for
any of them:

- **Code index (SCIP/LSIF)** - `investigate` has not blown a step budget yet ([Q7](../OPEN_QUESTIONS.md)).
- **The three postponed skills** (`assess-impact`, `design`, `review`) - the run wrote
  `impact.md` and `design.md` by hand without wanting a procedure. Revisit if a later
  change does.
- **`forge stats`** - needs about ten real changes first ([Q1](../OPEN_QUESTIONS.md)).
  One is not ten.
- **API claims, `oasdiff`, architecture-rule generation, knowledge graph, cross-project
  store, MCP server.**

And one thing to *stop* doing: **do not add a new mechanism before the existing ones can
finish a change.** The first run found nine kernel defects in roughly one afternoon of
real use, all of them in code that passed 624 tests. The tests were not wrong; they were
testing the parts. What they could not test was a change reaching the end.

---

## Order, in one line

~~R1, R3~~, R2 (a change can finish) → **R4 (the ledger)** → R5, R6 (an existing
repository survives contact) → R8 (the other agents) → everything else, measured.

> **Run 2 is done** (2026-09-11) - `forge init`, bootstrap and a full track C change on
> `requests` 2.34.2, recorded in
> [docs/measurements/run2-requests-lifecycle.md](measurements/run2-requests-lifecycle.md).
> Four of the five repairs held on unfamiliar code; F2 introduced a new defect. The run
> added eighteen findings, two of which reorder everything below:
>
> - ~~**G16 - `forge archive` is unreachable on any repository today.**~~ **Wrong** -
>   corrected 2026-09-11 by probing it. `pending` conditions do not block the verdict;
>   `unavailable` ones do. With `build` and `typecheck` declared the same change reached
>   `pass` and archived. What was really in the way is now G19 (a project cannot declare
>   a step inapplicable) and G20 (`forge verify` writes a tracked file and so fails its
>   own `derived_fresh`). R4 is back to being about the marquee feature, which is reason
>   enough.
>
> **R4 is done** (2026-09-11). `docs/system/DRIFT.md`, `forge drift record | list |
> resolve | confirm | waive`, and the `drift` condition is no longer pending: it reads
> the ledger, scoped to the claims the change is accountable for. The first entry the
> ledger ever opened was real and unplanned - `PIT-regex-across-newlines`, flagged
> because the G14 edit touched the file its whole-file anchor points at.
>
> That entry also found the gap: **none of the four verdicts fitted it.** The claim was
> true, the code was right, and the anchor was simply too coarse - which will be the
> commonest signal there is. `forge drift confirm` is the answer and is deliberately not
> a fifth verdict; the argument is in [SYSTEM_KNOWLEDGE.md](../SYSTEM_KNOWLEDGE.md) §6.

---

## Run 3, and the first complete lifecycle (2026-09-12)

`corvus-db-studio` - 620 files, 19 TypeScript packages, 90 real commits - recorded in
[docs/measurements/run3-monorepo-lifecycle.md](measurements/run3-monorepo-lifecycle.md).

**`forge init` -> bootstrap -> a real track C change -> `verdict: pass` -> `forge
archive` without `--force` -> the spec delta folded to the right path.** Run 1 could
not reach a verdict; run 2 reached one only after a probe and archived only under
`--force`.

Three defects that neither earlier repository could have exposed:

- **H1** - `sync derived` took 93 seconds here and under a second on `requests`, all of
  it process creation. Now 1.4s, byte-identical output. My first fix was wrong in an
  instructive way: it traded one subprocess per blob for one per cache lookup.
- **H3** - workspace package imports were dropped entirely, so the import graph was
  wrong on every monorepo. 671 edges -> 900, and `0 cycles` became a finding rather
  than an artefact.
- **H9** - a claim's prose swallowed the next `##` section, which corrupted `end_line` -
  and `end_line` is what R1's per-claim edit detection uses. Editing a section *below* a
  claim reported that claim as edited. This also corrects run 2's G12, which blamed
  `seal` for a parser defect.

Still open and unmeasured: whether `Nearby` is actually read. Run 3's change touched no
claims at all, so the split three rounds of narrowing produced was never exercised.

A second change on the same repository closed that gap: editing `isSecretKey` produced
**2 touched, 0 nearby, 7 reached by import** - one function, two obligations, both
right. It cost three more defects, all invisible to a run that makes one change:
**H13** (`--follow` matched a change's `.forge.yaml` to the previous one that `archive`
had moved, so every change after the first measured itself from an earlier change),
**H14** (a CRLF rewrite marked every claim in a file as edited - Q3's rubber-stamping
through a *third* door, after claims sharing a file and claims sharing an import graph),
and **H15** (every `it.each` test was invisible to the index).

---

## M7 - the pre-commit hook **(done, 2026-09-12)**

[OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) Q10 names how every knowledge scheme dies:
drift accumulates unnoticed, the first scan after a busy week is a wall of findings, and
somebody declares bankruptcy. It recommends a pre-commit hook. Two things had to be true
first, and neither was until run 3.

**Fast enough.** 93 seconds for `sync derived` on a 620-file repository; 1.4 now, and
the hook does less.

**Looking at the right thing.** `drift --changed` selected by the working diff and still
classified against HEAD, so it returned the same verdict whether or not anything was
staged - a hook built on it would have been a placebo everybody trusted. `gitio` can now
address the index (`INDEX`, `:0:<path>`), and `drift --staged` compares against it.

**And a third thing, found by building it.** The first hook demanded the drift be
*resolved*, and that can never be satisfied: a verdict points at a commit, and at
pre-commit time the commit does not exist, so `confirm` restamps to HEAD and the index
still differs. The hook now blocks on drift with no **open ledger entry** - `drift
--staged --unrecorded`. Drift somebody wrote down is not an emergency; drift nobody
noticed is. `forge drift record --staged` lets the commit through, and the entry lands
in the same commit as the code, which is the reviewable unit SYSTEM_KNOWLEDGE.md §6
asks for.

Exercised end to end on the monorepo: blocked, recorded, committed, then confirmed
against the commit that now existed - ending at 12 of 12 claims fresh.

---

## R5 - `forge reconcile`, the other half of Q10 **(done, 2026-09-12)**

The hook is only Q10's first recommendation. It **will** be bypassed -
`--no-verify`, a colleague's commits, a dependency bot, a repository adopting the
harness after years of history - and Q10 says plainly that without a recovery path the
first scan after a busy week is the wall of findings that ends in bankruptcy.

What `reconcile` adds over `forge drift --store`, which already lists every stale claim,
is **attribution**. A scan says a claim is stale; only the history says which commit did
it and what that commit thought it was doing - which is exactly the question a reviewer
choosing between "the code is wrong" and "the decision changed" is asking. Forty stale
claims is a wall; forty with `42c437f Bob - feat(host): let the engine be opened
read-only` beside them is a review.

It records nothing unless asked, and `--record` opens one entry per claim, idempotently,
carrying the causing commits into the ledger - the report had the attribution and the
record did not, which left the one thing this command adds out of the artifact that
survives the terminal closing.

Exercised on the monorepo by simulating exactly what Q10 describes: two commits by two
people, both past the hook with `--no-verify`. It attributed the one real drift to Bob's
commit and correctly said nothing about Alice's, whose change added a term to a list
without touching the anchored symbol.

**Three buckets, not one**, and the third was a defect in the first cut: a claim nothing
could be *classified* about is not a claim that drifted. Every candidate carries this,
because a candidate is never stamped with a `@sha` - so the four candidates that review
rejected appeared in every reconcile under a heading saying they had drifted.

An anchoring lesson worth keeping, from Alice's commit: `PIT-secret-term-must-be-
normalised` is about a *list* and anchors only to the function that reads it, so adding
a badly-spelled term to that list would not be noticed. The anchor decides what the claim
can see, and a claim about one thing anchored to another is quietly blind.

---

## The three small debts, settled (2026-09-12)

None blocked anything, and all three were things a new user met first.

**F8** - `task.scope_and_covers` reported "Owed by: M4" long after M4 shipped without
bringing it, so the gate spent weeks naming a debt that had been settled without being
paid. The entries now say what is *missing* rather than who owes it: that check is
unscheduled, and it needs two things the format does not carry - a declared file scope
per task, and a diff attributable to one task rather than to the whole change. A label
that ages into a lie is worse than "nobody has scheduled this", because the first is
read as a plan.

**F1** - `forge change show 1` was positional while every other change-scoped command
took `--change`, and `change show` printed the flag form in its own "Next:" line, so the
tool taught a spelling it then rejected. Both work now; naming neither is a usage error
that shows both.

**H6** - `forge doctor` said "none declared" on a repository where `bootstrap derive`
had just printed four detected commands. Detection reads the project's manifests and
only `seal` writes them to config, so between the two the tool disagreed with itself
about the same facts. Doctor now reports what the manifests declare, and how to adopt
them.

>
> **Symbol-level narrowing is done too** (2026-09-11), with G19 and G20. A symbol anchor
> is touched when the diff's hunks intersect that symbol's own line span; a file anchor
> still answers for its whole file; every way of not knowing falls back to the file.
> Measured a third time on the same `requests` change: **10 → 5 → 1**, and the nine that
> left the obligation are listed under `Nearby` with the reason each is there.
>
> This loosened an obligation, and the thing to watch is a claim that needed re-reading
> and now sits quietly under `Nearby`. That list exists so the failure is visible; whether
> anybody reads it is unmeasured.
> - **G14 - the claim-touch set is matched against the blast radius, not the diff.** A
>   one-line change to `requests` touched 10 claims out of 10. This is R1's failure
>   through a second door, and it needs the same narrowing.
>
> Revised order: **~~G14~~ → R4 (which subsumes G16) → R2 → R5, R6 → R8**.
>
> **G14 is done** (2026-09-11), with G15, G17a, G17b and G1 in the same pass:
> obligations are computed against the diff, and claims reached only through the
> import graph are reported under a `Nearby` heading that says no account is owed -
> so the blast radius keeps its reading value without becoming an obligation. On this
> repository's own open change the split is 3 touched, 1 nearby. `forge doctor` now
> takes `--repo` and checks that every declared command resolves, which closes the
> item R3 left open.

---

## R9 - Q1, and the finding that cost the store something **(done, 2026-09-12)**

Every run before this one made the harness bigger. This one asked whether the largest
piece of it earns its place, and got a **null result** -
[the measurement](measurements/q1-does-the-store-help.md), plan and rubric committed
before the first agent ran. Six agents, one trap, one repository: three pointed at the
claim store, three pointed only at the code. **All six avoided it.** The arm with the
store averaged 18 tool calls against 13.

The reason is the useful part. The trap already had four written homes in that
repository - a rules table, a review checklist and two specs - and the agents found
them. **A claim derived from a document competes with that document for the same
reader, and the reader usually finds the document.**

That points straight back at H13's sibling, [run 3](measurements/run3-monorepo-lifecycle.md)'s
H7, where "rules the project already wrote down" was *added* as the bootstrap's first
source because a monorepo stating its three most important rules in `AGENTS.md` had been
scanned without them being read. Both are right, and together they say something neither
says alone: **the source that produces the best candidates also produces the most
redundant ones.** Making bootstrap better at finding rules made it better at copying
them.

Two changes, both in authoring rather than in mechanism, because the mechanism was not
what failed:

- The `bootstrap` skill now asks one question before a candidate drawn from a document
  is written: **what does the claim add that its source does not?** An anchor is a real
  answer - prose does not know when the code under it moved. Reach is the other -
  knowledge recorded nowhere near the work. A shorter restatement is neither, and the
  cap is better spent elsewhere.
- `forge bootstrap review` prints a `restates:` line under any candidate whose evidence
  names a document in the repository, and the sheet asks the reviewer plainly whether a
  reader would find that document anyway. Deliberately **not** a check: firing on any
  doc-backed evidence would flag good claims - the claim under test named a conformance
  test too, and was redundant regardless - so it is a judgement, and judgement belongs
  in pass 3 with a human in front of it.

**What this does not say, and the next experiment.** The measurement never exercised the
two things a store does that prose cannot - **staleness** and **reach**. It ran on a
repository with an unusually good rules tree, on a trap chosen by the person scoring it,
at n=6. The honest inverse is a trap recorded *only* in the store, in a repository with
no rules document. If the store loses there, that is an answer about the design; this
one is an answer about authoring.


## R10 - the census behind Q1, and what it moves to the top **(done, 2026-09-12)**

Q1 was one trap and six agents. [Q1b](measurements/q1b-where-else-does-the-knowledge-live.md)
asks the same question of **all thirteen** pitfalls in both bootstrapped repositories, by
inspection: where else does this knowledge already live? Reproducible, and a reader can
disagree with a row rather than with a number.

**Ten of thirteen have a home the reader meets while doing the work** - four in a prose
document, five in the code at the anchor, one in a test. Three have none.

The orphan worth reading is `PIT-adapter-prefix-is-a-raw-string-prefix`: mounting an
adapter on `https://example.com` also captures `https://example.com.other.com`, and no
docstring, changelog entry or test states it. The nearest test *looks* like it covers the
case and does not - its negative example is a subdomain, which does not start with the
prefix. Derivable by a careful reader, stated nowhere. That is the sharpest description of
what a store is for that these repositories produced.

**What predicts redundancy is what was read.** A candidate read out of a document restates
it; a candidate read out of code, or earned by a change that went wrong, is the one with no
other home. Bootstrap produced the best orphan in the census, so this is not an argument
against bootstrap - it is an argument about its sources, and `bootstrap.restates()` already
separates the redundant class mechanically.

**The consequence for this roadmap, stated as a reordering rather than as a conclusion:**

- **Claim prose is the weakest part of a claim.** Ten of thirteen are a second copy, and
  Q1 measured what one such copy buys: nothing, at 40% more tool calls. Work that makes
  claim prose better is now the *lowest* priority item on this list.
- **The anchor is the part with no competitor.** A comment, a runtime warning, a changelog
  line and a conformance test all state their knowledge perfectly well, and not one of them
  knows when the code underneath moved. Staleness is the only thing on the list that only
  this harness does.
- **And it is still unmeasured.** M1 measured whether anchors *survive* refactoring - a
  false-positive rate. Nothing has measured whether a stale-claim report changes what
  anybody does. That is now the top open question, ahead of `forge stats` and ahead of the
  inverse agent experiment R9 proposed.

**Next, concretely.** The inverse experiment R9 named is still worth running and now has
its trap chosen for it by this census: `PIT-adapter-prefix-is-a-raw-string-prefix`, in a
repository with no rules document, against a task where a bare-prefix mount is the obvious
answer. It needs six agent runs and the user's go-ahead, which is why it is a proposal here
and not a done item.


## R11 - what an anchor does not cover **(done, 2026-09-12)**

R10 put staleness at the top of this list and said it was unmeasured. This measures one
half of it - [Q1c](measurements/q1c-what-an-anchor-does-not-cover.md) - and it is the half
that matters more. M1 measured whether anchors *survive* refactoring, a false-positive
rate. The false negative is worse: a claim that fails to go stale when it breaks is a
checked-looking record of something untrue.

One question per claim: name an edit that makes this false **without touching an anchor**.

**Seven of eighteen.** And the reason is uniform enough to be a law:

> An anchor covers a claim exactly when the claim is about the code at the anchor. A rule
> the whole repository must obey has no such symbol, because it breaks by code appearing
> somewhere it was not.

Six of the seven are caught anyway - four by a conformance test, one by `forge check`
itself, one by a foreign key at runtime. **One is caught only instance by instance.**
`PIT-apply-takes-only-the-token` in corvus says `apply*` must accept nothing but the
preview token, the rule that keeps the SQL shown from differing from the SQL run. Every
`apply*` that exists is enforced by its own Zod params schema - the measurement's first
draft said "no test, no lint rule, no type" and was wrong about the type, corrected in
place rather than silently. What nothing enforces is the **rule**: a new `applyIndex`
declared with `{ previewToken, sql }` passes every check in that repository. The claim's
anchor is the class that *hands out* tokens rather than the code that must only accept
them, so it cannot notice either.

That is the first time this project has found something wrong in a repository rather than
something wrong with itself, and it came out of a question about forge.

**Shipped:** `curate-knowledge` now says to anchor a repository-wide rule at **what
enforces it** - the test, the lint rule, the guard, the constraint - not at an example of
it, and to say so in the prose when nothing does. `forge check --scope store` ends with one
line counting the claims that name no enforcer; a claim anchored *at* its conformance test
counts as enforced, which is the pattern corvus arrived at without writing it down.

**A check that was attempted and abandoned, recorded so nobody builds it again.** The
obvious detector is lexical - flag a pitfall whose title says *every*, *never*, *only*. Run
against these eighteen it is wrong in both directions, because the distinction is the scope
of the subject rather than the vocabulary. It is a count, not a verdict, for the same
reason the `restates:` line is: state the fact, let the human judge.

**Still open, and now the only thing above it:** whether a stale report, when it does fire,
changes what anybody does. Nothing measured here touches that.


## Handed over, 2026-09-12

The agent that wrote R1-R11 ran out of budget here. [HANDOVER.md](HANDOVER.md) carries the
remaining work - W1 whether a stale report changes anything, W2 the inverse agent
experiment with its trap already chosen by the Q1b census, W3 the corvus patch - plus the
ground rules and the specific ways this project has already gone wrong. It requires one
output, `docs/measurements/handover-report.md`, whose first section is fixed so the review
is cheap.
