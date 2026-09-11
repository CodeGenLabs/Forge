---
name: implement
phase: implement
description: >
  Do exactly one task from tasks.md, test first, inside the declared file
  scope and budget.
requires-kernel: ["forge change show", "forge impact", "forge check", "forge verify"]
reads: from-dag
writes: ["tasks.md", "the task's source and test files"]
---

# implement

## Announce

> Running `implement` for task \<n>: \<the task line, verbatim>.

## What this does

One task. Not the next one as well, not a tidy-up noticed on the way. The
scope of this skill is deliberately one line of `tasks.md`, because a diff
that does one thing is the only kind a reviewer can actually check.

Run each task in a fresh context. Carrying the previous task's context is how
the tenth task ends up implemented against the first task's assumptions.

## 1. Take the task

```bash
forge change show <n>
```

Take the first unchecked task. Read it verbatim into the announcement, so the
transcript records which one this was.

State before starting:

- which files you expect to touch;
- which test will fail first.

Both are cheap to write and they are what makes "went out of scope"
observable rather than arguable.

## 2. Red

Write the failing test first, and run it.

Watch it fail, and read the failure. A test that passes before the change
proves nothing, and a test that fails for the wrong reason - an import error,
a typo in the fixture - is worse, because it will pass as soon as the typo is
fixed and be counted as evidence.

Tag it with the requirement it discharges:

```python
# @covers REQ-refunds-1
def test_refund_over_balance_is_rejected():
    ...
```

That tag is what lets the kernel pair requirements with tests. Without it the
test exists and the requirement is still undischarged.

## 3. Green

The smallest change that passes the test. Not the general version, not the
version that also handles the case in the next task.

If making it pass requires touching a file you did not name in step 1, stop
and say so before doing it. The usual cause is that the task was mis-sized,
and the fix is to split it rather than to widen quietly.

## 4. Refactor

Only with the test green, and only in the code this task touched. Run the
test again afterwards.

## 5. Stop conditions

Stop and report rather than continuing when:

- **three consecutive attempts fail.** A fourth is rarely different. Say what
  you tried, what you expected, and what actually happened;
- **the task needs a decision the spec does not make.** That is a gap in the
  spec, and guessing hides it;
- **you find a high-risk operation** - a destructive migration, a permission
  or credential change, anything touching authentication. That is gate G4 and
  it is shown to a human immediately, on any track;
- **the change would break a claim.** Check with `forge impact --change <n>`.
  Breaking an invariant is a decision, not an implementation detail.

Stopping is a normal outcome. The budget exists so that an agent that is lost
stops being expensive, and reporting a clean failure is more useful than an
hour of plausible edits.

## 6. Close the task

Tick the checkbox. Then:

```bash
forge check --scope change --change <n>
```

If the diff touched a claimed file, the claim-touch account owes it a line -
`forge impact --change <n>` says which. Write it now, while you remember why,
rather than at the end when it becomes an archaeology exercise.

## 7. After the last task

```bash
forge verify --change <n>
```

Eight conditions, of which the tests passing is one. Read what it reports
rather than the exit code alone: a verdict of `pass` with conditions listed as
still unchecked by this kernel is not the same as everything being proven, and
the report says which.

## Exit

One task done, its test green, its checkbox ticked, and the claim-touch
account current. Hand back to the router for the next task.
