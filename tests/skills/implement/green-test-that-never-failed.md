---
skill: implement
id: green-test-that-never-failed
fails-without: >
  The test is written after the code and passes first time. It proves the
  code does what the code does, and it would keep passing if the behaviour
  were removed.
with-skill: >
  The test is run before the change, watched failing, and the failure is
  read - because a test that fails for the wrong reason is worse than one
  that never failed.
caught-by: none
---

The task is to reject an over-balance refund. The guard is a three-line `if`.

What to look for: whether the failing run happened and whether its output was
read. Coverage tooling cannot tell a test that constrains behaviour from one
that mirrors it, and `@covers` records intent, not strength.
