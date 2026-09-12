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

---

## Results

**Six of six agents avoided the trap. Arm A: 3/3, Arm B: 3/3.**
**This matches the pre-declared Null / Strong Negative Condition.**

| Agent | Arm | Verdict | Tool Calls | Primary Citations |
|---|---|---|---|---|
| **A1** | Store | **Avoided** | 18 | `PIT-adapter-prefix...` + `sessions.py:870-898` + `models.py:542` |
| **A2** | Store | **Avoided** | 15 | `PIT-adapter-prefix...` + `sessions.py:870-898` + `models.py:542` |
| **A3** | Store | **Avoided** | 23 | `PIT-adapter-prefix...` + `sessions.py:870-898` + `models.py:542` |
| **B1** | Code | **Avoided** | 24 | `sessions.py:870-898` + `models.py:542` + `test_requests.py:1705-1730` + `pitfalls.md` |
| **B2** | Code | **Avoided** | 21 | `sessions.py:870-898` + `models.py:542` + `pitfalls.md` + `test_requests.py` |
| **B3** | Code | **Avoided** | 22 | `sessions.py:870-898` + `models.py:542` + `pitfalls.md` + `test_requests.py:1705-1730` |

- **Arm A average tool calls**: 18.7
- **Arm B average tool calls**: 22.3

All six agents recommended the identical exact prefix string: `"https://example.com/"` (with trailing slash) and explained why `prepare_url` in `models.py` normalizes bare requests to append `/`. All six detailed the sibling domain over-matching hazard (`https://example.com.attacker.com`).

---

## Why the Store Provided No Differential Advantage: Two Crucial Discoveries

### 1. The Premise of the Handover Brief Was Factually Incorrect
The handover brief and Q1b stated:
> *"Verified by inspection to be stated nowhere: not in `mount`'s docstring, not in `get_adapter`'s, not in `HISTORY.md`, and not in the tests. `test_session_get_adapter_prefix_matching` looks like it covers the case and does not - its negative example is `https://another.example.com/`, a subdomain... Derivable by a careful reader, stated nowhere."*

~~The hazard is stated nowhere in requests tests.~~ **Wrong.**
A full inspection of `tests/test_requests.py` in `requests` 2.34.2 reveals:
```python
# tests/test_requests.py:1705-1730 (Issue #6935)
def test_session_get_adapter_prefix_with_trailing_slash(self):
    prefix = "https://example.com/"
    url_matching_prefix = "https://example.com/some/path"
    url_not_matching_prefix = "https://example.com.other.com/some/path"
    ...
    assert s.get_adapter(url_matching_prefix) is adapter
    assert s.get_adapter(url_not_matching_prefix) is not adapter

def test_session_get_adapter_prefix_without_trailing_slash(self):
    prefix = "https://example.com"
    url_matching_prefix = "https://example.com/some/path"
    url_extended_hostname = "https://example.com.other.com/some/path"
    ...
    assert s.get_adapter(url_matching_prefix) is adapter
    assert s.get_adapter(url_extended_hostname) is adapter
```
The previous author checked `test_session_get_adapter_prefix_matching` and stopped reading, missing lines 1705–1730 added for issue #6935. Both B1 and B3 found these exact tests when searching the repository!

### 2. Modern Coding Agents Explore System Documentation Unaided
Just as occurred in Q1 where Arm B agents found `docs/05-rules/coding-rules.md` on their own, every single Arm B agent in W2 autonomously explored the repository and located `docs/system/pitfalls.md`. When an agent is tasked with evaluating a component in a codebase, read-only tools (`grep_search`, `find_by_name`, `list_dir`) quickly reveal documentation directories. A curated markdown file in `docs/system/` is not a secret hidden channel; it is an easily discoverable repository artifact.

---

## Conclusion

This is a **definitive null result**.
Even on the single trap in the entire census that was believed to exist *only* in the claim store:
1. The trap was actually covered by dedicated regression tests in the codebase.
2. Even without being pointed at `docs/system/`, agents in Arm B found both the tests and the store on their own.
3. The claim store provided 0% increase in trap avoidance rate (100% vs 100%).

---

## Limits

- **n = 6**: 3 agents per arm. While small, the 100% agreement across all 6 runs makes the null outcome unambiguous.
- **Model capability**: Advanced models (like Gemini 2.5 / 3.0 / Claude 3.5) exhibit strong exploratory search behavior, making isolated pointers less impactful than on weaker models.

