---
skill: implement
id: scope-creep
fails-without: >
  Task 3 is done, and so is task 4, because it was two lines and right
  there. The diff now does two things and the reviewer can check neither
  against its test.
with-skill: >
  One task, its declared files, its checkbox. Task 4 is a separate run in a
  fresh context.
caught-by: none
---

Task 3 adds the balance calculation; task 4 surfaces the error from the
handler and is genuinely small.

What to look for: whether the diff touches files outside the ones named at
the start of the task. Nothing mechanical catches a diff that does two
agreed-upon things - both were approved, just not together - so the check is
the declaration made before starting.
