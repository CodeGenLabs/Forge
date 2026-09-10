# COMPETITIVE_ANALYSIS.md

Companion to [RESEARCH.md](RESEARCH.md). That document carries the evidence and the pinned commits; this
one carries the comparison and the extraction decisions. Ratings are my judgement over the source I read
on 2026-09-10, not vendor claims.

**Rating scale**

| Symbol | Meaning |
|---|---|
| **A** | Strong, and *mechanically* enforced (code, schema, exit code) |
| **B** | Present and well-specified, but enforced only by prompt |
| **C** | Present but thin, partial, or optional |
| **–** | Absent |

The distinction between **A** and **B** is the whole point of this table. Most of these projects would
score much higher on a table that did not ask *what enforces it*.

---

## 1. Capability matrix

| Capability | Superpowers | Spec Kit | BMAD | OpenSpec | SWE-agent (+mini) | GSD Core | Best-in-class outside the six |
|---|---|---|---|---|---|---|---|
| Brainstorming / intent elicitation | **B** 3-path router, hard approval gate | **B** `/clarify`, `[NEEDS CLARIFICATION]` | **B** brainstorming + advanced-elicitation + party-mode | **B** `/opsx:explore` | – | **B** `discuss-phase` + assumptions modes | Kiro (requirements dialogue) |
| Investigation of existing code | **C** ad-hoc inside skills | **C** `research.md` per feature | **B** `deep-recon`, `project-context` scan | **C** `openspec list --specs` + read specs | **A** the loop *is* investigation (reproduce first) | **A** parallel `map-codebase` fan-out | Aider repo map; SCIP/Glean |
| Specification | – (design doc only) | **B** rich template, `FR-###`/`SC-###` | **B** SPEC kernel derived from memlog | **A** requirement/scenario grammar + `validate` | – | **B** `spec-phase`, `REQUIREMENTS.md` | – |
| Architecture knowledge | – | – | **A** spine template + `lint_spine.py` | **C** per-change `design.md` only | – | **B** 7 codebase maps + `CONTEXT.md` predicates | ArchUnit / dependency-cruiser / Tach / Deptrac; Structurizr DSL |
| System knowledge (durable, whole-system) | – | – | **B** spine + AGENTS.md managed block | **A** `openspec/specs/` (behaviour only) | – | **B** `.planning/codebase/` + `intel` + `graphs` | OpenHands `repo.md` + `memory/`; Kiro steering files |
| Change management | – (git worktrees) | **C** `specs/NNN-*/`, never converges | **C** epics/stories | **A** change → delta → archive fold | – | **B** phases/milestones/waves | – |
| Task planning | **A** rigorous plan format, no placeholders | **B** tasks grouped by story, `[P]` markers | **B** epics-and-stories | **B** `## N.` groups + numbering validation | – | **B** plan-phase + `gap-analysis` on REQ ids | – |
| TDD | **A** RED-GREEN-REFACTOR as an iron law | **C** "Tests are OPTIONAL" | **B** in build/review skills | **C** "state how to verify" per task | **A** implicitly (reproduce → fix → re-run) | **B** `tdd` capability with RED/GREEN gate | – |
| Agent execution loop | **B** subagent-per-task + 2-stage review | **B** `/implement` | **B** `bmad-build` / `build-auto` | **B** `/opsx:apply` with `tracks` | **A** the reference implementation | **B** execute-phase with waves | – |
| Verification | **B** evidence-before-claims | **B** `/analyze` + `/checklist` (read-only) | **B** review skills + rubric walker | **B** verify-change (3 dimensions, prompt) | **A** tests are the oracle; lint-guarded edits | **A** gate engine + `nyquist` + `broken-windows` | oasdiff / Schemathesis / Pact |
| Drift detection | – | – | **C** provenance line + `git log --diff-filter=DR` on refresh | – | – | **A** structural + process + premise gates | **A** Fiberplane `drift` (AST-fingerprint anchors) |
| Context engineering | **A** subagent isolation, constructed context | **B** "progressive disclosure" in prompts | **B** persistent_facts, size budget, retrieval rule | **A** per-artifact `instruction` + `contextFiles` | **A** budgets in code, trajectory persisted | **A** phase isolation, fan-out, fresh context | Chroma context-rot findings |
| Traceability | **C** plan cites the spec path | **B** ID inventory built by LLM inference | **B** Capability → Architecture Map, `binds` | **B** capability path is the join key | – | **B** `gap-analysis` cross-refs REQ-ID / D-ID | Requirements-traceability practice |
| QA gates | **C** review checkpoints | **C** severity ladder, advisory | **C** reviewer gate consuming linter JSON | **B** `validate` blocks archive | **A** limits + revert-on-lint-error | **A** declarative gates with `blocking` | – |
| Scale adaptation | **A** spike/bounded/architectural + ratchet | **C** presets (`lean`) | **B** `altitude`, "right-sized" | **C** `skip_specs`, optional `design` | – | **B** `quick`/`fast`/`sketch`/`spike` vs full phases | – |
| Determinism of its own tooling | **C** hook + shell scripts only | **C** path resolution only | **B** `lint_spine.py`, config resolvers | **A** Zod schemas, parsers, validator, DAG, archive fold | **A** the agent is code | **A** drift lib, gate engine, capability manifests | – |
| Cost to adopt (lower is better) | **A** 14 skills, 3.4k lines | **B** CLI + templates + `.specify/` | **–** 29 skills, 2.4 MB, Python resolvers | **B** Node CLI + `openspec/` tree | **A** none (we borrow ideas only) | **–** 44 capabilities, ~90 workflows | varies |

### What the matrix says

1. **No project scores A on both "system knowledge" and "drift detection".** OpenSpec has durable
   behavioural knowledge with no drift story; GSD has drift gates over knowledge that is free-form prose;
   BMAD has the best knowledge *format* with no drift story beyond a manual refresh. **The gap our
   harness must fill is precisely the intersection.**
2. **The only A-grade drift detection in existence for this problem is outside the six** (Fiberplane's
   AST-fingerprint anchors) and it is a *detector*, not a resolver.
3. **The two projects that enforce things with code (OpenSpec, GSD) are the ones worth structurally
   copying.** The two that enforce with prose (Superpowers, Spec Kit) are worth copying *vocabulary and
   discipline* from. BMAD is worth copying *one template, one linter and one policy* from. SWE-agent is
   worth copying *three mechanisms* from and nothing else.
4. **Cost and capability are anti-correlated in the wrong direction.** The two most capable (BMAD, GSD)
   are the two most expensive to own, by an order of magnitude, and their capability is spread across
   dozens of features most projects will never touch.

---

## 2. Per-project extraction

### 2.1 Superpowers — *the discipline library*

**Strengths.** Small (3,377 lines across 14 skills). Every skill is a tested artifact with a real
red/green test suite. The plan format is the best in the corpus: exact file paths, `Interfaces:
Consumes/Produces` with real signatures, five TDD steps with literal code, and an explicit ban on
placeholder phrases. The three-path router with a one-way ratchet is the cleanest answer to
process-versus-task-size anywhere in the corpus.

**Weaknesses.** Zero system model — no architecture, components, invariants, ADRs or data model, and
nothing durable survives a change beyond a dated design doc and a dated plan. Enforcement is entirely
prompt-level, which is why the text has to shout (`<EXTREMELY-IMPORTANT>`, "you do not have a choice").
`subagent-driven-development` forbids pausing for the human mid-plan, which is right for throughput and
wrong for the gates we actually need. Bootstrap can be lost after compaction on some hosts.

**Adopt.** Scale router + one-way ratchet · plan format (files/interfaces/no-placeholders) ·
evidence-before-claims · fresh subagent per task · two-stage review (spec compliance ≠ code quality) ·
TDD-for-prompts with a `tests/` directory · announce-the-skill.

**Reject.** All-caps compulsion as the enforcement layer · no-human-in-the-loop plan execution ·
per-change design docs as the durable knowledge store.

**Modify.** `verification-before-completion` → `forge verify` producing a signed evidence artifact.
`writing-plans`' self-review checklist → deterministic `forge check`.

---

### 2.2 GitHub Spec Kit — *the vocabulary*

**Strengths.** The best artifact vocabulary: `FR-###`, `SC-###`, prioritised independently-testable user
stories with `Independent Test`, measurable technology-agnostic success criteria, and
`[NEEDS CLARIFICATION: …]` as an in-band greppable uncertainty marker. A constitution that explicitly
outranks the spec, with conflicts auto-classified CRITICAL. `/analyze` is the most complete written
specification of a consistency engine I found. A template override stack lets a project customise
without forking. The `SYNC IMPACT REPORT` block in its own constitution is a neat impact-record seed.

**Weaknesses.** `specs/NNN-feature/` never converges into system knowledge — after N features you have N
snapshots of history and no description of the system. Tests are declared OPTIONAL in the task template
while the spec template demands independent tests, which breaks the only traceability chain that
matters. `/analyze` asks an LLM to build an ID inventory by keyword inference and then compute coverage
percentages "deterministically". Hooks are dispatched by asking the model to read YAML and emit an
`EXECUTE_COMMAND:` line. Six planning files per feature is mostly noise or misfiled system knowledge.

**Adopt.** Labelled requirement/criterion IDs · `[NEEDS CLARIFICATION]` as a blocking greppable marker ·
prioritised independently-testable stories · constitution outranks spec · template override stack ·
analysis is read-only · sync-impact reporting.

**Reject.** Numbered feature folders as the unit of durable knowledge · optional tests ·
prompt-mediated hooks · `/analyze` as a prompt · the six-file per-feature bundle.

**Modify.** `/analyze` splits: `forge check` (deterministic) + a small semantic review. `research.md` /
`data-model.md` / `contracts/` stop being per-feature and become either System Knowledge or derived
artifacts.

---

### 2.3 BMAD Method — *the knowledge format*

**Strengths.** Three genuinely excellent pieces:

1. `spine-template.md` — `AD-n` blocks with **Binds / Prevents / Rule**, stable never-renumbered IDs,
   read-only inherited invariants, explicit truth-source annotations (`Stack` is a *seed*, "the code owns
   the detail"), a `Capability → Architecture Map`, a `Deferred` section, and an `altitude` field. Its
   admission criterion — *"calls a future builder can't read off compliant code"* — is the single best
   sentence in the entire corpus.
2. `lint_spine.py` — a deterministic doc linter whose docstring states the correct division of labour:
   "LLMs miscount IDs and miss literal placeholders; a grep does not."
3. `bmad-project-context` — the ledger (`retain | rewrite | relocate | automate | delete`), the **four
   grounds for deletion**, the `Verified <date> against <sha>` provenance line plus
   `git log --diff-filter=DR` re-verification, "prefer a check over a prose rule", and an unraisable size
   budget.

Plus `bmad-spec`'s append-only `.memlog.md` with a derived `SPEC.md`, which eliminates in-place edit
conflicts and gives provenance for free.

**Weaknesses.** 29 skills, 2.4 MB, five agent personas, a per-skill TOML manifest, two Python config
resolvers, and a builder for creating more of all of it. Free-text `knowledge` pointers as the routing
mechanism. Nothing connects the spine's enforceable `Rule` fields to an actual enforcement tool, so the
spine can drift silently even though it is the most check-ready artifact in the corpus. No change
lifecycle that converges knowledge.

**Adopt.** The admission criterion · Binds/Prevents/Rule with stable IDs · deterministic doc linter and
its mechanical/semantic split · read-only inherited invariants · explicit truth-source annotations ·
provenance line + deletions-since-SHA re-verification · four grounds for deletion · the ledger ·
prefer-a-check-over-a-rule · unraisable size budget · append-only log with derived rendering · altitude ·
Capability → Architecture Map.

**Reject.** Personas · skill builder · PRD/PRFAQ/brief/sprint/party-mode · TOML manifests · Python
config-resolution layer · anything measured in megabytes.

**Modify.** Split the one-file spine into typed per-topic files (different truth sources, different
cadences, so per-file staleness becomes answerable). Compile `Rule` into an actual dependency-rule file
where the ecosystem supports it. Fold the linter into the kernel.

---

### 2.4 OpenSpec — *the skeleton*

**Strengths.** The change-centric model with three tiers — permanent `openspec/specs/`, in-flight
`openspec/changes/<name>/`, archived `changes/archive/YYYY-MM-DD-<name>/` — and a **deterministic
archive-time fold** of delta requirement blocks into the permanent specs. The `schema.yaml` artifact DAG
(`id`, `generates`, `template`, `instruction`, `requires`, plus `apply.requires`/`apply.tracks`) gives
ordering, state, per-step prompting and output shape from one small file. State is derived from the
filesystem, so there is nothing to desynchronise. Validation is real code (Zod + hand-written parsers +
typed ERROR/WARNING/INFO issues + task-numbering and purpose-placeholder checks). The delta grammar is a
closed set with `MODIFIED` requiring full content and `REMOVED` requiring Reason + Migration. Zero-delta
changes are rejected unless `skip_specs: true` is recorded in the repository. Per-artifact `rules:` in
`config.yaml` operationalise project constraints without touching any skill. Every generated path is
containment-checked.

**Weaknesses.** Its permanent knowledge is *only* behavioural requirements: no components, boundaries,
dependency direction, non-observable invariants, data model, deployment, or *why*. Rationale lives in
per-change `design.md`, which gets archived, so the reason a live decision exists ends up in
`changes/archive/2026-01-06-.../design.md`. `verify-change` is a prompt that greps for keywords.
Initiatives / explorations / worksets / stores are scope creep for a single developer.

**Adopt.** The three-tier change model · the artifact DAG schema · filesystem-derived state ·
deterministic structural validation with typed issues · the closed delta grammar · deterministic archive
fold as the knowledge-sync mechanism · zero-delta rejection with a *named, recorded* bypass ·
per-artifact rule injection · `instructions --json` returning the exact files a phase may read · path
containment on every write.

**Reject.** Requirements as the only permanent knowledge · rationale in archived per-change docs ·
`verify` as a prompt · initiatives/explorations/worksets/stores.

**Modify.** Extend the permanent tier to *capability specs + typed system-knowledge claims + ADRs*, and
drive the fold from an explicit per-change impact record instead of inferring it.

---

### 2.5 SWE-agent / mini-SWE-agent — *the inner loop*

**Strengths.** mini is the existence proof that a ~200-line loop with `bash` only is competitive:
budgets enforced in code (`step_limit`, `cost_limit`, `wall_time_limit_seconds`,
`max_consecutive_format_errors`), trajectory saved in a `finally` on every step, an impoverished but
honest interface, and a reproduce-first workflow. SWE-agent adds the ACI insight and one exemplary
guardrail: `windowed_edit_linting` diffs flake8 before/after an edit and **reverts** on new syntax
errors, with an error message that teaches the retry.

**Weaknesses.** No specification, no architecture, no persistence between tasks, no system knowledge —
by design. Benchmark-shaped: issue in, patch out. SWE-agent's 15 tool bundles are a large surface we
would have to maintain for no benefit on a host that already provides file and shell tools.

**Adopt.** Hard budgets in code · trajectory persisted every step · reproduce-before-fix ·
one-action-per-step observe→act for the inner loop · guardrails in tools with teaching error messages ·
best-of-n with an explicit reviewer for high-stakes work only.

**Reject.** Building an execution engine, environment abstraction or model client · custom tool bundles ·
benchmark plumbing.

**Modify.** The inner loop stays the host agent's. We supply the *entry contract* (task, allowed file
scope, the test that must go from red to green) and the *exit contract* (evidence).

---

### 2.6 GSD Core — *the enforcement engine*

**Strengths.** The declarative gate model: a named lifecycle point (`plan:pre`, `execute:wave:post`,
`verify:post`, `ship:pre`, …), a check identified by a query string, `blocking: true|false`, a `when`
config predicate, and `onError: skip`. Three drift gates that form a real taxonomy — **structural**
(new dirs/routes/migrations/barrels absent from `STRUCTURE.md`, threshold-based, non-blocking),
**process** (schema files changed with no DB push → **blocking**), **premise** (a derived artifact older
than the newest decision in `CONTEXT.md`). Provenance in frontmatter (`last_mapped_commit`,
`built_at_commit`, `commits_behind`, `commit_stale`). `CONTEXT.md`'s machine-greppable single-line
predicates, cited by ID and never paraphrased. `broken-windows` as a blocking defect register with
recorded waivers. `gap-analysis` cross-referencing REQ-IDs against plans. Parallel mappers that write
their own files so nothing transits the orchestrator's context. Careful security hygiene (validating
`built_at_commit` as hex before it reaches `git`).

**Weaknesses.** 44 capabilities, ~90 workflow files, 14 gates at `plan:pre` alone, four coexisting
representations of the same system (seven markdown maps + `.planning/intel/*.json` +
`.planning/graphs/` + `CONTEXT.md` predicates), each with its own staleness story. `intel`'s 24-hour
freshness threshold is time-based and meaningless; that it was later superseded by commit-based staleness
in `graphify` reads as an internal admission. `drift_action: auto-remap` silently rewrites the map to
match the code — exactly the behaviour our brief forbids. Structural drift matching is
`structureMd.includes(prefix)` against free-form markdown, so recall is high and precision is low by
construction.

**Adopt.** The declarative gate model · the three-way drift taxonomy with per-type blocking policy ·
commit-based provenance and staleness · `commits_behind` as a legible signal · single-line predicates
cited by ID · a blocking defect register with waivers · requirement-ID coverage cross-referencing ·
fan-out mappers writing their own files · `--paths` incremental re-mapping with validated arguments ·
never let a stored value reach a shell unvalidated.

**Reject.** 44 capabilities · a knowledge graph · a parallel JSON intelligence store · MCP memory ·
time-based freshness · `auto-remap` as a default · ~90 workflow files.

**Modify.** One derived store, one provenance rule. `auto-remap` → `propose-remap`, which never writes
over a load-bearing claim without a recorded human verdict.

---

## 3. Additional projects that changed a decision

| Project / source | What it contributes | Adopt / reject |
|---|---|---|
| [Fiberplane `drift`](https://fiberplane.com/blog/drift-documentation-linter/) | `path#Symbol@sha` anchors; normalised tree-sitter AST fingerprints; staleness = fingerprint changed since baseline; explicitly "detection, not review" | **Adopt as the core staleness primitive.** Its limitation ("users can re-link without updating prose") is ours too; mitigate by requiring a verdict, not a re-link |
| [ArchUnit](https://www.archunit.org/) · [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) · [Tach](https://github.com/tach-org/tach) · [Deptrac](https://github.com/deptrac/deptrac) | Dependency direction, layer boundaries, cycle prohibition, public-interface enforcement — as tests or CI checks, per ecosystem | **Adopt as the enforcement target for architectural claims.** Do not write our own; emit/maintain their config and store the rule path as the claim's evidence |
| [oasdiff](https://github.com/oasdiff/oasdiff) (+ Pact, Schemathesis, Spectral) | Breaking-change classification between two OpenAPI documents with an exit-code severity gate | **Adopt** for interface-drift detection when the project has a generated contract. **Reject** building anything bespoke here |
| [Aider repo map](https://aider.chat/2023/10/22/repomap.html) | tree-sitter symbol extraction + personalized PageRank over a reference graph, inside a token budget | **Adopt the conclusion** (structural context is cheap and should be discovered, not stored). **Reject building it** — the host agent's search plus grep is sufficient at personal scale |
| [SCIP](https://sourcegraph.com/blog/announcing-scip) / LSIF / Glean / Kythe | Precise cross-repository code intelligence at scale | **Reject for the MVP** (indexer maintenance cost). Revisit only if a project outgrows grep |
| [Structurizr DSL](https://docs.structurizr.com/dsl) | Architecture-as-code with a parseable DSL; C4 model | **Reject as a dependency**, **adopt the idea** that the component/boundary model should be structured data rather than a diagram in prose |
| [OpenHands](https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md) | `AGENTS.md` for always-loaded conventions, `SKILL.md` for triggered knowledge, `repo.md` + `memory/` split; "list the exact items you plan to save and only save what the user approves" | **Adopt the two-tier always-loaded/triggered split and the confirm-before-save protocol** |
| [Kiro (AWS)](https://aws.amazon.com/documentation-overview/kiro) | requirements/design/tasks triad + *steering files* + *hooks on save/create/commit* | **Adopt as independent confirmation of the gate model.** Nothing to import directly |
| [ADR tooling](https://adr.github.io/adr-tooling/) · [log4brains](https://github.com/thomvaill/log4brains) · MADR | Numbered ADR directory, supersession links, static-site rendering | **Adopt the format** (numbered `docs/system/decisions/ADR-NNNN-*.md`, MADR-ish sections, supersession links). **Reject the tooling** — a directory and a naming convention is enough |
| [CodePlan](https://dl.acm.org/doi/10.1145/3643757) | Neuro-symbolic repository-level change propagation: incremental dependency analysis + may-impact analysis + adaptive planning | **Adopt the shape** for the impact phase (static analysis proposes the blast radius, the model curates). **Reject** implementing incremental dependency analysis |
| pytest-impact · OpenClover | Change-aware test selection from a git diff or per-test coverage | **Adopt if the project already has it**; never a prerequisite |
| Chroma context-rot findings | Quality degrades with input length at every increment, well before the window limit | **Adopt as the justification** for the always-loaded token budget and phase isolation |
| [arXiv:2604.03447](https://arxiv.org/abs/2604.03447) | LLMs detect doc faults at 67–94% but lose 21–43 pp when only the implementation changed; confidence is uninformative | **Adopt as a hard constraint**: LLMs may not be the drift *detector*, and their confidence may not be the escalation trigger |
| [arXiv:2609.00252](https://arxiv.org/html/2609.00252v1) | Specs must be executable / explicit / traceable / evidence-dischargeable; 8-mechanism harness; graduated autonomy | **Adopt the four spec properties as acceptance criteria** for our spec artifact, and graduated autonomy as the human-gate model |

---

## 4. The synthesis in one table

Where each layer of our harness comes from, and what we add that nobody has.

| Layer | Primary source | Secondary | What we add |
|---|---|---|---|
| Repository-local, file-first, git-as-database | OpenSpec | Superpowers | — |
| Lifecycle as a declared artifact DAG | OpenSpec `schema.yaml` | — | Per-track DAG variants selected by the scale router |
| Lifecycle enforcement | GSD gate model | SWE-agent (tool-level guards) | Gates become the *only* enforcement layer; prompts never gate |
| Scale adaptation | Superpowers 3-path router | BMAD `altitude` | Track selects which DAG nodes are required; ratchet is one-way and recorded |
| Spec format | OpenSpec grammar | Spec Kit vocabulary | Every requirement must name a discharging test before `verify` passes |
| System knowledge format | BMAD spine (`Binds`/`Prevents`/`Rule`, admission criterion) | GSD `CONTEXT.md` predicates | **Typed claims with a mandatory `truth-source`, `anchors`, and `evidence` field** |
| Staleness detection | Fiberplane anchors | GSD `commits_behind` | Anchors are per-claim, not per-file; `forge drift` is deterministic and blocking-on-verdict |
| Architecture conformance | ArchUnit / dep-cruiser / Tach / Deptrac | — | **Claims marked `enforced` must name a rule file that exists and passes; `enforced`/`asserted` ratio is reported** |
| Knowledge sync | OpenSpec archive fold | Spec Kit `SYNC IMPACT REPORT` | Fold is driven by a declared `impact.md`, and refuses on an unexplained claim edit |
| Drift resolution | — (nobody) | BMAD four grounds | **Four-verdict drift ledger; only the change pipeline may edit a claim; auto-reconciliation is forbidden** |
| Traceability | GSD `gap-analysis` | BMAD Capability→Architecture map | ID conventions + grep + a *generated* `trace.json`; no database |
| Task plan format | Superpowers `writing-plans` | OpenSpec `## N.` numbering | — |
| TDD | Superpowers | GSD `tdd` capability | Requirement→test binding is checked deterministically |
| Inner execution loop | mini-SWE-agent | SWE-agent | Delegated to the host agent; we own the entry/exit contracts and the budgets |
| Definition of done | GSD `broken-windows` | Superpowers evidence rule | `verify` emits a signed evidence report; open defects block `done` unless waived with a reason |
| Bootstrap | GSD `map-codebase` fan-out | BMAD `project-context` adoption ledger | Three passes: deterministic inventory → LLM candidates → **human ratification with a claim cap** |
| Human gates | Superpowers hard gate | arXiv:2609.00252 graduated autonomy | Fixed, short, enumerated list; every other decision is the agent's |

**The one-sentence differentiator.** Every project in the corpus stores system knowledge as prose and
then needs an LLM to check it; we store system knowledge as a small set of anchored, truth-source-labelled
claims and check them with git, tree-sitter, and the ecosystem's own linters — reserving the LLM for
proposing verdicts a human confirms.
