# RESEARCH.md — Personal Software Engineering Harness

**Status:** research phase output. No implementation.
**Date of research:** 2026-09-10.
**Method:** all six named repositories (plus one successor repository) were shallow-cloned and read as
source, not as documentation. Where behaviour could not be established from prose, the actual scripts,
schemas, linters and TypeScript/Python modules were read. External claims are cited to primary sources
(papers, tool repos, vendor docs). Search-engine summaries were used only to *find* primary sources.

**Reading conventions used throughout this document**

| Marker | Meaning |
|---|---|
| **FACT** | Verified by reading the repository at the stated commit, or quoted from a primary source. Reproducible. |
| **INTERPRETATION** | My reading of what the fact means. Could be wrong. |
| **RECOMMENDATION** | A design position for our harness. Opinionated by intent. |
| **UNKNOWN** | Named gap; listed again in `OPEN_QUESTIONS.md`. |

---

## 0. Repositories inspected, with pinned commits

| Project | Repo | Commit inspected | Commit date |
|---|---|---|---|
| Superpowers | `obra/superpowers` | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` (v6.3.0) | 2026-08-12 |
| Spec Kit | `github/spec-kit` | `e4842a03c830155e4c53315e4b8e32ef118d3f6e` | 2026-09-10 |
| OpenSpec | `Fission-AI/OpenSpec` | `9d4e5974e5c0d9a09b9c6c1e1eb0975e80ec4461` | 2026-09-09 |
| BMAD Method | `bmad-code-org/BMAD-METHOD` | `abe4eb1bce919c9d22cd18b3519353d5824c4b75` (6.13.0-next) | 2026-09-05 |
| SWE-agent | `SWE-agent/SWE-agent` | `3ea751c087f32b16e039a2233dd6eefecef325d5` | 2026-07-16 |
| mini-SWE-agent | `SWE-agent/mini-swe-agent` | `04d809ceab9df28f9adaed044884180159172930` | 2026-09-03 |
| GSD (archived) | `gsd-build/get-shit-done` | `bdcaab2c752d9a33a1a1ca9acf3a3c81fb991815` | 2026-05-31 |
| GSD Core (active) | `open-gsd/gsd-core` | `bcd99696d32cc919f82d9edefb1ce8ef68a05afc` | 2026-09-10 |

**FACT.** `gsd-build/get-shit-done` is archived. Its `README.md` says: "This repository is no longer the
active home for GSD development. The project now continues as **GSD Core** in the Open GSD repository:
`https://github.com/open-gsd/gsd-core`". Any research that reads only the repository named in the brief
is reading a May-2026 snapshot. Both were read.

---

## 1. The headline finding

**FACT.** Of the six projects, exactly one ships a deterministic, non-LLM check that compares the
committed code against a stored description of the system: GSD's codebase-drift gate
(`gsd-core/src/drift.cts`, 431 lines). Its detection surface is:

- a newly added file whose directory prefix does not appear anywhere in `.planning/codebase/STRUCTURE.md`
  (`new_dir`);
- a newly added barrel export matching `^(packages|apps)/[^/]+/src/index\.(ts|tsx|js|mjs|cjs)$`;
- a newly added migration matching one of seven hardcoded migration-directory regexes;
- a newly added route module under `routes/` or `api/`.

Matching against `STRUCTURE.md` is `structureMd.includes(prefix)`. The source file says so explicitly:
"Matching is deliberately substring-based — STRUCTURE.md is free-form markdown, not a structured
manifest."

**FACT.** Everything else that the six projects call consistency analysis, verification, coherence
checking or drift detection is a prompt. Spec Kit's `/speckit.analyze`
(`templates/commands/analyze.md`) is 100% instructions to the model — its only script,
`scripts/bash/check-prerequisites.sh`, resolves the feature directory and tests `[[ -f "$TASKS" ]]`.
OpenSpec's `openspec-verify-change` skill instructs the model to "search codebase for keywords related
to the requirement" and "assess if implementation likely exists".

**INTERPRETATION.** The reason is not laziness. It is that free-form Markdown is not checkable, and
every one of these projects chose free-form Markdown as its knowledge format. The moment you write
`Payment Service → PostgreSQL` as prose in `architecture.md`, the only thing that can compare it to the
code is a language model. GSD got a deterministic gate precisely by giving up on semantics and checking
something structural instead (does this directory appear anywhere in the text).

**RECOMMENDATION.** The central design decision of our harness is *not* which lifecycle to adopt. It is
**making a small number of system-knowledge claims machine-addressable and machine-checkable, and
accepting that the rest is prose that can only go stale, never be verified.** Everything else in this
document follows from that.

---

## 2. Evidence that LLM-only drift detection is the wrong primitive

**FACT.** Ulfat, Sabit & Hossain, *Measuring LLM Trust Allocation Across Conflicting Software Artifacts*,
arXiv:2604.03447 (submitted 2026-04-03, revised 2026-07-21). The study builds paired clean/perturbed
Java method bundles (Javadoc, signature, implementation, test prefix), injects known faults into
documentation, implementation, or both, and collects 22,339 valid responses from seven LLMs over 456
bundles. From the abstract, verbatim:

> "models exhibit a consistent source-origin asymmetry: they detect documentation faults at 67-94% and
> explicit documentation-implementation contradictions at 50-91%, but detection falls by 21-43 percentage
> points when only the implementation changes while documentation remains intact. Models also struggle to
> deprioritize faulty implementations, and confidence provides little separation between correct and
> incorrect judgments for six of seven models."

**INTERPRETATION.** This is directly fatal to the naive version of the brief's Section 3. The scenario in
the brief — `architecture.md` says PostgreSQL, the implementation now uses Redis — is *exactly* the
"only the implementation changed" case, which is the case where models are 21–43 points worse. And
"confidence provides little separation between correct and incorrect judgments" means you cannot even
use the model's own confidence to decide when to escalate to a human.

**FACT.** A second relevant paper: Macedo, *From Prompt to Process: a Process Taxonomy and Comparative
Assessment of Frameworks Supporting AI Software Development Agents*, arXiv:2606.04967, compares OpenSpec,
GitHub Spec-Kit, BMAD Method, Spec-Kitty, SpecFlow, GSD, ChatDev and SWE-agent. Its reported gaps
include "limited mechanisms for maintaining architectural knowledge across development phases",
"insufficient traceability between specifications and generated artifacts" and "inadequate handling of
specification drift when requirements evolve."

**FACT.** Díaz, Gayoso, Cimminio & Pérez, *Spec-Driven Development for Agentic Software Engineering:
Harnessing Human–Agent Teamwork*, arXiv:2609.00252v1 (2026-08-31, Universidad Politécnica de Madrid),
proposes an eight-mechanism "harness": H1 context engineering, H2 persistent shared knowledge, H3
executable specifications, H4 N-version parallel agents, H5 normative specifications, H6 structured
consultation, H7 evidence-backed acceptance, H8 graduated autonomy. It defines specifications as needing
to be *executable*, *explicit*, *traceable* and *evidence-dischargeable*, and lists as an open problem
"maintaining consistency between specifications, system knowledge, and code at scale". The authors
describe the work as "a first step toward an academic–industrial consensus, rather than as a validated
theory."

**INTERPRETATION.** The academic framing independently arrives at roughly the same shape the brief
sketches, and independently flags the same unsolved part. Nobody has solved knowledge synchronisation.
We should not plan to solve it either — we should plan to *contain* it.

**RECOMMENDATION.** Adopt three hard rules from this evidence:

1. **Staleness detection must be deterministic; correctness judgement may be LLM-assisted but must be
   human-gated.** Never ask a model "is this doc still true?" as a gate.
2. **Never allow automatic reconciliation of documentation to code.** The paper's asymmetry means the
   model will preferentially "fix" the document, which is the wrong half in the exact case we care about.
3. **Prefer claims that a tool can falsify** (a dependency rule, an OpenAPI diff, a named test) over
   claims that only a model can assess.

---

## 3. Superpowers

### 3.1 Facts

**FACT.** 14 skills, 3,377 lines of `SKILL.md` total. Full list with line counts:
`using-superpowers` (63), `executing-plans` (64), `requesting-code-review` (95),
`verification-before-completion` (120), `dispatching-parallel-agents` (167), `using-git-worktrees` (167),
`writing-plans` (171), `receiving-code-review` (205), `finishing-a-development-branch` (225),
`brainstorming` (250), `systematic-debugging` (283), `test-driven-development` (320),
`subagent-driven-development` (568), `writing-skills` (679).

**FACT.** Enforcement mechanism is a `SessionStart` hook (`hooks/hooks.json`, matcher
`startup|clear|compact`) that shells `hooks/session-start`, which reads
`skills/using-superpowers/SKILL.md` and injects it as `additionalContext` wrapped in
`<EXTREMELY_IMPORTANT>`. That skill contains:

> "If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST
> invoke the skill. IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT."

**FACT.** There is no state file, no artifact registry, no CLI, no validator. State is: the plan markdown
in `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`, the design doc in `docs/superpowers/specs/`, git
worktrees, and `- [ ]` checkboxes inside the plan.

**FACT.** `brainstorming` implements a three-way scale router — **spike** / **bounded** /
**architectural** — with an explicit one-way ratchet: "hidden complexity discovered mid-task upgrades
the path — stop, say so, and step up. Nothing downgrades mid-task." Only the *architectural* path
produces a written spec file and hands off to `writing-plans`.

**FACT.** `brainstorming` carries an unconditional approval gate: `<HARD-GATE>` "Do NOT invoke any
implementation skill, write any code, scaffold any project, or take any implementation action until you
have told your human partner what you intend and they have approved it." Plus an explicit anti-pattern
table ("This is too simple to need a design" → "Simple means a short design, not no design").

**FACT.** `writing-plans` mandates a plan header containing `Goal`, `Architecture`, `Tech Stack`, `Spec`
(path to the doc the plan implements) and `Global Constraints`; per-task blocks contain `Files:`
(Create/Modify with line ranges/Test), `Interfaces: Consumes/Produces` with exact signatures, and 5-step
TDD checkboxes with literal code in each step. It bans placeholders explicitly: "TBD", "add appropriate
error handling", "Similar to Task N", "Write tests for the above (without actual test code)".

**FACT.** `subagent-driven-development` (the largest workflow skill) dispatches a fresh implementer
subagent per task, then a two-stage review (spec compliance, then code quality), then a whole-branch
review. It forbids checking in with the human between tasks: "Rulings, not stalls. A running plan does
not wait on a human."

**FACT.** `verification-before-completion` states the rule as "NO COMPLETION CLAIMS WITHOUT FRESH
VERIFICATION EVIDENCE … If you haven't run the verification command in this message, you cannot claim it
passes."

**FACT.** `writing-skills` applies TDD to prompt authoring: write pressure scenarios, watch a subagent
fail without the skill (RED), write the skill, watch it comply (GREEN), then close loopholes. There is a
`tests/` directory with per-harness test suites (`tests/claude-code`, `tests/codex`, `tests/hooks`,
`tests/explicit-skill-requests/prompts`, …).

**FACT.** Known limitation, stated in the README: some host platforms lack post-compaction hooks, so the
bootstrap instruction can be lost in long sessions.

### 3.2 Interpretation

**INTERPRETATION.** Superpowers is a *behavioural* harness, not a *structural* one. It changes what the
agent does by making instructions loud and unconditional, and by isolating context in subagents. It has
no notion of the system being built. There is no architecture document, no component model, no
invariants, no ADRs, no cross-artifact validation. It is a discipline library.

**INTERPRETATION.** Its most transferable engineering idea is not any single skill; it is
**skills-as-tested-artifacts**. A prompt with a red/green test suite is an engineering artifact. A prompt
without one is folklore. This is the only project in the set that treats its own prompts as testable.

**INTERPRETATION.** The second most transferable idea is the **scale router with a one-way ratchet**.
This is the cheapest available answer to the "spec-driven development is too heavy for a one-line fix"
criticism, and it is one skill, not a framework.

**INTERPRETATION.** The `<EXTREMELY-IMPORTANT>` / "you do not have a choice" style is a symptom, not a
design. It exists because prompt instructions are not enforceable. Every escalation in that register is
evidence that the mechanism is at the wrong layer. Where we can move a rule into a script that returns a
non-zero exit code, we should, and then the shouting is unnecessary.

### 3.3 Borrow / reject

**Borrow:** the scale router + one-way ratchet; the plan format (`Files` / `Interfaces
Consumes-Produces` / no-placeholders); evidence-before-claims as a hard rule; fresh-subagent-per-task for
context isolation; two-stage review (spec compliance separate from code quality); TDD-for-prompts with a
real test directory; the "announce which skill you are using" convention (cheap observability).

**Reject:** unconditional all-caps compulsion as the primary enforcement layer; "never stop to ask the
human mid-plan" (we want *few* gates, not *zero* — see §16 of the brief and `WORKFLOW.md`); the absence
of any system model; the brainstorming→plan flow's assumption that a design doc plus plan is sufficient
durable knowledge (it is per-change knowledge and it rots the moment the change lands).

**Modify:** `verification-before-completion` should become a deterministic command (`forge verify`) that
emits an evidence artifact, not a skill that reminds the model to be honest.

---

## 4. GitHub Spec Kit

### 4.1 Facts

**FACT.** Command set (from `templates/commands/*.md`): `constitution`, `specify`, `clarify`, `plan`,
`tasks`, `analyze`, `checklist`, `implement`, `converge`, `taskstoissues`. Layout created by
`specify init`: `.specify/` (config, `memory/constitution.md`, `templates/overrides/`,
`presets/templates/`, `extensions/templates/`) and `specs/NNN-xxx/`.

**FACT.** Per-feature artifacts (from `templates/plan-template.md`): `plan.md`, `research.md` (phase 0),
`data-model.md` (phase 1), `quickstart.md` (phase 1), `contracts/` (phase 1), `tasks.md` (phase 2).
`spec.md` comes from `/speckit.specify`.

**FACT.** `spec-template.md` structure: prioritised user stories (P1/P2/P3) each with **Why this
priority**, **Independent Test** and Given/When/Then acceptance scenarios; Edge Cases; Functional
Requirements as `FR-001 … FR-00n` with `System MUST …`; Key Entities; Success Criteria as `SC-001 …`
("measurable" and "technology-agnostic"); Assumptions. Unresolved items are marked inline as
`[NEEDS CLARIFICATION: …]`.

**FACT.** The constitution lives at `.specify/memory/constitution.md` and is declared non-negotiable
inside `analyze.md`: "Constitution conflicts are automatically CRITICAL and require adjustment of the
spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle."

**FACT.** The repository's own constitution (`.specify/memory/constitution.md`) opens with a
`SYNC IMPACT REPORT` comment block that records the version bump, the bump rationale, the principles
defined, the sections added, and a checklist of *which downstream templates were reviewed for alignment*
with ✅ marks and line references.

**FACT.** `/speckit.analyze` detection passes: duplication, ambiguity (vague adjectives "fast, scalable,
secure, intuitive, robust" lacking measurable criteria; unresolved placeholders `TODO/TKTK/???`),
underspecification, constitution alignment, coverage gaps (requirements with zero tasks, tasks with no
requirement), inconsistency (terminology drift, entities in plan absent from spec, task ordering
contradictions, conflicting requirements). Severity ladder CRITICAL/HIGH/MEDIUM/LOW. Output is a report;
the command is `STRICTLY READ-ONLY` and must "NEVER modify files". Findings capped at 50. It also asks
"Would you like me to suggest concrete remediation edits for the top N issues?" and must not apply them.

**FACT.** `/speckit.analyze` builds a "Requirements inventory" keyed on `FR-###`/`SC-###` and a "Task
coverage mapping" by "inference by keyword / explicit reference patterns like IDs or key phrases".

**FACT.** The only executable code in the workflow is path resolution and file-existence checking:
`check-prerequisites.sh` (`--require-spec`, `--require-tasks`, `--paths-only`, `--template NAME`),
`common.sh` (finds repo root by walking up for `.specify/`, resolves the feature via `SPECIFY_FEATURE` or
`.specify/feature.json`), `create-new-feature.sh`, `setup-plan.sh`, `setup-tasks.sh`, and
`resolve-template.sh` (a template override stack: project overrides → presets → extensions → built-in).

**FACT.** `tasks-template.md` says: "**Tests**: The examples below include test tasks. Tests are
OPTIONAL - only include them if explicitly requested in the feature specification."

**FACT.** There is an extension hook system: `.specify/extensions.yml` with `hooks.before_analyze` /
`hooks.after_analyze` keys, each hook having `enabled`, `optional`, `condition`, `command`, `prompt`.
Crucially, the command file instructs the *model* to read the YAML and emit an `EXECUTE_COMMAND:` line —
hook dispatch is prompt-mediated, not engine-mediated.

**FACT.** There is no system-knowledge layer. The `extensions/agent-context/` extension has
`update-agent-context.sh`, which maintains agent instruction files; there is no architecture, component,
invariant, ADR or data-model store that outlives a feature folder.

### 4.2 Interpretation

**INTERPRETATION.** Spec Kit's real contribution is **artifact vocabulary and template discipline**, not
mechanism. `FR-###`, `SC-###`, `[NEEDS CLARIFICATION]`, independently testable prioritised stories, and
a project constitution that outranks the spec — those are good, cheap, and mostly language-agnostic.

**INTERPRETATION.** `/speckit.analyze` is the most complete *specification* of a consistency engine in
the whole corpus and simultaneously the clearest demonstration of why prompts are the wrong
implementation for it. Look at what it asks the model to do: build a requirements inventory, map tasks to
requirements by keyword inference, compute a coverage percentage, and produce "deterministic results:
rerunning without changes should produce consistent IDs and counts". Every one of those is a five-line
script over labelled IDs. Asking a model to do arithmetic over IDs it extracted by keyword inference is
strictly worse than grepping for the IDs.

**INTERPRETATION.** The `[NEEDS CLARIFICATION: …]` marker is under-appreciated. It is an *in-band,
greppable uncertainty marker*. A script can count them and refuse to advance a phase. That is a real gate
built out of a string convention — the cheapest kind of enforceability there is.

**INTERPRETATION.** "Tests are OPTIONAL" is, for our purposes, a defect. Spec Kit's own spec template
demands `Independent Test` per story and measurable `SC-###`, then its task template makes tests
optional. Nothing then discharges the acceptance scenarios. This is the traceability break that
arXiv:2606.04967 reports for the whole family.

**INTERPRETATION.** The `SYNC IMPACT REPORT` block is a small gem: when a governing document changes,
the change carries a machine-readable-ish list of the downstream artifacts that were re-checked. That is
the seed of a proper impact record.

### 4.3 Borrow / reject

**Borrow:** stable labelled requirement IDs (`FR-###` / `SC-###` style); `[NEEDS CLARIFICATION]` as a
greppable blocker; prioritised independently-testable stories; constitution outranking specs; the
template override stack (a project can override built-in templates without forking); the
`SYNC IMPACT REPORT` idea, generalised into a per-change impact artifact; the read-only nature of
analysis (it reports, it never edits).

**Reject:** the numbered `specs/NNN-feature/` folder as the unit of work (it never converges into
durable knowledge — see §6); prompt-mediated hook dispatch; a six-file-per-feature planning bundle
(`research.md`, `quickstart.md`, `data-model.md`, `contracts/` per feature) — most of that is either
system knowledge that should be permanent or noise that should not exist; optional tests; implementing
`analyze` as a prompt.

**Modify:** `analyze` splits into `forge check` (deterministic: ID coverage, orphan tasks, placeholder
scan, anchor staleness, mechanised constitution rules) plus a much smaller LLM review that only handles
genuinely semantic questions (is this requirement testable? do these two requirements conflict in
meaning?).

---

## 5. BMAD Method

### 5.1 Facts

**FACT.** 29 skills, 257 files, **2.4 MB** of skill content. Skill list: `bmad`,
`bmad-advanced-elicitation`, `bmad-agent-analyst`, `bmad-agent-architect`, `bmad-agent-dev`,
`bmad-agent-pm`, `bmad-agent-ux-designer`, `bmad-architecture`, `bmad-brainstorming`, `bmad-build`,
`bmad-build-auto`, `bmad-code-review`, `bmad-correct-course`, `bmad-create-epics-and-stories`,
`bmad-customize`, `bmad-deep-recon`, `bmad-forge-idea`, `bmad-party-mode`, `bmad-prd`, `bmad-prfaq`,
`bmad-product-brief`, `bmad-project-context`, `bmad-qa-generate-e2e-tests`, `bmad-retrospective`,
`bmad-review`, `bmad-spec`, `bmad-sprint-planning`, `bmad-ux`, `bmad-walkthrough`.

**FACT.** Agent personas exist as *skills* (`bmad-agent-analyst`, `-architect`, `-dev`, `-pm`,
`-ux-designer`), not as separate processes. Discovery is by `module-manifest.toml` next to each skill,
carrying `module`, `version`, `update_source`, and a free-text `knowledge` field pointing at a routing
document (all inspected manifests point to "`references/help.md` in the `bmad` skill").

**FACT.** Configuration is resolved by scripts, not prompts:
`_bmad/scripts/resolve_customization.py --skill … --key workflow` and
`_bmad/scripts/resolve_config.py --project-root …` (merges `_bmad/config.toml` with `_bmad/custom/`
overrides). Skills declare `activation_steps_prepend` / `activation_steps_append` / `persistent_facts`
(with `file:` entries loaded) in `customize.toml`.

**FACT — the most valuable single artifact in the corpus.** `bmad-architecture` ships
`assets/spine-template.md`, an "Architecture Spine" with YAML frontmatter
(`type: architecture-spine`, `purpose`, `altitude: initiative|feature|epic`, `paradigm`, `scope`,
`status`, `binds: []`, `sources: []`, `companions: []`) and these sections: Design Paradigm; Inherited
Invariants; **Invariants & Rules**; Consistency Conventions; Stack; Structural Seed; Capability →
Architecture Map; Deferred.

Each architectural decision block has a fixed shape:

```
### AD-1 — {decision}
- **Binds:** {capability / unit ids / fr/nfr's, areas, or `all`}
- **Prevents:** {the divergence this stops}
- **Rule:** {the constraint downstream must follow}
```

The template's own admission criterion for the Invariants section is, verbatim: *"The durable heart:
calls a future builder can't read off compliant code."* Its Stack section is annotated: *"SEED — verified
current at authoring; the code owns this once it exists."* Its Structural Seed section: *"The code owns
the detail — this is scaffold, not a mirror to maintain."* AD ids are "stable ascending id (never
reused/renumbered)". Inherited invariants are "read-only, never renumbered, not re-derived. A local
decision that contradicts one is a conflict to surface, not an override."

**FACT.** That template has a **deterministic linter**: `bmad-architecture/scripts/lint_spine.py`
(270 lines, with tests). Its docstring states the split explicitly: *"LLMs miscount IDs and miss literal
placeholders; a grep does not. This linter owns the checks a script does better than a prompt, and leaves
the semantic half (is each Rule actually enforceable? does the boundary make sense?) to the rubric
walker."* Checks: `placeholder` (literal TBD/TODO/FIXME/XXX, "similar to AD-n", unfilled
`{template-token}`), `ad_id` (duplicate or non-monotonic AD numbers), `ad_fields` (an AD block missing
Binds/Prevents/Rule), `version_pin` (a `## Stack` row naming something with no version). Code fences are
blanked before scanning so mermaid and source trees do not produce false positives while line numbers
still line up. Exit code is always 0; findings travel as JSON and the caller decides.

**FACT.** `bmad-spec` uses a derivation model: `.memlog.md` is "canonical — an append-only,
chronological record of every decision, constraint, capability (with its stable `CAP-N`), assumption,
open question … never edited or reordered", and `SPEC.md` plus companions are "**derived on each run**
from the memlog". The rationale given: *"Deriving the contract from a living log instead of editing the
contract in place is what lets the steps around the spec (PRD, UX, architecture, epics) run in any order
and feed the same spec without merge drift: the log only accumulates, the artifact is re-rendered."*
`bmad-spec` is declared the single writer; external hand-edits to `SPEC.md` are "unsupported and
overwritten on the next derive". Writes go through `_bmad/scripts/memlog.py` (atomic).

**FACT — the best knowledge-curation policy in the corpus.** `bmad-project-context` maintains a managed
block inside `AGENTS.md` delimited by `<!-- bmad:context -->` / `<!-- /bmad:context -->` with a
provenance line: `<!-- Verified 2026-08-08 against a1b2c3d. Managed by bmad-project-context; edits
inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->`

Refresh procedure: "Read the provenance line, re-verify every path and every caveat, and run
`git log --diff-filter=DR --name-only` since the recorded SHA against every line — update or remove lines
whose evidence is gone."

Deletion requires one of exactly four grounds:

> 1. **Stale or incorrect** — the referent is gone, or the instruction was never true; the evidence is named.
> 2. **Mechanically enforced** — a hook, linter, formatter, or CI check already fails the violation named by the instruction. A tool that only covers the same files or topic does not enforce the instruction.
> 3. **Harmful or contradictory** — it points agents at the wrong thing, or it contradicts another live instruction and loses the reconciliation.
> 4. **The user approved this deletion** — asked as a line item, never implied by approving a replacement block.

And, verbatim: *"Brevity is not grounds, nothing failing lately is not grounds, 'the agent could derive
it' is not grounds, and **'it is discoverable somewhere in the repository' is never, alone, grounds** —
that is the reasoning that empties good files."*

Other rules from the same skill: every write is preceded by a **ledger** with one entry per existing
instruction settling as `retain | rewrite | relocate | automate | delete` with evidence and risk; "For
each candidate, ask first whether a hook, lint rule, or CI check enforces it better than prose; if so
propose the check, and the line becomes the fallback if they decline"; "Never ask what a scan could
answer. Asking the user to confirm a path-checked claim … is a defect"; a size budget where "Over budget
means cut the weakest lines or move them behind a trigger — never raise the budget"; and a retrieval
rule: "An index the agent must choose to fetch gets skipped; one already in context does not."

**FACT.** The router skill `bmad` is explicitly read-only for help requests and refuses to guess:
"If something could not be read, say so and do not guess."

### 5.2 Interpretation

**INTERPRETATION.** BMAD is two projects in one repository. There is a large, ceremonious, role-based
planning suite (PRD, PRFAQ, product brief, sprint planning, party mode, five agent personas), and there
is a small kernel of genuinely excellent knowledge engineering (`spine-template.md` + `lint_spine.py`,
`.memlog.md` derivation, `project-context`'s ledger and four grounds). The second part is the reason to
read BMAD.

**INTERPRETATION — the single most important idea I found.** *"Calls a future builder can't read off
compliant code"* is the missing admission criterion for system knowledge. It answers the brief's
question "what should actually be stored versus dynamically discovered" in one sentence, and it is
falsifiable: for any candidate line, ask "if I deleted this and handed a competent engineer the code,
would they recover it?" If yes, it is derived, not knowledge. This alone eliminates the vast majority of
AI-generated documentation noise, because AI-generated architecture docs are almost entirely
restatements of what the code already shows.

**INTERPRETATION.** The `Binds` / `Prevents` / `Rule` triple is the right *shape* for an architectural
claim, and it is nearly executable. `Rule` is the constraint; `Binds` is the scope; `Prevents` is the
falsification test. A rule with a `Binds` scope and an enforceable `Rule` is one step away from a
dependency-cruiser / ArchUnit / Tach rule. That step is the whole opportunity.

**INTERPRETATION.** The append-only memlog + derived artifact pattern solves a problem the brief does not
name but will hit immediately: **who owns the file**. If both the human and multiple skills edit
`architecture.md` in place, you get merge drift and no provenance. If decisions accumulate in an
append-only log and the document is re-rendered, provenance is free and ordering conflicts vanish.
The cost is that the rendered document must never be hand-edited, which is a discipline problem, and it
doubles the artifact count.

**INTERPRETATION.** The four grounds for deletion are the correct answer to the brief's "how does the
system prevent documentation from becoming useless AI-generated noise?" — but note that they solve the
*opposite* failure too, and that is the subtler risk. An agent asked to "clean up the docs" will delete
true, load-bearing knowledge because it is not obviously used. "It is discoverable somewhere in the
repository is never, alone, grounds" is the guardrail against a tidy-minded model gutting the file.

**INTERPRETATION.** BMAD's cost is enormous. 2.4 MB of skills, a Python config resolver, a TOML manifest
per skill, five personas, and a builder for making more. For one developer this is a liability: every
line is paid in context or in indirection, and the surface that can rot is proportional to size. BMAD's
own `best-practices.md` says it better than I can: "Every line is paid in every session, and
instruction-following degrades as the loaded set grows."

**INTERPRETATION on the personas question.** BMAD's personas are skills in one agent, not separate
agents. The observable value of `bmad-agent-architect` versus a skill called `design` is a different
system prompt and a different checklist. There is no evidence in the repository that role-play improves
outcomes; the value is in the checklist. **Multiple agents earn their keep for context isolation and
parallelism, not for personality.**

### 5.3 Borrow / reject

**Borrow:** the admission criterion ("can't read off compliant code"); `AD-n` with Binds/Prevents/Rule
and stable never-renumbered ids; the deterministic doc linter and its explicit mechanical/semantic split;
inherited-invariants-are-read-only; `Stack`-is-a-seed / `code owns the detail` truth-source annotations;
the provenance line (`Verified <date> against <sha>`) plus `git log --diff-filter=DR` re-verification;
the four grounds for deletion and the ledger; "prefer a check over a prose rule"; the size budget with no
escape hatch; append-only decision log with derived rendering; altitude (initiative/feature/epic) as
scale adaptation; `Capability → Architecture Map` as a traceability table.

**Reject:** five agent personas; a skill-builder; PRD/PRFAQ/product-brief/sprint-planning/party-mode;
per-skill TOML manifests and a Python config-resolution layer; 2.4 MB of anything; free-text `knowledge`
pointers as a routing mechanism.

**Modify:** the spine becomes several small typed files rather than one document with eight sections,
because different sections have different truth sources and different update cadences, and mixing them in
one file makes "which parts are stale" unanswerable per-file. The linter becomes part of the kernel.

---

## 6. OpenSpec

### 6.1 Facts

**FACT.** Layout: `openspec/specs/<capability-path>/spec.md` (permanent), `openspec/changes/<name>/`
(in-flight), `openspec/changes/archive/YYYY-MM-DD-<name>/` (completed). Also present in this
repository's own instance: `openspec/config.yaml`, `openspec/initiatives/`, `openspec/explorations/`.

**FACT.** Per-change files: `proposal.md`, `specs/<capability-path>/spec.md` (delta), `design.md`,
`tasks.md`, plus `.openspec.yaml` carrying `schema: spec-driven` and `created: <date>` (and optionally
`skip_specs: true`).

**FACT — the best mechanism in the corpus.** The workflow is a **declared artifact DAG**, not a
hardcoded phase list. `schemas/spec-driven/schema.yaml`:

```yaml
name: spec-driven
version: 1
description: Default OpenSpec workflow - proposal → specs → design → tasks
artifacts:
  - id: proposal
    generates: proposal.md
    template: proposal.md
    instruction: |...|
    requires: []
  - id: specs
    generates: "specs/**/*.md"
    template: spec.md
    requires: [proposal]
  - id: design
    generates: design.md
    requires: [proposal]
  - id: tasks
    generates: tasks.md
    requires: [specs, design]
apply:
  requires: [tasks]
  tracks: tasks.md
  instruction: |...|
```

Each artifact carries `id`, `generates` (relative path or glob), `description`, `template`, a long
`instruction` (the prompt), and `requires` (dependency edges).

**FACT.** The DAG is validated deterministically in `src/core/artifact-graph/schema.ts`: Zod schema
parse, then `validateNoDuplicateIds`, `validateRequiresReferences`, `validateNoCycles` (DFS reporting the
full cycle path). `src/core/artifact-graph/types.ts` rejects absolute paths, `..` escapes and NUL bytes
in every path field.

**FACT.** Workflow state is **derived from the filesystem**, not stored.
`src/core/artifact-graph/state.ts`: `detectCompleted(graph, changeDir)` returns the set of artifact ids
whose `generates` path (or glob) exists. There is no state file to corrupt or desynchronise.

**FACT.** Spec format is enforced. From the schema's `specs` instruction: requirements are
`### Requirement: <name>`, scenarios are `#### Scenario: <name>` with WHEN/THEN bullets, "**CRITICAL**:
Scenarios MUST use exactly 4 hashtags (`####`). Using 3 hashtags or bullets will fail silently", "Every
requirement MUST have at least one scenario", "Use SHALL/MUST for normative requirements (avoid
should/may)".

**FACT.** Delta operations are a closed set of `##` headers: `ADDED Requirements`,
`MODIFIED Requirements` ("MUST include full updated content"), `REMOVED Requirements` ("MUST include
**Reason** and **Migration**"), `RENAMED Requirements` (FROM:/TO:). New capabilities must open with a
`## Purpose` of at least `MIN_PURPOSE_LENGTH` characters; `openspec validate --strict` reports it as too
brief otherwise. Deltas for existing capabilities must **not** carry `## Purpose`.

**FACT.** `openspec validate` is real code, not a prompt: `src/core/validation/validator.ts` +
`src/core/parsers/{markdown-parser, change-parser, requirement-blocks, requirement-text,
spec-structure, code-fence}.ts` + `src/core/schemas/{spec,change,base}.schema.ts` (Zod) +
`validation/{task-numbering, purpose-placeholder, constants}.ts`. Issues are typed
`{level: 'ERROR'|'WARNING'|'INFO', path, message, line?, column?}` with a summary count.
`findTaskNumberingIssues` detects ambiguous/duplicate task ids inside `## N.` groups.

**FACT.** A change with zero spec deltas is **rejected** by `openspec validate` unless `.openspec.yaml`
sets `skip_specs: true`, and the instruction adds: "Use `skip_specs: true` only when no spec-level
behavior changes (pure refactor, tooling, docs) … Do not invent a requirement just to satisfy
validation."

**FACT — the knowledge-sync mechanism.** `src/core/specs-apply.ts` + `src/core/archive.ts` perform a
**deterministic textual merge** of delta requirement blocks into the permanent capability specs at
archive time (`findSpecUpdates`, `buildUpdatedSpec`, `foldRequirementName`, `normalizeRequirementName`,
`extractRequirementsSection`, `findMissingCurrentScenarios`, `findMainSpecStructureIssues`), with path
containment assertions (`isLexicallyWithin`, `assertPathWithin`) and pre-write validation of the rebuilt
spec (`validateSpecContent`).

**FACT.** `openspec/config.yaml` carries a project-level `context:` free-text block and a per-artifact
`rules:` map:

```yaml
schema: spec-driven
context: |
  Tech stack: TypeScript, Node.js (>=20.19.0), ESM modules
  ...
rules:
  specs:
    - Include scenarios for Windows path handling when dealing with file paths
    - Prefer user-facing product behavior and observable outcomes over internal implementation mechanics
  tasks:
    - Add Windows CI verification as a task when changes involve file paths
  design:
    - Prefer Node.js path module over string manipulation for paths
```

**FACT.** Slash commands: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`, plus
workflows for `update`, `continue`, `ff`, `verify`, `sync-specs`, `bulk-archive`, `onboard`, `feedback`.
CLI: `openspec init|update|config|list|list --specs|show|status|instructions|validate|archive|doctor`.
`openspec instructions apply --change <name> --json` returns `contextFiles` (artifact id → concrete file
paths), which is how a skill learns what to read.

**FACT.** `openspec-verify-change` is a prompt. Its three dimensions are Completeness / Correctness /
Coherence, severities CRITICAL / WARNING / SUGGESTION. Completeness includes deterministic-ish checks
(parse `- [ ]` vs `- [x]`, count) but spec coverage is "search codebase for keywords related to the
requirement… assess if implementation likely exists".

### 6.2 Interpretation

**INTERPRETATION.** OpenSpec is the strongest *foundation* of the six, and the reason is architectural,
not stylistic: it separates **permanent capability specs** from **temporary change deltas**, and it
converges them with code, not with a prompt. Spec Kit's `specs/NNN-feature/` never converges — after
twenty features you have twenty folders describing twenty moments in history and nothing describing the
system. OpenSpec's `openspec/specs/` describes the system, and each change is a diff against it that
gets folded in and archived.

**INTERPRETATION.** The `schema.yaml` artifact DAG is the right way to make a lifecycle *enforceable
rather than suggested*, which is the brief's stated requirement. Note precisely why it works:

- the **order** is data (`requires`), so a script can compute what is blocked;
- the **state** is the filesystem (`generates` exists), so there is nothing to desynchronise;
- the **prompt** is attached to the node (`instruction`), so the model gets exactly the guidance for the
  step it is on and nothing else — this is context engineering as a side effect of the data model;
- the **template** is attached to the node, so output shape is predictable enough to validate.

That is four different benefits from one 40-line YAML file. Nothing else in the corpus is this efficient.

**INTERPRETATION.** The zero-delta rejection with an explicit `skip_specs: true` escape is the correct
pattern for every "you must document this" rule in a harness: *make the bypass explicit, named, and
recorded in the repository, rather than either unenforced or unbypassable.* This generalises directly to
ADR requirements and drift waivers.

**INTERPRETATION.** OpenSpec's weakness is that its permanent knowledge is only *behavioural*
requirements. There is nothing about components, boundaries, dependency direction, invariants that are
not user-observable, data model, deployment, or *why*. `design.md` holds decisions and rationale but it
is a per-change artifact that gets archived — so the rationale for a live architectural decision ends up
buried in `changes/archive/2026-01-06-.../design.md`. That is exactly the ADR problem, unsolved.

**INTERPRETATION.** The `config.yaml` `rules:` map keyed by artifact is a cheap, high-value mechanism. It
lets a project inject its own standing constraints into the generation of a specific artifact type
without editing any skill. It is also the place where our "constitution" can become operational rather
than aspirational.

### 6.3 Borrow / reject

**Borrow:** change-centric model; permanent specs vs change deltas vs archive; the `schema.yaml` artifact
DAG (id/generates/requires/template/instruction + `apply.tracks`); filesystem-derived state;
deterministic structural validation with typed ERROR/WARNING/INFO issues; the closed set of delta
operations with mandatory Reason/Migration on removal; requirement/scenario heading discipline;
`MODIFIED must include full updated content`; deterministic archive-time fold as the knowledge-sync
mechanism; zero-delta rejection with a named, recorded bypass; per-artifact `rules:` injection;
`instructions --json` returning the exact files a phase may read; path-containment assertions on every
generated path.

**Reject:** requirements as the *only* permanent knowledge; rationale living in archived per-change
design docs; `openspec-verify-change` as a prompt; the initiatives/explorations/workset/store layers
(scope creep beyond a single developer's needs); a Node/TypeScript CLI as the only implementation route
(irrelevant to the idea; relevant to our dependency budget).

**Modify:** extend the permanent layer from "capability specs" to "capability specs **plus** typed
system-knowledge claims **plus** ADRs", and make the archive fold apply to all three, driven by a
declared impact record rather than inferred.

---

## 7. SWE-agent and mini-SWE-agent

### 7.1 Facts

**FACT.** SWE-agent's stated research contribution is the **Agent-Computer Interface (ACI)** — the paper
is cited in the repository as "SWE-agent: Agent-Computer Interfaces Enable Automated Software
Engineering" (NeurIPS 2024). Tools are bundles under `tools/`: `windowed`, `windowed_edit_linting`,
`windowed_edit_replace`, `windowed_edit_rewrite`, `edit_anthropic`, `search`, `filemap`, `diff_state`,
`submit`, `review_on_submit_m`, `forfeit`, `registry`, `web_browser`, `image_tools`.

**FACT — a concrete guardrail worth copying.** `tools/windowed_edit_linting` runs `flake8` **before** the
edit, applies the edit, runs `flake8` **after**, diffs the error sets, and if new syntax errors appeared,
**reverts the edit** and returns `_LINT_ERROR_TEMPLATE`: "Your proposed edit has introduced new syntax
error(s). Please read this error message carefully and then retry editing the file."

**FACT.** `sweagent/agent/reviewer.py` implements a retry loop plus best-of-n selection
(`ReviewSubmission` carries the full trajectory across retries, model stats, and info).

**FACT.** mini-SWE-agent's whole agent is `src/minisweagent/agents/default.py`, ~200 lines. Its loop:
render `system_template` and `instance_template` into two messages, then `while True: step()`, where
`step()` = `execute_actions(query())`. `query()` calls the model; `execute_actions()` runs each parsed
action via `self.env.execute(action)` and appends the observation. Termination is
`messages[-1]['role'] == 'exit'`.

**FACT.** Hard budget limits are enforced in code, not prompted: `step_limit`, `cost_limit`
(default 3.0), `wall_time_limit_seconds`, `max_consecutive_format_errors` (default 3). Exceeding any
raises `LimitsExceeded` / `TimeExceeded` / `RepeatedFormatError`, which appends an `exit` message.
`save(self.config.output_path)` runs in a `finally` on **every** step, so the full trajectory is on disk
continuously.

**FACT.** Its interface is deliberately impoverished: `default.yaml` requires "exactly ONE bash code
block with ONE command (or commands connected with && or ||)", a THOUGHT section first, and notes
"Directory or environment variable changes are not persistent. Every action is executed in a new
subshell." Its recommended workflow, verbatim from `instance_template`: "1. Analyze the codebase by
finding and reading relevant files 2. Create a script to reproduce the issue 3. Edit the source code to
resolve the issue 4. Verify your fix works by running your script again 5. Test edge cases to ensure your
fix is robust 6. Submit your changes …". Completion is a magic echo:
`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.

**FACT.** README claims: "Just some 100 lines of python for the agent class"; "Scores >74% on the
SWE-bench verified benchmark"; "starts much faster than Claude Code"; "mini-swe-agent now powers Ramp
SWE-Bench". These are the project's own claims; I did not independently reproduce the benchmark.

### 7.2 Interpretation

**INTERPRETATION.** The pair is a controlled experiment in how much scaffolding an execution loop needs,
and the answer is "very little, if the environment is honest". mini's ~200 lines with `bash` only reaches
within a few points of the heavily-engineered version. That is a strong argument against building an
execution engine at all.

**INTERPRETATION.** What mini has that prompts cannot provide, and what we should therefore copy:
**budgets enforced in code, and a trajectory persisted on every step**. A step/cost/time cap converts
"the agent went off the rails for two hours" from a supervision problem into a bounded failure with a
readable log. This is the single cheapest reliability mechanism in the corpus.

**INTERPRETATION.** `windowed_edit_linting` is the template for the right kind of enforcement: the
guardrail lives *inside the tool*, is deterministic, and its failure message teaches the model what to do
next. Compare with Superpowers' approach to the same class of problem (an all-caps instruction not to
break things). The tool-level version cannot be rationalised away.

**INTERPRETATION.** Both projects are single-task, single-repo, benchmark-shaped: given an issue, produce
a patch. They have no specification, no architecture, no persistence between tasks, and no notion of
system knowledge. They belong strictly inside our `implement` and `debug` phases and nowhere else.

**INTERPRETATION.** mini's recommended workflow *is* a reproduce-first debugging discipline, and it
agrees with Superpowers' `systematic-debugging` ("NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST").
Two independent projects converging on "reproduce before you fix" is the strongest methodological signal
in the corpus.

### 7.3 Borrow / reject

**Borrow:** hard budgets in code (steps, cost, wall-time, consecutive format errors); trajectory
persisted every step; reproduce-before-fix; the observe→act loop with one action per step for the inner
implementation loop; guardrails implemented in tools with teaching error messages (pre/post lint diff →
revert); best-of-n with an explicit reviewer, for high-stakes tasks only.

**Reject:** building our own execution engine, environment abstraction, or model client — the host agent
(Claude Code and equivalents) already provides these; SWE-agent's 15 custom tool bundles; benchmark
plumbing.

**Modify:** the inner loop stays the host agent's; we contribute the *entry contract* (what the task is,
which files it may touch, which test must go green) and the *exit contract* (evidence).

---

## 8. GSD / GSD Core

### 8.1 Facts

**FACT.** Scale. The archived `get-shit-done` has ~90 workflow files and ~68 slash commands. `gsd-core`
has 44 capability packages under `capabilities/`.

**FACT — the closest existing analogue to the brief's System Knowledge layer.**
`get-shit-done/templates/codebase/` defines seven documents written to `.planning/codebase/`:
`STACK.md` (languages, runtime, package manager, frameworks, testing, build),
`STRUCTURE.md` (directory layout tree, directory purposes, key file locations, entry points),
`ARCHITECTURE.md` (pattern overview, conceptual layers with Purpose/Contains/Depends on/Used by, data
flow), `CONVENTIONS.md` (naming, formatting, style), `INTEGRATIONS.md` (external APIs, auth, data
storage, rate limits), `TESTING.md` (runner, assertion library, run commands, file organisation),
`CONCERNS.md` (tech debt with Issue/Why/Impact/Fix approach, known bugs with
Symptoms/Trigger/Workaround/Root cause, security considerations). Every template header carries
`**Analysis Date:** [YYYY-MM-DD]`.

**FACT.** They are produced by `map-codebase.md` (443 lines) which fans out parallel
`gsd-codebase-mapper` subagents, each writing its own document directly. Stated rationale: "Fresh context
per domain (no token contamination) / agents write documents directly (no context transfer back to
orchestrator) / orchestrator only summarizes what was created (minimal context usage)". It supports
`--paths p1,p2` incremental remap, validates path arguments against `..`, leading `/` and shell
metacharacters, and stamps `last_mapped_commit: <HEAD sha>` into each document's YAML frontmatter.

**FACT — the drift gates.** `capabilities/drift/capability.json` declares four gates:

| point | check | blocking | when |
|---|---|---|---|
| `execute:wave:post` | `verify.schema-drift` | **true** | `workflow.schema_drift_gate` |
| `execute:wave:post` | `verify.codebase-drift` | false | `workflow.schema_drift_gate` |
| `plan:pre` | `verify.codebase-drift` | false | `workflow.plan_drift_precheck` |
| `plan:pre` | `verify.context-drift` | false | `workflow.context_drift_precheck` |

All four carry `onError: skip`. Config: `workflow.drift_threshold` (default 3),
`workflow.drift_action` (`warn` | `auto-remap`, default `warn`), plus per-gate booleans and
`workflow.context_drift_action` (`warn` | `block`).

The schema gate is described as: "blocks verification if schema-relevant files changed during execution
but no database push command was executed" — its rationale being to "prevent false-positive verification
where build/types pass because TypeScript types come from config, not the live database"
(`capabilities/schema-gate`).

The **context-drift** gate is described as: "Compares each artifact's effective last-changed time (git
commit time, falling back to mtime for uncommitted edits) against CONTEXT.md's own — an artifact that
predates CONTEXT.md's newest decision was derived from a premise that has since changed."

**FACT.** `gsd-core/CONTEXT.md` opens with: "**Format**: this document is machine-greppable. Each
operational fact is a single-line predicate (`CLASS.subkey=value`). Agent briefs cite predicates by ID
verbatim (per `META.RULE.brief-must-cite-doc`) — never paraphrase from this file. New learnings go in as
predicates; chronological prose belongs in the session log at the bottom."

**FACT.** Gate points in use across all capabilities: `plan:pre` (14 gates), `execute:wave:post` (7),
`verify:post` (4), `plan:post` (4), `execute:post` (3), `ship:pre` (2), `verify:pre` (1), `ship:post`
(1), `execute:wave:pre` (1), `discuss:pre` (1), `discuss:post` (1).

**FACT.** Other relevant capabilities, quoting their own descriptions:

- `intel` — "Code-intelligence store … `gsd-tools intel` subcommands (query, status, update, diff,
  snapshot, patch-meta, validate, extract-exports, api-surface)".
  `docs/features/queryable-codebase-intelligence.md` specifies JSON files in `.planning/intel/`:
  `stack.json`, `api-map.json`, `dependency-graph.json`, `file-roles.json`, `arch-decisions.json`, with
  "`status` mode MUST report freshness (FRESH/STALE, stale threshold: 24 hours)".
- `graphify` — "Build, query, and inspect the project knowledge graph in `.planning/graphs/`", opt-in via
  `graphify.enabled`, subcommands `build|query|status|diff|snapshot`. Commit-based staleness added later:
  `built_at_commit`, `current_commit`, `commits_behind`, `commit_stale` (nullable), with validation that
  `built_at_commit` is 4–40 hex chars "before reaching `git` — a hostile `graph.json` cannot inject
  dashed options into argv".
- `gap-analysis` — "cross-references every REQ-ID and D-ID from REQUIREMENTS.md and CONTEXT.md against
  plan bodies. Emits a Source | Item | Status table. Does not block phase advancement."
- `broken-windows` — "Cross-phase defect register accumulating stubs, TODOs, skipped tests, unrun
  verifies, and unmet truths into .planning/WINDOWS.md. When enforcement is enabled, it blocks /gsd-ship
  while any window is open unless explicitly waived with a recorded reason."
- `nyquist` — "Validation coverage audit that maps executed work back to tests and manual-only evidence."
- `refactor-trigger` — measures complexity of touched code, proposes a scoped refactor when a function
  "crosses a configured threshold or jumps past its recorded anchor"; "Advisory by default — it never
  edits code and never blocks."
- `assumption-delta` — "triggers when a phase makes something plural, optional, or chosen that used to be
  singular, required, or derived. Surfaces one identity-model question … so a silent primary-key drift
  does not accumulate into a later user-facing bug. Non-blocking; fires only on a detected signal."
- `tdd` — "Injects TDD heuristics into the planner and enforces RED/GREEN gate compliance on type:tdd
  plans after execution."

**FACT.** `get-shit-done/get-shit-done/contexts/` contains exactly three context files: `dev.md`,
`research.md`, `review.md`.

### 8.2 Interpretation

**INTERPRETATION.** GSD is the most *mechanically* advanced of the six and the most over-built. Its
declarative gate model — a named lifecycle point, a check identified by a query string, a `blocking`
flag, a `when` config predicate, and `onError: skip` — is the correct architecture for making a lifecycle
enforceable, and it is about 100 lines of engine. Everything valuable in GSD's drift story is downstream
of that one abstraction.

**INTERPRETATION.** The three drift gates form a taxonomy that the brief does not have, and it is a
better taxonomy than "architectural drift":

1. **Structural drift** — the code grew a shape the map does not mention. Cheap, deterministic, high
   recall, low precision. Right answer: re-map, non-blocking.
2. **Process drift** — a class of change happened without its mandatory companion action (schema file
   edited, no migration push). Deterministic, high precision. Right answer: **block**.
3. **Premise drift** — a derived artifact is older than the decision it was derived from. Deterministic,
   cheap, and it catches the failure that matters most for agents: planning against stale analysis.

**INTERPRETATION — the most reusable single trick in GSD.** Premise drift by timestamp comparison
(`artifact.mtime < CONTEXT.md.newest_decision`) costs nothing and answers "is this analysis still
trustworthy?" without any semantics. Generalise it: **every derived artifact records what it was derived
from; staleness is a comparison, not a judgement.**

**INTERPRETATION.** `CONTEXT.md`'s "single-line predicate, cited by ID verbatim, never paraphrased" is
the format-level answer to noise. A predicate is short, addressable, greppable, and diffable; a paragraph
is none of those. The prohibition on paraphrase is what makes traceability survive: if briefs quote
`AUTH.session.ttl=30m` by id, a grep tells you every place that fact is load-bearing.

**INTERPRETATION.** `broken-windows` is a genuinely good idea badly named. A blocking register of
"things we knowingly left broken, each either fixed or explicitly waived with a reason" is how you stop
an agent from declaring done on a pile of `TODO`s and `it.skip`. This is the enforceable version of "the
harness must NOT declare success merely because tests pass".

**INTERPRETATION.** Where GSD goes wrong: 44 capabilities, ~90 workflows, a knowledge graph, an
intelligence store, a memory-palace MCP integration, and 14 gates at `plan:pre` alone. The `intel`
freshness rule ("stale threshold: 24 hours") is a time-based heuristic where a commit-based one was
available — and indeed `graphify` later added exactly that (`built_at_commit`, `commits_behind`), which
reads as an admission that the time-based version was wrong. **Two knowledge stores (`.planning/intel/`
JSON and `.planning/graphs/` graph) plus seven markdown maps plus `CONTEXT.md` predicates means four
representations of the same system, each with its own staleness story.** That is the failure mode our
harness must avoid by construction.

### 8.3 Borrow / reject

**Borrow:** the declarative gate model (point + check + `blocking` + `when` + `onError`); the three-way
drift taxonomy (structural / process / premise) and the correct blocking policy for each (warn / block /
warn-or-block); `last_mapped_commit` / `built_at_commit` provenance in frontmatter; commit-based rather
than time-based staleness; `commits_behind` as a legible signal; machine-greppable single-line predicates
cited by ID and never paraphrased; a blocking defect register with recorded waivers; requirement-ID
coverage cross-referencing (`gap-analysis`); parallel fan-out mappers writing their own files to avoid
context transfer; `--paths` incremental re-mapping with argument validation; never trusting stored values
that reach a shell (the `built_at_commit` hex validation).

**Reject:** 44 capabilities; a knowledge graph; a second JSON intelligence store; MCP memory integration;
14 gates at one lifecycle point; time-based freshness thresholds; auto-remap as a default (it silently
rewrites the map to match code — precisely the behaviour the brief forbids); ~90 workflow files.

**Modify:** collapse `intel` + `graphify` + the seven maps into **one** derived store with one provenance
rule; `auto-remap` becomes `propose-remap` and never writes without a human verdict when the drifted
claim is load-bearing.

---

## 9. Research beyond the six

Only projects that changed a design decision are listed.

### 9.1 Anchoring documentation to code — the closest thing to a solution

**FACT.** Fiberplane's `drift` documentation linter anchors doc files to code via frontmatter or inline
annotations:

```
---
drift:
  files:
    - src/auth/login.ts@a1b2c3d
    - src/auth/provider.ts#AuthConfig@a1b2c3d
---
```

An anchor is *path* (required) + `#Symbol` (optional, narrows to a declaration) + `@<git-sha>` (optional,
"which commit last addressed this anchor"). Staleness detection: get the baseline commit (from
provenance, else last spec-file modification), fetch the file/symbol at that baseline with `git show`,
and compare to current. For TypeScript, Python, Rust, Go, Zig and Java it "parses the code with
tree-sitter and hashes a normalized AST fingerprint (node kinds + token text, no whitespace or position
data)"; unsupported languages fall back to raw content comparison. Stated limitation: it "helps with
*detection*, not the review itself" — a user can re-link without updating prose.
Source: <https://fiberplane.com/blog/drift-documentation-linter/>

**INTERPRETATION.** This is the mechanism the brief is looking for and none of the six have. It gives
**deterministic, whitespace- and format-insensitive, symbol-scoped staleness detection** with per-claim
provenance, using tools we already have (git + tree-sitter). It does not tell you whether the prose is
*wrong* — nothing can — but it tells you exactly which prose is *unverified as of this commit*, which is
the actionable half.

**RECOMMENDATION.** Adopt `path#Symbol@sha` anchors with normalised-AST fingerprints as the primary
staleness primitive of our System Knowledge layer. This is the single most important import from outside
the six repositories.

### 9.2 Architecture conformance as executable rules

**FACT.** Mature, widely used, per-ecosystem tools enforce dependency-direction and module-boundary rules
as tests or CI checks: **ArchUnit** (Java; "check dependencies between packages and classes, layers and
slices, check for cyclic dependencies"; layered/onion-architecture rule library) with community ports
**ArchUnitTS** and **ArchUnitPython**; **dependency-cruiser** (JS/TS; rule-based `forbidden`/`allowed`
dependency rules); **Tach** (Python; "define boundaries and control dependencies between your Python
packages… each package can also define its public interface", Rust-implemented); **Deptrac** (PHP;
"define your architectural layers over classes and which rules should apply to them").
Sources: <https://www.archunit.org/>, <https://github.com/TNG/ArchUnit>,
<https://github.com/sverweij/dependency-cruiser>, <https://github.com/tach-org/tach>,
<https://github.com/deptrac/deptrac>, <https://github.com/LukasNiessen/ArchUnitTS>.

**FACT.** There is peer-reviewed work on the exact problem: *Detecting deviations in the code using
architecture view-based drift analysis*, Computer Standards & Interfaces, 2023,
doi:10.1016/j.csi.2023.103774.

**FACT.** **Structurizr DSL** provides architecture-as-code for the C4 model, with a DSL that can be
parsed and validated in CI. Source: <https://docs.structurizr.com/dsl>.

**INTERPRETATION.** For a *subset* of architectural claims — "the domain layer must not import the web
layer", "no cycles between packages", "only `src/repos/` may import the database client" — drift
detection is a solved, deterministic, ecosystem-native problem. Nobody in the six wires it up. The BMAD
spine's `Binds` + `Rule` fields are one small step from being compilable into exactly these rules.

**RECOMMENDATION.** Any architectural claim that *can* be expressed as a dependency rule **must** be, and
the harness stores the rule file path as that claim's evidence. Claims that cannot be mechanised are
allowed, but must be labelled `asserted` rather than `enforced`, and the harness reports the ratio. This
turns "architectural drift detection" from an AI problem into a linting problem for the part that matters
most, and makes the un-mechanised remainder visible instead of pretending it is covered.

### 9.3 Interface and data-model drift

**FACT.** **oasdiff** compares two OpenAPI documents, classifies every difference as breaking or
non-breaking, returns a non-zero exit code above a chosen severity as a merge gate, and supports OpenAPI
3.0/3.1/3.2. Source: <https://github.com/oasdiff/oasdiff>, <https://www.oasdiff.com/docs/breaking-changes>.
**Pact** provides consumer-driven contract testing. **Schemathesis** generates property-based tests from
an OpenAPI/GraphQL schema and reports response-schema violations. **Spectral** lints OpenAPI/AsyncAPI
documents against custom rulesets.

**INTERPRETATION.** "API changes without contract updates" — item 6 in the brief's list of analyse
checks — is fully deterministic if and only if the contract is generated from code (or the code is
generated from the contract). The check is `oasdiff` between the committed contract and the contract
regenerated at HEAD, with a severity gate. Same shape for the data model: diff the ORM/schema snapshot,
or require a migration file. GSD's blocking schema gate is the crude version of this, and it is blocking
for good reason.

### 9.4 Codebase context for agents: what is actually needed

**FACT.** **Aider's repo map** parses each file with tree-sitter to extract defined symbols, builds a
graph where files are nodes and symbol references are edges, and ranks with **personalized PageRank**
biased toward symbols in the current chat, serialising the top-ranked symbols into a compact map inside a
token budget (`--map-tokens`, default 1k). Source: <https://aider.chat/2023/10/22/repomap.html>.

**FACT.** Precise code navigation at scale uses **SCIP** (Sourcegraph's Protobuf successor to LSIF;
claimed "8x smaller, and can be processed 3x faster" than LSIF, and integrated with Meta's **Glean** in
~550 lines vs 1500 for LSIF). Source: <https://sourcegraph.com/blog/announcing-scip>.

**FACT.** OpenHands convention: `AGENTS.md` at the repository root for "short, repository-wide
conventions", `SKILL.md` for "focused knowledge needed only for some tasks",
`.openhands/microagents/repo.md` as a high-level always-loaded overview linking into
`.openhands/memory/` for details; and an update protocol where the agent "should always ask for user
confirmation first by listing the exact items they plan to save … and only save items the user approves."
Sources: <https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md>,
<https://docs.openhands.dev/overview/skills>.

**FACT.** AWS **Kiro** ships the same triad as Spec Kit under different names — `requirements.md`,
`design.md`, `tasks.md` — plus **steering files** (persistent project context read on every interaction)
and **hooks** (event-driven automations on file save / create / commit, e.g. "validate task completion
against your requirements.md after every commit").

**INTERPRETATION.** Three independent conclusions:

1. **Symbol-level structural context is cheap and effective, and we should not build it.** Aider,
   Sourcegraph, and the host agent's own search all solve it. Our harness should *discover* structure at
   query time (grep, tree-sitter, the host's tools) and store only what discovery cannot recover.
2. **The "ask before you save, list the exact items" protocol from OpenHands is the right default for
   knowledge writes.** It costs one interaction and prevents the slow accumulation of confident noise.
3. **Kiro's hooks confirm the gate model independently.** Two of the strongest commercial/OSS designs
   (Kiro hooks, GSD gates) reached the same place: event-triggered deterministic checks around the
   lifecycle, not more prompting inside it.

### 9.5 Context engineering evidence

**FACT.** Chroma's 2025 "context rot" study tested 18 frontier models and found quality degradation with
increasing input length at every increment tested, well before the context window limit. Mitigations now
standard in the literature: just-in-time retrieval (keep lightweight references, fetch content on
demand), compaction, structured note-taking, and sub-agent isolation.

**INTERPRETATION.** This is the empirical backing for GSD's phase isolation, Superpowers'
fresh-subagent-per-task, and OpenSpec's per-artifact `instruction`/`contextFiles`. It also argues against
a large always-loaded system-knowledge document: **a 3,000-line `architecture.md` loaded every session
actively degrades the agent.** BMAD's independently-derived "every line is paid in every session, and
instruction-following degrades as the loaded set grows" says the same thing.

**RECOMMENDATION.** Impose a **hard token budget on always-loaded knowledge** (target: ≤400 lines total
across the always-loaded set) and put everything else behind an observable trigger (a path, a file type,
a named phase). Budget overrun is resolved by cutting or relocating, never by raising the budget.

### 9.6 Change-impact analysis and test selection

**FACT.** **CodePlan** (Microsoft Research; ACM PACMSE, doi:10.1145/3643757; arXiv:2309.12499) frames
repository-level coding as planning: "a novel combination of an incremental dependency analysis, a change
may-impact analysis and an adaptive planning algorithm", synthesising a chain of edits where each step is
an LLM call on a code location with repository-derived context, propagating changes to dependent code.

**FACT.** Test impact analysis is available off the shelf: **OpenClover** (Java/Groovy, per-test coverage
mapping and change-aware selection), **pytest-impact** ("selects only the tests affected by a git diff,
with no coverage tracing or database needed"), Datadog Test Impact Analysis (commercial).

**INTERPRETATION.** CodePlan's neuro-symbolic shape is the right *idea* for our impact phase — compute a
candidate blast radius with static analysis, then let the model reason over it — but building incremental
dependency analysis is far beyond a personal harness. The tractable version is: run the ecosystem's
dependency/import tool over the changed files to get reverse dependencies, intersect with the components
named in System Knowledge, and hand the model that list as the *candidate* impact set to curate.

---

## 10. Consolidated answers to the brief's research questions

### 10.1 "How should an AI agent maintain accurate knowledge of an existing software system?"

**RECOMMENDATION.** By storing very little, labelling every stored thing with its truth source, anchoring
each stored thing to the code it describes, and re-verifying anchors mechanically rather than re-reading
prose.

Concretely, the five-part answer:

1. **Admission rule.** Store a fact only if a competent engineer could not recover it from compliant code
   (BMAD). This removes most of what AI-generated architecture docs contain.
2. **Truth-source label.** Every stored claim declares which artifact is authoritative for it: `code`,
   `tests`, `config`, `spec`, `decision`, or `derived`. Contradiction handling is then a lookup, not a
   debate.
3. **Anchors with provenance.** Every claim lists `path#Symbol@sha` anchors (Fiberplane). Staleness = the
   anchor's normalised AST fingerprint changed since `@sha`. Deterministic, cheap, no LLM.
4. **Mechanised evidence where possible.** A claim's rule compiles to a dependency rule, a contract diff,
   or a named test whenever it can (ArchUnit / dependency-cruiser / Tach / oasdiff / a test id). Claims
   that cannot be mechanised are marked `asserted` and counted.
5. **Human verdict on drift.** When an anchor goes stale, the harness never rewrites the claim. It opens
   a drift item with four permitted verdicts (code wrong / claim was never true / intentional change
   requiring an ADR / claim needs refinement) and requires one.

### 10.2 "What should actually be stored versus dynamically discovered?"

| Information | Store? | Truth source | Why |
|---|---|---|---|
| Directory layout, file inventory | **No** (derive) | code | `ls`/glob answers it; storing it guarantees drift |
| Tech stack + pinned versions | **No** (derive) | config | lockfiles are authoritative; a stored copy is a lie waiting to happen |
| Exported API surface | **No** (derive) | code | generated snapshot, diffable |
| Import/dependency graph | **No** (derive) | code | ecosystem tools |
| Test inventory, coverage | **No** (derive) | tests | test runner |
| Component boundaries and their *names* | **Yes** | decision | the code has directories; "these three directories are one component with this responsibility" is a human judgement |
| Allowed dependency direction | **Yes**, as a rule file | decision, enforced by tool | not recoverable from code that currently complies |
| Domain concepts and vocabulary | **Yes** | decision | naming intent is not in the code |
| Domain rules / invariants | **Yes**, with a discharging test | tests | code shows *an* implementation, not the *required* property |
| Why a design is the way it is | **Yes** (ADR) | decision | not in the code at all, ever |
| Rejected alternatives | **Yes** (ADR) | decision | absent from the code by definition |
| Constraints from outside the repo (compliance, SLAs, contracts) | **Yes** | decision | not in the repo |
| Known pitfalls an agent keeps falling into | **Yes** | observed evidence | earned knowledge; the highest value-per-line in the store |
| Deployment topology | **Yes** if not in IaC, else derive | config or decision | if there is Terraform, the Terraform is the truth |
| Testing strategy (what *must* be tested how) | **Yes** | decision | the current test suite is evidence of practice, not of policy |

**INTERPRETATION.** The pattern: **store judgements, derive facts.** Every project in the corpus stores
facts (GSD's `STACK.md`, `STRUCTURE.md`; Spec Kit's per-feature `research.md`) and that is where their
documentation rots first, because facts are exactly what the code can contradict on any commit.

### 10.3 "Which checks can be deterministic and which require an LLM?"

**Deterministic (must be scripts):** required artifacts present for the declared track; DAG order
respected; unresolved-marker scan (`[NEEDS CLARIFICATION]`, TBD/TODO/FIXME, `{template-token}`);
requirement/scenario heading shape; every requirement has ≥1 scenario; ID uniqueness and monotonicity;
every `REQ-###` referenced by ≥1 task; every task referencing a real `REQ-###`; every `REQ-###`
discharged by ≥1 named test that exists and passes; anchor staleness by AST fingerprint; claim
`truth-source` field valid; every architectural claim marked `enforced` has an existing rule file and
that rule passes; contract diff severity (oasdiff); schema change without migration; task checkbox
completion; defect register empty or waived; build / typecheck / lint / test exit codes; token budget of
always-loaded knowledge; git provenance (`commits_behind`).

**Requires an LLM (advisory, never the sole gate):** is this requirement actually testable; do these two
requirements mean the same thing; is this rule enforceable as written; does the design satisfy the spec's
intent; is the chosen approach reasonable; what is this drift item's correct verdict (proposes, human
decides); code review for quality; is this claim worth storing at all.

**RECOMMENDATION.** The ratio matters: aim for the deterministic list to be the gate and the LLM list to
be the reviewer. A harness whose gates are prompts is a harness with no gates.

### 10.4 Multi-agent or one agent with skills?

**RECOMMENDATION. One agent, many skills, subagents used purely as context boundaries.**

Evidence: BMAD's personas are already skills in one agent; Superpowers gets its results from
fresh-subagent-per-task (isolation), not from personas; GSD's mappers fan out for isolation and to avoid
context transfer; the context-rot literature explains why isolation helps and says nothing about roles.
Spawn a subagent when (a) the work needs a large amount of context that must not pollute the main
session, (b) the work is independent and parallelisable, or (c) you need an *uncontaminated* judgement
(review of work the main session produced). Never spawn one to play a character.

### 10.5 Is documentation the source of truth?

**RECOMMENDATION. No, and neither is the code.** The correct model is *per-fact authority*:

| Question | Authority |
|---|---|
| What does the system do right now? | code, plus the tests that pass |
| What must the system do? | spec (permanent capability requirements) |
| What property must always hold? | invariant claim, discharged by a test |
| What structure must be respected? | architecture claim, enforced by a rule file |
| Why is it like this? | ADR |
| What is currently true about the shape of the repo? | derived artifacts, regenerated |

A "contradiction" is only meaningful between a claim and *its own declared authority*. `architecture.md`
says PostgreSQL and the code says Redis is not a contradiction between two peers — it is either a stale
claim whose authority (a decision, recorded in an ADR, enforced by a rule) has been violated by code, or
an undocumented decision. Those two cases have different fixes, which is exactly why the harness must not
guess.

---

## 11. Failure modes to design against (observed, not hypothetical)

| # | Failure mode | Evidence it is real | Our countermeasure |
|---|---|---|---|
| 1 | Prompt-only gates get rationalised away | Superpowers needs `<EXTREMELY-IMPORTANT>` and a red-flag table to hold the line | gates are exit codes |
| 2 | Doc auto-reconciled to code, decision lost | GSD's `drift_action: auto-remap` does exactly this | drift needs a verdict; only the change pipeline may alter claims |
| 3 | LLM cannot see implementation-only drift | arXiv:2604.03447: −21 to −43 pp | anchors + rules, not judgement |
| 4 | Requirements never discharged by tests | Spec Kit: "Tests are OPTIONAL" | `verify` fails on any `REQ-###` with no passing test |
| 5 | Per-feature specs never converge into system knowledge | Spec Kit `specs/NNN-*/` | OpenSpec-style archive fold |
| 6 | Rationale buried in archived per-change docs | OpenSpec `changes/archive/*/design.md` | ADRs are permanent, first-class, referenced by claims |
| 7 | Multiple knowledge stores, inconsistent staleness | GSD: 7 maps + intel JSON + graph + CONTEXT.md | exactly one store, one provenance rule |
| 8 | Instruction bloat degrades the agent | Chroma context rot; BMAD's own budget rule | hard token budget, no escape hatch |
| 9 | Tidy-minded agent deletes load-bearing knowledge | BMAD wrote four grounds specifically to stop this | four grounds enforced at review time |
| 10 | Success declared because tests pass | GSD needed `broken-windows` to stop it | defect register + explicit waivers block `done` |
| 11 | Time-based freshness is meaningless | GSD's `intel` 24h threshold, later superseded by commit-based `graphify` | commit/fingerprint-based only |
| 12 | Framework grows faster than the project | GSD 44 capabilities / ~90 workflows; BMAD 2.4 MB | fixed budgets in `CONSTITUTION.md`, reviewed per release |
| 13 | Agent runs away for hours | mini-swe-agent enforces limits in code | budgets per phase, trajectory persisted |
| 14 | Schema/contract change passes verification spuriously | GSD's blocking schema gate exists for this | blocking process-drift gates |

---

## 12. What I could not establish

**UNKNOWN.** Whether any of these frameworks measurably improves outcomes. None of the six ships an
evaluation of its own methodology. Superpowers tests that *agents comply with its skills*, which is
compliance, not outcome. The only outcome numbers in the corpus are mini-SWE-agent's SWE-bench claims,
which measure a bare loop with no methodology at all — and it scores >74%. **There is no evidence in the
corpus that heavy process improves agent output quality.** Treat every methodological claim here,
including mine, as a hypothesis.

**UNKNOWN.** Real-world adoption durability. I found no longitudinal report of a repository keeping a
system-knowledge layer accurate for a year. The Fiberplane limitation is telling: "Users can re-link
without updating prose." Every anchoring scheme can be defeated by a bored human or an obliging agent.

**UNKNOWN.** How well normalised-AST-fingerprint anchoring behaves on a real refactor (rename a symbol,
move a file). Renames will show as staleness on every claim anchored to the old name. Mitigation
strategies exist (git rename detection, symbol-level rather than path-level anchors) but I have not
tested them. This is the biggest implementation risk in my proposal.

**UNKNOWN.** The right size of the always-loaded knowledge budget. My 400-line figure is an extrapolation
from BMAD's stated budget discipline and the context-rot literature, not a measurement.

---

## 13. Sources

Repositories (read as source at the commits in §0):
[obra/superpowers](https://github.com/obra/superpowers) ·
[github/spec-kit](https://github.com/github/spec-kit) ·
[Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) ·
[bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) ·
[SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) ·
[SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) ·
[gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) (archived) ·
[open-gsd/gsd-core](https://github.com/open-gsd/gsd-core)

Papers:
[arXiv:2604.03447 — Measuring LLM Trust Allocation Across Conflicting Software Artifacts](https://arxiv.org/abs/2604.03447) ·
[arXiv:2609.00252 — Spec-Driven Development for Agentic Software Engineering](https://arxiv.org/html/2609.00252v1) ·
[arXiv:2606.04967 — From Prompt to Process](https://arxiv.org/pdf/2606.04967) ·
[arXiv:2309.12499 / doi:10.1145/3643757 — CodePlan](https://dl.acm.org/doi/10.1145/3643757) ·
[doi:10.1016/j.csi.2023.103774 — Architecture view-based drift analysis](https://dl.acm.org/doi/10.1016/j.csi.2023.103774)

Tools and write-ups:
[Fiberplane drift linter](https://fiberplane.com/blog/drift-documentation-linter/) ·
[Aider repo map](https://aider.chat/2023/10/22/repomap.html) ·
[SCIP announcement](https://sourcegraph.com/blog/announcing-scip) ·
[ArchUnit](https://www.archunit.org/) ·
[dependency-cruiser](https://github.com/sverweij/dependency-cruiser) ·
[Tach](https://github.com/tach-org/tach) ·
[Deptrac](https://github.com/deptrac/deptrac) ·
[oasdiff](https://github.com/oasdiff/oasdiff) ·
[oasdiff breaking-change rules](https://www.oasdiff.com/docs/breaking-changes) ·
[Structurizr DSL](https://docs.structurizr.com/dsl) ·
[OpenHands AGENTS.md](https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md) ·
[OpenHands skills](https://docs.openhands.dev/overview/skills) ·
[ADR tooling index](https://adr.github.io/adr-tooling/) ·
[log4brains](https://github.com/thomvaill/log4brains) ·
[Kiro (AWS)](https://aws.amazon.com/documentation-overview/kiro)
