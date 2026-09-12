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

*(written after the runs, below this line)*
