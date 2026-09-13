# Q1 — does the store help? The plan, written before the results

> **This half was written and committed before a single agent was run.** Q1 is the
> question [MVP.md](../../MVP.md) calls P0 "for honesty", and the reason it is P0 is
> [RESEARCH.md](../../RESEARCH.md)'s third finding: the projects with the most machinery
> have the least evidence it helps. A badly-designed Q1 produces a number that *looks
> like* evidence, which is worse than no number. So the criteria are fixed first.

## The task

`OracleIntrospector.listDatabases` in `packages/driver-oracle/src/introspect.ts` ends:

```ts
} catch {
  return []
}
```

Every failure - a dead connection, a permissions error, a missing `v$pdbs` view -
becomes an empty list. The caller cannot tell "this database has no pluggable
databases" from "we could not ask".

Six agents get the identical task: **say what you would change and why.** A written
proposal, not code, so the reasoning is visible rather than inferred from a diff.

## The two arms

| Arm | Told to read |
|---|---|
| **A** (3 agents) | `docs/system/` - the claim store - and then the code |
| **B** (3 agents) | the code |

Nothing forbids arm B from reading anything. `AGENTS.md`, `docs/05-rules/` and the
conformance tests are all there for anyone who looks. The difference under test is a
**pointer to curated knowledge**, not access to it, because that is the only thing the
store actually claims to buy.

## Why this task and not the obvious one

The obvious choice was `PIT-secret-key-match-must-be-substring`, whose trap is
seductive: "substring matching over-redacts, let us make it exact" is what a careful
engineer proposes, and an earlier version of that code did exactly that and leaked.

It was rejected because **`redact.ts` explains itself for eleven lines at the top**,
citing the audit. An agent asked to change it reads the warning on the way in. That
tests whether agents read comments, not whether a store helps.

This task was chosen because the knowledge is **real, recorded, and somewhere else**:

- `docs/05-rules/coding-rules.md` §3.8
- `tools/__tests__/no-mock-in-bundle.test.ts`
- `docs/04-plan/audit-2026-08-18.md`
- and, for arm A only as a pointer, `PIT-no-fake-data-outside-transport-mock`

`introspect.ts` says none of it. The word "mock" does not appear in the file, and
neither does "fake" or "fixture". This is the case the claim store exists for: a trap
whose record lives nowhere near the work.

## What the store says, and what it cost

`PIT-no-fake-data-outside-transport-mock` records that earlier work embedded hard-coded
sample rows inside `driver-*` - a literal array from `listDatabases()`, ~200 lines of
fake data in the MySQL driver, ~170 in SQLite. The audit names it a root cause of a much
larger failure: **the UI looked like it was running against real databases, concealing
that not one line of the repo connected to one, across 230 tasks marked done.**

The rule that came out of it: fake data lives only in `transport-mock`, and a driver
that has not implemented a capability throws rather than returning something plausible.

## Scoring, fixed now

Each proposal is scored on one binary question:

> **Does it make the failure visible to the caller, or does it keep returning a value
> that reads as a successful empty result?**

- **Avoided** - proposes throwing, or otherwise surfacing the failure so a caller can
  distinguish "no pluggable databases" from "could not ask".
- **Fell in** - proposes returning `[]`, a default, a placeholder, or logging-and-
  continuing as the success path.

Recorded alongside, not scored: whether the proposal cites the rule or the claim, and
roughly how much of the repository it read to get there.

## What would make this a null result, said in advance

**If arm B avoids the trap at the same rate as arm A, the store added nothing here, and
that is the finding.** A well-run repository that documents itself in `AGENTS.md` and a
`docs/` tree may not need a claim store to keep an agent out of a hole, and if so this
project should know it.

Two limits that no amount of care removes, and which the result must be read against:

- **n = 6, on one task, in one repository.** This is an anecdote with a fixed rubric,
  not a measurement. It can show a mechanism working or failing; it cannot show a rate.
- **The scorer designed the task.** I chose a task where the store has something to say.
  A fair reading of any positive result has to include that.

---

## Results

**Six of six avoided the trap. Arm A 3/3, arm B 3/3. This is the null result
declared above, and it is the finding.**

| | arm | verdict | tool calls | cited |
|---|---|---|---|---|
| A1 | store | avoided | 21 | `PIT-no-fake-data` + coding-rules §7.1/7.2/7.4/7.5 + `CON-connection-vs-session` |
| A2 | store | avoided | 16 | `PIT-no-fake-data` + coding-rules §7.2/7.4/7.5 |
| A3 | store | avoided | 16 | `PIT-no-fake-data` + coding-rules §7.1/7.2/7.4 |
| B1 | code | avoided | 14 | coding-rules §3.8/7.1/7.2/7.4/7.5 + capability-matrix + driver-spi |
| B2 | code | avoided | 14 | coding-rules §7.1/7.2/7.4/7.5 + driver-spi §7 |
| B3 | code | avoided | 11 | coding-rules §3.8/7.2/7.4/7.5/9.10 |

All six proposed the same core change: drop the blanket catch, rethrow through the
driver's own `toStudioError` mapper, and keep one narrow commented exception for the
non-CDB case. None proposed a fallback, a default, or logging-and-continuing.

## Why the store did not help here, stated precisely

**Every arm-B agent found `docs/05-rules/coding-rules.md` unaided**, and cited the same
sections. Two of three also cited **§3.8** - which is one of the three sources
`PIT-no-fake-data-outside-transport-mock` names in its own `evidence-from` line.

That is the whole result. The claim was a **restatement of a rule that already had a
home in this repository**, and the agents that were not pointed at the claim found the
rule instead. Arm A cited the claim *alongside* `coding-rules.md`, never instead of it,
so even with the pointer the rule was doing the work.

The store cost something and returned nothing measurable: arm A averaged **18 tool
calls against arm B's 13** for the same verdict. Reading `docs/system/` was 40% more
looking around for an answer the rules document already gave.

**The sharpest single output came from arm B.** B1 and A3 both noticed that ORA-00942
is ambiguous - `v$pdbs` missing on a non-CDB instance and a missing `SELECT` grant raise
the same code - so the "narrow exception" everyone proposed is not actually narrow. B1
wrote it down as a caveat for the PR: *"the narrowest honest exception, not a fix for
it."* Neither arm had a monopoly on the best reasoning.

### The task was harder on the store than I realised when I chose it

Written before the runs, the plan says the knowledge is "real, recorded, and somewhere
else" and names three sources. A survey of the repository afterwards found the rule
against exactly this shape of code written down in **four** more places:

- `docs/05-rules/coding-rules.md` §7.4 - no empty `catch`; a deliberate swallow needs a
  comment saying why - with the canonical bad example being a `catch` that does nothing.
- `docs/05-rules/review-checklist.md` §5 - the same line as a review gate.
- `specs/002-docker-real-env-testing/spec.md` **FR-014** - MUST NOT silently fall back
  when the backend is unavailable; MUST show an explicit connection error.
- `specs/001-multi-engine-navigation/data-model.md` **invariant IV-A** - a capability
  declared `true` must actually list; a violation must be caught by conformance rather
  than discovered by a user.

`eslint.config.js:51` even sets `no-empty` with `allowEmptyCatch: false`. It does not
fire on this code - `catch { return [] }` has a body - but the intent was already
machine-declared.

So the store was not competing with one rules document. It was competing with a rules
table, a review checklist, two specs and a lint config, all saying the same thing. **A
claim cannot add much in a repository that has already said the thing four times**, and
the fair reading of the null result is that I chose a trap this repository had already
closed in prose - not that the store failed at something it had a fair shot at.

That is itself a usable finding, and it is the one that generalises: before writing a
claim, the question to ask is not "is this true and important" but **"where else does
this already live, and will the agent get there anyway."**

## What this does and does not say

**It does not say the store is useless.** It says that on *this* repository, for *this*
trap, the claim was redundant with the document it was derived from, and n=6 on one task
cannot say more than that.

**It does say something uncomfortable and specific**, which is worth more than a
reassuring number: the bootstrap's best claims come from rules the project already wrote
down - that source was added to the skill deliberately, as finding H7 of
[run 3](run3-monorepo-lifecycle.md) - and **a claim derived from a written rule is the
claim most likely to be redundant with it.** The two mechanisms point in opposite
directions, and the run-3 change that made bootstrap better at finding rules made it
better at producing duplicates.

**Where the store could still earn its place**, untested here and named so nobody reads
this as a verdict on the whole design:

- Knowledge with **no** written home: a trap somebody learned and never documented,
  which is what `PIT-` is defined as and what this repository happened not to need.
- A repository **without** a `docs/05-rules/` tree. Studio is unusually well documented;
  the store was competing with a good rules document rather than with nothing.
- **Anchors and staleness**, which this task did not exercise at all. A rules document
  does not know when the code under it moved; that is the one thing the store does that
  prose cannot, and it is untouched by this measurement.

## What would test it properly

The honest next experiment is the inverse: a trap whose record exists **only** in the
store - a `PIT-` earned from a failure nobody wrote a rule about - on a repository with
no equivalent rules document. If the store loses there too, that is a real answer about
the design rather than about monorepo.
