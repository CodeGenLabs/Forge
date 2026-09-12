# Run 3 — a TypeScript monorepo, and the first unforced lifecycle

> `corvus-db-studio`: 620 files, 19 packages, 90 real commits, 342 `.ts` + 99 `.tsx`.
> Cloned into a scratchpad; the original was never touched. Run on 2026-09-12.
>
> Chosen because it is shaped nothing like the flat Python library the first two runs
> used. Everything the harness believed about monorepos was untested, and the run
> found three defects that neither earlier repository could have exposed.

**The headline: this is the first complete lifecycle anywhere.** `forge init` →
bootstrap → a real track C change → `verdict: pass` → `forge archive` **without
`--force`** → the spec delta folded to the right path. Run 1 could not reach a verdict;
run 2 reached one only after a probe and archived only under `--force`.

---

## 1. What ran

| Pass | Result |
|---|---|
| `forge init`, `bootstrap derive` | 635 files, 900 import edges, 0 cycles, 369 tests |
| `bootstrap` pass 2 | 14 candidates from two subagents, **clean on the first lint** |
| review / seal | **10 ratified, 4 rejected** |
| Track C change `0001-every-seeded-driver-is-registered` | every gate passed |
| `forge verify` | **`pass`** — 8 conditions green, 2 kernel-owed pending |
| `forge archive` | succeeded unforced; folded to `docs/system/specs/driver-registry/spec.md` |
| Final `forge check` | **0 errors** |

The change came out of the bootstrap's own `## Uncertain` section, which is the
sequence the harness is built around: the scan said it could not tell whether a MariaDB
driver gap was a one-off or an instance of a general rule; the history said commit
`61df6d8` had fixed it by hand; the change settles it with a conformance test and a
`PIT-` claim. The test was **proved to fail** — the `mariadb` guard was removed, it went
red naming `mariadb`, and the guard was restored.

---

## 2. The three defects only a monorepo could find

### H1 — 93 seconds, and my first fix was wrong

`forge sync derived` took **93s** here and under a second on `requests`. Seven times
the files, a hundred times the wall clock. `gitio.blob_at` spawns `git show` per file
and four builders each walk every tracked file: ~1,900 process creations at ~47ms.

The first fix memoised a `git cat-file --batch` by resolved commit — and called
`rev_parse` to build the cache key on **every one of the 635 iterations**, trading one
subprocess per blob for one per cache lookup. 93s became 86.6s. The profiler said so
at once and my assumption had not. Hoisting the map out of the four loops is the fix:
**93s → 1.4s**, with `derive_all(dry_run=True)` reporting zero artifacts whose bytes
differ from the ones the slow path wrote.

Not only speed: `derived.freshness` gates two lifecycle points, and R5's pre-commit
hook is impossible at 93 seconds.

### H3 — the import graph was wrong on every monorepo

`packages/client/src/createClient.ts` imports `@corvus/contract`, a package inside this
same repository, and had **zero** recorded edges. The resolver skipped every specifier
not starting with a dot, reasoning that the graph is about this repository's coupling
and `react` is a lockfile fact. Right about `react`; it confused *not relative* with
*not in this repository*.

671 edges → **900**. Cycles stay 0, which is now a finding about a well-layered monorepo
rather than an artefact of dropping the only edges that could have formed one.

### H9 — a claim's prose swallowed the next section

A claim ran to the next `### <ID>` and stopped nowhere else, so a trailing
`## Uncertain` was absorbed into the last claim in the file. `CON-read-only` had
`end_line` 191 against a real end of 165.

Run 2 saw the symptom — the always-loaded budget inflating — and recorded it as **G12:
"seal copies the Uncertain section into the store"**. That diagnosis was wrong. Seal
copies nothing; the parser handed it prose that already contained the section.

The consequence run 2 never saw is the serious one. `end_line` is what R1's per-claim
edit detection uses, so **editing a section below a claim reported that claim as having
had its own definition edited** — a false obligation inside the mechanism three rounds
of narrowing had just been spent on.

Fixing it immediately unmasked a check that had been passing on borrowed prose: a
fixture component claim with one line of body satisfied `store.prose_present` only
because the section beneath it was being counted.

---

## 3. Every finding

| # | Finding |
|---|---|
| **H1** | **`sync derived` 93s → 1.4s. The first fix traded one subprocess per blob for one per cache lookup** |
| H2 | `modules` listed `docs`, `docker`, `specs`, `scripts` as architecture. A module must hold code; a directory holding only directories expands one level — which replaces the hardcoded `src`/`lib`/`pkg`/`internal` rule with the same answer for those four and the right one for a monorepo. One entry became 21 packages |
| **H3** | **Workspace package imports were dropped: 671 edges → 900, and `0 cycles` became trustworthy** |
| H4 | The `stack` line printed a dict repr, 25 packages wide. Now formatted — and it surfaced that only 7 of 25 resolve, on a repo declaring pnpm commands while carrying a `package-lock.json` |
| H5 | Command detection found all four (`build`, `lint`, `test`, `typecheck`); on `requests` it found two (positive) |
| H6 | `forge doctor` says "none declared" on a repo where `bootstrap derive` has just printed four detected commands — detection lives in derive, only seal writes config |
| H7 | The bootstrap skill's source list omitted the richest source when it exists: the rules a project already wrote down. This repo states its three most important in `AGENTS.md` |
| H8 | Pass 2 passed the candidate linter **first time** (run 2: 5 errors). The whole difference was stating, in the brief, the two conventions run 2 proved were undocumented. Both now in the skill (positive) |
| **H9** | **A claim's prose swallowed the following section, corrupting `end_line` and with it the per-claim edit rule** |
| H10 | A file-level `@covers` binds to the *first* test in the file by the proximity convention, not to the one the claim's evidence names. The check caught it and its message named which test actually carried the tag (positive) |
| H11 | A failing command recorded only the last five lines of **stderr**. For a test runner that is the least informative part: the record was an indented code fragment with no test name and no file, and the only way to learn what broke was to re-run the suite by hand. Now both streams, ANSI stripped, with the lines that name a failure picked out |

H11 paid for itself immediately. The `tests` condition went red once and green on the
next run: a flaky 10-second-timeout test in the project's own suite, which passed 405/405
when run alone. With tail-only capture there was no way to tell that from a real failure.

---

## 4. What this run did not measure

**Whether `Nearby` is read.** The change touched no claims at all — nothing anchors into
`tools/__tests__/` — so the split that three rounds of narrowing produced was never
exercised here. The question of whether a claim that needed re-reading now sits quietly
under `Nearby` remains open, and this run does not answer it.

**A second agent host.** Still one CLI, one session. [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md)
Q12 is untested.

**Whether the store helped.** Eleven claims now exist for a repository whose maintainer
already keeps `AGENTS.md` and a `docs/` tree. Whether the claims add anything over what
was already written down is exactly Q1, and nobody has measured it.
