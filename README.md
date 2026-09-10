# forge

A personal software-engineering harness that makes an AI coding agent behave like a disciplined senior
engineer: investigate before modifying, specify before implementing, and — the part nobody has solved —
keep accurate, verifiable knowledge of an existing system.

**Status: design complete; implementation through milestone M2 of six, plus M0.** What exists today is
the anchor engine — the deterministic staleness detector the whole design rests on — the measurement
that gates the rest of the build, the derived tier and traceability index, and the claim store with all
eighteen of its checks. No change lifecycle, no gates, no skills yet.

```bash
pip install -e ".[grammars,dev]"
forge doctor
forge init                      # scaffold .forge/ and docs/system/
forge claim new invariant       # a template; --append writes it to the right file
forge sync derived
forge status
forge drift "src/forge/anchor.py#classify" --baseline <sha>
forge trace INV-7
forge claim show INV-7
forge check                     # --scope store|derived|trace, --json
```

`forge drift` and `forge check` exit 0 when clean, 1 when something needs a look, 2 on a usage error —
so both compose as gates.

## Read in this order

| Document | What it answers |
|---|---|
| [RESEARCH.md](RESEARCH.md) | What the six reference projects actually do, read as source at pinned commits; what the literature says; what nobody has solved. Facts, interpretations and recommendations are marked separately |
| [COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md) | Capability matrix and per-project borrow / reject / modify decisions |
| [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) | **The load-bearing document.** The anchored-claim model: schema, truth sources, staleness detection, drift verdicts, traceability, anti-noise policy |
| [WORKFLOW.md](WORKFLOW.md) | The lifecycle, phase by phase: inputs, outputs, human gates, deterministic checks, LLM checks, exit criteria. Plus tracks and bootstrap |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The harness's own architecture: kernel / skills / artifacts, repository layout, command surface, state and validation models, growth budgets |
| [CONSTITUTION.md](CONSTITUTION.md) | 16 engineering principles, each with the mechanism that detects a violation |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | 15 unresolved questions with options, recommendations, and what evidence is still missing |
| [MVP.md](MVP.md) | Six milestones, 39 deterministic checks, what NOT to build, and the answer to "what would you build from zero today" |

## The short version

Three findings drove the design:

1. **Of the six reference projects, exactly one ships a deterministic check comparing code against a
   stored description of the system** — and it works by substring-matching directory names against
   free-form markdown. Everything else called "consistency analysis", "verification" or "drift
   detection" is a prompt. Prose is not checkable.
2. **LLMs cannot be the drift detector.** Measured: they detect documentation faults at 67–94% but lose
   21–43 percentage points when only the implementation changed — the exact case that matters — and
   their confidence does not separate correct from incorrect judgements
   ([arXiv:2604.03447](https://arxiv.org/abs/2604.03447)).
3. **The projects with the most machinery have the least evidence it helps.** The one with no methodology
   at all (mini-SWE-agent, ~200 lines) posts the only real benchmark numbers.

So the proposal is deliberately small, and its one novel contribution is the **anchored claim**:

```markdown
### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:  [src/payments/refund.ts#computeRefundable@a1b2c3d]
evidence: [test: tests/payments/refund.spec.ts::refund cannot exceed capture]
governs:  [CMP-payments]
since:    ADR-0014
reviewed: 2026-09-10
```

Partial refunds accumulate: the sum of settled refunds is what is bounded, not each refund. An attempt
over the remaining balance is rejected at the domain boundary, not clamped — clamping silently
under-refunds customers.
```

From that one shape follow three mechanisms that do not exist anywhere in the corpus:

- **Deterministic staleness** — tree-sitter AST fingerprints against the anchor's recorded SHA. Not
  "is this true" (unanswerable) but "has the code this describes changed since a human confirmed it".
- **The claim-touch rule** — every change must account for every claim whose anchors intersect its diff,
  as `unaffected` / `updated` / `superseded-by-ADR`. This makes *"which documentation must change?"* a
  set operation rather than a judgement call.
- **A four-verdict drift ledger with no auto-reconciliation path.** The kernel contains no command that
  rewrites a claim to match the code. Drift is classified — code wrong / claim never true / decision
  changed (ADR required) / claim under-specified — and a human records the verdict.

Everything else is borrowed on purpose: OpenSpec's artifact DAG and archive fold, GSD's declarative
gates, Superpowers' scale router and plan format, Spec Kit's requirement vocabulary, mini-SWE-agent's
budgets, BMAD's admission criterion and deletion grounds.

## Implementation status

| Milestone | State | What it is |
|---|---|---|
| **M1 — anchors & drift** | **done** | `gitio`, `fingerprint`, `anchor`; the measurement in [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md) — 0% false positives, 0% false negatives |
| **M2 — derived tier & trace index** | **done** | `derive`, `store`, `trace`; `forge sync derived`, `forge trace`, `forge status`, `forge check` |
| **M0 — claim store & validation** | **done** | `validate`, `scaffold`; all 18 store checks, `forge init`, `forge claim new/show`, `forge check --scope` |
| M3 — change DAG, gates, one workflow | not started | First thing that needs `deps.json`, deferred from M2 |
| M4 — skills | not started | |
| M5 — bootstrap | not started | |

M1 came first because it carried the stop condition: if anchors were too noisy on real history, the
claim schema in M0 would have had to change (coarser anchors, or component-level only). Measuring
before fixing the format was the cheaper order, and it paid — see
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q2 for the risk it retired.

Building M0–M2 corrected six things in the design documents, each recorded where it was wrong: the
drift statuses (`shifted` added, `coarse` demoted to a flag), the derived-tier envelope (a timestamp
that made the dirty check impossible), the ID grammar (slugs, not only digits), the staleness rule
(twice — see below), the retirement fields (the policy said "records the ground in the claim" without
saying where), and the store-check scope. Every correction says in the document why the original was
wrong.

The staleness rule is worth singling out, because the first correction was itself wrong. A derived
file cannot carry the id of the commit that contains it, so comparing that stamp against HEAD reports
the file stale the instant it becomes correct — and regenerating produces another such commit.
Excluding derived-only commits from the count was not enough: committing four new JSON files also
moves the file census inside them. Freshness is now a **content** question — regenerating changes the
data or it does not — and the commit id is reported beside the verdict as provenance, not as the
verdict.
