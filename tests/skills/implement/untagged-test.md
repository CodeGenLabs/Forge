---
skill: implement
id: untagged-test
fails-without: >
  The test exists and passes, but carries no `@covers` tag. The requirement
  is still undischarged, and `forge verify` says so at the end of the change
  when the fix is least convenient.
with-skill: >
  The tag is written with the test, in the same edit.
caught-by: trace.requirement_discharged
---

A task discharges `REQ-refunds-1` with a new test in an existing file that
already has several untagged tests.

What to look for: whether the tag appears. The kernel catches this, so the
skill's value is only in *when* - at the task, where the requirement is still
in mind, rather than at verification.
