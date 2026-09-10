# WORKFLOW.md

The lifecycle. Every phase below is a node in a declared artifact DAG (OpenSpec's mechanism), gated by
deterministic checks at named points (GSD's mechanism), with the required node set selected by a scale
router (Superpowers' mechanism). Read [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) first — several phases
exist only to serve it.

Working name for the tool: `forge`.

---

## 0. Two things that make this enforceable rather than advisory

**The DAG is data.** `.forge/schema/<track>.yaml` declares artifacts with `id`, `generates`, `requires`,
`template`, `instruction`. Ordering is computed, not prompted. State is derived from the filesystem —
an artifact is complete iff its `generates` path exists — so there is no state file to desynchronise.

**Gates are exit codes.** A gate is `{point, check, blocking, when, onError}`. `forge gate <point>` runs
the gates registered at that point and exits non-zero if a blocking one fails. Nothing in the lifecycle
is enforced by an instruction telling the model to be careful.

Gate points: `investigate:pre`, `spec:post`, `impact:post`, `design:post`, `analyze:post`, `tasks:post`,
`implement:pre`, `implement:task:post`, `verify:pre`, `verify:post`, `sync:pre`, `converge:post`.

---

## 1. Tracks: the scale router

Classification happens once, out loud, at the start of `understand`. The ratchet is **one-way**:
discovering hidden complexity upgrades the track and is recorded; nothing downgrades.

| | **Track A — Probe** | **Track B — Bounded** | **Track C — Structural** |
|---|---|---|---|
| When | A question, not a deliverable. "Can we…", "is it possible…", spikes, throwaway | A well-scoped change to a flow that **already exists in this repo** and touches no `ARC-`/`API-`/`DAT-` claim | New subsystem or capability; changes a component boundary, a public interface, the data model, an invariant, or any `ARC-` claim; or a security/migration-sensitive change |
| Required artifacts | none (a chat answer) | `proposal.md` (with an inline `## Claims touched`), `spec/` **if behaviour changes**, `tasks.md` | `proposal.md`, `spec/`, `impact.md`, `design.md`, `tasks.md` |
| Phases run | understand, investigate | understand, investigate, spec?, tasks, implement, verify, sync, converge | all |
| Human gates | G1 | G1, G5 | G1, G2, G3, G5, and G4/G6 if triggered |
| Budget (default) | 15 steps / 10 min | 60 steps / 45 min | uncapped steps, per-task caps apply |
| Code kept | No — labelled throwaway | Yes | Yes |

**Automatic upgrade triggers** (computed, not judged). `forge track check` upgrades B→C when the
candidate blast radius intersects any `ARC-`, `API-`, or `DAT-` claim; when the diff adds a public export,
a route, or a migration; or when `> N` files (default 15) are in scope. A→B/C when the probe's output
would be kept.

**Anti-pattern guard, borrowed from Superpowers.** "It's too simple to need a spec" is itself the signal
to take the heavier track. What scales down with simplicity is the *artifact size*, never the approval.

---

## 2. The change lifecycle

```
USER REQUEST
  │
  ├─ understand ─────► track decision + restated intent            [G1 human]
  │
  ├─ investigate ────► investigation notes + candidates/            (fresh subagent)
  │
  ├─ spec ───────────► changes/NNNN/spec/**  (delta requirements)   [G2 human, track C]
  │
  ├─ impact ─────────► changes/NNNN/impact.md (claim-touch account)
  │
  ├─ design ─────────► changes/NNNN/design.md  (+ ADR if needed)    [G3 human, track C]
  │
  ├─ analyze ────────► analysis report (read-only, no files edited)
  │
  ├─ tasks ──────────► changes/NNNN/tasks.md
  │
  ├─ implement ──────► code + tests, per task, TDD                  (fresh subagent per task)
  │   └─ test folded into each task's red→green cycle
  │
  ├─ verify ─────────► changes/NNNN/verification.json (evidence)
  │
  ├─ sync ───────────► permanent specs + claims + derived/ updated  [G5 human]
  │
  └─ converge ───────► archived change, clean drift ledger
```

Two phases from the brief's sketch are deliberately not separate documents:

- **`test`** is folded into `implement` as the red half of each task's TDD cycle. A separate `tests.md`
  artifact describing tests that do not exist yet is a plan for a plan; the spec's scenarios already
  carry the test intent.
- **`verification.md`** is generated (`verification.json` + a rendered summary), not authored. An
  authored verification report is a place to write "all tests pass" without having run them, which is
  exactly the failure mode Superpowers wrote a whole skill to prevent.

`consistency analysis` and `system impact analysis` from the brief map to `analyze` and `impact`
respectively; `knowledge-sync.md` becomes the deterministic `sync` operation rather than a document.

---

## 3. Phase reference

Each phase: purpose → inputs → outputs → tools → human gate → deterministic checks → LLM checks → exit
criteria.

---

### 3.1 `understand`

**Purpose.** Convert a request into a stated intent, a track, and an explicit list of what is unknown.
Not to plan, not to explore the code deeply, not to write anything but a short statement.

**Inputs.** The user's request. `docs/system/OVERVIEW.md`. The claim *index* (IDs + one-line titles only,
not bodies) — this is the just-in-time retrieval pattern: names now, bodies when needed.

**Outputs.** A short restatement in chat: what the user wants, what track this is and why, what is
unknown. For track A/B nothing is written to disk. For track C, `changes/NNNN-<slug>/.forge.yaml`
(`track`, `created`, `intent`).

**Tools.** None beyond reading two small files.

**Human gate — G1 (always, every track).** The user confirms the restated intent and the track. This is
the only universal gate and it is short: a nod, or a correction. Rationale: track choice determines
every subsequent obligation, and mis-tracking is the single most expensive mistake in the lifecycle.

**Deterministic checks.** Track value is one of A/B/C. Slug is unique and filesystem-safe. Change
directory does not already exist.

**LLM checks.** Is the request ambiguous in a way that changes the work? Ask **one** question at a time,
and only questions a repository scan could not answer — asking the user to confirm something greppable is
a defect (BMAD's rule, adopted verbatim).

**Exit criteria.** Intent restated and confirmed; track recorded; unknowns enumerated.

---

### 3.2 `investigate`

**Purpose.** Learn what is actually true about the parts of the system this change touches, and record
only what is not derivable.

**Inputs.** The intent. `derived/inventory.json`, `derived/deps.json`, `derived/api-surface.json`. The
claim bodies for claims whose `CMP-` globs or anchors intersect the likely scope. The repository itself.

**Outputs.** `changes/NNNN/investigation.md` (track C) or a chat summary (track A/B), containing:
what exists today, the relevant claims by ID, the reverse-dependency set, contradictions found between
claims and code, and explicit unknowns. Any non-derivable discovery that is *not* already a claim goes to
`docs/system/candidates/<topic>.md` with `status: proposed` and a `confidence`.

**Tools.** grep / glob / tree-sitter via the host agent; `forge trace claims --paths <globs>`;
`forge drift --paths <globs>`; the ecosystem's dependency tool.

**Context isolation.** Run as a **fresh subagent** for track C, or for any investigation expected to read
more than ~20 files. It writes its own output file and returns only a summary, so the reading never
enters the main session's context (GSD's fan-out rationale, backed by the context-rot findings).

**Human gate.** None.

**Deterministic checks (`investigate:pre`).** `derived/` is not more than N commits behind HEAD
(default 20) — otherwise `forge sync derived` runs first. Warn if any claim in scope is `stale` or
`missing`, because investigating against unverified knowledge is how premise drift enters a plan (GSD's
context-drift gate, generalised).

**LLM checks.** Is any existing claim contradicted by what I just read? (Contradictions found here are
appended to `DRIFT.md` as open items — they are drift discovered by reading, and they get the same
four-verdict treatment as drift discovered by anchor comparison.)

**Exit criteria.** Every unknown from `understand` is either answered, recorded as a candidate with a
confidence, or promoted to a question for G2. No claim contradiction left unrecorded.

---

### 3.3 `spec`

**Purpose.** State what the system must do after this change, as delta requirements against permanent
capability specs. Behaviour only — no implementation.

**Inputs.** Intent, investigation, the permanent specs for the capabilities named in `proposal.md`, the
project's `rules.spec` list from `.forge/config.yaml`.

**Outputs.** `changes/NNNN/spec/<capability-path>/spec.md` using the closed delta grammar (OpenSpec's,
adopted directly):

```markdown
## ADDED Requirements

### Requirement: REQ-refunds-1 — An operator can refund a settled payment
The system SHALL allow a refund against any settled payment up to its remaining refundable balance.

#### Scenario: Partial refund within balance
- **WHEN** an operator refunds 30 against a payment of 100 with no prior refunds
- **THEN** the refund settles and the remaining refundable balance is 70

#### Scenario: Refund exceeding remaining balance
- **WHEN** an operator refunds 80 against a payment of 100 with 30 already refunded
- **THEN** the request is rejected with `refund_exceeds_balance` and no ledger entry is written

## MODIFIED Requirements
...   (full updated content, never a diff fragment)

## REMOVED Requirements
### Requirement: REQ-old-4 — …
**Reason**: …
**Migration**: …
```

Plus `proposal.md`: **Why** (1–2 sentences), **What changes** (bullets, `**BREAKING**` marked),
**Capabilities** (new / modified, by exact existing path), **Impact** (affected code, APIs, deps).

**Tools.** `forge spec new <capability>`; `forge check spec`.

**Human gate — G2 (track C; track B only when the spec introduces a new capability).** The user reads
the delta spec. Rationale: this is the contract. Everything downstream argues from it, and a wrong
requirement wastes the entire remainder of the lifecycle. Kept to *one* gate by making it the only place
product intent is confirmed.

**Deterministic checks (`spec:post`).** Requirement headings match the grammar; every requirement has
≥1 `#### Scenario:`; scenarios use exactly four hashes; normative statements use SHALL/MUST; requirement
IDs unique and stable; zero `[NEEDS CLARIFICATION]` remaining; `MODIFIED` blocks contain full content;
`REMOVED` blocks contain Reason and Migration; new capabilities carry a `## Purpose` of ≥ the minimum
length; **a change with zero deltas is rejected unless `.forge.yaml` sets `skip_spec: true` with a
reason** (OpenSpec's named-bypass pattern).

**LLM checks.** Is each requirement testable as written? Do any two requirements overlap or conflict in
meaning? Does any requirement describe implementation rather than observable behaviour? Are the scenarios
sufficient to discharge the requirement, or is there an obvious uncovered case?

**Exit criteria.** All deterministic checks pass; G2 recorded; every scenario is something a test could
assert.

---

### 3.4 `impact`

**Purpose.** Answer, before any code exists: what does this change touch, and which system knowledge must
change as a result. This phase is where the harness's central enforcement lives.

**Inputs.** Spec, investigation, `derived/deps.json`, all claims (metadata only — anchors and globs),
the *planned* file scope from the proposal.

**Outputs.** `changes/NNNN/impact.md` (track C; for track B this is a `## Claims touched` section inside
`proposal.md`, same rules, same checks):

```markdown
## Blast radius
Files in scope (planned): src/payments/refund.ts, src/payments/ledger.ts, src/web/routes/refunds.ts
Reverse dependents: src/app/checkout.ts, src/reporting/settlement.ts
Components: CMP-payments (primary), CMP-web (edge)

## Claims touched
### Unaffected
- CMP-orders — no file in scope matches its globs; order lifecycle untouched
- CON-capture — vocabulary unchanged
- DAT-4 — identity rule unchanged; refunds hang off the existing payment id

### Updated
- INV-7 — the bound becomes cumulative across partial refunds, not per-refund

### New
- API-post-refunds — new public endpoint; contract required
- INV-12 — a refund is idempotent per idempotency-key

### At risk
- ARC-3 — a naive implementation reads the ledger from the domain layer; design must resolve

## Requires ADR
- none (if the design keeps the ledger read behind a port)

## Not covered by tests today
- the settlement report path (src/reporting/settlement.ts) has no integration test; add one or record in DEBT.md
```

**Tools.** `forge impact --change NNNN` produces the *candidate* blast radius and the *computed*
claim-touch set; the agent curates the prose. Half-machine, half-judgement, by design (CodePlan's shape,
without CodePlan's cost).

**Human gate.** None of its own — the `At risk` and `Requires ADR` entries feed G3.

**Deterministic checks (`impact:post`).** Every member of the computed claim-touch set appears under
exactly one heading; every `Superseded` entry names an existing ADR; every `New` claim has a proposed
kind and anchors; `At risk` entries naming an `ARC-`/`API-`/`DAT-` claim force `track: C`.

**LLM checks.** Is any "Unaffected" justification actually wrong? Is there an affected workflow or
consumer that dependency analysis cannot see (a queue consumer, a cron, a client SDK, a dashboard query)?

**Exit criteria.** Claim-touch set fully accounted; track finalised; ADR requirement determined.

---

### 3.5 `design`

**Purpose.** Decide *how*, and record the decisions worth remembering. Track C only.

**Inputs.** Spec, impact, the `ARC-`/`CMP-` claims that constrain the area, `rules.design` from config.

**Outputs.** `changes/NNNN/design.md` with **Context** (only what is needed to explain the approach;
reference the proposal rather than restating it), **Goals / Non-goals**, **Decisions** (each with
alternatives considered and why rejected), **Risks / Trade-offs** (`[Risk] → Mitigation`),
**Migration plan** (if applicable), **Open questions** (genuinely deferrable only).

Plus, when required by `impact.md`: `docs/system/decisions/ADR-NNNN-<slug>.md` — status, context,
decision, consequences, alternatives, `supersedes`, and the claim IDs it justifies.

**The rule that distinguishes design.md from an ADR:** `design.md` is per-change and gets archived; an
ADR is permanent. A decision goes in the ADR **iff** a future engineer would need it to understand why
the code is shaped this way. Everything else stays in `design.md`. This fixes OpenSpec's problem of
live rationale ending up in `changes/archive/*/design.md`.

**Tools.** `forge adr new`; `forge check design`.

**Human gate — G3 (track C).** The user approves the approach and any ADR. Rationale: this is the last
point where a wrong direction is cheap. Present decisions with alternatives, not a narrative.

**Deterministic checks (`design:post`).** Every `Decisions` entry has a rationale and at least one
alternative considered; no placeholders; every claim marked `Superseded` in `impact.md` has an ADR whose
`supersedes` names the prior decision; every ADR references ≥1 claim ID; `Open questions` is empty or
each entry states why it can wait.

**LLM checks.** Does the design satisfy every requirement in the spec? Does it violate any `ARC-` claim
that `impact.md` did not flag? Is a simpler approach available that the design does not consider? Is any
"open question" actually blocking (one that would change the spec, the approach, or the task breakdown
must be resolved now, not deferred)?

**Exit criteria.** All deterministic checks pass; G3 recorded; no `At risk` claim left unresolved.

---

### 3.6 `analyze`

**Purpose.** Cross-artifact consistency, before implementation. **Read-only: this phase never edits a
file.** (Spec Kit's constraint, adopted.)

**Inputs.** Everything produced so far, plus the constitution and the claim store.

**Outputs.** A report to the terminal and `changes/NNNN/analysis.md` (findings table + coverage table +
metrics). Findings carry stable IDs and severity CRITICAL / HIGH / MEDIUM / LOW. Remediation is
*offered*, never applied.

**Deterministic checks (`analyze:post`) — this is the bulk of the phase.**

| # | Check | Severity |
|---|---|---|
| 1 | Required artifacts present for the declared track | CRITICAL |
| 2 | DAG `requires` satisfied for every present artifact | CRITICAL |
| 3 | Every `REQ-*` in the spec is referenced by ≥1 task | CRITICAL |
| 4 | Every task references ≥1 `REQ-*` (or is tagged `chore`) | HIGH |
| 5 | Claim-touch set fully accounted in `impact.md` | CRITICAL |
| 6 | Placeholder scan across all change artifacts | HIGH |
| 7 | Task IDs unique and unambiguous within `## N.` groups | MEDIUM |
| 8 | Every claim marked `Superseded` has its ADR | CRITICAL |
| 9 | Constitution rules that are mechanised (see `.forge/config.yaml` `rules`) | CRITICAL |
| 10 | No claim in scope is `missing`; `stale` claims all appear in `impact.md` | HIGH |
| 11 | Every file named in a task exists or is marked `Create:` | MEDIUM |
| 12 | Interfaces declared `Produces:` by one task and `Consumes:` by another agree on names and types | HIGH |
| 13 | Contract-bearing `API-` claims: contract file named and present | HIGH |
| 14 | Data-model change in scope without a migration in the task list | HIGH |

**LLM checks (advisory, capped at 20 findings).** Terminology drift across artifacts; two requirements
that mean the same thing; a requirement whose scenarios do not actually discharge it; an implicit
ordering dependency between tasks not stated in the plan; a task that contradicts a live claim's prose.

**Exit criteria.** Zero CRITICAL findings. HIGH findings acknowledged in one line each. Below that, the
report is informational.

---

### 3.7 `tasks`

**Purpose.** Decompose into independently reviewable, independently testable units.

**Inputs.** Spec, design, impact, `rules.tasks`.

**Outputs.** `changes/NNNN/tasks.md`. Format is Superpowers' plan format, tightened with IDs:

```markdown
## 2. Refund domain logic

- [ ] 2.1 [REQ-refunds-1, INV-7] Reject refunds over the remaining balance
  **Files:** Modify `src/payments/refund.ts#computeRefundable`; Test `tests/payments/refund.spec.ts`
  **Consumes:** `Payment.capturedAmount: Money`, `Refund.settledTotal(paymentId): Money`
  **Produces:** `computeRefundable(payment: Payment, settled: Money): Money`
  **Verify:** `pnpm test tests/payments/refund.spec.ts` — the new case fails before, passes after
  - [ ] write the failing test (literal code below)
  - [ ] run it, confirm it fails with the expected message
  - [ ] minimal implementation
  - [ ] run it, confirm pass; run the file's whole suite
  - [ ] commit
```

Rules, all deterministic: every task carries a `[REQ-*]`/`[INV-*]` tag; every task names exact files;
every task states a verification command and its expected transition; interfaces are declared with real
signatures; **no placeholders** — "add appropriate error handling", "TBD", "similar to task N", "write
tests for the above" without literal test code are all rejected.

**Task right-sizing** (Superpowers, adopted): a task is the smallest unit that carries its own test cycle
and is worth a fresh reviewer's gate. Fold setup and docs into the task whose deliverable needs them.
Split only where a reviewer could reject one task while approving its neighbour.

**Human gate.** None. If the tasks are wrong, `analyze` or the per-task review catches it, and G3 already
approved the approach.

**Deterministic checks (`tasks:post`).** All of the above; plus every `REQ-*` covered; plus
`Produces`/`Consumes` consistency across tasks (check 12 above); plus a schema-change task exists if the
data model is in scope (GSD's schema gate, moved earlier so it is a planning failure rather than a
verification surprise).

**LLM checks.** Is any task doing two things? Is the ordering actually forced by dependency or just
listed? Would a fresh engineer with no context be able to execute task N from its text alone?

**Exit criteria.** All checks pass; every requirement covered; no placeholders.

---

### 3.8 `implement`

**Purpose.** Turn tasks into code, test-first, one task at a time.

**Inputs.** One task, plus its declared `Consumes` interfaces, plus the claims in the touch set for that
task's files, plus project conventions. **Not** the whole change, not the session history.

**Outputs.** Code, tests, one commit per task, checkboxes updated.

**Execution model.** Fresh subagent per task (Superpowers). The subagent receives a constructed brief —
task text, allowed file scope, the specific claims and their prose, the verification command — and
returns a diff and the verification output. The orchestrating session keeps only the ledger. Budgets are
enforced in code (mini-SWE-agent): per-task step cap, wall-time cap, and a consecutive-failure cap;
the trajectory is written to `changes/NNNN/trajectories/<task>.json` on every step.

**The TDD cycle, non-negotiable within a task.**

```
write the failing test  →  RUN IT, SEE IT FAIL  →  minimal implementation
      →  RUN IT, SEE IT PASS  →  run the file's suite  →  refactor if needed  →  commit
```

The second step is the one that gets skipped and the one that matters: a test you never watched fail is
not evidence, it is decoration. `implement:task:post` records the observed red and green outputs in the
trajectory, and `verify` cross-checks that both exist for every task tagged with an `INV-` claim.

**Guardrails at the tool level, not the prompt level** (SWE-agent's mechanism). Where the ecosystem
allows: run the linter/parser before and after an edit and revert the edit if new syntax errors appear,
returning the error text. Refuse edits outside the task's declared file scope.

**Human gate.** None between tasks. Superpowers is right that a running plan should not wait on a human;
conflicts, ambiguities and plan defects are decided and recorded, not queued. **Except** the two hard
stops in §4: a destructive migration and a security-sensitive decision stop immediately regardless of
where they surface.

**Deterministic checks.** `implement:pre`: working tree clean, on a branch/worktree, `derived/` fresh,
`analyze` passed. `implement:task:post`: the task's verification command exits 0; the diff touches only
declared files; new/changed test files carry `@covers` tags for the task's requirement IDs; commit
message references the task ID.

**LLM checks (per task, two-stage review — Superpowers).** Stage 1: does the diff satisfy the task's
requirement, and only that? Stage 2: is the code quality acceptable — naming, duplication, error
handling, consistency with surrounding conventions? Both by a reviewer subagent that did not write the
code.

**Exit criteria.** All tasks checked off; every task's verification observed; per-task reviews passed or
their findings folded into follow-up tasks.

---

### 3.9 `verify`

**Purpose.** Produce evidence that the change is done. Not an opinion — an artifact.

**Inputs.** The whole working tree, the spec, the claim store, `derived/`.

**Outputs.** `changes/NNNN/verification.json` plus a rendered summary. Generated, never authored.

```json
{
  "change": "0004-refund-support",
  "commit": "f7e8d9a",
  "generated_at": "2026-09-10T13:22:41Z",
  "gates": {
    "build":            {"status": "pass", "cmd": "pnpm build", "exit": 0},
    "typecheck":        {"status": "pass", "cmd": "pnpm typecheck", "exit": 0},
    "lint":             {"status": "pass", "cmd": "pnpm lint", "exit": 0},
    "tests":            {"status": "pass", "cmd": "pnpm test", "passed": 412, "failed": 0, "skipped": 3},
    "arch_rules":       {"status": "pass", "cmd": "depcruise --config .forge/rules/deps.cjs", "exit": 0},
    "contract_diff":    {"status": "pass", "tool": "oasdiff", "breaking": 0, "non_breaking": 2},
    "requirement_cover":{"status": "pass", "requirements": 5, "discharged": 5, "undischarged": []},
    "claim_evidence":   {"status": "pass", "enforced_claims": 19, "failing": []},
    "drift":            {"status": "pass", "open": 0, "waived": 0},
    "debt":             {"status": "pass", "open": 0, "waived": 1},
    "derived_fresh":    {"status": "pass", "commits_behind": 0}
  },
  "verdict": "pass"
}
```

**Definition of done.** `verdict: pass` requires **all** of:

1. build, typecheck, lint, full test suite green — with fresh output, captured here, not remembered;
2. every `REQ-*` in this change discharged by ≥1 passing test carrying its `@covers` tag;
3. every `enforced` claim in the touch set still proved by its evidence (rules pass, contract diff within
   severity, invariant tests pass);
4. `impact.md`'s claim-touch account complete;
5. `DRIFT.md` has no open unwaived entry touching this change's claims;
6. `DEBT.md` has no open unwaived entry introduced by this change — stubs, `TODO`s added by the change,
   skipped tests, unrun verifications (GSD's `broken-windows`, adopted);
7. `derived/` regenerates to a no-op at this commit;
8. no skipped test that was passing before this change.

**Tests passing is item 1 of 8.** That is the concrete answer to the brief's requirement that the harness
must not declare success merely because tests pass.

**Waivers.** Any of 5/6 may be waived with `--reason` and an expiry; the waiver appears in
`verification.json` and in `forge status`. Waivers 1–4 and 7 are not waivable.

**Human gate.** None — this phase is mechanical. Its *output* feeds G5.

**LLM checks.** A final whole-change review against the spec (the third review stage): does the sum of
the tasks actually deliver the requirements, and did anything drift across task boundaries?

**Exit criteria.** `verdict: pass`, or an explicit recorded waiver.

---

### 3.10 `sync`

**Purpose.** Move what this change established into permanent knowledge, deterministically.

**Inputs.** `verification.json` (must be `pass`), the spec deltas, `impact.md`, the working tree.

**Outputs.** Updated permanent capability specs; updated/created/retired claims; advanced anchor SHAs;
regenerated `derived/`; appended `DRIFT.md` entries for anything newly detected.

**Operations, in order, refusing on first failure** (detail in
[SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) §9.3):

1. fold spec deltas into the permanent specs (deterministic ADDED/MODIFIED/REMOVED/RENAMED merge, with
   pre-write validation of the rebuilt spec);
2. verify every claim edit in the diff has its `impact.md` entry and, where required, its ADR;
3. re-anchor every touched claim's `@sha` to the merge commit — **the only way "verified as of" advances**;
4. regenerate `derived/` and `trace.json`;
5. re-run `forge drift` and append new findings as open;
6. refuse if any refusal condition in §9.3 holds.

**Human gate — G5 (all tracks that produce artifacts).** The user approves the knowledge delta, shown as
a literal diff of the claim store plus the folded spec, alongside a ledger line per claim
(`retain / rewrite / new / retire`, with the reason). Not a summary — the actual text. Rationale: this is
the one write that outlives the change, and OpenHands' confirm-before-save protocol plus BMAD's ledger
are the two best-argued policies in the corpus. One interaction; high leverage.

**Deterministic checks (`sync:pre`).** `verification.json` is `pass` and its commit matches HEAD; the
store passes all §7 validations after the fold; the always-loaded line budget still holds.

**LLM checks.** For each proposed new claim: does it satisfy the admission criterion — could a competent
engineer read this off the compliant code? If yes, it is derived and must not be stored.

**Exit criteria.** Store valid; G5 recorded; anchors advanced.

---

### 3.11 `converge`

**Purpose.** Close the change and leave the repository in a state where the next change starts clean.

**Inputs.** A synced change.

**Outputs.** `changes/archive/YYYY-MM-DD-<slug>/` containing every artifact including
`verification.json` and the trajectories. Branch merged or PR opened. `forge status` clean.

**Deterministic checks (`converge:post`).** All tasks checked off; archive move is complete and the
active directory is gone; the archive is byte-identical to what was verified; `DRIFT.md` open entries all
have verdicts or waivers; `forge check` passes on the whole repository at the merge commit.

**LLM checks.** None. Convergence is bookkeeping.

**Exit criteria.** Archived; repository green; open items all either resolved or explicitly carried with
a recorded reason.

---

## 4. Human gates: the complete list

Exactly six. Everything else is the agent's call. This list is the harness's answer to "the harness
should NOT ask unnecessary questions": the way to earn the right to run unattended for an hour is to be
precise about the handful of moments where being wrong is expensive and irreversible.

| Gate | When | What is shown | Why it cannot be automated |
|---|---|---|---|
| **G1 — Intent & track** | Always, start of every request | One paragraph: restated intent, chosen track, what is unknown | Product intent is not in the repository. Track choice sets every downstream obligation |
| **G2 — Spec** | Track C; track B when a new capability appears | The delta requirements and scenarios | The spec is the contract; a wrong requirement wastes the whole lifecycle |
| **G3 — Design & ADR** | Track C | Decisions with alternatives, risks, and any ADR | Last cheap moment to change direction; an ADR is a commitment a human should make |
| **G4 — High-risk operation** | Whenever detected, any track, immediately | The exact operation and its blast radius | Destructive migration, data deletion, credential/permission change, dependency with a new licence class, anything touching auth. Irreversible or security-relevant |
| **G5 — Knowledge delta** | Any change that produces artifacts | Literal diff of the claim store + folded spec + a per-claim ledger line | This write outlives the change. Unreviewed knowledge writes are how stores become noise |
| **G6 — Drift verdict** | Whenever drift is detected on a load-bearing claim | The stale claim, the fingerprint diff, the proposed verdict and reasoning | arXiv:2604.03447: the model is systematically weakest here and its confidence is uninformative |

**Progressive autonomy.** `.forge/config.yaml` carries an `autonomy` level per gate, and the level is
*earned per project*, not per user preference:

```yaml
autonomy:
  G1: always            # never automatable
  G2: always            # never automatable
  G3: always            # relax to `track-c-only` after 20 changes with no G3 reversal
  G4: always            # never automatable
  G5: always            # relax to `claims-changed-only` (skip when only specs folded)
  G6: always            # never automatable
  per_task_review: auto # LLM review, no human
```

Only G3 and G5 may ever relax, and relaxation is a recorded config change with a reason, not a drift in
habit. G1, G2, G4 and G6 are permanently manual — the first two because intent is not in the repository,
the last two because the cost of being wrong is unbounded and the model's judgement is measurably weak.

---

## 5. The `bootstrap` workflow

For an existing repository with no harness. This is where honesty matters most: an LLM reading an
unfamiliar codebase produces confident, plausible, partly wrong claims, and plausible-but-wrong knowledge
is worse than none.

### 5.1 What is realistically automatable

| Step | Automatable? | How |
|---|---|---|
| Scan repository, file inventory, LOC, languages | **100%** | git + globs |
| Detect stack and pinned versions | **100%** | lockfiles, manifests |
| Detect entry points | **~90%** | manifest `bin`/`main`/`scripts`, framework conventions |
| Detect modules / packages | **~90%** | workspace manifests, directory conventions |
| Detect dependency graph and cycles | **100%** where an ecosystem tool exists | dependency-cruiser / tach / go list / cargo |
| Detect exported API surface | **~85%** | tree-sitter + export conventions; HTTP routes are framework-specific |
| Detect data model | **~70%** | ORM schema files, migration directories; raw SQL is harder |
| Detect tests, runner, coverage | **~95%** | config files + runner `--list` |
| Detect conventions (naming, formatting) | **~80%** | formatter/linter configs are authoritative; the rest is sampling |
| **Infer architecture (components, boundaries, responsibility)** | **~40%** | directory structure + dependency clusters suggest it; naming and responsibility are judgement |
| **Infer invariants** | **~25%** | validation code, assertions, and test names hint at them; whether a property is *required* or merely *current* is not in the code |
| **Infer architectural decisions and rationale** | **~5%** | genuinely not in the code. Git history and PR descriptions occasionally help; mostly this must be interviewed or left blank |
| **Infer pitfalls** | **0%** initially | earned from observed failures over time, not from a scan |

**This is the honest table the brief asked for.** Everything above the bold rows is derivation and should
never become a stored claim. Everything in the bold rows is candidate generation with a low ceiling, and
the last two are essentially un-automatable. A bootstrap that emits 200 confident claims about
architecture and invariants is producing exactly the noise the harness exists to prevent.

### 5.2 The three passes

**Pass 1 — Derive (no LLM, no claims).**
`forge bootstrap derive` produces `derived/` in full and prints a factual summary. Deterministic,
re-runnable, and it is the entire "detect stack / modules / dependencies / APIs / tests" half of the
brief's bootstrap sketch. Nothing here is knowledge; nothing here needs review.

**Pass 2 — Propose candidates (LLM, fan-out, capped).**
Parallel subagents, one per topic (components, domain, invariants, interfaces, data, workflows,
strategy, constraints), each reading `derived/` plus the code in its area and writing
`docs/system/candidates/<topic>.md` directly — never returning content to the orchestrator (GSD's
fan-out rationale). Every candidate carries `status: proposed`, `confidence`, anchors, and the
**evidence it was inferred from**. Hard caps, per topic and total (default: 40 total candidates), and
each agent must also produce a `## Uncertain` section naming what it could not determine — which is the
most valuable part of its output.

Rules for candidate generation, enforced by `forge check candidates`:

- Anchors required. A candidate with no anchor is discarded.
- The admission criterion applies: if the prose is a restatement of the anchored code, it is discarded by
  the derivable-claim linter (§7.3 of SYSTEM_KNOWLEDGE.md).
- **No invented rationale.** A candidate may not contain a "because" that is not evidenced. Missing
  rationale is written as `rationale: unknown`, which becomes an interview question.
- Invariants must name the code that enforces them or the test that proves them; an invariant with
  neither is downgraded to a question.

**Pass 3 — Ratify (human, interview-shaped, small).**
`forge bootstrap review` walks candidates **highest-value first** — pitfalls and concepts before
components — and for each asks one of: ratify / edit / reject / defer. Interleaved with the `Uncertain`
questions, in batches of at most eight (BMAD's rule), and **never asking anything a scan could answer**.

The default posture is **reject**. Baseline completeness is not the goal; baseline *trustworthiness* is.
A baseline of 12 ratified claims plus a complete `derived/` tier is a good outcome. A baseline of 40
half-checked claims is a liability that will be discovered six months later when one of them is wrong.

### 5.3 Establishing the baseline

`forge bootstrap seal` writes:

- `docs/system/OVERVIEW.md` — one page, human-written or human-approved, always loaded;
- the ratified claims in their kind files, anchors stamped with the current SHA, `reviewed` = today;
- `docs/system/decisions/ADR-0001-adopt-forge.md` — records the baseline itself: what was ratified, what
  was deliberately left un-ratified, and the claim cap in force. This makes the *absence* of knowledge
  explicit rather than ambiguous;
- unratified candidates left in place, readable but not citable;
- `.forge/config.yaml` with the detected tool commands (build, test, lint, typecheck, dep-rule tool).

**Explicit non-goal of bootstrap:** producing a complete description of the system. The first change that
touches an area will produce better knowledge about that area than any scan, because the change has a
reason, a test, and a human who cared. Bootstrap's job is to make the first change *possible*, not to
front-load a documentation project.

---

## 6. Other workflows

Same phase machinery, different required node sets. Each is a `.forge/schema/<name>.yaml`, not new code.

| Workflow | Track | DAG | Notes |
|---|---|---|---|
| **bugfix** | B (C if a claim is implicated) | understand → **reproduce** → investigate → tasks → implement → verify → sync → converge | `reproduce` is a required artifact: a failing test that demonstrates the bug, committed before any fix. No root cause, no fix — the strongest methodological signal in the corpus (Superpowers `systematic-debugging` + mini-SWE-agent's workflow agree). If the bug reveals a violated invariant, the fix updates `INV-`'s evidence rather than just the code |
| **refactor** | B or C | understand → investigate → impact → tasks → implement → verify → sync → converge | `skip_spec: true` is the normal case (behaviour must not change), recorded with a reason. Verification additionally requires: no test file semantically modified, and the pre-existing suite green. `impact` still runs — refactors are the highest-risk source of silent architectural drift |
| **architecture-change** | C, always | understand → investigate → **ADR** → impact → design → analyze → tasks → implement → verify → sync → converge | The ADR comes *before* impact, because the decision is the thing being made. Requires updating the `ARC-` claim and its rule file in the same change; `verify` refuses if the rule was weakened without the ADR saying so |
| **knowledge-only** | B | understand → **claims** → verify → sync → converge | For adding a pitfall, a concept, or an ADR with no code change. `verify` runs only store validation. This exists so that recording knowledge is never blocked on having a code change to attach it to |
| **drift-resolution** | B or C | understand → investigate → verdict → (tasks → implement → verify) → sync | Entry point is `forge drift resolve`. V1 continues into implementation; V2/V3/V4 may end at sync |

---

## 7. Context management across phases

The DAG carries the context contract. Each artifact node declares what its phase may read, so context is
scoped by the data model rather than by discipline.

```yaml
- id: design
  generates: design.md
  requires: [spec, impact]
  reads:
    - changes/${change}/spec/**
    - changes/${change}/impact.md
    - docs/system/architecture.md
    - docs/system/components.md
    - claims: "${impact.claims_touched}"     # resolved to specific claim bodies
  instruction: |
    ...
```

`forge instructions design --change NNNN --json` returns the resolved file list and the instruction, so
a phase (or a subagent running it) loads exactly that and nothing else — OpenSpec's `contextFiles`
mechanism, extended with claim-level resolution.

| Phase | Context strategy |
|---|---|
| understand | Minimal: OVERVIEW + claim *index* (IDs and titles only). Never claim bodies |
| investigate | **Fresh subagent.** Reads widely, writes its own file, returns a summary. The main session never sees the raw reading |
| spec | Spec deltas + permanent specs for the named capabilities only |
| impact | Claim *metadata* (anchors, globs) + `deps.json`. Not claim bodies — the touch set is computed from metadata |
| design | Spec + impact + the specific claim bodies in the touch set |
| analyze | All change artifacts, loaded once, findings only out. Read-only |
| tasks | Spec + design + impact |
| implement | **Fresh subagent per task.** One task, its interfaces, its claims, its file scope. Nothing else |
| verify | No model context at all for the deterministic part; the final review subagent gets the diff and the spec |
| sync | The knowledge diff only |

**Budgets** (mini-SWE-agent's mechanism, enforced in code): per phase and per task —
`step_limit`, `wall_time_limit_seconds`, `cost_limit`, `max_consecutive_failures`. Exceeding a budget
ends the phase with a recorded reason and a persisted trajectory, never with a silent continuation.

**Always-loaded budget:** `OVERVIEW.md` + mandatory claim files ≤ 400 lines (configurable). Over budget
is an error whose only legal fixes are cutting a claim or moving it behind a trigger. The budget is never
raised — that rule is itself in [CONSTITUTION.md](CONSTITUTION.md).
