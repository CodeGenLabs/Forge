---
skill: specify
id: modified-as-a-fragment
fails-without: >
  A MODIFIED block carries only the sentence that changed. The fold applies
  it and the permanent spec ends up saying less than either version did.
with-skill: >
  MODIFIED carries the requirement's full new text, scenarios included.
caught-by: spec.grammar
---

A requirement needs one clause changed: "up to its remaining balance" becomes
"up to its remaining balance, clamped".

What to look for: whether the block reads as a whole requirement. The kernel
catches the obvious diff-fragment shape and a short block, but a plausible
two-line block that silently drops a scenario slips through both - so the
skill's reason ("a reviewer reads what the system will do, not a patch") is
doing the work.
