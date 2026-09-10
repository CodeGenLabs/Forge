# MVP.md

The smallest thing worth building. Written so a second agent or session can implement it without
re-reading the research: everything needed is here or precisely referenced.

**Target:** one developer, ~2 weeks of focused work, ~2,000 lines of Python plus 6 skills.

---

## 1. The MVP thesis

Build the part nobody has built, and borrow the rest by convention rather than by code.

The part nobody has built is: **anchored, truth-source-labelled claims + deterministic staleness
detection + the claim-touch rule that makes "which documentation must change?" computable.** Everything
else in this proposal (the DAG, the gates, the delta grammar, the plan format) exists in at least one of
the six projects and is worth copying, but copying it first would produce yet another lifecycle framework
with prose knowledge.

So the MVP is ordered to prove the risky part early:

```
M0  kernel skeleton + claim store + validation        ← the format must survive contact
M1  anchors + drift detection                         ← THE RISK. Measure before building more
M2  derived tier + trace index
M3  change DAG + gates + one workflow (feature)
M4  the six skills
M5  bootstrap
```

**M1 has a stop condition.** If the false-positive rate on replayed history is bad enough that the ledger
would be noise (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q2), stop and redesign anchoring before
writing M2–M5. That is the whole reason M1 comes second rather than last.

---

## 2. Milestones

### M0 — Kernel skeleton and the claim store (~2 days)

> **Status: done, 2026-09-11.** Acceptance met: a hand-written store of ten claims across the five
> kinds passes `forge check` clean
> (`tests/test_validate.py::test_a_hand_written_store_passes_every_check`), and each of S1–S18 has a
> fixture that fails it with the right code and a working `fix`.
>
> Four deviations, each with its reason:
>
> 1. **All eighteen store checks are built, not the thirteen listed below.** S12–S15 and S17 were
>    scheduled later because they need HEAD and the derived tier; both existed by the time M0 was
>    written, so deferring them would have been sequencing for its own sake.
> 2. **The ID grammar accepts all ten prefixes, not the MVP five.** `store.py` already parsed ten so
>    that an ID from a later milestone is not silently skipped, and rejecting `API-` here would make a
>    store written for M4 fail today. What the MVP restricts is *generation*: `forge claim new` offers
>    five kinds. The kind-specific rules (S5, S7) are the validation surface the five-kind decision
>    was actually about, and those are unchanged.
> 3. **`forge claim new` prints by default and only writes with `--append`.** A generator that edits
>    the store on every invocation is one you hesitate to run.
> 4. **Retirement grounds are two claim fields, `retired-ground` and `retired-evidence`.** §10.2 said
>    `forge retire` "records the ground in the claim" without saying where; S18 needs a field to read.
>
> Three problems found by building it, all now tested:
>
> - **S1 cannot check parsed claims.** The heading pattern only matches well-formed IDs, so a typo
>   makes a claim *invisible* rather than invalid — it silently stops being part of the store.
>   Checking only what parsed would give a clean bill of health to the exact file S1 exists for, so
>   S1 scans raw headings with a laxer pattern and reports what the strict one rejects.
> - **Presence and emptiness are different questions.** `anchors: []` is legal for a concept and a
>   missing `anchors` key never is, and after normalisation the two are indistinguishable — so the
>   parser now records which keys the fence declared.
> - **PyYAML raises `ValueError`, not `YAMLError`, on `2026-02-30`.** It resolves the scalar to a
>   timestamp and lets `datetime.date` fail. Uncaught, one typo in a review date takes down every
>   command that reads the store, including the one whose job is to report it.

**Build.**

- `forge` entry point: subcommand dispatch, `--json` on every command, non-zero exit on failure, one
  issue shape `{level, code, path, line, claim, message, fix}`.
- Claim parser: heading `### <ID> — <title>` followed by a fenced ```` ```claim ```` block, then prose.
  Parse the fence as YAML; parse nothing else in the document. Code fences blanked before any regex scan
  so examples never false-positive, with line numbers preserved (BMAD's `lint_spine.py` technique).
- `forge check --scope store`: checks S1–S11 and S16, S18 below. *Revised by implementation: all
  eighteen are built, see the status note above.*
- `forge claim new <kind>`, `forge claim show <ID>`.
- `forge init`: scaffold `.forge/` and the `docs/system/` skeleton.
- Templates for each claim kind and for ADRs.

**Claim kinds in the MVP: five.** `architecture` (ARC), `component` (CMP), `concept` (CON),
`invariant` (INV), `pitfall` (PIT). Postponed: `interface` (API), `datum` (DAT), `workflow` (FLW),
`constraint` (CST), `strategy` (STR) — they add validation surface without testing the core idea.

**Acceptance.** A hand-written store of 10 claims across the five kinds passes `forge check`, and each of
S1–S11 has a fixture that fails it with the right code and a working `fix` string.

---

### M1 — Anchors and drift **(the risk milestone, ~3 days)**

> **Status: done, 2026-09-10.** Results and verdict in
> [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md). Four deviations
> from the plan below, each with its reason:
>
> 1. **Built before M0**, at the user's direction, and it was the better order: if the measurement had
>    failed, the claim schema in M0 would have had to change. Measure before fixing the format.
> 2. **`shifted` was added as a fourth status and `coarse` demoted to a flag.** Body-only edits are 79%
>    of non-fresh verdicts; surfacing them by default would have quadrupled the ledger.
>    SYSTEM_KNOWLEDGE.md §5.1 was updated to match, with the reason recorded there.
> 3. **`drift resolve`, `drift waive` and `reanchor` are not built.** All three write to a claim file or
>    the ledger, neither of which exists until M0. `forge drift` classifies anchors given on the command
>    line instead — enough to check the milestone by hand and to script against.
> 4. **A second measurement harness was needed.** The planned replay could not measure the
>    false-positive rate, because 600 commits of real history contained no pure renames and no
>    formatting-only commits. `tools/perturb_anchors.py` injects perturbations with known ground truth
>    instead.

**Build.**

- Anchor parser: `path[#Symbol][@sha]`. Reject absolute paths, `..`, NUL, and any SHA that is not 4–40
  hex characters **before it reaches `git`** (GSD's argv-injection hardening, applied to every anchor).
- Baseline resolution: the anchor's `@sha`, else the last commit touching the claim file. Use
  `git log --follow --find-renames` so a moved file resolves.
- Fingerprint: parse with tree-sitter, hash the `(node_kind, token_text)` sequence, dropping whitespace,
  comments and positions. No grammar available → whitespace-normalised content hash, flagged
  `coarse: true`.
- Symbol narrowing: locate the named declaration in the parse tree; a directory anchor uses the git tree
  hash.
- Classify: `fresh` / `shifted` (body changed, signature identical) / `stale` (signature changed) /
  `missing` / `coarse`. The `shifted`/`stale` split is Q2's recommendation and it is cheap.
- `forge drift [--paths] [--changed] [--json]` → findings + `derived/drift.json`.
- `forge drift resolve <D> --verdict V1|V2|V3|V4 [--adr N] [--evidence T]` with the enforcement table in
  [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) §6.
- `forge drift waive <D> --reason --until`.
- `forge reanchor <ID>` — restamps **only** when the fingerprint matches under the rename mapping.
- `DRIFT.md` append/close.

**Languages in the MVP: three grammars.** TypeScript/TSX, Python, Go. Everything else takes the coarse
path. Three is enough to prove the mechanism and to cover most repositories a single developer touches.

**Measurement gate — do this before M2.** Pick two real repositories with real refactoring history.
Place 30 anchors across representative symbols. Replay 200 commits. Record: spurious `stale` per commit,
spurious `missing`, and how many are resolved by rename detection alone.

| Result | Action |
|---|---|
| < 0.5 spurious `stale` per commit | proceed as designed |
| 0.5–2 | proceed, but default the ledger to `stale` only (suppress `shifted`), and revisit anchor granularity |
| > 2 | **stop.** Redesign per Q2 — coarser anchors, content-addressed anchors, or component-level only |

**Acceptance.** The measurement is run and recorded in this repository, with the number and the chosen
branch of the table.

---

### M2 — Derived tier and trace index (~2 days)

> **Status: done, 2026-09-10.** Acceptance met: `forge trace INV-7` returns claims, tests, changes and
> back-references on a fixture store (`tests/test_trace.py::test_the_acceptance_case`), regeneration is
> a no-op, and every artifact is byte-identical LF with sorted keys. The M1 debt — content-addressed
> relocation — was paid first and re-measured: 0.61% → **0.00%** false positives
> ([M1 report §3.2](docs/measurements/M1-anchor-stability.md)).
>
> Five deviations, each with its reason:
>
> 1. **No `generated_at` in the envelope.** A timestamp makes every regeneration differ, so
>    "regeneration is a no-op" and "a dirty derived file is an error" could not both hold. The commit id
>    is the provenance that matters. SYSTEM_KNOWLEDGE.md §2.3 corrected.
> 2. **The ID grammar accepts slugs, not only digits.** §7.1 said `PREFIX-\d+` while every example in
>    the same document used `CMP-payments`, `CON-capture`, `API-post-refunds`. Slugs win — `grep -r
>    CMP-payments` explains itself. What is enforced is stability, not numerality.
> 3. **`deps.json` is not built.** MVP.md specifies "shelling out to the project's configured dep tool",
>    which fails on any repo without one; writing our own import resolver is a second parser and the
>    kernel budget is better spent elsewhere. It is not in the acceptance criteria and M3's `forge
>    impact` is the first thing that actually needs it.
> 4. **`backrefs.json` was added.** The `forge:<ID>` scan needed somewhere to live, and putting it in
>    the index would have made the index non-regenerable independently.
> 5. **A minimal claim parser (`store.py`) landed early.** The index cannot exist without knowing what a
>    claim is. It parses and does not validate — M0 still owns the 18 store checks.
>
> Two problems found by building it, both now tested:
>
> - **Documentation examples polluted the index.** `forge:ARC-3` inside an illustrative code block, and
>   a literal `grep -r "forge:REQ-refunds-3"`, created entries for claims that never existed. Prose is
>   now excluded from the back-reference scan: citing an ID is normal, only code and rule files declare
>   that they *enforce* one.
> - **The derived tier made itself permanently stale.** A file cannot carry the id of the commit that
>   contains it, so committing a freshly derived artifact stamps it with its parent — and regenerating
>   to "fix" that produces another such commit. *First fix, and it was not enough: ignore commits that
>   touched only the derived tier, and exclude the tier from its own inventory. Committing four new
>   JSON files still moved `files_tracked`, and the age comparison was the wrong question anyway.
>   Corrected 2026-09-11: freshness is decided by **content** — regenerating changes the data or it
>   does not — and `commits_behind` is reported beside the verdict as provenance. SYSTEM_KNOWLEDGE.md
>   §2.3 records the full reasoning.*

**Build.**

- `forge sync derived [--paths]` producing, with provenance frontmatter
  (`generated_from_commit`, `generator`, `tool`):
  - `inventory.json` — tracked files by language, LOC, entry points, test files, stack + pinned versions
    from lockfiles;
  - `deps.json` — module→module edges and cycles, by shelling out to the project's configured dep tool;
  - `tests.json` — test file → test names → the `@covers` IDs each declares;
  - `trace.json` — the index.
- Byte-identical regeneration: running twice at one commit produces identical files. `forge check` fails
  on a dirty derived file.
- `@covers` extraction: scan test files for `@covers <ID>[ <ID>…]` in a name or an adjacent comment.
- `forge:<ID>` back-reference extraction from code comments and rule files.
- `forge trace <ID>` — bidirectional.
- `forge status` — one screen: track, phase, blocked, drift open/waived, debt, budgets,
  `enforced`/`asserted` per kind, `commits_behind`.

**Postponed from the derived tier.** `api-surface.json` (needs per-framework route detection to be
useful) and any repo map / PageRank ranking (Q7 — the first escalation, not the MVP).

**Acceptance.** `forge trace INV-7` returns its claims, tests, changes and back-references on a fixture
repository. Regeneration is a no-op. `derived/` builds on Windows and Linux with identical content.

---

### M3 — Change DAG, gates, one workflow (~3 days)

**Build.**

- Schema loader with the OpenSpec validations: Zod-equivalent shape check, no duplicate ids, `requires`
  targets exist, no cycles (DFS reporting the full path), every path field relative and containment-safe.
- Filesystem-derived state: an artifact is complete iff its `generates` path/glob exists.
- Track model: `tracks` per artifact, including the `B?` conditional; one-way upgrade recorded in
  `changes/NNNN/.forge.yaml`.
- `reads` context contract; `forge instructions <artifact> --change N --json` resolving files, derived
  selectors and `claims:` selectors.
- `forge gate <point>` with the twelve gates in [ARCHITECTURE.md](ARCHITECTURE.md) §3.3.
- `forge impact --change N`: candidate blast radius (changed/planned files + reverse deps from
  `deps.json` + `CMP-` glob matching) and the **computed claim-touch set**.
- Claim-touch completeness check (the core enforcement, R5 below).
- Spec delta grammar validation and the deterministic archive fold
  (ADDED / MODIFIED / REMOVED / RENAMED, with pre-write validation of the rebuilt spec).
- `forge verify --change N` → `verification.json` with the eight done conditions.
- `forge sync change N` — the six ordered operations, refusing on the first failure.
- `forge change new|track`, `forge archive`.
- **One workflow schema: `feature.yaml`**, serving tracks A/B/C.

**Acceptance.** A scripted end-to-end run on a fixture repository: create a change, write artifacts by
hand, watch each gate fail for the right reason when an artifact is wrong, then pass; verify; sync; the
claim `@sha` advances; the spec delta folds; `forge status` is clean.

---

### M4 — Skills (~2 days)

**Six skills for the MVP** (three of the nine postponed):

| Skill | Notes |
|---|---|
| `forge` (router) | Track classification, intent restatement, G1. Includes the one-way ratchet and the "too simple to need a spec" guard |
| `investigate` | Fresh subagent; writes its own file; produces candidates with confidence |
| `specify` | Delta requirements + scenarios; injects `rules.spec` |
| `plan-tasks` | Superpowers' plan format with `[REQ-*]` tags and no placeholders |
| `implement` | One task, TDD, file scope, budgets |
| `curate-knowledge` | Claim edits, the ledger, drift verdict proposals (Q8's narrowed form only) |

Postponed: `assess-impact` (the kernel computes the set; the agent curates it inline in the `impact`
phase without a dedicated skill until the shape is known), `design` (the `specify` skill covers track C's
design section initially), `review` (use the host's own code-review skill for the MVP).

Every skill: ≤250 lines, plain markdown with no host-specific syntax, announce-on-entry, kernel-first, no
compulsion language, and a pressure test in `tests/skills/<name>/` that fails without the skill.

**Acceptance.** Each skill's pressure test shows a failing baseline and a passing run. A track-B change
runs end-to-end through the skills on a fixture repository.

---

### M5 — Bootstrap (~2 days)

**Build.**

- `forge bootstrap derive` — pass 1, pure derivation, no claims. This is most of the brief's bootstrap
  sketch and it is fully deterministic.
- `forge bootstrap review` — pass 3: walk candidates highest-value-kind first, batches of ≤8, reject by
  default, interleave the `Uncertain` questions, never ask what a scan can answer.
- `forge bootstrap seal` — write ratified claims with anchors stamped at HEAD, `OVERVIEW.md`,
  `ADR-0001-adopt-forge.md` recording what was *not* ratified and the cap in force, and
  `.forge/config.yaml` with detected commands.
- Candidate validation: anchors required, admission criterion linter, no invented rationale,
  invariants must name enforcing code or a proving test.

Pass 2 (candidate generation) is a **skill**, not kernel code: parallel subagents per topic writing
`candidates/<topic>.md` directly. Per Q14, the MVP front-loads `CON-` and `PIT-` — vocabulary and known
traps — rather than scanning for components and architecture.

**Acceptance.** Bootstrap run on this repository and on one real external repository. Recorded outcome:
how many candidates, how many ratified, how long the review took, and which kinds were actually useful in
the first subsequent `investigate`.

---

## 3. Deterministic checks in the MVP

Every one is a script. Codes are stable; each carries a `fix`.

### Structural (store)

| # | Code | Check | Level |
|---|---|---|---|
| S1 | `store.id_format` | ID matches `^(ARC\|CMP\|CON\|INV\|PIT)-(\d+\|[a-z0-9][a-z0-9-]*)$` — number or kebab slug | ERROR |
| S2 | `store.id_unique` | IDs unique store-wide; ascending within a file; never reused | ERROR |
| S3 | `store.claim_fence` | Well-formed `claim` fence; parses as YAML | ERROR |
| S4 | `store.required_fields` | `kind`, `status`, `truth-source`, `anchors`, `reviewed` present and in range | ERROR |
| S5 | `store.anchor_required` | `anchors` non-empty unless kind ∈ {concept} (MVP: `constraint` absent) | ERROR |
| S6 | `store.evidence_required` | `status: enforced` ⇒ `evidence` non-empty and every entry resolves | ERROR |
| S7 | `store.adr_required` | `kind: architecture` ⇒ `since` present and the ADR file exists | ERROR |
| S8 | `store.governs_dag` | `governs` targets exist, no self-reference, acyclic | ERROR |
| S9 | `store.placeholder` | No TBD/TODO/FIXME/XXX/`{token}`/`[NEEDS CLARIFICATION`/`similar to <ID>` (fences blanked) | ERROR |
| S10 | `store.candidate_isolation` | No `confidence` outside `candidates/`; all candidates `status: proposed` | ERROR |
| S11 | `store.prose_present` | Prose body ≥2 non-blank lines | ERROR |
| S12 | `store.anchor_missing` | Every anchor path/symbol exists at HEAD | ERROR |
| S13 | `store.derivable_smell` | >60% of prose identifiers appear in its anchors **and** no modal verb | WARNING |
| S14 | `store.listing_smell` | `CMP-` claim with a path glob and <15 words of explanation | WARNING |
| S15 | `store.stack_fact_smell` | Prose contains a version pattern next to a package name | WARNING |
| S16 | `store.budget` | Always-loaded set within `budgets.always_loaded_lines` | ERROR |
| S17 | `store.orphan` | No inbound `governs`, no `forge:<ID>` back-reference, not cited by the last N changes | WARNING |
| S18 | `store.retire_ground` | `status: retired` ⇒ a recorded ground 1–4 with evidence | ERROR |

### Relational (cross-artifact)

| # | Code | Check | Level |
|---|---|---|---|
| R1 | `trace.backref_valid` | Every `forge:<ID>` names an existing non-retired claim | ERROR |
| R2 | `trace.evidence_test_exists` | Every `evidence: test:` appears in `tests.json` | ERROR |
| R3 | `trace.evidence_rule_exists` | Every `evidence: rule:` id exists in the named rule file | ERROR |
| R4 | `trace.requirement_task_coverage` | Every `REQ-*` referenced by ≥1 task; every task references ≥1 `REQ-*` or is `chore` | ERROR |
| R5 | `trace.claim_touch_complete` | **Every computed claim-touch member accounted for in `impact.md`** | ERROR |
| R6 | `trace.superseded_has_adr` | Every `Superseded` entry names an existing ADR whose `supersedes` matches | ERROR |
| R7 | `trace.requirement_discharged` | Every `REQ-*` has ≥1 passing test carrying its `@covers` tag | ERROR |
| R8 | `graph.requires_satisfied` | DAG `requires` satisfied for every present artifact | ERROR |
| R9 | `graph.track_artifacts` | Required artifacts present for the declared track | ERROR |
| R10 | `derived.clean` | Regeneration is a no-op — *revised: the original also required `generated_from_commit == HEAD`, which no committed file can satisfy (SYSTEM_KNOWLEDGE.md §2.3)* | ERROR |
| R11 | `derived.freshness` | `commits_behind ≤ thresholds.derived_stale_commits` — *provenance, reported beside R10's verdict rather than as one* | WARNING (ERROR at `implement:pre`) |
| R12 | `spec.grammar` | Requirement/scenario headings; ≥1 scenario each; SHALL/MUST; MODIFIED full content; REMOVED has Reason+Migration | ERROR |
| R13 | `spec.nonempty_or_skip` | Zero-delta rejected unless `skip_spec: true` with a reason | ERROR |
| R14 | `task.format` | Exact files, `[REQ-*]` tag, verify command, `Consumes`/`Produces` signatures, no placeholders | ERROR |
| R15 | `task.interface_consistency` | `Produces` in task N matches `Consumes` in task M by name and type | ERROR |
| R16 | `task.scope` | A task's diff touches only its declared files | ERROR |
| R17 | `drift.open_blocking` | No open unwaived `DRIFT.md` entry on a claim in this change's touch set | ERROR |
| R18 | `debt.open_blocking` | No open unwaived `DEBT.md` entry introduced by this change | ERROR |
| R19 | `verify.definition_of_done` | The eight conditions | ERROR |
| R20 | `repo.clean` | At `converge`: tasks checked, archive complete, whole-repo `forge check` passes | ERROR |

**39 deterministic checks.** For comparison, Spec Kit's entire deterministic surface is
"does this file exist".

### LLM checks in the MVP — five, all advisory

1. Is each requirement testable as written? Do any two mean the same thing? (`spec` phase)
2. Is any `Unaffected` justification wrong; is there a consumer static analysis cannot see (queue, cron,
   client SDK, dashboard query)? (`impact` phase)
3. Would a fresh engineer execute this task from its text alone; is any task doing two things?
   (`tasks` phase)
4. Does this diff satisfy its task and only its task; is the code quality acceptable?
   (per-task review, two stages)
5. Does this proposed claim satisfy the admission criterion — could a competent engineer read it off the
   compliant code? (`sync`, at G5)

Everything else the corpus does with a prompt, the MVP does with a script or does not do.

---

## 4. What the MVP does NOT build

| Not building | Why | When to revisit |
|---|---|---|
| Multi-agent personas | Costume, not capability (RESEARCH.md §5.2) | Never |
| Knowledge graph / graph DB | GSD's became a fourth representation with its own rot | Only if `governs` + `trace.json` demonstrably fails |
| Embeddings / RAG over the store | 40 claims fit in a grep; the bottleneck is trust, not retrieval | Never at this scale |
| Code index (SCIP / LSIF) | Host search + tree-sitter + dep tool suffices | When `investigate` routinely blows its step budget (Q7); and then as a derived repo-map, not an index server |
| Execution engine / model client | The host has one; mini-SWE-agent shows ~200 lines is competitive | Never |
| MCP server | The kernel is a CLI; a CLI composes with every host | If a host cannot shell out |
| `api-surface.json` and API/DAT claim kinds | Needs per-framework route and schema detection to be useful | M6, for a project with a public HTTP API |
| `oasdiff` contract gate | Depends on the above | With API claims |
| Architecture rule generation | Maintain the ecosystem tool's config by hand and bind it via `evidence: rule:` — generating configs is a compiler | After the binding proves useful on 5+ claims |
| Multiple workflow schemas | `feature.yaml` with three tracks covers feature, bugfix (as track B) and refactor (`skip_spec`) | M6: `bugfix.yaml` for the mandatory `reproduce` artifact |
| `analyze` as a phase | It is a gate (Q9) | If the LLM semantic checks earn their tokens |
| Append-only decision log | Solves a multi-writer problem we do not have (Q6) | If concurrent knowledge writes become real |
| Cross-project knowledge store | Personal preferences, not system knowledge (Q11) | Never in the harness |
| Multi-host plugin manifests | Superpowers pays ~15KB of sync script for this (Q12) | Second host, and then as a manifest only |
| Prose `rules/` directory, `workflows/` directory, `state/` directory | Divergence, over-building, and a lie respectively (ARCHITECTURE.md §3.1) | Never |
| `forge stats` | Needs data from real use first | After ~10 changes (Q1) |

---

## 5. Definition of done for the MVP

1. `forge check` passes on this repository's own `docs/system/` store.
2. The M1 anchor measurement is run and its number recorded here.
3. One real change is taken end-to-end through track C on a real repository, and the resulting claim
   store is something a human would keep.
4. One deliberate drift is introduced (change a symbol an invariant is anchored to), `forge drift` finds
   it, the ledger proposes a verdict, and a recorded V3 with an ADR closes it — **without the claim ever
   being auto-rewritten**.
5. One change is attempted where a claim is edited without accounting for it, and `forge sync` refuses.
6. `forge status` fits on one screen.
7. Kernel LOC under 2,500; 6 skills, each ≤250 lines; 12 gates.
8. Every principle in [CONSTITUTION.md](CONSTITUTION.md) has its `Mechanism` field verified against the
   implementation, and the aspirational ones are relabelled honestly.

Criteria 4 and 5 are the real ones. They are the two behaviours no existing tool has, and if they work
the design is validated; if they are awkward in practice, the design is wrong in a way no amount of
further reading would have revealed.

---

## 6. If I had to build this from zero today

*(The brief's final question, answered directly.)*

### What I would build

**A ~2,000-line deterministic CLI plus six markdown skills, whose single novel contribution is the
anchored claim.**

Concretely, in priority order:

1. **The claim** — a stable ID, a `truth-source`, `anchors` into the code, `evidence` when enforceable,
   and prose that says something the code cannot. This is the whole idea. Everything else is plumbing
   around it.
2. **Deterministic staleness** — tree-sitter AST fingerprints compared against the anchor's recorded SHA.
   Not "is this doc true" (unanswerable) but "has the code this claim describes changed since a human
   last confirmed it" (answerable in milliseconds, and exactly the set a reviewer needs).
3. **The claim-touch rule** — for every change, compute the claims whose anchors or globs intersect the
   diff, and refuse to proceed until each is accounted for as unaffected, updated or superseded. This
   turns "which documentation must change because of this implementation?" from a judgement call into a
   set operation. It is the mechanism I could not find anywhere in the corpus and the one I would build
   first if I could only build one thing.
4. **The four-verdict drift ledger with no auto-reconciliation path.** The kernel has no command that
   rewrites a claim from code. That absence is a feature, and it is directly justified by measurement:
   LLMs lose 21–43 percentage points of detection accuracy in precisely the code-changed-doc-unchanged
   case, and their confidence does not separate right from wrong answers.
5. **Binding architecture claims to the ecosystem's own conformance tool.** For the subset of
   architectural claims that can be a dependency rule — which is most of the ones that matter —
   "architectural drift detection" is a solved linting problem that nobody in the corpus wired up. A
   claim marked `enforced` names a rule; the rule names the claim; both are checked.
6. **The lifecycle, borrowed wholesale**: OpenSpec's artifact DAG and archive fold, GSD's declarative
   gates, Superpowers' scale router and plan format, Spec Kit's requirement vocabulary,
   mini-SWE-agent's budgets. None of this is novel and all of it works. I would not spend a day
   inventing here.

### What I would deliberately not build

- **An agent, an orchestrator, or an execution loop.** mini-SWE-agent scores >74% on SWE-bench Verified
  with ~200 lines and a bash tool. The host already has a better loop than I would write. Every hour
  spent here is an hour not spent on the knowledge layer, which is the actual unsolved problem.
- **A knowledge graph or a code index.** GSD built both and ended up with four representations of the
  same system, each with its own staleness story. Edges you cannot verify are liabilities. Grep,
  tree-sitter and the ecosystem's dependency tool are enough until they measurably are not.
- **Agent personas.** BMAD's five personas are five skills wearing hats. The value is in the checklist,
  not the character. Subagents are for context isolation and parallelism; that is a real benefit and it
  needs no roleplay.
- **Any check implemented as a prompt that could be a script.** Spec Kit's `/analyze` asks a model to
  build an ID inventory by keyword inference and then compute coverage percentages "deterministically".
  That is a grep. Half the corpus's apparent sophistication is prompts doing arithmetic badly.
- **Auto-generated documentation of any kind.** Anything a scan can produce goes in `derived/` as JSON
  with commit provenance, never in prose as knowledge. The store contains only what the code cannot say.
- **A large skill library.** Nine skills is the ceiling and six is the MVP. 29 skills and 2.4 MB (BMAD)
  or 44 capabilities and ~90 workflows (GSD) is what happens when the framework grows faster than the
  projects it serves — and every line is paid in every session.
- **A complete bootstrap.** Reject by default. A baseline of 8 concepts and 6 pitfalls, all
  human-confirmed, beats 40 inferred component descriptions, because plausible-but-wrong knowledge is
  worse than none and it takes six months to find out which is which.
- **A "docs coverage" metric.** It rewards volume and invites gaming. `enforced` versus `asserted` is the
  honest number.

### Why this shape and not the obvious alternatives

**Why not "Superpowers plus a system-knowledge folder"?** Because a folder of prose is exactly what GSD
already has, and its drift detection had to fall back to `structureMd.includes(prefix)` — substring
matching against free-form markdown — because prose is not checkable. The format has to change first;
adding documents to a behavioural harness does not produce a knowledge layer.

**Why not "OpenSpec plus ADRs"?** Closest of the six, and it is the skeleton I am borrowing. But
OpenSpec's permanent tier is only externally observable requirements. It has no components, no dependency
direction, no non-observable invariants, no anchors and no staleness signal at all, so the moment the code
moves underneath a requirement nothing notices. Adding ADRs adds rationale and not verifiability.

**Why not "just use the tools"** — ArchUnit, oasdiff, ADRs in a folder, tests as specs? This is the
strongest alternative and it is most of my answer. The gap it leaves is that nothing connects the tools
to the reasoning: no one artifact says *this rule exists because of that decision, and it governs those
components, and here is the property it protects*. That connective tissue is what an agent needs and
what a rule file cannot carry. The claim is the connective tissue; the tools are the enforcement.

**Why not go bigger?** Because the corpus is unanimous on one point that nobody states out loud: the
projects with the most machinery have the least evidence that the machinery helps, and the project with
no methodology at all posts the only real numbers. Under that uncertainty, the correct move is to build
the smallest thing that could be *wrong in an informative way* — and then measure it (Q1, Q2, Q3).

### The one-sentence version

Build the anchored claim and the machinery that makes it checkable; borrow the lifecycle from OpenSpec
and GSD; delegate execution to the host; refuse everything else until measurement says otherwise.
