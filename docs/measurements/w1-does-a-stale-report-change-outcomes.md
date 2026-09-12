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

---

## Results

### 1. Historical Drift Census (n=3)

Every recorded drift event in this project's history was examined:

| Event | Repository | Claim | Cause | Action Taken | Code/Claim Changed? |
|---|---|---|---|---|---|
| **D-001** | `forge-harness` | `PIT-regex-across-newlines` | G14 edit in `impact.py` touched file | Restamped via `confirm` | **No** (0 lines) |
| **Run 2** | `requests` | `PIT-regex-across-newlines` | Lifecycle change touched anchor file | Restamped via `confirm` | **No** (0 lines) |
| **Run 3** | `corvus-db-studio` | `PIT-dev-credentials-must-not-reach-the-image` | Synthetic simulated commit (Bob) | Recorded & confirmed | **No** (0 lines) |

**Tally:**
- Substantive repairs triggered (V1 code bug fix, V2-V4 claim revision): **0 of 3 (0%)**
- Discharged via `confirm` restamp: **3 of 3 (100%)**
- Real regressions prevented: **0**

In every real instance to date, drift was triggered by an anchor being too coarse or by an adjacent refactor. In not a single instance did a stale report catch a regression or cause a maintainer to modify code.

### 2. Triage Sufficiency Across 18 Ratified Claims

For each of the 18 claims across the three repositories, we evaluated whether `forge reconcile`'s attribution (commit SHA, author, subject line) provides enough information to determine if the invariant broke, or whether the maintainer must read the claim prose / inspect code:

| Repository | Claims | Self-Triaging (ST) | Prose-Dependent (PD) | Code-Audit Required (CA) |
|---|---|---|---|---|
| `forge-harness` | 5 | 0 | 5 | 0 |
| `requests` | 6 | 0 | 6 | 0 |
| `corvus-db-studio` | 7 | 0 | 5 | 2 |
| **Total** | **18** | **0 (0%)** | **16 (88.9%)** | **2 (11.1%)** |

**Findings:**
1. **Zero claims are Self-Triaging.** A commit subject line describes the author's intentional goal (e.g. `refactor(session): optimize adapter lookup` or `feat(host): add driver`), never an inadvertent invariant violation.
2. **100% of claims require manual reading.** 88.9% require reading the full claim prose to learn what rule exists; 11.1% require full multi-file audit because the anchor is structural (e.g. Dockerfile stages or seed profiles).
3. **The Rubber-Stamp Incentive is structural.** When an alert requires 5-10 minutes of manual code and prose audit to verify, but 100% of historical occurrences have been benign false alarms, maintainers will predictably default to `forge drift confirm` as a ritual.

---

## Verdict on W1: Strong Negative / Null Result

**A stale report has never changed a code outcome or prevented a defect in any run to date.**

Staleness reporting was designed as the marquee capability that competitors lack ("a comment does not know when code moves"). However:
1. When anchors are broad, routine edits trigger false drift that trains maintainers to restamp.
2. When anchors are tightened (as done in G14/R1/R2), they suffer from Q1c's false negatives (7 of 18 break without touching the anchor).
3. Attribution via `reconcile` aids forensic attribution ("who touched the file"), but provides zero automated help in answering the only question that matters: *did the code actually violate the invariant?*

---

## Limits

- **Tiny historical sample size (n=3)**: Only three drift events occurred during the development and measurement phases. While the sample is small, it represents 100% of the project's real drift history.
- **Absence of human team observation**: Observational data on whether real engineers in production heed stale alerts over weeks cannot be gathered in this harness without human subjects.
- **Triage classification is subjective**: The categorization of the 18 claims into ST/PD/CA was performed by analysis of each claim's definition and typical git commit messages; however, even the most generous reading cannot make commit messages self-triaging for subtle pitfalls.

