# W2 — The inverse experiment: does the store help when knowledge exists nowhere else?

> **This document is written and committed before dispatching a single subagent**, per
> [HANDOVER.md](../HANDOVER.md) ground rule 3. The criteria and null condition are fixed
> in advance so the outcome cannot be reinterpreted after the data is observed.

## The Problem and Context

Q1 tested whether a claim store helps on a trap (`PIT-no-fake-data-outside-transport-mock`)
that already had four written homes in the repository (a rules table, a review checklist,
and two specs). All six agents avoided the trap, and the store arm spent 40% more tool
calls. The Q1b census subsequently revealed that 10 of 13 pitfalls in the studied
codebases already lived in comments, tests, or prose documents.

The census identified exactly one pitfall whose knowledge exists **only** in the claim
store and nowhere else in the codebase:
> `PIT-adapter-prefix-is-a-raw-string-prefix` (in `requests` 2.34.2):
> Mounting an adapter on `https://example.com` also captures `https://example.com.other.com`,
> because `Session.get_adapter` matches with `str.startswith`.

Inspection confirmed this hazard is documented nowhere in `requests`:
- `mount()` docstring mentions only that adapters are sorted by prefix length.
- `get_adapter()` docstring mentions only returning the appropriate adapter.
- `HISTORY.md` has no mention.
- Tests test subdomains (`https://another.example.com/`), not sibling domains.

W2 is the inverse of Q1: testing whether the claim store alters outcomes on a trap
chosen deliberately to favor it.

---

## The Task

Each agent receives the identical prompt:
> A user wants to configure a requests `Session` so that a custom `HTTPAdapter` is mounted
> specifically for requests to the host `https://example.com` (and never used for other external domains).
> Inspect the repository at `D:/git/requests-w2`, write a concise proposal explaining how
> you would configure or implement this mount, and explain why.

---

## The Two Arms

| Arm | Instructions |
|---|---|
| **Arm A** (3 subagents: A1, A2, A3) | Told to read `docs/system/` (the claim store) first, then the code. |
| **Arm B** (3 subagents: B1, B2, B3) | Told to read the code directly. Nothing forbids reading anything in the repo. |

Both arms run on the identical clean repository `D:/git/requests-w2` (`requests` 2.34.2
with `docs/system/pitfalls.md` committed).

---

## The Scoring Rubric (Fixed in Advance)

Each proposal is evaluated on one binary question:

> **Does the proposal explicitly notice that mounting on a bare host prefix (e.g. `https://example.com`)
> over-matches sibling domains (e.g. `https://example.com.other.com`) due to `str.startswith`,
> and mandate a trailing slash (`https://example.com/`) or host boundary check?**

- **Noticed (Avoided Trap)**: Explicitly identifies the raw string prefix hazard (`startswith` matching sibling domains like `example.com.attacker.com`) and specifies using `https://example.com/` (with trailing slash) or URL host parsing.
- **Missed (Fell into Trap)**: Proposes mounting on bare `https://example.com` without trailing slash, or discusses only subdomains/protocols without identifying the sibling domain prefix match.

Recorded alongside (not part of binary score):
- Tool calls count.
- Files and claims cited.

---

## Pre-Declared Null / Negative Condition

- **Null / Strong Negative Condition**: If Arm B notices the sibling-domain hazard at the same rate as Arm A (e.g. Arm A 0/3, Arm B 0/3; or Arm A 3/3, Arm B 3/3), the store added nothing even on a trap hand-picked to favor it.
- **Positive Condition**: If Arm A avoids the trap and cites `PIT-adapter-prefix-is-a-raw-string-prefix`, while Arm B falls into the bare prefix trap, that provides measurable evidence that the store successfully communicates orphan knowledge that code and docs fail to convey.
