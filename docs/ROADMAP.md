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

### R2 - Move the claim-touch gate to where the diff exists **(P0)**

Fix F3. Declare `trace.claim_touch_complete` at `sync:pre` as well as `impact:post`, and
soften the `impact:post` instance to advisory with honest wording: on track C it is a
forecast, and its current advice ("the anchors are pointing at the wrong files") is
wrong for every claim by construction.

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

### R5 - Decide the `@covers` / `exclude_id_scan` collision **(P1)**

Fix F11. This repository's test suite is built out of the strings the scanner looks for -
366 ID mentions, including literal `@covers INV-7` inside fixtures - so the exclusion is
necessary and makes `requirement_cover` permanently unsatisfiable. The M5 postscript found
the same collision for `INV-` claims; it generalises to requirements.

Options, in preference order: a distinguishable tag form that a fixture would not
naturally contain; harvesting only from comments the AST confirms (not string literals);
or per-directory exclusion with `tests/fixtures/` conventions. Whichever is chosen, say
in the config template that a project excluding its tests is giving up requirement
coverage, which nothing says today.

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

### R8 - `forge install --host <name>` **(P1)**

A manifest, never a port. Write the packaged skills to where each host reads them
(`.claude/skills/`, `AGENTS.md`, and so on), and nothing else. The rule that makes this
stay cheap: **no skill may depend on a host-specific feature** - not a subagent API, not a
hook type, not a tool name. Every mechanism lives in the kernel, and the kernel is a
command.

Do R8 after R1-R3. Shipping the harness to four agents before a change can reach a verdict
multiplies the friction by four.

### R9 - Distribution **(P2)**

Publish to PyPI so `pipx install forge-harness` works; pin the kernel version in
`.forge/config.yaml` so a repository can detect skew ([Q11](../OPEN_QUESTIONS.md)
recommends this and nothing implements it).

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
- **R11 - CLI consistency (P3).** Fix F1: `forge change show --change 1`, keeping the
  positional form as an alias.
- **R12 - Honest debt labels (P3).** Fix F8: `task.scope_and_covers` is owed by nobody
  now that M4 has shipped. Either schedule it or say it is unscheduled.
- **R13 - Open deltas define their requirements (P2, done).** Fix F16. `trace` now indexes
  `REQ-` from open changes' spec deltas, marked `provisional`; a permanent spec always
  wins, so a stale delta cannot move a folded requirement back. `REMOVED` defines nothing,
  and the archive is not a definition.
- **R14 - A task is a bullet, not a line (P1, done).** Fix F5, and the reason
  `PIT-bullet-continuation-lines` exists. `Change.tasks()` joins indented continuation
  lines; the indent requirement is what stops a closing paragraph being swallowed into the
  last task.

---

## 7. `bugfix.yaml` - the "fix bug" case **(P2)**

[MVP.md](../MVP.md) section 4 defers this to M6, and the deferral still looks right. A
bug fix runs as track B today. What a dedicated schema would add is one mandatory
artifact - `reproduce` - holding a failing test written **before** the fix, which then
becomes the `evidence:` of whatever claim the bug produces. That is the mechanism that
turns a bug into a pitfall claim instead of a forgotten commit.

Do it after R1-R5, and only once a few bugs have actually been fixed through track B, so
its shape is decided by what track B was missing rather than by what it looks like it is
missing.

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
> - **G16 - `forge archive` is unreachable on any repository today.** It blocks on a
>   verdict of `unproven`, which three kernel-owed conditions guarantee. R4 (the ledger)
>   is no longer only about the marquee feature; it is what unblocks the lifecycle.
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
