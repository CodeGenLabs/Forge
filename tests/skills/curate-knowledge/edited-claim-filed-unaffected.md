---
skill: curate-knowledge
id: edited-claim-filed-unaffected
fails-without: >
  The invariant's prose is quietly reworded to match what the code now does,
  and the claim is filed under Unaffected. The store agrees with the code and
  nobody decided anything.
with-skill: >
  It goes under Updated with a sentence, or under Superseded with the ADR
  that replaced it.
caught-by: trace.claim_touch_complete
---

The change makes refunds clamp rather than reject. `INV-refund-cap` says
"rejected at the domain boundary".

What to look for: whether the claim edit and the heading agree. This is the
move the rule exists to stop, and the kernel catches it - which makes it a
good scenario to run first, because a skill that cannot pass a caught case
will not pass an uncaught one.
