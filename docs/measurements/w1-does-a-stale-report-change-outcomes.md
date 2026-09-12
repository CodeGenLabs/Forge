# W1 — Does a stale report change what anybody does? The plan and rubric

> **This document is written and committed before running the measurement**, per
> [HANDOVER.md](../HANDOVER.md) ground rule 3. A measurement whose criteria were chosen
> after seeing the data is not a measurement.

## The Question

R10 and R11 established that:
> A comment, a runtime warning, a changelog line and a conformance test all state their
> knowledge perfectly well, and not one of them knows when the code underneath moved.
> Staleness is the only thing on the list that only this harness does - and it is
> unmeasured.

M1 measured false positives (anchors surviving refactoring). Q1c measured false negatives
(7 of 18 claims break without an anchor moving). W1 asks the remaining half:
**When a stale report fires, does it change an outcome, or is it an administrative ritual?**

---

## Disagreements with the Handover Brief

HANDOVER.md proposed two design directions for W1:
1. *(a) The rubber-stamp rate: could the reader discharge it without reading the claim? If the available action is `forge drift confirm` and a restamp, the report is a ritual.*
2. *(b) Information content of the report: replay M1 commits, collect stale detections, and classify whether the report names commit, author, symbol and candidate verdict.*

I disagree with both framings as stated:

1. **Disagreement with (a): Conflating tool affordance with user behavior.**
   `forge drift confirm` is mechanically available as a CLI subcommand for 100% of drift
   events. If "rubber-stamp rate" is measured by whether `confirm` can be executed without
   the tool forcing a claim read, the answer is trivially 100% across the board.
   Furthermore, an affordance to restamp is *essential* for benign refactors (which M1
   showed constitute 79% of AST changes). The real question is not whether the command
   exists, but whether a maintainer *can* or *does* distinguish benign shifts from
   broken invariants, and whether the report aids that decision.

2. **Disagreement with (b): M1 commits have no claims or maintainers.**
   M1 was an AST stability replay across 600 git commits on repositories (`OpenSpec`,
   `mini-swe-agent`, `oasdiff`) that possessed no forge claim stores. Replaying them
   produces symbol signature diffs, not maintainer interactions with claims. Inspecting
   the format string of `forge reconcile` only measures output schema richness, not
   whether anyone's actions changed.

---

## The Measurement Design

Since behavioral observation requires live teams or interactive agent trials (which W2
covers if funded), a deterministic measurement on existing artifacts must combine two
honest dimensions:

### 1. Census of Real Drift Events in Forge History (n=3)
We inspect every real drift event recorded across the three lifecycles:
- **Event 1 (forge-harness)**: `docs/system/DRIFT.md` entry `D-001` (`PIT-regex-across-newlines`).
- **Event 2 (requests)**: Run 2 drift on `PIT-regex-across-newlines` (`docs/measurements/run2-requests-lifecycle.md`).
- **Event 3 (corvus-db-studio)**: Run 3 simulated drift on `PIT-dev-credentials-must-not-reach-the-image` (`docs/measurements/run3-monorepo-lifecycle.md` and ROADMAP R5).

For each event, we evaluate:
- **Signal**: What did the tool report (drift/reconcile)?
- **Information completeness**: Did the report provide enough context to judge the invariant without opening git log or reading the claim?
- **Action taken**: Was code modified, claim updated (V1-V4), or merely restamped (`confirmed`)?
- **Outcome change**: Did the report prevent a defect or reverse a decision, or did it only impose a restamping step?

### 2. Triage Sufficiency Analysis Across All 18 Ratified Claims
For every ratified claim in the three stores (5 forge, 6 requests, 7 corvus):
If the anchor goes stale:
- Does `forge reconcile` attribution (commit + author + subject) reveal whether the claim's invariant is threatened?
- Classification categories:
  - **Self-Triaging (ST)**: The commit message/diff against the symbol alone makes the verdict obvious without reading claim prose.
  - **Prose-Dependent (PD)**: The reader must read the claim prose to know what invariant was at risk.
  - **Code-Audit Required (CA)**: Neither the report nor the claim prose is sufficient; full call-site analysis is required.

---

## Pre-Declared Null / Negative Condition

- **Negative Condition**: If 100% of real drift events to date (n=3) resulted in `confirm` restamps with 0 code or claim changes, then the staleness mechanism has functioned to date purely as a restamping tax rather than an outcome-altering guardrail.
- **Triage Deficit**: If >50% of claims are **Prose-Dependent** or **Code-Audit Required**, then `forge reconcile` attribution alone does not discharge the report — the user must conduct a manual audit, creating heavy friction that incentivizes rubber-stamping.
