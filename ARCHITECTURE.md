# ARCHITECTURE.md

The architecture of the harness itself. Working name: **forge**.

Reads on from [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) (what is stored) and
[WORKFLOW.md](WORKFLOW.md) (what happens). This document answers the brief's §6: what kind of thing is
this, what goes where, and how is it validated.

---

## 1. What kind of system is this?

**Answer: a repository-local framework made of three layers — a deterministic CLI kernel, a small set of
LLM skills, and plain-text artifacts in git. It is not an agent, not an orchestrator, and not a
platform.**

The brief offers five candidate shapes. Assessed:

| Candidate | Verdict |
|---|---|
| A collection of skills | **Insufficient alone.** Superpowers proves skills change behaviour, and also proves that prompt-only enforcement has to shout to hold the line. Skills cannot compute a claim-touch set or diff an AST fingerprint |
| A CLI | **Necessary but insufficient.** A CLI cannot write a spec or judge a design |
| A prompt/skill framework | Same as (1) |
| An agent orchestration layer | **Rejected.** The host agent (Claude Code, Codex, Copilot CLI, …) already runs the loop, owns the tools, and manages subagents. mini-SWE-agent shows a ~200-line loop is competitive; writing a better one is not where the leverage is |
| A repository-local framework | **Yes — as the container for the other pieces** |

So: **CLI + skills + artifacts, with a hard rule about which layer owns what.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST AGENT  (Claude Code / Codex / Copilot CLI / …)                    │
│  Owns: the execution loop, file & shell tools, subagents, the model      │
│  forge does not replace, wrap, or re-implement any of this               │
└───────────────┬──────────────────────────────────────┬──────────────────┘
                │ invokes skills                       │ runs commands
                ▼                                      ▼
┌───────────────────────────────┐      ┌───────────────────────────────────┐
│  SKILLS  (judgement)          │      │  KERNEL  `forge`  (mechanism)     │
│  Markdown procedures, on-      │◄────►│  Deterministic. NEVER calls an    │
│  demand. Write artifacts.     │ JSON │  LLM. Exit codes are the gates.   │
│  Cannot enforce anything.     │      │  Reads/writes only text + git.    │
└───────────────┬───────────────┘      └───────────────┬───────────────────┘
                │                                      │
                └──────────────┬───────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ARTIFACTS  (state)  — plain text, in git                               │
│  docs/system/**   changes/**   .forge/**                                │
│  Git is the database. There is no other state store.                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### The three inviolable rules

1. **The kernel never calls a model.** Every kernel output is reproducible from the repository at a
   commit. This is what makes gates trustworthy.
2. **Skills never enforce.** A skill may refuse to proceed, but the *check* that justifies refusing is a
   kernel command. If a rule matters, it is an exit code; if it cannot be an exit code, it is guidance
   and is written as guidance.
3. **All state is text in git.** No database, no daemon, no cache that can disagree with the repository.
   Derived data is committed and regenerable; deriving it twice at the same commit produces identical
   bytes.

---

## 2. Components

### 2.1 Kernel (`forge`) — six modules

| Module | Responsibility | Key inputs | Key outputs |
|---|---|---|---|
| **`store`** | Parse, validate and edit the claim store and ADRs | `docs/system/**` | typed claims, validation issues |
| **`graph`** | Load the artifact DAG, resolve order, derive completion state, resolve context contracts | `.forge/schema/*.yaml`, filesystem | next artifact, blocked set, `instructions --json` |
| **`anchor`** | Resolve anchors, compute normalised-AST fingerprints, classify staleness | claims, git, tree-sitter | `fresh`/`stale`/`missing`/`coarse` per anchor |
| **`derive`** | Produce the derived tier by shelling out to ecosystem tools | repo, `.forge/config.yaml` | `derived/*.json` |
| **`gate`** | Run registered checks at a named point; aggregate severity; exit code | `.forge/config.yaml`, other modules | pass/fail + findings |
| **`trace`** | Scan claims, ADRs, changes, tests and code back-references; build the index | everything | `derived/trace.json` |

Deliberately **not** modules: a model client, a tool registry, a sandbox, a scheduler, a server, a
plugin loader.

### 2.2 Command surface

Small on purpose. Every command is scriptable, `--json`-capable, and has a non-zero exit on failure.

```
forge init                              # scaffold .forge/ and docs/system/ skeleton
forge status                            # one screen: track, phase, blocked set, drift, debt, budgets, enforced/asserted ratio

forge check [--scope store|change|all]  # all deterministic validations (§5)
forge gate <point> [--change N]         # run gates registered at a lifecycle point

forge sync derived [--paths ...]        # regenerate the derived tier
forge sync change <N>                   # the archive fold + re-anchor (WORKFLOW §3.10)

forge drift [--paths ...] [--json]      # anchor staleness + rule conformance + structural gaps
forge drift resolve <D-id> --verdict V1|V2|V3|V4 [--adr N] [--evidence TEXT]
forge drift waive <D-id> --reason TEXT --until <sha|date>

forge claim new <kind> | show <ID> | edit <ID>
forge ratify <ID>                       # candidate -> ratified
forge retire <ID> --ground 1|2|3|4 --evidence TEXT
forge reanchor <ID>                     # only when the fingerprint is unchanged under rename mapping

forge impact --change <N>               # candidate blast radius + computed claim-touch set
forge trace <ID> [--json]               # bidirectional: what references this, what it references
forge verify --change <N>               # produce verification.json

forge change new <slug> --track A|B|C
forge change track <N> --upgrade B|C --reason TEXT
forge archive <N>

forge instructions <artifact> --change <N> --json   # context contract + instruction for a phase
forge adr new <slug>
forge bootstrap derive | review | seal
```

Roughly 20 commands. For comparison, GSD Core exposes ~68 slash commands and 44 capability packages.

### 2.3 Skills

Nine, and the count is a budget (see [CONSTITUTION.md](CONSTITUTION.md)). Each is one `SKILL.md`, each
under ~250 lines, each with pressure tests.

| Skill | Phase | What it does that the kernel cannot |
|---|---|---|
| `forge` (router) | entry | Classify the track, restate intent, route. Read-only, refuses to guess |
| `investigate` | investigate | Read code and decide what is worth knowing; produce candidates with confidence |
| `specify` | spec | Turn intent into delta requirements and scenarios |
| `assess-impact` | impact | Curate the computed blast radius; find consumers static analysis cannot see |
| `design` | design | Choose an approach, name alternatives, write the ADR |
| `plan-tasks` | tasks | Decompose into reviewable, testable units with real interfaces |
| `implement` | implement | Execute one task, TDD, inside its file scope |
| `review` | implement / verify | Two-stage review: spec compliance, then code quality |
| `curate-knowledge` | sync / drift | Propose claim edits, ledger lines, and drift verdicts |

Deliberately absent: personas (analyst, PM, architect, UX), a skill-builder, brainstorming as a separate
skill (it is the router's job), party mode, retrospectives, PRD/PRFAQ.

### 2.4 What the host agent provides and we must not rebuild

File read/write/edit; shell; search (grep/glob); subagent spawning; the model; session compaction; git
integration; permission prompts. Every one of these is a place where a harness could grow a competing
implementation, and every one of them would be worse than the host's.

---

## 3. Repository structure

### 3.1 The harness's own directory

```
.forge/
  config.yaml            # the only configuration file
  constitution.md        # engineering principles (human-amended; see CONSTITUTION.md)
  schema/
    feature.yaml         # artifact DAG: the default change workflow
    bugfix.yaml
    refactor.yaml
    architecture.yaml
    knowledge.yaml
  templates/
    proposal.md  spec.md  impact.md  design.md  tasks.md  adr.md  claim.md
  rules/                 # ecosystem conformance configs, tagged back to claims
    deps.cjs             # or archunit tests / tach.toml / deptrac.yaml
  checks/                # project-specific check scripts referenced by claim evidence
  skills/                # the nine SKILL.md files (or a host plugin pointing here)
  cache/                 # gitignored. Fingerprints only. Deleting it changes nothing but speed
```

**Rejected from the brief's example layout:**

- `rules/` as *prose* rules — the brief's sketch implies a directory of rule documents. Prose rules
  belong in `constitution.md` (governance) or as claims (system-specific). `.forge/rules/` here holds
  *executable* conformance configs. Having both a prose `rules/` and a `constitution.md` guarantees they
  diverge.
- `workflows/` as a directory of procedure documents — GSD has ~90 of these and it is the single clearest
  symptom of over-building. Workflows are DAG declarations in `schema/`; procedures are skills.
- `config/` as a directory — one `config.yaml`. A configuration directory is where configuration goes to
  fragment.
- A `state/` directory — state is derived from the filesystem (OpenSpec's mechanism). The only thing
  under `.forge/` that is not source is `cache/`, and it is disposable by design.

### 3.2 Knowledge and change directories

```
docs/system/            # permanent knowledge — see SYSTEM_KNOWLEDGE.md §2.1
changes/
  0004-refund-support/
    .forge.yaml         # track, created, upgraded_from, skip_spec + reason
    proposal.md         # (track B: includes the `## Claims touched` section)
    investigation.md    # track C
    spec/<capability-path>/spec.md
    impact.md           # track C
    design.md           # track C, or when an ADR is required
    tasks.md
    analysis.md         # generated by `analyze`
    verification.json   # generated by `verify`
    trajectories/*.json # per-task execution records
  archive/
    2026-09-10-0003-idempotent-capture/
```

**Naming.** `changes/NNNN-<slug>/`, zero-padded, monotonic. `specs/` is *not* used for changes — the word
`spec` is reserved for the permanent tier so that "the spec" is never ambiguous. This is a direct
correction of Spec Kit's `specs/NNN-feature/`, where the per-feature folder occupies the name that should
belong to the durable description of the system.

**Rejected from the brief's example change layout:** `tests.md` (tests are code; the spec's scenarios
carry the intent), `verification.md` (generated, and authoring it invites unverified claims),
`knowledge-sync.md` (an operation, not a document — the declaration lives in `impact.md` and the
execution in `forge sync`). Five authored artifacts at maximum, three for a bounded change, one for a
probe.

### 3.3 `.forge/config.yaml`

One file, and it is the seam where a project customises without forking anything.

```yaml
version: 1

commands:                       # how to build/test/lint THIS project
  build:     pnpm build
  typecheck: pnpm typecheck
  lint:      pnpm lint
  test:      pnpm test
  test_one:  pnpm test {file}
  test_list: pnpm test --reporter=json --listTests
  dep_rules: pnpm depcruise --config .forge/rules/deps.cjs
  contract:  pnpm openapi:generate -o {out}

derive:
  languages: [typescript, tsx]
  dep_tool: dependency-cruiser
  entry_globs: ["src/index.ts", "src/cli/*.ts"]

budgets:
  always_loaded_lines: 400      # never raised (see CONSTITUTION.md)
  claims_max: 80                # soft cap; over it, `forge status` demands a prune review
  bootstrap_claims_max: 40
  phase:
    investigate: { steps: 40, wall_seconds: 900 }
    task:        { steps: 30, wall_seconds: 600, max_consecutive_failures: 3 }

thresholds:
  structural_drift: 3
  review_debt_commits: 50
  derived_stale_commits: 20
  orphan_change_window: 20      # how many recent changes S17 looks back over
  contract_severity: breaking   # oasdiff severity that fails the gate

autonomy:                       # WORKFLOW.md §4
  G3: always
  G5: always

rules:                          # injected into artifact generation (OpenSpec's mechanism)
  spec:
    - Money is integer minor units; never express amounts as floats in a requirement
    - Every requirement about a payment must state its idempotency behaviour
  design:
    - Prefer a port over a direct dependency when the domain layer is involved (see ARC-3)
  tasks:
    - A migration task is always [BLOCKING] and always precedes tasks that read the new column

gates:                          # GSD's declarative model
  - point: investigate:pre
    check: derived.freshness
    blocking: false
    onError: skip
  - point: spec:post
    check: store.spec_grammar
    blocking: true
  - point: impact:post
    check: trace.claim_touch_complete
    blocking: true
  - point: analyze:post
    check: trace.requirement_task_coverage
    blocking: true
  - point: implement:pre
    check: derived.freshness
    blocking: true
  - point: implement:task:post
    check: task.scope_and_covers
    blocking: true
  - point: verify:post
    check: verify.definition_of_done
    blocking: true
  - point: verify:post
    check: drift.rules_conformance
    blocking: true
  - point: sync:pre
    check: store.valid
    blocking: true
  - point: converge:post
    check: repo.clean
    blocking: true
```

Twelve gates total, at ten points. GSD has 14 at `plan:pre` alone. The number is a budget, not an
accident: every gate must be justifiable in one sentence, and gates that never fire get deleted.

---

## 4. Models

### 4.1 Artifact model

An artifact is a file (or glob) declared as a node in a DAG. Directly OpenSpec's design, with two
additions.

```yaml
name: feature
version: 1
tracks: [B, C]
artifacts:
  - id: proposal
    generates: proposal.md
    template: proposal.md
    requires: []
    tracks: [B, C]                      # ADDITION 1: per-track requirement
    instruction: |
      ...
  - id: spec
    generates: "spec/**/*.md"
    template: spec.md
    requires: [proposal]
    tracks: [B?, C]                     # B? = required only if behaviour changes
    reads:                              # ADDITION 2: explicit context contract
      - changes/${change}/proposal.md
      - docs/system/specs/${capability}/spec.md
    instruction: |
      ...
  - id: impact
    generates: impact.md
    requires: [spec]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - derived: [deps, inventory]
      - claims: metadata
  - id: design
    generates: design.md
    requires: [spec, impact]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - changes/${change}/impact.md
      - claims: "${impact.claims_touched}"
  - id: tasks
    generates: tasks.md
    requires: [spec, impact, design]
    tracks: [B, C]
apply:
  requires: [tasks]
  tracks: tasks.md
```

**Addition 1 (`tracks`)** is the scale router expressed as data. The same DAG serves all tracks; the track
selects which nodes are required. This avoids maintaining separate lightweight and heavyweight
workflows, which is how GSD ended up with `quick`, `fast`, `sketch`, `spike` and `do` as distinct
commands.

**Addition 2 (`reads`)** turns context engineering into a property of the data model rather than of the
prompt. `forge instructions <id> --change N --json` resolves it — including `claims:` selectors, which
expand to specific claim bodies — so a phase loads exactly its contract. This is the single most
important structural difference from every prompt-first framework in the corpus.

**Artifact lifecycle.**

| Class | Artifacts | Lifetime | Owner | Validated by |
|---|---|---|---|---|
| **Permanent** | `docs/system/**` claims, ADRs, permanent capability specs, `OVERVIEW.md` | forever | human (agent proposes) | `forge check --scope store` |
| **Derived** | `docs/system/derived/**` | until the next commit that changes its inputs | `forge sync derived` | byte-identical regeneration |
| **Ledger** | `DRIFT.md`, `DEBT.md` | entries live until resolved or waived; the files are permanent | kernel appends, human resolves | `forge check` |
| **Temporary** | `changes/NNNN/**` | until `converge`, then archived read-only | the change | `forge gate <point>` |
| **Ephemeral** | `.forge/cache/**`, trajectories mid-run | disposable / archived with the change | kernel | not validated |

**Versioning.** Permanent specs and claims are versioned by git, not by a version field — a version field
in a file that git already versions is a second truth. ADRs are immutable once accepted and are
*superseded*, never edited. `.forge/schema/*.yaml` carries a `version` integer so the kernel can refuse a
schema it does not understand.

**Archival.** `converge` moves `changes/NNNN/` to `changes/archive/YYYY-MM-DD-NNNN-<slug>/` unchanged,
including `verification.json` and the trajectories. Archives are read-only by convention and are never an
input to any phase — if something in an archive matters going forward, it belongs in the permanent tier,
which is exactly the discipline the archive fold enforces.

### 4.2 Skill model

```markdown
---
name: assess-impact
phase: impact
requires-kernel: ["forge impact", "forge trace"]
reads: from-dag                     # the DAG's `reads` contract is authoritative
writes: ["changes/${change}/impact.md"]
---
```

Rules for every skill, each with a reason:

- **≤ 250 lines.** Above that, the procedure is doing too much and should be split or moved into the
  kernel. Superpowers' two longest skills (568 and 679 lines) are its two least crisp.
- **Kernel-first.** A skill must call the kernel for anything computable and must not re-derive it in
  prose. "Check that every requirement has a task" is `forge check`, not a paragraph of instructions.
- **No compulsion language.** No all-caps, no "you have no choice". If it needs that, it needs a gate.
- **Pressure-tested.** Each skill ships with scenarios in `tests/skills/<name>/` that fail without the
  skill and pass with it (Superpowers' `writing-skills` methodology, adopted wholesale — it is the only
  reason to believe a prompt does anything).
- **Announce on entry.** One line, so the transcript records which procedure ran.

### 4.3 Workflow model

A workflow is a `(schema, gates, track policy)` triple. Adding a workflow means adding a YAML file, not
code. This is the property that keeps the harness small as it grows.

### 4.4 State model

There is no state file. Everything is computed:

| Question | Computed from |
|---|---|
| Which artifacts are complete? | `generates` path exists (OpenSpec) |
| What is blocked? | DAG `requires` minus complete set |
| What is the current track? | `changes/NNNN/.forge.yaml` |
| Which tasks are done? | `- [x]` in `tasks.md` |
| Is knowledge stale? | anchor fingerprint vs `@sha`; `generated_from_commit` vs HEAD |
| What is open? | `DRIFT.md` + `DEBT.md` entries without a verdict or unexpired waiver |
| What does X reference? | `derived/trace.json`, regenerated from scans |

Consequences: no migration path for a state format; no desynchronisation; `git checkout` of an old commit
gives you that commit's harness state exactly; and two people (or two sessions) never fight over a
lockfile.

### 4.5 Validation model

Three tiers, and the tier determines who may act on a finding.

| Tier | Implemented as | Examples | Consequence |
|---|---|---|---|
| **Structural** | kernel parsers | claim fields, spec grammar, ID uniqueness/monotonicity, placeholder scan, DAG order | **ERROR** — blocks the gate |
| **Relational** | kernel + `trace.json` | requirement↔task↔test coverage, claim-touch completeness, evidence resolution, rule back-references, budget | **ERROR** — blocks the gate |
| **Semantic** | LLM via a skill | is this testable, do these two mean the same thing, is this rule enforceable, is this the right drift verdict | **FINDING** — advisory; only a human may turn one into a block |

The tier boundary is the design's central bet: **anything that can be moved down a tier, must be.** A
semantic check that becomes relational (by introducing an ID convention) or structural (by introducing a
field) is a permanent improvement; the reverse is a permanent regression.

Issue shape, borrowed from OpenSpec:

```json
{"level": "ERROR", "code": "store.anchor_missing", "path": "docs/system/domain.md",
 "line": 84, "claim": "INV-7", "message": "anchor src/payments/refund.ts#computeRefundable no longer exists",
 "fix": "forge reanchor INV-7, or forge retire INV-7 --ground 1"}
```

Every ERROR carries a `fix` naming the command that resolves it. An error message without a next action
trains people to ignore errors.

---

## 5. Interfaces between the layers

### 5.1 Kernel → skill

JSON on stdout, one shape, always. Skills parse it; they never parse human-formatted output.

```json
{"ok": false, "command": "forge check --scope change --change 4",
 "summary": {"errors": 2, "warnings": 5, "findings": 0},
 "issues": [ ... ],
 "next": ["forge impact --change 4", "forge check --scope change --change 4"]}
```

### 5.2 Skill → kernel

Skills only ever invoke documented commands. They never write to `derived/`, never edit `DRIFT.md`
directly, and never restamp an anchor by hand — those paths exist only through the kernel, which is what
makes provenance meaningful.

### 5.3 Host → harness

Two integration points, both optional and both thin:

1. **Session start**: inject `docs/system/OVERVIEW.md` + the claim index + the output of `forge status`.
   That is the always-loaded set, and it is inside the 400-line budget by construction.
2. **Phase entry**: the skill calls `forge instructions <artifact> --change N --json` and loads exactly
   the returned files.

If the host supports hooks, one more is worth having: a pre-commit hook running `forge check --scope
store`, so a broken claim store cannot be committed. Everything else the harness needs, it gets by being
invoked.

---

## 6. Implementation choices

**Language: Python 3.11+, stdlib-first.** Reasoning: the harness must run against repositories in any
language, so its own runtime must be the least intrusive one available; Python is present or trivially
installed everywhere; `uv run` makes a single-file script with inline dependency metadata practical
(BMAD does exactly this for `lint_spine.py`); and `py-tree-sitter` is the most direct route to the anchor
fingerprints that everything depends on.

**Dependency budget: two.** `tree-sitter` (+ grammar packages) and a YAML parser. Everything else is
stdlib and `subprocess` calls to tools the project already has. If `tree-sitter` is unavailable, anchors
degrade to whitespace-normalised content hashes and are reported `coarse: true` — the harness works with
zero third-party dependencies, just less precisely.

**Cross-platform from day one.** The developer's environment here is Windows with PowerShell and Git
Bash. Therefore: no bash-only scripts in the kernel path (Spec Kit maintains parallel bash/PowerShell/
Python copies of every script — a real maintenance tax we avoid by having one Python implementation);
`pathlib` everywhere; never assume `/`; git invoked with explicit arguments and never through a shell
string; and any stored value that reaches `git` is validated first (GSD validates `built_at_commit` as
4–40 hex characters precisely because a hostile `graph.json` could otherwise inject argv options — we
apply that rule to every anchor SHA and path).

**Not Go/Rust for v1**, despite single-binary appeal: it slows the iteration this design needs while the
claim format is still being learned. Revisit once the format has survived a few months of real use.

**Testing the harness itself.** The kernel gets ordinary unit and golden-file tests over fixture
repositories (including a Windows-path fixture). The skills get pressure tests: a scenario, a baseline
run without the skill that must fail, and a run with the skill that must pass. A skill without a failing
baseline is undemonstrated and does not ship.

---

## 7. What this architecture refuses to become

| Refused | Why |
|---|---|
| A multi-agent platform | Subagents are context boundaries. Personas are costume. BMAD's five personas are five skills wearing hats |
| A graph database | GSD built one; it became a fourth representation of the system with its own rot |
| An MCP server | The kernel is a CLI. A CLI composes with every host; a server needs a lifecycle, a protocol version, and a reason |
| A custom IDE or editor | Nothing here needs a UI. `forge status` is one screen of text |
| An execution engine | mini-SWE-agent is ~200 lines and competitive. The host already has one |
| A model client / provider abstraction | The kernel never calls a model. That is the point |
| A plugin system | Nine skills, twelve gates, five schemas. A plugin system for that is more machinery than machine. Projects extend via `config.yaml` (`rules`, `gates`, `commands`) and by overriding templates |
| A parallel documentation site generator | The store is markdown in git. If it needs rendering, the platform already renders markdown |
| An orchestration DSL | The DAG is 40 lines of YAML with three fields. Anything more expressive becomes a language nobody can debug |

---

## 8. Growth budget

The corpus' clearest lesson is that these frameworks grow faster than the projects they serve — GSD to 44
capabilities and ~90 workflows, BMAD to 29 skills and 2.4 MB. Numbers are therefore part of the
architecture, and changing one is a decision that requires a reason recorded in
[CONSTITUTION.md](CONSTITUTION.md).

| Budget | v1 | Hard ceiling | What to do at the ceiling |
|---|---|---|---|
| Skills | 9 | 12 | Merge two or delete one before adding |
| Kernel commands | ~20 | 25 | Prefer a flag on an existing command |
| Gates | 12 | 16 | Delete a gate that has never fired |
| Workflow schemas | 5 | 7 | Express the variant as a track, not a schema |
| Kernel LOC | — | ~3,000 | Above this the kernel is doing judgement work; find it and move it to a skill |
| Skill lines each | — | 250 | Split, or move the computable part into the kernel |
| Always-loaded lines | — | 400 | Cut or relocate a claim. **Never raise the budget** |
