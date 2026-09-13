# Q1b - where else does each claim's knowledge already live?

[Q1](q1-does-the-store-help.md) ran six agents on one trap and got a null result: the
store added nothing, because the trap already had four written homes and the agents found
them. That was n=6 on one claim. This asks the same question of **every** pitfall in both
stores, by inspection rather than by anecdote - so it is reproducible, and a reader can
disagree with a row instead of with a number.

**Method.** For each `PIT-` claim in the two bootstrapped repositories, find the
strongest *other* record of the same knowledge and classify it: a prose document, the
code at or near the anchor, a test that fails if you get it wrong, or nothing. The
selection was mechanical - `forge`'s own `bootstrap.restates()` partitions claims by
whether their evidence names a document - and the classification is a judgement, made by
reading each anchor and grepping for the hazard. Every row below names the file that
settles it.

## The census

**studio-monorepo** (TypeScript monorepo, `docs/05-rules/` tree, 7 pitfalls)

| claim | strongest other home | where |
|---|---|---|
| `PIT-secret-key-match-must-be-substring` | code, at the anchor | an eleven-line comment atop `redact.ts` citing the audit |
| `PIT-no-fake-data-outside-transport-mock` | prose, four times | coding-rules §3.8/§7.4, review-checklist §5, spec FR-014, invariant IV-A |
| `PIT-dev-credentials-must-not-reach-the-image` | a test | `tools/__tests__/no-dev-credential-in-image.test.ts` |
| `PIT-workspace-parent-rows-must-be-ensured` | code, at the anchor | comment naming the FK, plus an error message that names the fix |
| `PIT-apply-takes-only-the-token` | prose | coding-rules + `audit-2026-08-18.md` |
| `PIT-seeded-driver-must-be-registered` | **nothing** | the covering test exists only because run 3 wrote it |
| `PIT-secret-term-must-be-normalised` | **nothing** | `redact.ts`'s comment states the doctrine, never the normalisation gap |

**requests** (flat Python library, no rules document, 6 pitfalls)

| claim | strongest other home | where |
|---|---|---|
| `PIT-proxy-auth-leaks-through-tls-tunnel` | code, at the anchor | `sessions.py`: "Avoid appending this to TLS tunneled requests where it may be leaked" |
| `PIT-netrc-lookup-must-use-parsed-hostname` | prose | `HISTORY.md`; the code shows `ri.hostname` and says nothing about why |
| `PIT-no-proxy-matching-is-not-endswith` | prose | `HISTORY.md`; the boundary logic is visible, the hazard is not named |
~~| `PIT-adapter-prefix-is-a-raw-string-prefix` | **nothing** | see below |~~
| `PIT-adapter-prefix-is-a-raw-string-prefix` | a test | `tests/test_requests.py:1705-1730` (issue #6935) |
| `PIT-content-length-from-text-mode-file` | code, at the anchor | `super_len` raises `FileModeWarning` with a paragraph of explanation |
| `PIT-redirected-body-must-be-rewound` | code, at the anchor | `rewind_body`'s docstring and the named `UnrewindableBodyError` |

**Tally: ~~10~~ 11 of 13 have a home a reader meets while doing the work.** Four in a prose
document, five in the code at the anchor, ~~one~~ two in a test. ~~Three~~ Two have none.

## The one that is worth looking at closely

`PIT-adapter-prefix-is-a-raw-string-prefix` says that `Session.mount("https://example.com", a)`
also captures `https://example.com.other.com`, because `get_adapter` matches with
`str.startswith`.

~~Nothing in the repository states this:
- `mount`'s docstring says only that adapters are sorted by descending prefix length.
- `get_adapter`'s docstring says only that it returns the appropriate adapter.
- `HISTORY.md` has no entry.
- `test_session_get_adapter_prefix_matching` looks like it covers the case and does not:
  its negative example is `https://another.example.com/`, a **sub**domain, which does not
  start with the prefix. The sibling-domain case is absent.
- `test_transport_adapter_ordering` mounts `http://git` alongside `http://github.com`, so
  a careful reader can *derive* the hazard from it. Nobody states it.~~

**Correction (2026-09-12, during W2):**
The claim that this hazard was stated nowhere was an overclaim caused by checking `test_session_get_adapter_prefix_matching` and stopping. `tests/test_requests.py` lines 1705–1730 carries two dedicated tests added for issue #6935: `test_session_get_adapter_prefix_with_trailing_slash` and `test_session_get_adapter_prefix_without_trailing_slash`, which explicitly test matching against `https://example.com.other.com`. The knowledge lives in the tests, which is why all three Arm B agents found it during W2.

## What the census says that Q1 could not

**The source of a candidate predicts whether it is redundant.** Every claim in the
"prose" rows was written by reading the document it restates. The three orphans were not:
two were earned by making a change in run 3 - a registry gap and a normalisation gap that
a wrong test had to find first - and the third came from bootstrap reading `get_adapter`
closely instead of reading a changelog.

So the rule is not "bootstrap produces redundant claims and changes produce good ones".
Bootstrap produced the best orphan in this census. The rule is about **what was read**:

> A candidate read out of a document restates that document. A candidate read out of
> code, or earned by a change that went wrong, is the one with no other home.

`bootstrap.restates()` separates the first class mechanically, which is why it is now
printed in the review sheet. The second class has no detector and does not need one - it
is what the cap should be spent on.

## What follows for the design

**The prose of a claim is its weakest part.** Ten of thirteen claims are a second copy of
something the reader meets anyway, and Q1 measured what that copy buys on one of them:
nothing, at 40% more tool calls. Writing better claim prose is not where the next
improvement is.

**The anchor is the part with no competitor.** A comment atop `redact.ts`, a
`FileModeWarning`, a line in `HISTORY.md` and a conformance test all state their
knowledge perfectly well and none of them knows when the code underneath moved. That is
the one thing on this list that only the store does, and - stated plainly because it is
uncomfortable - **it is still unmeasured.** Q1 did not test it and neither does this.

## Limits

- **Thirteen claims, two repositories, one author.** I wrote or ratified every claim in
  this census, and I classified them. A second reader would move rows.
- **"Strongest other home" is a judgement**, and the interesting cases are the ambiguous
  ones: `PIT-workspace-parent-rows-must-be-ensured` has a comment naming the foreign key
  but not the two-commit history of getting it wrong, and calling that "homed" is a
  choice that cuts against the store.
- **requests was read from its sdist**, which omits the Sphinx `docs/` tree the project
  actually ships. Three rows cite `HISTORY.md`; upstream prose might home more of them.
  This limit biases the census *toward* the store, and the finding survives it anyway.
- **This says nothing about staleness**, which is the whole remaining question.
