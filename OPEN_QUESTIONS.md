# OPEN_QUESTIONS.md

Unresolved questions in the design. Each carries: why it matters, the options, a recommendation where I
have one, and **what evidence is still missing** — because several of these cannot be settled by more
reading, only by running the thing.

Priority: **P0** = must be answered before the MVP is written · **P1** = must be answered during the MVP
· **P2** = deferred deliberately.

---

## Q1 — Does any of this actually improve outcomes? **PARTLY ANSWERED 2026-09-12 — one null result, recorded**

> **First evidence.** [docs/measurements/q1-does-the-store-help.md](docs/measurements/q1-does-the-store-help.md)
> ran option **B** in miniature: six agents, one trap, one repository, rubric and null
> condition committed before a single agent started. Three were pointed at the claim
> store; three were pointed only at the code. **All six avoided the trap**, and the arm
> with the store spent 40% more tool calls getting there.
>
> The store did not lose on its merits - it lost because the trap already had four
> written homes in that repository (a rules table, a review checklist, two specs) and
> the agents found them. The finding that generalises is about *authoring*, not about
> the mechanism: **a claim derived from a document competes with that document, and the
> reader usually finds the document.** That is now in the `bootstrap` skill as the
> question to answer before writing a candidate - what does the claim add that its
> source does not - and in the review sheet as a `restates:` line, so the human
> ratifying it is told.
>
> **Still open, and this is most of the question.** The measurement says nothing about
> the two things the store does that prose cannot: **anchors going stale when the code
> moves**, and **reach** - knowledge recorded nowhere near the work. Neither was
> exercised. The honest next experiment is the inverse of this one: a trap whose record
> exists *only* in the store, in a repository with no rules document. Option **C**
> (`forge stats`) is unstarted and still waits on ~10 real changes.

**Why it matters.** It is the question the whole proposal rests on, and the corpus provides no evidence
either way. None of the six projects ships an evaluation of its own methodology. The only hard numbers
anywhere near this space belong to mini-SWE-agent — a ~200-line loop with *no* methodology, no spec, no
architecture knowledge — which reports >74% on SWE-bench Verified. It is entirely possible that process
buys reliability on long-lived codebases and buys nothing on well-scoped tasks, and it is possible that
it buys nothing at all.

**Options.**

- **A. Assume value, build, never measure.** What every project in the corpus did.
- **B. Build the MVP, then run a paired comparison** on real changes in one repository: same request,
  once with the harness and once without, comparing rework rate, review findings, and time-to-green.
- **C. Instrument from day one**: `verification.json` and the trajectories already record enough to
  compute per-change step count, cost, wall-time, number of failed verifications before pass, and
  post-merge defect attribution.
- **D. Don't build; use mini-SWE-agent's discipline and nothing else.**

**Recommendation. C, then B.** Option C is nearly free because the artifacts already exist — add a
`forge stats` command that aggregates them. Option B needs discipline but only needs ~20 changes to be
suggestive. Explicitly reject A: a harness that cannot show its own value is a belief system.

**Missing evidence.** Any controlled comparison, anywhere, of spec-driven agent workflows against a bare
loop on a *maintained* codebase (SWE-bench measures single-issue patches on repos the agent does not
maintain — the wrong shape for this question).

---

## Q2 — Will anchors survive real refactoring? **ANSWERED 2026-09-10 — largely yes**

> **Resolution.** Measured in [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md):
> 600 commits replayed across three repositories plus a controlled perturbation experiment.
> Recommendation **A + D** was implemented — path+symbol anchors with git rename following, plus the
> `shifted`/`stale` split — and the perturbation results retire the risk for the mechanical cases
> (formatting, comment edits, quote style, pure file moves). Option **C** (component-level anchors) was
> not needed and is not implemented. Option **B** (content-addressed relocation) *is* implemented, but
> not for the reason it was proposed: it turned out to be needed as a fallback when git's rename
> detection gives up on a low-similarity move, which the measurement found and it then closed
> (0.61% → 0.00%). Its other intended use, the `forge reanchor` guard, still waits for the claim store
> in M0.
>
> Three residual pieces keep this from being fully closed:
> 1. Semantically neutral refactors (extract variable, reorder independent statements) have no
>    mechanical ground truth and are excluded from the measured rate, so the true false-positive rate is
>    higher than reported by an unknown margin.
> 2. Only declarations with a body were perturbed; interfaces, type aliases and `const` declarations are
>    covered by unit tests only.
> 3. Three languages, three repositories, shallow clones, mainline only.
>
> The original question and options are kept below because the residual pieces are still live.

### Original question **P0**

**Why it matters.** The entire staleness mechanism rests on `path#Symbol@sha` + normalised AST
fingerprints. A rename, a file move, or an extract-method marks every anchor on the affected symbol
stale. If a routine refactor produces 15 spurious drift entries, the ledger becomes noise and gets
ignored — and an ignored ledger is worse than no ledger, because it looks like coverage. Fiberplane
names this limitation and does not solve it.

**Options.**

- **A. Path+symbol anchors with git rename detection** when resolving the baseline (`git log --follow`,
  `--find-renames`). Handles pure moves and renames-with-no-semantic-change.
- **B. Content-addressed anchors** — anchor to the fingerprint itself, and locate the symbol by searching
  for a matching fingerprint at HEAD. Survives moves entirely; fails when the code changes at all,
  which is the case we want to detect anyway.
- **C. Coarser anchors** — anchor to the component (a path glob) rather than a symbol. Far fewer false
  positives, far less precision; effectively GSD's structural approach.
- **D. Tolerance policy** — treat "fingerprint changed but the symbol's *signature* is unchanged" as a
  weaker signal (`shifted`) than a signature change (`stale`), and only surface `stale` by default.

**Recommendation. A + D, with B as the re-anchoring aid.** `forge reanchor` accepts a restamp only when
the fingerprint matches under git's rename mapping — free when nothing semantic changed, impossible when
something did. Add the `shifted`/`stale` distinction so a body-only edit is quieter than a
signature change. Reject C: losing symbol precision loses the mechanism's whole advantage over GSD.

**Evidence obtained.** Both experiments were run (see the resolution above). Two findings changed the
design rather than merely confirming it: `shifted` had to become a first-class status because body-only
edits are 79% of all non-fresh verdicts, and `coarse` had to become a flag rather than a status.
Three defects in the fingerprint were found by the perturbation harness, all of which would have
surfaced as ledger noise rather than as crashes.

**Evidence still missing.** A rate for semantically neutral refactors, which needs human labelling; and
any language outside the three grammars.

---

## Q3 — Will "Unaffected" accounting become rubber-stamping? **P0**

**Why it matters.** The claim-touch rule (SYSTEM_KNOWLEDGE.md §9.2) is the core enforcement of the whole
design: every claim whose anchors or globs intersect the diff must be accounted for in `impact.md`. If
the honest answer is usually "unaffected", the agent will learn to emit "unaffected — no behavioural
change" for everything, and the check becomes a formality that costs tokens and buys nothing. This is the
same decay that makes checkbox compliance worthless.

**Options.**

- **A. Accept it.** Even a rubber-stamped list surfaces the claim IDs into context, which has value.
- **B. Require differentiated justification** — reject an `Unaffected` reason that is textually similar to
  another entry's, or that is under N words, or that does not name something specific about the claim.
- **C. Reduce the touch set** — only claims whose anchors intersect the diff *and* whose kind is in
  {invariant, architecture, interface, datum} require accounting; component and concept claims are
  listed for context only.
- **D. Sample** — require full accounting for a random subset plus all high-kind claims, so the habit
  cannot form around a predictable subset.
- **E. Keep the claim count genuinely low** so the list is 3–5 items, where reading it is cheaper than
  gaming it.

**Recommendation. C + E, with B's similarity check as a cheap linter.** C targets the accounting at the
kinds where being wrong is expensive. E is the real answer, and it is why the budgets in
CONSTITUTION.md X and XIV exist: **the claim-touch rule is only sustainable if the store stays small,
and the rule is what makes keeping it small economically rational.** Reject D — unpredictable obligations
train avoidance, not care.

**Missing evidence.** The actual distribution of touch-set sizes on real changes. Measurable after ~10
changes with the MVP.

---

## Q4 — What is the right always-loaded budget? **P1**

**Why it matters.** Principle X forbids raising the budget, which makes the initial number consequential.
400 lines is my extrapolation from BMAD's stated budget discipline and the context-rot literature — not a
measurement. Too low and the agent lacks the concepts it needs and asks questions it shouldn't; too high
and instruction-following degrades across the board, which is invisible and blamed on the model.

**Options.**

- **A. 400 lines fixed** (proposed).
- **B. Token-based, not line-based** (e.g. 6,000 tokens) — more accurate, needs a tokenizer dependency.
- **C. Tiered**: a ~100-line always-loaded core (OVERVIEW + claim index) plus per-phase claim loading via
  the DAG `reads` contract, with no separate always-loaded claim files at all.
- **D. Measure per project**: run a fixed task battery at several budget levels and pick the knee.

**Recommendation. C, with A as the ceiling on the whole store's mandatory files.** The DAG already
resolves claim bodies per phase — so the *always-loaded* set really only needs `OVERVIEW.md` plus the
claim index (IDs and titles), which is closer to 100 lines. That makes the 400-line figure a store-size
budget rather than a context budget, which is a better use for it. Revisit B once a tokenizer is present
for another reason.

**Missing evidence.** Any measurement of instruction-following degradation as a function of
always-loaded project context, on the specific hosts we care about. The Chroma work establishes the
phenomenon, not the threshold.

---

## Q5 — Are permanent capability specs and invariant claims redundant? **P1**

**Why it matters.** The design keeps two permanent behavioural stores: OpenSpec-style capability specs
(`REQ-*` requirements with scenarios) and `INV-*` claims. Both describe things that must be true. Two
stores of overlapping obligations is exactly the multi-representation failure I criticise GSD for.

**Options.**

- **A. Keep both, with a sharp rule.** A `REQ-*` is *externally observable behaviour of a capability*; an
  `INV-*` is a *property that must hold across all behaviours*, often not externally observable
  (referential integrity, monotonicity, idempotency, accounting identities). Different truth sources
  (spec vs tests), different lifecycles (a REQ is created by a change; an INV outlives many changes).
- **B. Collapse into claims.** Make requirements a claim kind (`REQ-`) and drop the separate spec tier.
  Loses OpenSpec's deterministic archive fold and the capability grouping that makes specs readable as
  documents.
- **C. Collapse into specs.** Express invariants as requirements with scenarios. Loses anchoring and the
  `enforced`/evidence machinery, which is the part that makes invariants checkable.

**Recommendation. A, and write the rule down as a claim-kind admission test**: "if this can fail without
any user noticing, it is an invariant, not a requirement." Also enforce a non-overlap check: an `INV-`
whose prose is a paraphrase of a `REQ-` is a finding.

**Missing evidence.** How often the boundary is genuinely ambiguous in practice. Suspect: rarely, but the
first ten changes will show.

---

## Q6 — In-place claim editing, or an append-only log with derived rendering? **P2**

**Why it matters.** BMAD's `bmad-spec` uses an append-only `.memlog.md` as canonical with `SPEC.md`
*derived on each run*, and gives a good reason: it lets several processes feed one artifact in any order
without merge drift, and provenance is free. Our design edits claims in place and relies on git plus the
ADR `supersedes` chain for provenance.

**Options.**

- **A. In-place editing** (proposed). Simple, `git blame` works on the readable document, one file per
  kind.
- **B. Append-only log + derived render.** No merge drift, complete decision history, but doubles the
  artifact count, makes `git blame` on the readable file useless, and requires that nobody ever
  hand-edits the rendered file — a discipline that will be violated.
- **C. Hybrid**: in-place claims, plus an append-only `docs/system/decisions/LOG.md` of one-line decision
  records that ADRs expand on.

**Recommendation. A for the MVP; C if multi-writer becomes real.** The merge-drift problem B solves is a
multi-writer problem, and we have one developer and one agent. The ADR chain already gives provenance for
the part that needs it. Revisit if the harness ever runs several agents writing knowledge concurrently —
at which point B becomes clearly correct.

**Missing evidence.** Whether concurrent knowledge writes actually occur in single-developer use. Suspect
not.

---

## Q7 — Will grep and the derived tier be enough, or is a code index eventually required? **P2**

**Why it matters.** The design deliberately refuses a code graph, SCIP index, or embeddings, on the
grounds that GSD's became a fourth representation with its own rot. That refusal is right at 20k lines
and probably wrong at 2M.

**Options.**

- **A. Never.** Grep + tree-sitter + the ecosystem's dependency tool.
- **B. Add SCIP when a threshold is crossed** (repo size, or measured investigation cost per change).
- **C. Add Aider-style tree-sitter + PageRank ranking** as a `derived/repo-map.json` — a compact,
  regenerable artifact rather than an index server. This fits the derived tier perfectly: provenance by
  commit, byte-identical regeneration, no daemon.

**Recommendation. A for the MVP; C as the first escalation, not B.** C keeps the property that everything
is regenerable text with commit provenance; B introduces an indexer with its own lifecycle. Set the
trigger explicitly: if `investigate` routinely exceeds its step budget on a repository, add C.

**Missing evidence.** The repository size at which the host agent's own search stops being adequate.
Unknown and probably host-dependent.

---

## Q8 — How much can an LLM usefully contribute to a drift verdict? **P1**

**Why it matters.** The design has the model *propose* a verdict (V1–V4) and a human *record* one. But
arXiv:2604.03447 shows the model is weakest exactly here — detection drops 21–43 points when only the
implementation changed — and its confidence does not separate correct from incorrect judgements. If the
proposals are mostly wrong, they are worse than absent: they anchor the human's judgement in the wrong
place.

**Options.**

- **A. Propose a verdict with reasoning** (as designed).
- **B. Propose only evidence, never a verdict**: show the fingerprint diff, whether the discharging test
  still passes, whether the conformance rule still passes, what the commit messages in the range say —
  and let the human classify.
- **C. Propose a verdict only when a mechanical signal disambiguates.** If the rule now fails → V1 or V3
  (never V2/V4). If the invariant's test still passes and only the body changed → likely V1 or
  under-specification. If the change came through a `forge` change with an ADR → V3, already accounted.
- **D. No LLM involvement at all** in drift.

**Recommendation. C.** It uses the model only where a deterministic signal has already narrowed the space,
which is the only regime the paper gives grounds for trusting. Present B's evidence bundle *always*, and
attach C's narrowed proposal *when available*. Never a bare verdict with prose reasoning and no
mechanical signal.

**Missing evidence.** Verdict-proposal accuracy on real drift, measurable once the ledger has ~20
resolved entries. Until then, prefer B's shape.

---

## Q9 — Is `analyze` a phase or just a gate? **P1**

**Why it matters.** It currently exists as both: a set of deterministic checks at `analyze:post` and a
document `analysis.md`. If the deterministic checks are the substance, the document is a report nobody
reads and the phase is a ritual. Spec Kit made it a full command with a 50-row findings table and a
severity ladder; whether that is worth its cost is unclear.

**Options.**

- **A. Phase with an artifact** (as designed).
- **B. Gate only** — `forge check --scope change` runs at `tasks:post`, prints findings, blocks on
  CRITICAL, writes nothing. The LLM semantic review folds into the `tasks` phase's own self-review.
- **C. Gate + optional artifact** — the document is written only when findings exist and are not fixed
  immediately.

**Recommendation. B, with C's escape.** A separate phase that produces a document summarising checks that
already ran is a phase-shaped ritual. Superpowers gets the same value from an inline self-review
checklist ("If you find issues, fix them inline. No need to re-review — just fix and move on"). Keep the
document only for findings that are *accepted rather than fixed*, because those need a record.

**Missing evidence.** Whether the LLM semantic checks find anything the deterministic ones miss, on real
changes. If they do not, drop them and save the tokens.

---

## Q10 — What happens to changes made outside the harness? **P1**

**Why it matters.** Hotfixes, other people's commits, dependency bots, and "I just fixed it in the
editor" are guaranteed. If out-of-band commits silently accumulate stale anchors and unmapped files, the
first `forge drift` after a busy week produces a wall of findings and the human declares harness
bankruptcy. Every knowledge-maintenance scheme dies this way.

**Options.**

- **A. Reconcile pass** — `forge reconcile <range>` classifies the commits in a range: which touched
  claim anchors, which added unmapped files, which changed contracts. Produces a batch of drift entries
  with a single review flow.
- **B. Pre-commit / pre-push hook** running `forge check --scope store` (cheap) and `forge drift --changed`
  (also cheap, since it only checks anchors in the diff). Catches drift at the moment it is created,
  when the reason is still in someone's head.
- **C. Accept the backlog** and rely on the ledger's waiver mechanism to keep the gates usable.
- **D. Require all changes to go through the harness.** Unrealistic, and will be violated on day one.

**Recommendation. B primarily, A as the recovery path.** B is the design's cheapest high-value addition
and it is the one integration point worth taking a hook for (ARCHITECTURE.md §5.3): checking only the
anchors touched by the current diff is fast enough to run on every commit. A exists because B will
sometimes be bypassed.

**Missing evidence.** The actual runtime of `forge drift --changed` on a large diff. Should be
milliseconds-to-seconds; needs confirming.

---

## Q11 — Where does the harness live, and does knowledge cross repositories? **P2**

**Why it matters.** The kernel could be installed globally (one `forge` on PATH) or vendored per
repository. The claim store is per-repository by design, but a single developer accumulates
cross-project pitfalls ("I always get pnpm workspace globs wrong") that belong somewhere.

**Options.**

- **A. Global kernel, per-repo config and store** (proposed). Standard tool shape.
- **B. Vendored kernel per repo.** Reproducible, no version skew, but N copies to update.
- **C. Global kernel + a global pitfall store** merged into the always-loaded set.
- **D. Global kernel + per-repo store only**; cross-project lessons go in the developer's own agent
  config, not in the harness.

**Recommendation. A + D.** Cross-project knowledge is a personal-preferences problem, not a
system-knowledge problem, and mixing them breaks the truth-source model (a global pitfall has no anchor
in this repository). BMAD reaches the same conclusion: rules "repeating across their projects, or
personal rather than the team's, belong in their global agent config". Pin the kernel version in
`.forge/config.yaml` so a repo can detect skew.

**Missing evidence.** None needed; this is a preference with a clean argument.

---

## Q12 — Which hosts must the skills work on, and at what cost? **P1**

**Why it matters.** Superpowers maintains plugin manifests for eight host runtimes (`.claude-plugin`,
`.codex-plugin`, `.cursor-plugin`, `.devin-plugin`, `.hermes-plugin`, `.kimi-plugin`, `.opencode`, `.pi`)
plus a sync script of ~15,000 bytes and per-host test suites. Spec Kit maintains bash, PowerShell **and**
Python copies of every script. That portability tax is large and recurring.

**Options.**

- **A. One host (Claude Code) for v1.** Skills as a local plugin; the kernel as a CLI, which is portable
  by nature.
- **B. Host-agnostic skills from the start** — plain markdown in `.forge/skills/`, invoked by path, with a
  thin per-host shim.
- **C. Full multi-host support.** Reject: it is the tax Superpowers pays, for a personal harness.

**Recommendation. A, structured so B is cheap.** Keep every skill as plain markdown with no host-specific
syntax, and keep all mechanism in the kernel — a CLI runs everywhere. Then supporting a second host is a
manifest, not a port. The single most important consequence: **skills must never depend on a host-specific
feature** (a particular subagent API, a hook type, a tool name).

> **Tested 2026-09-12, and the bet holds - with one violation the audit found.**
> Six of the seven skills named no host feature. `bootstrap` told its reader to fan out
> across subagents, which is a mechanism where it meant an outcome and one a host without
> subagents cannot follow. It now states the requirement - each topic's file written
> directly by whoever read the code, never summarised back - and says fan-out is the fast
> way *if the host has it*.
>
> A rule that holds because somebody looked once is not a rule, so `skill.host_specific`
> checks it. The frontmatter was already uniform and host-neutral across all seven.
>
> `forge skill export --host <name>` is the manifest, and `hosts.HOSTS` is a table: a
> host is an entry saying where it reads from and in what shape. Two are there, both
> verifiable on this machine - a pointer section merged into `AGENTS.md`, and the layout
> `forge init` already writes. **No format this project has not seen is invented here**;
> a third host is a table row when somebody can check what that host actually reads.
>
> Exercised on the monorepo of run 3, which carries its own `AGENTS.md` in Vietnamese:
> the section merged in under markers, the project's prose untouched, and re-exporting is
> idempotent.
>
> It also found a gap nobody had named: `forge init` copies the skills out and they then
> drift from the kernel **in silence**. That monorepo was still telling its reader to fan
> out a day after the kernel stopped saying so. `forge skill list` now marks a local copy
> that differs, and `export --host forge` refreshes it - sourcing from the kernel, not
> from the copy, which is what the first cut got wrong: it copied the stale file onto
> itself and reported `unchanged`.

**Missing evidence.** None; this is a scope decision.

---

## Q13 — Should the harness enforce TDD, or require evidence and let the order vary? **P1**

**Why it matters.** Superpowers makes red-green-refactor an iron law; Spec Kit makes tests optional; GSD
makes TDD a mode you opt into per plan. There is no evidence in the corpus that strict TDD improves agent
output — only that *tests as evidence* does. Enforcing the order is much more intrusive than enforcing
the evidence, and intrusive rules that are hard to verify are the ones that get faked.

**Options.**

- **A. Strict TDD, verified.** Each task's trajectory must show a failing run before a passing run.
  Strong, and mechanically checkable from the trajectory.
- **B. Evidence-only.** Require a test that discharges the requirement and passes; do not care when it
  was written.
- **C. Kind-conditional.** Strict for tasks tagged with an `INV-` claim or a bug reproduction (where
  "did the test actually test the thing" is the entire question); evidence-only elsewhere.

**Recommendation. C.** It puts the expensive discipline exactly where the failure mode it prevents is
real: a test written after the fix, against the fixed code, frequently passes for the wrong reason. For
ordinary feature tasks, evidence is enough, and the trajectory check still records what happened.

**Missing evidence.** Whether strict TDD changes defect rates for agent-written code at all. Nobody in the
corpus measured it; `forge stats` (Q1) could.

---

## Q14 — Is a reject-by-default bootstrap too thin to be useful? **P1**

**Why it matters.** WORKFLOW.md §5 proposes a claim cap of 40, a reject-by-default posture, and calls a
baseline of 12 ratified claims a good outcome. That may leave the store so sparse that the claim-touch
rule almost never fires and the harness's value is invisible for the first month — which is exactly when
adoption is decided.

**Options.**

- **A. Reject-by-default, cap 40** (proposed).
- **B. Generous baseline** with everything marked `asserted` and `confidence`, relying on the linters to
  catch noise. Faster perceived value, higher risk of a store full of plausible-but-wrong claims — which
  is the failure mode the entire design exists to prevent.
- **C. Reject-by-default, but front-load the two highest-value kinds**: interview for `CON-` (vocabulary)
  and `PIT-` (known traps) rather than scanning for `CMP-`/`ARC-`. Those two are un-derivable, cheap to
  confirm, and immediately useful to an agent.
- **D. No bootstrap claims at all.** Derived tier only; claims accrue from the first changes.

**Recommendation. C.** A store of 8 concepts and 6 pitfalls, all human-confirmed, is more useful on day
one than 40 inferred component descriptions, and it makes the first `investigate` noticeably better. Keep
the cap. Option D is tempting for purity and loses the first-week value that decides adoption.

**Missing evidence.** Which claim kinds actually get cited during real investigation phases. Instrument
`forge trace` usage and find out.

---

## Q15 — How is the `enforced` ratio kept from becoming a metric to game? **P2**

**Why it matters.** `forge status` reports `enforced` vs `asserted` per kind, and CONSTITUTION.md V
frames `asserted` as an honest state. But any reported ratio invites gaming — here, by attaching a weak
test or a trivially-satisfied rule to a claim in order to call it `enforced`.

**Options.**

- **A. Report and trust.** Personal harness, single developer, no incentive to game.
- **B. Require the evidence to have been observed failing** at least once — a rule that has never failed
  might not constrain anything. Mechanically: record the first observed failure of each evidence artifact.
- **C. No ratio.** Report only the absolute count of unenforced claims of high-value kinds.

**Recommendation. A for the MVP, B if it ever matters.** B is genuinely elegant — it is Superpowers'
"if you didn't watch the test fail, you don't know if it tests the right thing" applied to claim
evidence — but it needs a place to record first-observed-failure, which is state, which the design avoids.
Revisit if the ratio starts looking suspiciously good.

**Missing evidence.** None; this is a judgement about incentives that only real use will settle.
