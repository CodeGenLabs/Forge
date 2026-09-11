# SYSTEM_KNOWLEDGE.md

The design of the System Knowledge layer. This is the load-bearing document of the proposal; the
lifecycle in [WORKFLOW.md](WORKFLOW.md) and the components in [ARCHITECTURE.md](ARCHITECTURE.md) exist to
serve it. Evidence for every position taken here is in [RESEARCH.md](RESEARCH.md).

---

## 0. The problem, restated precisely

The brief asks for a durable layer that lets an agent reason about an existing system, and asks how to
stop it from drifting. Those are two different problems and conflating them is why existing tools fail:

- **Problem A — usefulness.** Give the agent knowledge it cannot recover from the code, in a form that
  costs almost nothing to load.
- **Problem B — trustworthiness.** Make it possible to know, mechanically, which parts of that knowledge
  are still verified as of this commit, and forbid silent reconciliation in either direction.

A solution to A alone is GSD's seven markdown maps: useful, and rotting. A solution to B alone is a
linter over documents nobody reads. The design below solves them with one mechanism — **the anchored,
truth-source-labelled claim** — because a claim is simultaneously the unit of usefulness and the unit of
verification.

### Three principles that fall out of the evidence

1. **Store judgements, derive facts.** If a competent engineer could recover it from compliant code, it
   is a fact and must be derived on demand, never stored. (BMAD's admission criterion; §5.2 of
   RESEARCH.md.)
2. **Staleness is a comparison; correctness is a judgement.** Comparisons are the kernel's job.
   Judgements are the human's, with the LLM proposing. LLMs lose 21–43 percentage points of detection
   accuracy exactly in the case where only the implementation changed (arXiv:2604.03447), so they cannot
   be the detector.
3. **Every line is paid in every session.** The always-loaded set has a hard budget that is never raised.
   Everything else sits behind an observable trigger.

---

## 1. Unit of knowledge: the Claim

**Decision: structured metadata + Markdown prose, one claim at a time, in git. Not a graph, not a
database, not YAML-only, not AST-derived.**

Why not the alternatives:

| Alternative | Why rejected |
|---|---|
| Pure Markdown prose | Not addressable, not diffable at fact level, not checkable. This is the corpus-wide failure. |
| Pure YAML/JSON | Loses the prose that makes knowledge *usable* by a human or an agent; nobody reads it or maintains it. |
| Knowledge graph | GSD built one (`graphify`) and it became a fourth representation with its own staleness story. Edges you cannot verify are worse than no edges. Rejected for the MVP; see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q7. |
| Database (SQLite) | Not diffable, not reviewable in a PR, not mergeable, invisible in `git log`. Kills the one property that makes this work: knowledge changes review like code changes. |
| AST-derived metadata as the store | That is the *derived* tier, not the knowledge tier. It can only ever restate the code. |
| Embeddings / RAG index | Answers "what is similar", not "what must be true". Adds a build step, an index to rot, and no verifiability. |

### 1.1 Claim shape

A claim is a Markdown heading carrying a stable ID, immediately followed by a fenced `claim` block, then
prose. The fence is why this is parseable with ~20 lines of code and no YAML parse of the whole document.

```markdown
### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:
  - src/payments/refund.ts#computeRefundable@a1b2c3d
  - src/payments/refund.ts#Refund@a1b2c3d
evidence:
  - test: tests/payments/refund.spec.ts::refund cannot exceed capture
governs: [CMP-payments, API-post-refunds]
since: ADR-0014
reviewed: 2026-09-10
```

Partial refunds accumulate: the sum of all settled refunds against an order is what is bounded, not each
refund individually. A refund attempt over the remaining balance is rejected at the domain boundary, not
clamped — clamping silently under-refunds customers, which is worse than an error.
```

The prose is the part an agent actually reasons with. The block is the part the kernel reasons with. The
prose is required to say something the code does not — in this example, *why* rejection beats clamping —
and that is checked by review, not by script.

### 1.2 Field reference

| Field | Required | Values | Meaning |
|---|---|---|---|
| `kind` | yes | see §2 | Determines which validations apply |
| `status` | yes | `enforced` \| `asserted` \| `proposed` \| `retired` | `enforced` = a tool fails when it is violated. `asserted` = believed true, only anchored. `proposed` = not yet ratified (candidates only). `retired` = kept for history, excluded from checks |
| `truth-source` | yes | `code` \| `tests` \| `config` \| `spec` \| `decision` \| `derived` | Which artifact is authoritative for this claim (§3) |
| `anchors` | yes¹ | list of `path[#Symbol][@sha]` | Where in the code this claim is about. Drives staleness (§5) |
| `evidence` | if `status: enforced` | list of `test:` / `rule:` / `contract:` / `check:` entries | What mechanically fails when the claim is violated (§4) |
| `governs` | no | list of claim IDs | Claims constrained by this one. Directed, acyclic |
| `since` | no² | `ADR-nnnn` | The decision that created or last changed this claim |
| `supersedes` | no | claim ID | Replaces a retired claim |
| `reviewed` | yes | `YYYY-MM-DD` | Date a human last ratified the prose. Not a staleness signal; a review-debt signal |
| `confidence` | candidates only | `high` \| `medium` \| `low` | Bootstrap output only; forbidden in ratified claims |
| `retired-ground` | if `status: retired` | `1`–`4` | Which of the four deletion grounds applies (§10.2) |
| `retired-evidence` | if `status: retired` | free text | What makes that ground true. A ground without evidence is an assertion |

¹ `anchors` may be the literal `[]` **only** for `kind: constraint` (constraints that originate outside
the repository) and `kind: concept` (vocabulary with no single home). Empty anchors on any other kind is
a validation error, because an unanchored claim can never be checked and will silently rot.

² `since` is **required** for `kind: architecture` and for any claim whose `status` changes from
`asserted` to `enforced` or vice versa. Rationale: those are the changes that need a recorded reason.

### 1.3 Why the ID matters more than it looks

IDs are the entire traceability substrate (§8). Consequences, all borrowed from what worked in the
corpus:

- **Stable and never renumbered or reused** (BMAD `AD-n`). A claim ID is a permanent name.
- **Cited verbatim, never paraphrased** (GSD `CONTEXT.md`). A change proposal writes `INV-7`, not "the
  refund invariant". This is what makes `grep -r INV-7` a complete answer to "where is this
  load-bearing?".
- **One claim per ID, one ID per line-anchored heading**, so `git blame` on the heading tells you who
  introduced the claim and `git log -S INV-7` tells you every artifact that ever referenced it.

---

## 2. Claim kinds, files, and which are mandatory

### 2.1 The store

```
docs/system/
  OVERVIEW.md              # prose, <= 1 page, always loaded. No claims.
  architecture.md          # ARC-*  mandatory
  components.md            # CMP-*  mandatory
  domain.md                # CON-*, INV-*  mandatory
  pitfalls.md              # PIT-*  mandatory (may be empty at baseline)
  interfaces.md            # API-*  optional
  data.md                  # DAT-*  optional
  workflows.md             # FLW-*  optional
  constraints.md           # CST-*  optional
  strategy.md              # STR-*  optional
  decisions/
    ADR-0001-<slug>.md     # mandatory directory; may be empty at baseline
  derived/                 # machine-owned. Never hand-edited. Regenerable.
    inventory.json
    api-surface.json
    deps.json
    tests.json
    trace.json
    drift.json
  candidates/              # unratified. Readable by the agent; NOT citable as truth.
    <topic>.md
  DRIFT.md                 # the open drift ledger (§6)
  DEBT.md                  # the defect register (§9)
```

**Rationale for splitting by kind rather than by subsystem.** Different kinds have different truth
sources and different update cadences. If `architecture.md` also contains the stack list, "is this file
stale?" has no answer. Splitting by kind makes per-file staleness meaningful, which is what makes the
gates usable. (This is the modification to BMAD's single-file spine noted in COMPETITIVE_ANALYSIS.md
§2.3.)

**Rationale for a flat file per kind rather than a file per claim.** A file per claim is 200 tiny files
and an unreadable `git log`. A file per kind reads top-to-bottom as a document, and claims are still
individually addressable by ID.

### 2.2 Kind reference

| Kind | Prefix | Answers | Default `truth-source` | Mechanisable? |
|---|---|---|---|---|
| `architecture` | `ARC-` | What structure must be respected? Dependency direction, layering, allowed coupling, cycle prohibition, "only X may talk to Y" | `decision` | **Usually yes** — dependency-cruiser / ArchUnit / Tach / Deptrac rule |
| `component` | `CMP-` | What are the named parts, what is each responsible for, what are its boundaries? | `decision` | Partly — path globs are checkable, responsibility is not |
| `concept` | `CON-` | What does this domain word mean here, and what is it *not*? | `decision` | No |
| `invariant` | `INV-` | What property must always hold? | `tests` | **Yes** — a named test |
| `interface` | `API-` | What is the external contract and its compatibility policy? | `spec` or `code` | **Yes** — contract file + `oasdiff` severity gate |
| `datum` | `DAT-` | What does the data model mean, what is the identity/ownership rule, what migration policy applies? | `code` (schema) or `decision` | Partly — schema snapshot diff, migration presence |
| `workflow` | `FLW-` | What is the end-to-end sequence, and what must not be reordered or skipped? | `code` | Rarely — sometimes an integration test |
| `constraint` | `CST-` | What is imposed from outside the repository? Compliance, SLA, contractual, licence, platform | `decision` | Sometimes — a check or a policy scan |
| `strategy` | `STR-` | What *must* be tested how / deployed how / secured how? (policy, not current practice) | `decision` | Sometimes — coverage thresholds, required CI job |
| `pitfall` | `PIT-` | What do agents and humans keep getting wrong here? | observed evidence (`decision`) | Sometimes — the best outcome is converting it into a lint rule and retiring the claim |

**Mandatory at baseline:** `architecture.md`, `components.md`, `domain.md`, `pitfalls.md`,
`decisions/`. The rest are created when the project actually has that surface — an internal library has
no `interfaces.md`, and generating an empty one is noise.

**Highest value per line, in my judgement:** `PIT-` and `CON-`. A pitfall is knowledge that was *paid
for* by a failure and cannot be derived from anything. A concept prevents an entire class of wrong code
by fixing vocabulary. Both are cheap, both are invisible to any static analysis, and both are what
AI-generated documentation never contains.

**Lowest value per line:** anything restating structure. `components.md` is the file most likely to
degenerate into a directory listing, and its validation should be hostile to that (§7.3).

### 2.3 The derived tier

`docs/system/derived/*.json` is generated by `forge sync`, is machine-owned, and carries provenance:

```json
{
  "$schema": "forge/derived/v1",
  "generated_from_commit": "a1b2c3d4e5f6",
  "generator": "forge sync derived",
  "tool": "dependency-cruiser@16.3.3",
  "data": { }
}
```

> **Revised by implementation, 2026-09-10.** This envelope originally carried a `generated_at`
> timestamp. It cannot: a timestamp makes every regeneration produce different bytes, so "regeneration
> is a no-op" and "a hand-edited derived file is an error" — both stated below — could never hold at
> once. The commit id is the provenance that matters, and it is what the staleness signal compares.

Rules:

- **Never hand-edited.** A hand edit is detected because regenerating produces a different file; `forge
  check` fails on a dirty derived file.
- **Never cited as authority in a claim's prose.** Claims cite anchors and evidence; derived data is for
  *the agent's reading* and for computing impact.
- **Committed, not gitignored.** Committing them makes their diffs visible in review, which is how you
  notice that the API surface changed. This is a deliberate trade of repo noise for reviewability.
- **Staleness is "regenerating changes the content"**, never a time threshold (GSD's `intel` used 24
  hours; it was wrong and their own later work replaced it). `commits_behind` is still reported, as
  provenance beside the verdict rather than as the verdict.

  > *Revised by implementation, 2026-09-11: this rule originally read "staleness is
  > `generated_from_commit != HEAD`", and that comparison can never come out clean for a file that is
  > itself committed. Writing the artifact stamps HEAD; committing it moves HEAD past that stamp; the
  > file is therefore reported stale the instant it became correct, and regenerating produces another
  > such commit. The first attempt at a fix — ignore commits that touched only the derived tier — was
  > not enough, because committing four new JSON files also changes the file census they contain.*
  >
  > *The honest split is that **content is the truth and the stamp is provenance**. A regeneration
  > that produces the same data leaves the file alone, keeping the id of the commit it was genuinely
  > derived from, which is more honest than restamping it with a commit whose contents it was never
  > shown. Two consequences worth stating: the derived tier excludes itself from its own file counts
  > (a census that counts its own output is not stable under its own commit), and a body-only edit
  > does not make the tier stale — the tier is a census, and whether that edit invalidated a claim is
  > `forge drift`'s question.*

Contents, in order of value:

| File | Content | Produced by |
|---|---|---|
| `inventory.json` | tracked files by language, LOC, entry points, test files, config files, stack + pinned versions read from lockfiles | git + globs + lockfile parse |
| `deps.json` | module→module import edges, cycles, per-component fan-in/fan-out | ecosystem tool (dependency-cruiser / tach / go list / cargo tree …) |
| `api-surface.json` | exported symbols with signatures per public module; HTTP routes if discoverable | tree-sitter / ecosystem tool |
| `tests.json` | test file → test name list, plus the requirement/claim IDs each test declares (§8.2) | test runner `--list` or grep |
| `trace.json` | the traceability index (§8) | computed from the other files + claim/change parsing |
| `drift.json` | current anchor-staleness and rule-conformance results | `forge drift` |

### 2.4 The candidates tier

Bootstrap and investigation write here (`docs/system/candidates/`). The distinction is enforced, not
stylistic:

- A candidate claim has `status: proposed` and a `confidence` field.
- The agent **may read** candidates and **must not cite** them as established. When a phase output relies
  on a candidate, it must say so explicitly and treat it as an assumption.
- `forge check` fails if any ratified claim's `governs` or `since` points into candidates.
- Ratification is a human action (`forge ratify <ID>`) that moves the claim into its kind's file, strips
  `confidence`, sets `reviewed`, and stamps anchors with the current SHA.

This tier is the answer to the bootstrap problem's honest core: an LLM reading an unfamiliar codebase
produces plausible claims, and plausible-but-wrong knowledge is worse than none. Candidates make
"plausible" a first-class state instead of laundering it into truth.

---

## 3. Truth sources and precedence

### 3.1 Per-fact authority table

There is no global source of truth. Each *kind of question* has an authority, and this table is the
harness's constitution for contradiction handling.

| Question | Authority | Who may change it |
|---|---|---|
| What does the system do right now? | the code, plus the tests that currently pass | any change |
| What must the system do (externally observable)? | permanent capability specs | a change with a spec delta |
| What property must always hold? | the `INV-` claim, discharged by a named test | a change with `impact.md` naming the claim |
| What structure must be respected? | the `ARC-` claim, enforced by a rule file | a change with an ADR |
| What is the external contract? | the contract artifact (OpenAPI/proto/schema), generated from or generating code | a change with a contract diff below the severity gate, or an ADR above it |
| Why is it like this? | the ADR | a new ADR (never an edit to a decided one; supersede instead) |
| What is currently true about the repo's shape, stack, surface? | `derived/` | `forge sync` only |
| What do we keep getting wrong? | `PIT-` claims | anyone, on observed evidence |

### 3.2 What a "contradiction" actually is

A contradiction is only meaningful **between a claim and its own declared authority**. This is the point
the brief's §3 example needs sharpened:

> `architecture.md` says `Payment Service → PostgreSQL`, the code now does `Payment Service → Redis`.

That is not two peers disagreeing. It resolves into exactly one of four situations, and the harness's job
is to *refuse to guess which*:

| Verdict | What it means | Required resolution |
|---|---|---|
| **V1 — code is wrong** | The claim is still policy; the implementation violated it | Fix the code. Claim untouched. If the claim was `asserted`, promote it to `enforced` by adding a rule so this cannot recur |
| **V2 — claim was never true** | The claim was wrong at authoring (bootstrap noise, or a mistake) | Correct the claim. **No ADR** — nothing was decided, something was mis-recorded. Record the evidence in the drift ledger |
| **V3 — the decision changed** | Someone deliberately moved to Redis | **Requires an ADR** that supersedes the prior decision, plus a claim update, plus a rule update. The ADR is the artifact that makes this legitimate |
| **V4 — the claim is under-specified** | Both PostgreSQL and Redis are compatible with the real intent; the claim was too concrete | Refine the claim to state the actual constraint (e.g. "the payment ledger must be durable and transactional") and add the real rule |

**The harness never picks.** It detects, classifies as far as evidence allows, proposes a verdict with
reasoning, and blocks until a human records one. This is the direct consequence of arXiv:2604.03447: the
model's judgement here is systematically weakest and its confidence is uninformative.

**Auto-reconciliation is forbidden by construction**, not by convention: `forge` has no command that
rewrites a claim from code. GSD's `drift_action: auto-remap` is exactly the behaviour we exclude.

### 3.3 The one asymmetry we do allow

`derived/` may be regenerated from code freely and without ceremony, because it makes no normative
claims. This is deliberate: it gives the "just make the docs match the code" impulse a legitimate outlet
that cannot destroy a decision.

---

## 4. Making claims mechanically checkable

This section is the difference between this design and everything in the corpus.

### 4.1 `status: enforced` requires named evidence

A claim may only carry `status: enforced` if its `evidence` names at least one artifact that fails when
the claim is violated, and the kernel verifies that artifact exists and passes. Evidence entry forms:

```yaml
evidence:
  - test: tests/payments/refund.spec.ts::refund cannot exceed capture
  - rule: .forge/rules/deps.cjs#no-domain-to-web
  - contract: contracts/payments.openapi.yaml
  - check: scripts/checks/no-raw-db-client.sh
```

| Form | Verified by the kernel as | Typical kind |
|---|---|---|
| `test:` | that test exists in `derived/tests.json` **and** passed in the last verification run | `INV-`, `FLW-`, `DAT-` |
| `rule:` | that rule id exists in the named rule file **and** the rule tool exits 0 | `ARC-`, `CMP-` |
| `contract:` | that contract file exists **and** `oasdiff` (or equivalent) against the regenerated contract is within the declared severity | `API-` |
| `check:` | that script exists **and** exits 0 | `CST-`, `STR-`, `PIT-` |

### 4.2 Compiling architecture claims into rules

For `ARC-` claims, the `Rule` prose maps to the ecosystem's own conformance tool. The harness does not
implement conformance checking; it maintains the config and binds it to the claim.

```markdown
### ARC-3 — The domain layer must not depend on transport or persistence

```claim
kind: architecture
status: enforced
truth-source: decision
anchors:
  - src/domain/@a1b2c3d
evidence:
  - rule: .forge/rules/deps.cjs#domain-no-outbound
governs: [CMP-domain, CMP-web, CMP-repos]
since: ADR-0002
reviewed: 2026-09-10
```

Prevents: a domain rule becoming untestable because instantiating it requires a database or an HTTP
request. Enforced for `src/domain/**` only; `src/app/**` is the composition layer and is exempt.
```

and in `.forge/rules/deps.cjs`:

```js
{
  name: 'domain-no-outbound',           // <- the id ARC-3 binds to
  comment: 'forge:ARC-3',               // <- back-reference, greppable
  severity: 'error',
  from: { path: '^src/domain/' },
  to:   { path: '^src/(web|repos|infra)/' }
}
```

The bidirectional binding (`evidence: rule:` forward, `comment: forge:ARC-3` back) is checked by
`forge check`: a rule tagged `forge:ARC-3` where `ARC-3` does not exist is an error, and an `ARC-` claim
marked `enforced` whose rule id is missing is an error. **This is how "architectural drift" stops being
an AI problem for the claims that matter most.**

### 4.3 The `enforced` / `asserted` ratio is a reported metric

`forge status` prints, per kind, how many claims are `enforced` versus `asserted`. Un-mechanised claims
are legitimate — most `CON-` and many `CMP-` claims cannot be mechanised — but the ratio must be
*visible* rather than implied. A project whose architecture claims are 100% `asserted` has no
architectural conformance, and should know it.

**Recommended baseline targets** (project-configurable, not enforced by the kernel):
`INV-` ≥ 80% enforced, `ARC-` ≥ 60% enforced, `API-` 100% enforced where a contract exists. Everything
else: no target.

---

## 5. Detecting stale knowledge

### 5.1 The anchor primitive

Adopted from Fiberplane's `drift` linter (RESEARCH.md §9.1). An anchor is:

```
path[#Symbol][@sha]
src/payments/refund.ts#computeRefundable@a1b2c3d
src/domain/@a1b2c3d                              # directory anchor: the tree hash
```

`forge drift` for each anchor:

1. Resolve the baseline: the anchor's `@sha`; if absent, the commit that last touched the claim's file.
2. Extract the anchored unit at the baseline (`git show <sha>:<path>`, then narrow to `#Symbol`).
3. Extract the same unit at `HEAD`.
4. Compare **normalised AST fingerprints**: parse with tree-sitter, hash the sequence of
   `(node_kind, token_text)` with whitespace, comments and positions dropped. Languages without a
   tree-sitter grammar available fall back to a whitespace-normalised content hash, and the claim is
   reported as `coarse: true` so the weaker signal is visible.
5. Classify:

| Status | Meaning |
|---|---|
| `fresh` | fingerprint unchanged since baseline |
| `shifted` | the symbol's **body** changed, its signature did not → a weaker signal |
| `stale` | the signature changed, or a non-symbol anchor changed → the claim is **unverified**, not wrong |
| `missing` | anchor path or symbol no longer exists → **blocking**; a claim about code that is gone is either retired or re-anchored |

Plus two flags that travel with the status rather than replacing it: `coarse` (no grammar for this
file, so the comparison is line-based and weaker) and `symbol_unresolved` (the declaration table could
not locate the symbol, so the whole file was compared instead).

> **Revised by measurement, 2026-09-10.** This table originally listed four statuses with `coarse` as
> the fourth. Implementing M1 changed it twice. `coarse` became a flag because a coarse comparison still
> yields a verdict, and folding it into the status would throw that verdict away. `shifted` was added
> because the measurement showed body-only changes are 79% of all non-fresh verdicts (176 of 222 over
> 600 commits) — surfacing them by default would have quadrupled the ledger. See
> [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md).

**What this buys, precisely:** for every claim, a deterministic, format-insensitive answer to "has the
code this claim describes changed since a human last confirmed the claim?" That is not "is the claim
true", and pretending otherwise is where every other tool goes wrong. It is, however, the exact set of
claims a reviewer needs to look at — and it is computed with git and tree-sitter, no model call, in
seconds.

**Known weakness (also Fiberplane's, and our biggest implementation risk).** A rename or a file move
marks every anchor on that symbol stale. Mitigations, in order: use `git log --follow` / rename detection
when resolving the baseline; prefer `#Symbol` anchors over line-based ones (already the design); allow
`forge reanchor <ID>` to restamp an anchor *only* when the fingerprint is unchanged after applying git's
rename mapping — i.e. re-anchoring is free when nothing semantic changed and impossible when something
did. See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q3.

### 5.2 Three additional staleness signals, all deterministic

| Signal | Computation | Severity | Borrowed from |
|---|---|---|---|
| **Derived-tier staleness** | regenerating changes the content; report `commits_behind` as provenance (§2.3, revised) | warn; block at `verify` | GSD `built_at_commit` |
| **Premise staleness** | a change artifact's last-commit time predates the newest commit touching any claim it cites | warn at `plan`, block at `implement` | GSD context-drift gate |
| **Review debt** | `reviewed` older than N commits touching the claim's anchors (default N=50), or older than 12 months | warn only, never blocking | BMAD provenance line |
| **Referent deletion** | `git log --diff-filter=DR --name-only <sha>..HEAD` intersected with anchor paths | block (same as `missing`) | BMAD refresh procedure |

Review debt is deliberately non-blocking. A blocking review-debt gate trains you to click through it,
which destroys the value of every other gate.

### 5.3 Structural drift: knowledge that should exist and does not

The signals above find claims that *are* stale. The opposite gap — the system grew something no claim
describes — needs GSD's structural detector, generalised and made precise by our derived tier:

For each newly added source file in the diff, compute its component by matching `CMP-` claims' path
globs. If it matches none, it is **unmapped**. Report unmapped files grouped by directory, plus new
route modules, new migrations, and new public exports absent from `api-surface.json`. Threshold-based
(default 3), non-blocking, and — unlike GSD — it never auto-remaps: it emits a proposal.

This is strictly better than GSD's `structureMd.includes(prefix)` because `CMP-` claims carry explicit
path globs instead of prose that might happen to mention a directory name.

---

## 6. The drift ledger and the verdict protocol

`docs/system/DRIFT.md` is the open ledger. Machine-appended, human-resolved.

```markdown
## D-014 — INV-7 unverified
```drift
claim: INV-7
detected: 2026-09-10
detected_by: forge drift
signal: stale
anchors_changed:
  - src/payments/refund.ts#computeRefundable  (a1b2c3d -> f7e8d9a)
diff_summary: "computeRefundable now consults a Redis cache before the ledger"
proposed_verdict: V3
proposed_reasoning: |
  The change introduces a cache read on the path the invariant constrains. The
  invariant's discharging test still passes, so the property appears preserved,
  but ARC-3's rule now reports a new dependency edge from domain to infra.
status: open
```
```

Resolution is `forge drift resolve D-014 --verdict V3 --adr 0021` (or `--verdict V1`, `--verdict V2
--evidence <note>`, `--verdict V4`). The kernel enforces the consequences:

| Verdict | Kernel enforces |
|---|---|
| V1 code is wrong | Ledger entry stays open until the anchor fingerprint returns to matching, or a change fixes the code. Claim untouched. Prompts to add a rule if `status: asserted` |
| V2 claim never true | Claim may be edited **without** an ADR. Requires a non-empty `--evidence` note, recorded in the ledger. Anchors restamped |
| V3 decision changed | **Requires** an existing ADR id whose `supersedes` names the prior decision. Claim edit permitted, `since:` updated, anchors restamped. Refuses if the ADR does not exist |
| V4 under-specified | Claim edit permitted; requires that the new claim's `status` be `enforced` with new evidence, or an explicit `--accept-asserted` flag recorded in the ledger |

Every resolution is a commit that touches the ledger and the claim together, so the reasoning and the
edit are one reviewable unit.

**Waivers.** `forge drift waive D-014 --until <sha|date> --reason "<text>"` exists because the
alternative is a permanently red gate that gets disabled. A waiver is recorded, expires, and is listed by
`forge status`. This is OpenSpec's `skip_specs: true` pattern: make the bypass explicit, named, and
committed.

> **Added when the ledger was built, 2026-09-11: `forge drift confirm <id>`.** The four verdicts are a
> closed grammar about what a drift *means*, and all four say something is wrong somewhere. The very
> first entry this ledger ever opened — on this repository, unplanned — was none of them: a whole-file
> anchor on `src/forge/impact.py` went stale because an unrelated edit touched the file, while the rule
> the claim states was never touched and still held. With only V1–V4 available the honest options were
> to file a false V1 or to leave the entry open forever, and both end with the ledger being ignored.
>
> This will be the *commonest* signal, not an edge case: a file-level anchor goes stale on every edit to
> its file. `confirm` records that a human read the drift and the claim still holds, then restamps the
> anchor's `@sha` and `reviewed:` — **and touches no prose**. That is not the auto-reconciliation this
> design refuses: nothing is made to agree with the code, and it happens only when somebody names an
> entry and asks. Restamping *is* what `@sha` means — the commit at which a human last confirmed the
> claim — so recording a confirmation without moving it would be the dishonest option.
>
> It is deliberately not a fifth verdict. Adding it to `VERDICTS` would make "nothing is wrong" one of
> the answers to "what is wrong", and the closed set is worth more than the symmetry.

---

## 7. Validation: what the kernel checks

All of the following are deterministic scripts. None calls a model.

### 7.1 Structural (per file, per claim)

1. Claim ID matches `^(ARC|CMP|CON|INV|API|DAT|FLW|CST|STR|PIT)-(\d+|[a-z0-9][a-z0-9-]*)$` —
    a number or a kebab slug. *Revised by implementation, 2026-09-10: this rule originally said
    digits only, while every example in this document used slugs (`CMP-payments`, `CON-capture`,
    `API-post-refunds`). Slugs win because `grep -r CMP-payments` explains itself. What is
    enforced is **stability**, not numerality — the token is permanent, so a component renamed
    from payments to billing keeps `CMP-payments` and changes only its title.*
2. IDs unique across the whole store; never reused (checked against `git log -S` for the ID in
   retired claims). Numeric IDs additionally ascend within a file; slugs have no ordering, so
   the ascending check applies only to the numeric form.
3. Every claim has a well-formed `claim` fence, and every required field is present and in the allowed
   value set.
4. `anchors` non-empty unless `kind` ∈ {`constraint`, `concept`}.
5. `status: enforced` ⇒ `evidence` non-empty and every entry resolves.
6. `kind: architecture` ⇒ `since` present and the ADR file exists.
7. `governs` targets exist, are not self-referential, and the graph is acyclic.
8. `supersedes` targets exist and are `status: retired`.
9. No placeholders anywhere: `TBD`, `TODO`, `FIXME`, `XXX`, `{template-token}`, `[NEEDS CLARIFICATION`,
   `similar to <ID>`. Code fences blanked before scanning (BMAD's `lint_spine.py` technique) so examples
   do not false-positive while line numbers stay correct.
10. No `confidence` field outside `candidates/`; every claim in `candidates/` has `status: proposed`.
11. Prose body non-empty and at least ~2 lines — a claim with a heading and no explanation is a label,
    not knowledge.

### 7.2 Cross-artifact

12. Every `forge:<ID>` back-reference in a rule/test/code comment names an existing, non-retired claim.
13. Every `evidence: test:` entry appears in `derived/tests.json`.
14. Every `evidence: rule:` id appears in the named rule file.
15. Every permanent spec requirement `REQ-*` is discharged by ≥1 test (§8.2).
16. No ratified claim references anything in `candidates/`.
17. `derived/` is clean: regeneration is a no-op. *Revised by implementation, 2026-09-11: this
    originally also required `generated_from_commit == HEAD` at `verify` time, which no committed
    file can ever satisfy — see §2.3.*
18. Always-loaded budget: `OVERVIEW.md` + the mandatory claim files ≤ the configured line budget
    (default 400). Over budget is an **error**, and the only fixes are cutting or relocating.

### 7.3 Anti-noise checks (the interesting ones)

These exist specifically to stop the store degenerating into AI-generated restatement of the code. Each
is a heuristic and each is a *warning* with an explicit acknowledgement path — a hard error here would be
too brittle:

19. **Derivable-claim smell.** A claim whose prose is >60% composed of identifiers that appear in its own
    anchors, and which contains no modal (`must`, `never`, `always`, `may not`), is flagged: it probably
    restates the code. Acknowledge with `# forge:not-derivable <reason>` on the claim.
20. **Directory-listing smell.** A `CMP-` claim whose prose contains a path glob and fewer than ~15 words
    of explanation is flagged. A component claim must say what the component is *responsible for*, which
    is the part `ls` cannot tell you.
21. **Stack-fact smell.** Any claim prose containing a version pattern (`\d+\.\d+`) alongside a package
    name is flagged: versions live in lockfiles, and `derived/inventory.json` reports them. (BMAD's
    "`Stack` is a seed; the code owns this once it exists.")
22. **Orphan claim.** A claim with no inbound `governs`, no `forge:<ID>` back-reference anywhere, and
    never cited by any change's `impact.md` in the last N changes (default 20) is flagged for review.
    **Not for deletion** — see §10 — but a claim nothing ever consults is either badly placed or
    genuinely dead, and both deserve a look.

---

## 8. Traceability without a database

### 8.1 The mechanism: ID conventions + grep + a generated index

`derived/trace.json` is a build artifact, never a source of truth. It is recomputed from four
deterministic scans:

| Scan | Yields |
|---|---|
| Claim files | claim IDs, `governs`, `since`, `anchors`, `evidence` |
| ADR files | ADR ids, `supersedes`, the claim IDs they reference |
| `changes/**` (active + archive) | change ids, `REQ-*` deltas, task ids, the claim IDs cited in `impact.md` |
| Code and tests | `forge:<ID>` comment back-references; test names; `@covers REQ-*` / `@covers INV-*` annotations |

The whole index is a few hundred lines of scanning code. There is no schema migration, no server, and no
state that can disagree with the repository, because it is regenerated from the repository.

### 8.2 The one convention that makes it work: `@covers`

A test declares what it discharges, in the test name or an adjacent comment:

```ts
// @covers INV-7 REQ-refunds-3
it('rejects a refund exceeding the remaining captured balance', () => { … })
```

```python
def test_refund_cannot_exceed_capture():  # @covers INV-7 REQ-refunds-3
    ...
```

`forge sync tests` extracts these into `derived/tests.json`. This single convention makes the following
deterministic and answers most of the brief's §11:

| Question | Answer |
|---|---|
| Which requirement caused this code? | `grep -r "forge:REQ-refunds-3"`, plus `trace.json` reverse map |
| Which task implements this requirement? | `tasks.md` task lines carry `[REQ-refunds-3]` tags; `trace.json` maps them |
| Which tests verify this requirement? | `@covers` reverse map |
| Which architecture component does this task affect? | task file paths ∩ `CMP-` path globs |
| Which invariants are affected? | changed files ∩ claim anchors (the "claim-touch set", §9.2) |
| Which ADR explains this decision? | claim `since:` → ADR, and ADR `supersedes` chain |
| Which documentation must change because of this implementation? | **the claim-touch set minus what `impact.md` already accounts for** — see §9.2 |

### 8.3 What is deliberately *not* traceable

Individual lines of code to requirements. Requiring `forge:REQ-*` comments on implementation code is
achievable but the discipline decays, and decayed traceability is worse than absent traceability because
it reads as complete. We trace at the granularity of **file ↔ claim** (via anchors and component globs)
and **test ↔ requirement/invariant** (via `@covers`), and we accept that "which line implements FR-3" is
unanswerable. That trade is deliberate; see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q5.

---

## 9. Update mechanism: how knowledge changes

### 9.1 Two, and only two, legitimate paths

```
                    ┌──────────────────────────────────────────┐
  a change lands →  │ forge sync  (archive fold + re-anchor)   │ → knowledge updated
                    └──────────────────────────────────────────┘
                    ┌──────────────────────────────────────────┐
  drift detected →  │ forge drift resolve --verdict …          │ → knowledge updated
                    └──────────────────────────────────────────┘
```

There is no third path. In particular there is no "update the docs" command, and no phase in which an
agent is asked to bring documentation in line with the code. That absence is a feature.

### 9.2 The claim-touch rule — the core enforcement

This is the mechanism that makes "which documentation must change?" computable, and it is the piece I
found nowhere in the corpus.

For a change with diff `D`:

```
claim_touch_set(D) = { claim | any anchor of claim resolves to a file in D }
                   ∪ { claim | any CMP- path glob of claim matches a file in D }
                   ∪ { claim | any evidence artifact of claim is in D }
```

`impact.md` must account for **every** member of that set, under exactly one heading:

```markdown
## Claims touched

### Unaffected
- CMP-payments — new file lands inside the existing component boundary; responsibility unchanged
- CON-capture — vocabulary unchanged

### Updated
- INV-7 — bound now accumulates across partial refunds (was per-refund)

### Superseded
- ARC-3 → ADR-0021 — domain may now read the projection cache; ARC-3 replaced by ARC-9
```

`forge check` computes the set and **blocks** if any member is unaccounted for. It also blocks if a claim
file was edited in the diff but the claim does not appear under `Updated` or `Superseded`, and if a claim
appears under `Superseded` without an existing ADR.

> **Corrected while running the first real change through the lifecycle (2026-09-11).** Two errors, both
> in the sentence above, and both of which made the rule unusable rather than merely strict.
>
> 1. **"a claim *file* was edited" is the wrong granularity.** Claims share files by design — the whole
>    store is five or six markdown files. Appending one new claim to `pitfalls.md` marked all three
>    existing claims in it as having had their definitions edited, and the rule then demanded each be
>    re-filed as `Updated`. The only ways through were to write `Updated` about claims nobody updated, or
>    to split every claim into its own file. That is exactly the rubber-stamping
>    [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q3 asks about, arriving by the front door on the first change
>    anyone made. The test is now whether the diff's changed line ranges intersect the claim's own
>    `[line, end_line]` — information the parser has recorded since M0 for precisely this purpose.
> 2. **`New` was missing from the permitted headings.** A claim the change introduces has, trivially, had
>    its definition edited, so demanding `Updated` or `Superseded` rejected every change that records a
>    new piece of knowledge — the single most common thing a change should do, and the reason the store
>    exists. `New` now counts, which is what [WORKFLOW.md](WORKFLOW.md) §3.4's own worked example always
>    assumed.
>
> **Corrected again on `requests`, 2026-09-11.** The definition above says `D` and means it, and the
> implementation had been matching anchors against the **blast radius** — the diff *plus every file that
> imports it*. Measured on `requests` (35 modules, 88 import edges, 20 cycles), a one-line type-annotation
> change to `models.py` put 10 claims out of 10 into the touch set; eight were anchored to files the diff
> never opened. `impact.md` then carried nine honest `Unaffected` sentences about code the change could
> not have reached.
>
> The two sets answer different questions and are not interchangeable. The **blast radius** answers *what
> might this affect?* and is a reading aid, so a wide answer costs a reader some time. The **touch set**
> answers *what must you account for?* and is an obligation, so a wide answer costs every change a page of
> sentences — and an obligation that always fires is one people learn to discharge without reading. Claims
> reached only through the import graph are now reported separately, under a heading that says no account
> is owed. See [docs/measurements/run2-requests-lifecycle.md](docs/measurements/run2-requests-lifecycle.md).
>
> **Third correction, the same day: "resolves to a file in `D`" is the wrong granularity too.** Narrowing
> to the diff took that change from 10 claims to 5, and the five that remained were all anchored to
> *symbols* in `models.py` — `#PreparedRequest`, `#Response.next`, `#Response.iter_content` — while the
> diff had touched only `Response.content`. An anchor that names a symbol is a claim about that symbol,
> and matching it against the file taxes it for every edit to every neighbour.
>
> The rule is now: a symbol anchor is touched when the diff's hunks intersect the symbol's own line span,
> found with the same `find_symbol` the drift engine has used since M1. A **file** anchor is still touched
> by any edit to its file, because a claim that points at a whole file is making a claim about the whole
> file. Every way of *not knowing* — no grammar installed, a declaration form the table does not cover, a
> symbol renamed away, a file gone from the working tree — falls back to the file, because over-reporting
> costs a sentence and under-reporting costs a claim nobody re-read.
>
> Measured on the same change, third time: **10 → 5 → 1**, and the one is the only claim that describes
> `Response.content`. The nine now appear under `Nearby`, which is the point: they are not hidden, they
> are just not owed a sentence.

Consequences worth stating plainly:

- The agent cannot quietly change behaviour that an invariant constrains, because the invariant is in the
  touch set and demands a sentence.
- The agent cannot quietly edit a claim, because editing it puts it in the touch set *and* requires a
  heading.
- "Unaffected" is cheap but not free: it costs one honest sentence per claim, which is the right price.
  This is also the pressure that keeps the claim count low — every claim taxes every change that touches
  its files. **A store of 40 good claims is far more valuable than 400, and this rule is what makes that
  economically true rather than merely advisable.**

### 9.3 `forge sync` at archive time

When a change is archived, `forge sync` performs, in order, refusing on the first failure:

1. **Fold spec deltas** into permanent capability specs — OpenSpec's deterministic
   ADDED/MODIFIED/REMOVED/RENAMED merge, with pre-write validation of the rebuilt spec.
2. **Apply declared claim edits** from `impact.md`: `Updated` claims are already edited in the working
   tree (the change authored them); `sync` verifies each has a matching `impact.md` entry and, for
   architecture/interface-breaking kinds, an ADR.
3. **Re-anchor**: for every claim in the touch set, restamp `@sha` to the merge commit. This is the
   moment "verified as of" advances, and it advances *only* because a human accounted for the claim.
4. **Regenerate `derived/`** and rebuild `trace.json`.
5. **Re-run `forge drift`**; any newly detected drift is appended to `DRIFT.md` as open.
6. **Refuse** if: any `REQ-*` in the change has no passing `@covers` test; any claim-touch member is
   unaccounted for; `DEBT.md` has open entries without waivers; a claim edit lacks its required ADR.

Step 3 is the crux. In every other system, "verified as of" either does not exist or is stamped by a
regeneration job — which means it certifies nothing. Here it can only advance through a human-accounted
change or a human-recorded drift verdict.

### 9.4 Who writes what

| Artifact | Writer | Hand-editable? |
|---|---|---|
| `OVERVIEW.md`, claim files, ADRs | human, or agent-with-approval | Yes — this is normal reviewed authoring |
| `derived/**` | `forge sync` only | **No** — checked |
| `DRIFT.md` | `forge drift` appends; `forge drift resolve` closes | Only through the commands |
| `candidates/**` | bootstrap / investigation phases | Yes |
| `trace.json` | `forge sync` | **No** |

**Note on the rejected alternative.** BMAD's append-only `.memlog.md` + derived artifact is elegant and I
seriously considered it (RESEARCH.md §5.2). Rejected for the MVP: it doubles the artifact count, makes
`git blame` on the readable document useless, and the merge-drift problem it solves is a multi-writer
problem we do not have with one developer and one agent. The ADR chain (`supersedes`) already gives us
provenance for decisions, which is the part that actually needed it. Revisit if multi-writer becomes real
— [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q6.

---

## 10. Preventing noise, and preventing over-pruning

Both failure directions are real. AI-generated docs bloat; AI-driven cleanups gut. The countermeasures
are asymmetric on purpose.

### 10.1 Against bloat

| Mechanism | Effect |
|---|---|
| **Admission criterion** — store only what cannot be read off compliant code | The single highest-leverage rule. Applied at authoring and at review |
| **Anchor requirement** | An unanchored claim cannot be written (except `CST-`/`CON-`), so vague claims have nowhere to live |
| **Always-loaded line budget, never raised** | Forces prioritisation; over-budget is an error with only two legal fixes |
| **The claim-touch tax** (§9.2) | Every claim costs a sentence on every change that touches its files. Low-value claims become visibly expensive |
| **Anti-noise linters** (§7.3) | Catch the four specific shapes AI-generated docs take |
| **Claim cap during bootstrap** (default 40) | Prevents day-one flooding; see [WORKFLOW.md](WORKFLOW.md) bootstrap phase |
| **Prefer a check over a prose rule** | BMAD's rule: if a lint rule can enforce it, the claim becomes evidence-bearing or disappears |

### 10.2 Against over-pruning

Adopted essentially verbatim from BMAD's `project-context`, because it is the best-argued policy in the
corpus. A claim may be **deleted or retired** only on one of four grounds:

1. **Stale or incorrect** — the referent is gone, or it was never true. The evidence is named.
2. **Mechanically enforced** — a check now fails the violation the claim names. (A tool that merely
   covers the same topic does not count.) The claim is retired *and* the check is recorded.
3. **Harmful or contradictory** — it points at the wrong thing, or it contradicts a live claim and loses
   the reconciliation.
4. **The human approved this specific deletion**, asked as a line item.

And explicitly **not** grounds: brevity; nothing has failed lately; "the agent could derive it"; and — the
one that empties good files — "it is discoverable somewhere in the repository".

`forge retire <ID> --ground <1-4> --evidence <text>` records the ground in the claim (`status: retired`,
plus `retired-ground` and `retired-evidence` — *added by implementation, 2026-09-11: this said "records
the ground in the claim" without saying where, and S18 needs a field to read*) and in the commit. Grounds 1–3 the agent may carry itself; ground 4 requires the human. Retired claims
stay in the file, excluded from checks and budgets, so the history of what we used to believe is not
lost.

### 10.3 The review protocol for knowledge writes

Adopted from OpenHands: before writing to the store, the agent **lists the exact claims it proposes to
add or change, with their kind and prose, and writes only what is approved.** Not a summary of intent —
the literal text. One interaction, and it is the difference between a curated store and an accreted one.

---

## 11. Worked example: the brief's refund scenario

**Repository state.** `docs/system/` holds 31 claims, among them `CMP-payments`, `CMP-orders`,
`CON-capture`, `INV-7` (refund ≤ capture), `ARC-3` (domain must not depend on transport or persistence),
`API-post-refunds` absent (no refund endpoint yet), `DAT-4` (order/payment identity rule).

**Request.** "Add refund support to orders."

**investigate** reads `derived/inventory.json`, `deps.json`, `api-surface.json`, then greps
`CMP-payments`' and `CMP-orders`' path globs. It reads `CON-capture`, `INV-7`, `DAT-4`, `ARC-3` — four
claims, ~40 lines — instead of a 3,000-line architecture document. Anything it learns that is not
already a claim and is not derivable goes to `candidates/refunds.md` with `status: proposed` and a
confidence.

**spec** produces delta requirements against the `payments` and `orders` capabilities:
`REQ-refunds-1..5`, each with `#### Scenario:` blocks in WHEN/THEN form. `forge check` verifies heading
shape, ≥1 scenario per requirement, and zero `[NEEDS CLARIFICATION]`.

**impact** — the kernel computes the candidate blast radius: files matched by `CMP-payments` /
`CMP-orders` globs, reverse dependencies from `deps.json`, and the claim-touch set. The agent curates it
into `impact.md`:

```
Claims touched
  Unaffected:  CMP-orders, CON-capture, DAT-4
  Updated:     INV-7 (bound accumulates across partial refunds)
  New:         API-post-refunds, INV-12 (a refund is idempotent per idempotency-key)
  At risk:     ARC-3 (the proposed design reads the payment ledger from the domain layer)
```

The `At risk` entry on `ARC-3` is what forces the next step: either the design changes to respect the
rule, or an ADR is required. **This is the harness earning its keep** — the conflict surfaces before any
code exists, because the claim was anchored to `src/domain/` and the design touches it.

**design** (required: the change is track C because it touches an `ARC-` claim and adds a public API)
records the decision to keep the ledger read behind a port, so `ARC-3` survives. No ADR needed. Had the
decision gone the other way, `forge check` would refuse `tasks` until `ADR-0021` existed.

**analyze** — deterministic: every `REQ-refunds-*` has ≥1 task; no task lacks a requirement; no
placeholders; claim-touch set fully accounted; `ARC-3`'s rule still present. LLM review: are
`REQ-refunds-2` and `REQ-refunds-4` distinct? is `INV-12` testable as stated?

**tasks / implement / test** — per-task TDD; each test tagged `@covers REQ-refunds-N` and, for the
invariants, `@covers INV-7` / `@covers INV-12`.

**verify** — build, typecheck, lint, tests; `deps.cjs` conformance (so `ARC-3` is re-proved);
`oasdiff` on the regenerated contract for `API-post-refunds`; every `REQ-refunds-*` has a passing
`@covers` test; `DEBT.md` empty; `forge drift` clean.

**sync / converge** — deltas fold into the permanent specs; `INV-7`'s prose is updated (already authored
in the change, accounted for in `impact.md`); `API-post-refunds` and `INV-12` are added with anchors and
evidence; every touched claim's `@sha` advances to the merge commit; `derived/` and `trace.json`
regenerate; the change is archived.

**Six months later**, someone swaps the ledger for Redis. `forge drift` reports `INV-7` and `ARC-3`
stale with the fingerprint diff; `ARC-3`'s dependency rule *fails*, which is a blocking error, not a
warning. The ledger proposes V3 with reasoning. A human records `--verdict V3 --adr 0034`, or fixes the
code. **The architecture document is never silently rewritten to say Redis.**

---

## 12. Deliberate non-goals

| Not building | Why |
|---|---|
| A knowledge graph | GSD's became a fourth representation with its own rot. Edges we cannot verify are liabilities. `governs` + `trace.json` covers the useful 90% |
| Embeddings / semantic search over the store | 40 claims fit in a grep. Retrieval quality is not the bottleneck; trustworthiness is |
| A code graph / SCIP index | The host agent's search plus tree-sitter plus the ecosystem's dependency tool is enough at personal scale. Revisit only when grep genuinely fails |
| LLM-generated architecture diagrams as knowledge | A diagram is not addressable, not anchored, not checkable. Mermaid inside a claim's prose is fine as illustration; it is never the claim |
| A "docs coverage" percentage | Invites gaming and rewards volume. `enforced`/`asserted` ratio is the honest metric |
| Automatic claim extraction from commits | Produces plausible noise at scale. Candidates + ratification, always |
| Multi-repo / org-wide knowledge | Out of scope for a personal harness. The claim format would extend, the tooling would not |
