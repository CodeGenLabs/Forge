---
skill: bootstrap
id: unprovable-invariant
fails-without: >
  "Order totals are always positive" is proposed as an invariant because the
  code happens never to produce a negative one. Nothing enforces it and no
  test proves it, so the store now asserts a property the system does not
  actually guarantee.
with-skill: >
  With no enforcing guard and no proving test, it is downgraded to a question
  in `## Uncertain`.
caught-by: candidate.unproven_invariant
---

An order module with no validation on the total and a test suite that only
uses positive fixtures.

What to look for: whether the candidate names a guard or a test. Whether a
property is *required* or merely currently true is not in the code, and that
distinction is the whole difference between an invariant and an observation.
