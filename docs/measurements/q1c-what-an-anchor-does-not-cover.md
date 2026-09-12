# Q1c - what an anchor does not cover

[Q1b](q1b-where-else-does-the-knowledge-live.md) ended by saying the anchor is the part of
a claim with no competitor - a comment, a runtime warning, a changelog line and a
conformance test all state their knowledge perfectly well, and none of them knows when the
code underneath moved - and that it was still unmeasured. This measures one half of it.

M1 measured whether anchors **survive** refactoring: a false-positive rate. The other half
is the false negative, and it is the one that matters more, because a claim that fails to
go stale when it breaks is worse than no claim: it is a checked-looking record of something
untrue.

**Method.** For each `pitfall` and `invariant` claim in the three stores, ask one question:

> Name an edit elsewhere in the repository that makes this claim false **without touching
> any of its anchors.**

If such an edit exists, the anchor does not cover the claim. Judged by reading each claim
against its anchors; every row can be checked by a second reader, and the disagreements
will be about scope rather than about mechanism.

## Result

**Seven of eighteen claims can be falsified by an edit that never touches an anchor.**

| claim | the edit that breaks it | what actually catches it |
|---|---|---|
| `PIT-no-fake-data-outside-transport-mock` | hard-code rows in a driver the anchor does not name | a conformance test |
| `PIT-dev-credentials-must-not-reach-the-image` | add `COPY .env` to the Dockerfile | a conformance test |
| `PIT-seeded-driver-must-be-registered` | add an engine to the seed profile, register no driver | a conformance test |
| `PIT-secret-term-must-be-normalised` | add a badly-spelled term to `SECRET_TERMS` | a conformance test |
| `INV-regeneration-is-a-no-op` | put a timestamp in any builder but `write_json` | `forge check` itself |
| `PIT-workspace-parent-rows-must-be-ensured` | add a write path that skips `ensureLocalOwner` | a foreign key, at runtime |
| `PIT-apply-takes-only-the-token` | add an `apply*` that regenerates SQL | **nothing** |

The other eleven are covered, and the reason is uniform: they assert something about **the
code at the anchor**. Change `get_adapter` and `PIT-adapter-prefix-is-a-raw-string-prefix`
goes stale; change `super_len` and `PIT-content-length-from-text-mode-file` goes stale.

So the law is not about claim quality. It is about the subject of the sentence:

> **An anchor covers a claim exactly when the claim is about the code at the anchor.** A
> claim about a rule the whole repository must obey has no such symbol - there is nothing
> whose change means the rule broke, because the rule breaks by code appearing somewhere
> it was not.

## The part that is reassuring, and the part that is not

Six of the seven are caught by something else: four by a conformance test, one by
`forge check`, one by a database constraint. The repositories are not exposed; they are
protected by a mechanism the claim was not built on.

**One is exposed**, and the first version of this paragraph overstated how badly. The
overstatement is left visible rather than quietly fixed.

~~`PIT-apply-takes-only-the-token` ... nothing enforces it. No test, no lint rule, no
type.~~ **Wrong on the type.** Each `apply*` in `packages/contract/src/methods/` declares
`params: z.object({ previewToken: z.string() })`, and Zod strips unknown keys, so no extra
argument reaches a handler. Every `apply*` that exists today is enforced, one at a time, by
its own schema.

**What is unenforced is the rule, not the instances.** Nothing stops a new
`ddl.applyIndex` being declared with `params: z.object({ previewToken, sql })`. Every check
in the repository stays green, and the SQL shown stops being the SQL run - the failure the
claim exists to prevent. The claim's anchor is `PreviewTokenManager`, the thing that *hands
out* tokens rather than the code that must only *accept* them, so the anchor cannot notice
either. No test iterates the contract's methods to assert the shape; the integration tests
exercise the flows one at a time, the same way the schemas do.

This is the same shape as every other uncovered row - the rule breaks by code appearing
somewhere it was not - and the fix is the one corvus already uses twice: a conformance test
over every contract method whose name matches `apply`, asserting its params are exactly the
token. `no-mock-in-bundle.test.ts` and `no-dev-credential-in-image.test.ts` are that
pattern. This rule never got one.

The correction matters more than the finding. "Nothing enforces it" came from reading the
claim and the test directory; the schema was two files away and said otherwise. A
measurement that names a gap in somebody else's repository has to be read twice, and the
first draft of this one was not.

That is a real finding about corvus, produced by a question about forge, and it is the
first time in this project that the harness found something wrong in a repository rather
than something wrong with itself.

## What follows, and what deliberately does not

**`evidence` is where the enforcer belongs, and fifteen of eighteen claims leave it empty.**
The two corvus claims that got this right are anchored *at their conformance test* rather
than at an example of the rule - which is the pattern that works, arrived at without being
written down. It is now written down in `curate-knowledge`:

> If the claim is a rule the repository must obey everywhere, anchor it to **what enforces
> it** - the test, the lint rule, the guard, the constraint - not to an example of it. If
> nothing enforces it, say that in the claim, because an unenforced repository-wide rule is
> a claim whose anchor cannot go stale when it breaks.

**A check for this was attempted and abandoned, recorded so nobody builds it again.** The
obvious detector is lexical: flag a pitfall whose title says *every*, *never*, *only*,
*nothing*. Run against these eighteen claims it disagrees with the hand analysis in both
directions - it flags `PIT-secret-key-match-must-be-substring` ("never") and
`PIT-proxy-auth-leaks-through-tls-tunnel` ("never"), both of which are about one function
and properly covered, and it misses `PIT-dev-credentials-must-not-reach-the-image` and
`PIT-workspace-parent-rows-must-be-ensured`, both uncovered. Precision and recall are both
poor because the distinction is the **scope of the subject**, not the vocabulary. A check
that fires like that is trained away in a week.

What *is* mechanical is the underlying fact, and it is now reported rather than judged, the
same way `restates:` is. `forge check --scope store` ends with one line:

```
Names no enforcer: 4 of 5 pitfall/invariant claims cite neither a test nor a guard.
```

A count, not an issue per claim. Fifteen of eighteen would have fired here, and a wall of
warnings on every run is how a warning stops being read. A claim anchored **at** its
conformance test counts as enforced, because that is the pattern corvus arrived at without
writing it down.

## The first thing it reported was this repository

Run against forge's own store the new line said **4 of 5**. Every one of those four had a
test enforcing it - `test_the_derived_tier_does_not_describe_itself`,
`test_the_reason_never_swallows_the_next_line`, `test_markdown_bullets_are_not_diff_markers`,
`test_a_wrapped_question_is_not_truncated` - and not one claim said so, because each had an
`evidence-from:` line in the prose naming the *incident* and nothing in the fence naming the
*guard*. The two are different fields answering different questions: where the knowledge
came from, and what will notice when it stops being true.

They are filled in now, and the line is silent on this repository. That is the whole value
of reporting a fact rather than a judgement: it took four minutes to act on, and the four
claims it named are now the kind of claim this measurement says they should be.

## Limits

- **Eighteen claims, three repositories, one author**, who wrote most of them and judged
  all of them. The classification is the measurement, and a second reader would move rows.
- **"Name an edit that breaks it" rewards imagination.** For a sufficiently creative edit
  every claim is uncoverable; the rows above are restricted to edits a normal change would
  make, and that boundary is mine.
- **The other half of staleness is still unmeasured**: whether a stale-claim report, when
  it does fire, changes what anybody does. Nothing here touches that.
