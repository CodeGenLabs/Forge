# CONSTITUTION.md — forge

**Status:** draft for ratification. Version 0.1.0. Not yet ratified.

This is the governing document of the harness. It binds two things:

- **the harness's own development** — what we may build and what we may not;
- **the harness's behaviour** — what it requires of any project that adopts it.

Where a principle applies to only one of those, it says so.

## How this document differs from the constitutions in the corpus

Spec Kit's `constitution-template.md` is a list of principles with a governance footer, and its
`/analyze` command treats violations as automatically CRITICAL — but nothing computes whether a principle
was violated. A principle whose violation cannot be detected is a preference.

So every principle here carries four fields:

| Field | Meaning |
|---|---|
| **Rule** | The normative statement. MUST / MUST NOT / SHOULD |
| **Why** | The evidence or reasoning. Cited where it comes from research |
| **Mechanism** | What detects a violation: a kernel check, a gate, review, or `none (aspirational)` |
| **Waiver** | How it may be bypassed, and what that costs |

A principle with `Mechanism: none` is explicitly labelled aspirational. Being honest about which
principles are enforced is more useful than pretending all of them are.

---

## I. Deterministic before probabilistic

**Rule.** Any check that *can* be a deterministic script MUST be one. A language model MUST NOT be the
sole authority for any gate. Moving a check from LLM judgement to a script — by introducing an ID
convention, a field, or an anchor — is always an improvement and MUST be preferred over improving the
prompt.

**Why.** Prompt-only enforcement has to escalate to compulsion to hold the line (Superpowers'
`<EXTREMELY-IMPORTANT>`), and even then it is negotiable. Spec Kit's `/analyze` asks a model to build an
ID inventory by keyword inference and then compute "deterministic" coverage percentages — a task a
five-line grep does perfectly. BMAD's own linter states the division correctly: "LLMs miscount IDs and
miss literal placeholders; a grep does not."

**Mechanism.** `forge gate` exit codes are the only blocking authority. A skill that blocks progress must
cite a kernel check. Reviewed at every skill change.

**Waiver.** None. This is the principle the rest depend on.

---

## II. Investigate before modifying; reproduce before fixing

**Rule.** No implementation action before the relevant existing behaviour has been read and stated. No
bug fix before a committed failing test reproduces the bug. Root cause before remedy — a symptom fix is a
failure, not a partial success.

**Why.** Independent convergence: Superpowers' `systematic-debugging` ("NO FIXES WITHOUT ROOT CAUSE
INVESTIGATION FIRST") and mini-SWE-agent's default workflow ("Create a script to reproduce the issue"
before "Edit the source code") arrive at the same rule from opposite directions — a methodology library
and a benchmark-optimised loop. That is the strongest methodological signal in the corpus.

**Mechanism.** The `bugfix` DAG requires a `reproduce` artifact before `tasks`. Gate at `implement:pre`.
For features, `investigate` precedes `spec` in the DAG.

**Waiver.** Track A probes skip investigation depth, not investigation. A bugfix may not waive
`reproduce`; if the bug cannot be reproduced, that fact is the finding and the change stops there.

---

## III. Specification before implementation, sized to the change

**Rule.** Every change that alters observable behaviour MUST carry a spec delta with at least one
testable scenario per requirement. A change with no behavioural delta MUST declare `skip_spec: true`
with a reason. What scales with the size of the change is the *artifact*, never the *approval*.

**Why.** OpenSpec rejects zero-delta changes unless the bypass is explicit and recorded — the right
pattern, because it makes the exception visible instead of either unenforced or unbypassable. The
"spec-driven development is too heavy" criticism is correct for a one-line fix and wrong for a
subsystem, which is why the router (Superpowers' spike/bounded/architectural) exists.

**Mechanism.** `spec:post` gate: grammar, ≥1 scenario per requirement, zero `[NEEDS CLARIFICATION]`,
zero-delta rejection unless `skip_spec` with a reason.

**Waiver.** `skip_spec: true` + reason, recorded in `changes/NNNN/.forge.yaml`. Inventing a requirement to
satisfy the validator is a violation of this principle, not compliance with it.

---

## IV. Store judgements; derive facts

**Rule.** A fact MUST NOT be stored in system knowledge if a competent engineer could recover it from
compliant code. Directory layouts, stack versions, export lists, dependency graphs and test inventories
are derived, never authored. What is stored is what the code cannot say: responsibility, intent,
constraint, vocabulary, prohibition, and reason.

**Why.** BMAD's admission criterion, verbatim: *"calls a future builder can't read off compliant code."*
Every project in the corpus that stores facts (GSD's `STACK.md`, `STRUCTURE.md`; Spec Kit's per-feature
`research.md`) rots there first, because facts are exactly what the next commit can contradict.

**Mechanism.** `forge check` anti-noise linters: derivable-claim smell, directory-listing smell,
stack-fact smell (SYSTEM_KNOWLEDGE.md §7.3). Warnings with an explicit acknowledgement path, plus review
at G5.

**Waiver.** `# forge:not-derivable <reason>` on the claim, which is recorded and reviewable.

---

## V. Every claim is anchored, labelled, and evidenced

**Rule.** Every stored claim MUST carry a stable ID, a `truth-source`, and at least one anchor into the
code — except `constraint` claims (which originate outside the repository) and `concept` claims (which
have no single home). A claim marked `enforced` MUST name an artifact that mechanically fails when the
claim is violated, and that artifact MUST exist and pass.

**Why.** An unanchored claim can never be checked and will rot silently; it is a comment in a file nobody
diffs. Anchors give deterministic, format-insensitive staleness detection (Fiberplane's mechanism).
Truth-source labels turn contradiction handling into a lookup instead of a debate. Named evidence is what
separates "we believe this" from "this cannot break without something going red".

**Mechanism.** `forge check --scope store`: anchor presence, field validity, evidence resolution,
`enforced`⇒evidence-passes. Blocking at `sync:pre` and in the pre-commit hook.

**Waiver.** A claim may be `asserted` rather than `enforced` — that is not a waiver, it is an honest
state, and `forge status` reports the ratio.

---

## VI. Documentation is never silently reconciled to code

**Rule.** The harness MUST NOT contain any operation that rewrites system knowledge to match the
implementation. Detected drift MUST be classified and MUST require a recorded verdict: the code is wrong
(V1), the claim was never true (V2), the decision changed (V3, requires an ADR), or the claim was
under-specified (V4). An LLM may propose the verdict. Only a human may record one.

**Why.** This is the brief's central requirement and it is directly supported by measurement: LLMs detect
documentation faults at 67–94% but lose 21–43 percentage points when only the implementation changed
(arXiv:2604.03447) — the exact case drift resolution faces — and their confidence "provides little
separation between correct and incorrect judgments". GSD's `drift_action: auto-remap` is the behaviour
this principle exists to forbid: it silently rewrites the map so the code is always right, which destroys
the decision.

**Mechanism.** No such command exists in the kernel (ARCHITECTURE.md §2.2). `DRIFT.md` entries block
`verify` until they carry a verdict or an expiring waiver. Gate G6 is permanently manual.

**Waiver.** `forge drift waive --reason --until`, recorded and expiring. Never silent, never permanent.

---

## VII. Architecture changes require explicit reasoning

**Rule.** Changing an `architecture`-kind claim, breaking a public interface, or altering an invariant
MUST be accompanied by an ADR that supersedes the prior decision. An accepted ADR MUST NOT be edited; it
is superseded. An ADR MUST name at least one claim it justifies, and every architecture claim MUST name
the ADR it came from.

**Why.** OpenSpec keeps rationale in per-change `design.md`, which is then archived, so the reason a live
decision exists ends up buried in `changes/archive/2026-01-06-.../design.md`. Rationale is the one thing
that is never recoverable from the code, so it is the one thing that must be permanent.

**Mechanism.** `impact.md` `Superseded` entries require an existing ADR; `design:post` and `sync:pre`
gates verify the bidirectional `since:` / `supersedes:` links; `forge sync` refuses a claim edit that
requires an ADR and lacks one.

**Waiver.** Verdict V2 (the claim was never true) permits a claim correction without an ADR, because
nothing was decided — something was mis-recorded. It requires a recorded evidence note instead.

---

## VIII. Tests are evidence, and evidence is fresh or absent

**Rule.** A completion claim MUST be accompanied by verification output produced in the same run. Every
requirement MUST be discharged by at least one passing test that declares it (`@covers`). A test that was
never observed to fail is not evidence. "Tests pass" is one of eight conditions for done, not the
definition of done.

**Why.** Superpowers needed a whole skill for this ("NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION
EVIDENCE"), which tells you how strong the pull in the other direction is. Spec Kit's task template makes
tests OPTIONAL while its spec template demands independent tests per story — the traceability chain
breaks exactly there. GSD needed `broken-windows` to stop `done` being declared over a pile of stubs and
skipped tests.

**Mechanism.** `verify` produces `verification.json` from fresh command output; `requirement_cover` and
`claim_evidence` gates; the red-then-green transition recorded in each task's trajectory; `DEBT.md` open
entries block `done`.

**Waiver.** `DEBT.md` and `DRIFT.md` conditions are waivable with a reason and an expiry. Build,
typecheck, lint, tests, requirement coverage and derived freshness are not.

---

## IX. Knowledge is deleted only on named grounds

**Rule.** A claim may be retired or deleted only on one of four grounds: (1) stale or incorrect, with
named evidence; (2) mechanically enforced by a check that fails the specific violation it names;
(3) harmful or contradictory, losing a reconciliation with a live claim; (4) the human approved this
specific deletion, asked as a line item. Brevity is not grounds. Nothing failing lately is not grounds.
"The agent could derive it" is not grounds. **"It is discoverable somewhere in the repository" is never,
alone, grounds.**

**Why.** Adopted from BMAD's `project-context`, which is the most carefully argued policy in the corpus,
and whose own justification is the point: that last reasoning "is the reasoning that empties good files".
Bloat is the obvious failure; a tidy-minded agent gutting earned knowledge is the subtler and worse one,
because a working rule erases its own evidence.

**Mechanism.** `forge retire <ID> --ground N --evidence TEXT` records the ground; ground 4 requires the
human; `forge check` rejects a retirement with no ground. Retired claims stay in the file, excluded from
checks and budgets.

**Waiver.** None. The grounds *are* the waiver mechanism.

---

## X. Every line of always-loaded context is paid for in every session

**Rule.** The always-loaded set (`OVERVIEW.md` plus the mandatory claim files) MUST stay within its line
budget. Over budget is resolved by cutting a claim or moving it behind an observable trigger. **The
budget is never raised.** A pointer out of the always-loaded set MUST name a trigger the agent can
observe — a path, a file type, a named phase — never one it must judge ("when the task is complex") or
track about itself ("before your first edit").

**Why.** Chroma's context-rot study found degradation at every input-length increment across 18 frontier
models, well before the window limit. BMAD reached the same conclusion independently: "Every line is paid
in every session, and instruction-following degrades as the loaded set grows." And: "An index the agent
must choose to fetch gets skipped; one already in context does not."

**Mechanism.** `forge check` budget check, blocking. `budgets.always_loaded_lines` in config; raising it
requires amending this document.

**Waiver.** None. Amending the budget is a constitutional amendment (§Governance), which is the friction
we want.

---

## XI. Few gates, and each one earns its place

**Rule.** Human gates are enumerated, short, and justified in one sentence each: intent & track, spec,
design & ADR, high-risk operation, knowledge delta, drift verdict. The harness MUST NOT ask the human
anything a repository scan could answer. Asking the human to confirm a path-checked fact is a defect, not
diligence. Within a running plan, ambiguities are decided and recorded, not queued.

**Why.** Superpowers is right that a running plan should not wait on a human ("Rulings, not stalls"), and
right that some gates are unconditional. The synthesis is *few* gates rather than *zero* or *many*. BMAD's
rule is the sharp edge: "Never ask what a scan could answer." A harness that asks constantly gets its
gates clicked through, which is indistinguishable from having none.

**Mechanism.** The gate list in WORKFLOW.md §4 is closed. Adding one is a constitutional amendment.
`autonomy` config may relax only G3 and G5; G1, G2, G4 and G6 are permanently manual.

**Waiver.** Per-project `autonomy` relaxation for G3/G5, recorded in config with a reason.

---

## XII. Bounded runs, persisted trajectories

**Rule.** Every phase and every task runs under limits enforced in code: steps, wall-clock, cost,
consecutive failures. Exceeding a limit ends the run with a recorded reason. The trajectory is written on
every step, not at the end.

**Why.** mini-SWE-agent enforces exactly this in ~200 lines and it is the cheapest reliability mechanism
in the corpus. It converts "the agent ran away for two hours" from a supervision problem into a bounded
failure with a readable log.

**Mechanism.** `budgets.phase` in config; the orchestrating skill passes limits to each subagent; per-task
trajectories under `changes/NNNN/trajectories/`.

**Waiver.** Per-invocation override with an explicit flag, recorded in the trajectory.

---

## XIII. No unrelated modifications

**Rule.** A change touches only what its tasks declare. Opportunistic fixes, drive-by reformatting, and
unrelated refactors MUST NOT ride along. A defect noticed in passing goes to `DEBT.md` or becomes its own
change.

**Why.** Unrelated edits destroy reviewability, which is the only real control on agent output, and they
corrupt the claim-touch set: an unrelated file in the diff pulls unrelated claims into the accounting and
teaches everyone to write "unaffected" without thinking.

**Mechanism.** `implement:task:post` gate: the diff touches only files declared by the task. Blocking.

**Waiver.** Amend the task, which is free and takes one line. That is the intended path.

---

## XIV. No unnecessary abstraction; the harness has a size budget

**Rule.** The harness MUST stay within the growth budgets in ARCHITECTURE.md §8: 9 skills (ceiling 12),
~20 kernel commands (25), 12 gates (16), 5 workflow schemas (7), ~3,000 kernel LOC, 250 lines per skill.
At a ceiling, something is merged or deleted before anything is added. A gate that has never fired is
deleted at the next review.

**Why.** The clearest empirical lesson in the corpus: these frameworks grow faster than the projects they
serve. GSD reached 44 capabilities, ~90 workflows and four coexisting representations of the same system.
BMAD reached 29 skills and 2.4 MB with five personas and a builder for making more. Neither started
there. Numbers in a document that requires an amendment to change are the only defence that has ever
worked.

**Mechanism.** `forge status` reports each budget. A release checklist verifies them. `Mechanism: review`
for LOC and skill length.

**Waiver.** Constitutional amendment with a recorded reason. Not a judgement call in the moment.

---

## XV. Prefer a check over a prose rule

**Rule.** Before writing a rule as prose — in this document, a claim, or a skill — ask whether a hook,
linter, formatter, type, or CI check enforces it better. If one does, build the check; the prose becomes
the fallback only if the check is declined. A prose rule that a check later enforces is retired under
ground 2.

**Why.** BMAD's rule, and the mechanism behind Principle I. Also the practical route by which the store
shrinks over time instead of growing: knowledge that becomes mechanised stops needing to be remembered.

**Mechanism.** Review at G5 and at every skill change. `Mechanism: review` — honestly aspirational, and
labelled as such.

**Waiver.** N/A.

---

## XVI. Report faithfully

**Rule.** State what was run and what it returned. If a check was skipped, say so. If a step was waived,
name the waiver. Do not describe intended behaviour as observed behaviour, do not report a partial run as
complete, and do not soften a failing verdict. A `verdict: pass` with a waiver is reported as
`pass (1 waiver)`, never as `pass`.

**Why.** Every other principle here depends on the reports being true. An agent that reports optimistically
converts a harness full of gates into theatre, and the failure is invisible precisely because everything
looks green.

**Mechanism.** `verification.json` is generated from captured command output, never authored; waivers
appear in it and in `forge status`. Beyond that: review.

**Waiver.** None.

---

## Governance

**Precedence.** This document outranks skills, templates and per-project configuration. Where a
`.forge/config.yaml` value conflicts with a principle, the principle wins and `forge check` reports the
config as invalid. Where a claim conflicts with a principle, the principle wins and the claim is a
finding.

**Precedence within a project.** For questions about the *system being built*, this document does not
compete with the claim store: authority is per-fact (SYSTEM_KNOWLEDGE.md §3.1). This document governs
*how work is done*, not *what is true about the system*.

**Amendment.** An amendment is a `knowledge-only` change carrying: the diff, the reason, the evidence,
and a **sync impact report** naming every skill, template, gate, schema and budget that was re-checked
for alignment — with the check result for each. (Spec Kit's `SYNC IMPACT REPORT` block, adopted.)
Semantic versioning: MAJOR removes or reverses a principle, MINOR adds one or materially expands one,
PATCH clarifies wording without changing obligations.

**Ratification.** Version 0.1.0 is a draft. It is ratified when the MVP in [MVP.md](MVP.md) exists and
every principle's `Mechanism` field has been checked against the implementation — including the ones that
turn out to be `none (aspirational)`, which must then be either mechanised or explicitly accepted as
aspirational.

**Review cadence.** Every 10 changes, or on any amendment: are the budgets holding? has any gate never
fired? has any aspirational principle become mechanisable? has any claim in the store become mechanically
enforced and therefore retirable under ground 2?

**Self-application.** The harness is developed under its own rules from the first change after the MVP
lands. Anything that is too painful to apply to this repository will be too painful to apply to a real
one, and that pain is the most useful signal available.

**Version**: 0.1.0 · **Ratified**: — (draft) · **Last amended**: 2026-09-10
