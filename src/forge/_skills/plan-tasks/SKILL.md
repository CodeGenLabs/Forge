---
name: plan-tasks
phase: tasks
description: >
  Turn the spec and design into ordered, checkable tasks, each naming the
  requirement it discharges.
requires-kernel: ["forge instructions", "forge impact", "forge gate", "forge change show"]
reads: from-dag
writes: ["changes/${change}/tasks.md"]
---

# plan-tasks

## Announce

> Running `plan-tasks`: turning the spec into ordered work.

## What this does

Writes `changes/<n>/tasks.md`: the ordered list of work that discharges the
spec. One task is one sitting - a red-green cycle with a reviewable diff.

## 1. Load the contract

```bash
forge instructions tasks --change <n>
forge impact --change <n>
```

The impact set matters here because a task that touches a claimed file owes
that claim an account, and it is cheaper to see that while ordering the work
than while doing it.

## 2. The format

```markdown
## 1. Refund domain logic

- [ ] Add the remaining-balance calculation to the refund domain (REQ-refunds-1)
- [ ] Reject an over-balance refund at the domain boundary (REQ-refunds-1)

## 2. Transport

- [ ] Surface `refund_exceeds_balance` from the handler (REQ-refunds-2)
- [ ] chore: drop the now-unused clamp helper
```

Every task line carries either a `REQ-` id or the word `chore`. That is
checked, and both directions are checked: a requirement with no task is a
promise nobody planned to keep, and a task with no requirement is work nobody
agreed to - which is the most common way a change grows past what was
approved.

## 3. Ordering

Order by dependency, not by comfort:

- a migration comes before anything that reads the new column, always;
- the domain rule comes before the transport that exposes it, so the rule can
  be tested without standing up a server;
- anything that changes an interface comes before its callers.

Mark a task `[BLOCKING]` when the tasks after it cannot even be started
correctly until it lands. Use it sparingly; if everything is blocking the
ordering is not saying anything.

## 4. Sizing

One task is one red-green cycle. If a task cannot be stated as "this test
fails, then this test passes", it is two tasks or it is a chore.

Signs a task is too big: it names more than one requirement, its description
needs the word "and", or you cannot say what test proves it. Signs it is too
small: it has no test of its own, and it is really a step inside the next
task.

## 5. No placeholders

No `TBD`, no "figure out the approach", no "investigate X". Those are not
tasks; they are admissions that the spec or the design is not finished, and
the honest response is to go back to `specify` rather than to plan around the
hole.

If a task genuinely depends on something only discoverable while doing it,
say what the decision is and what the options are, so the person doing it
recognises the moment.

## 6. Check it

```bash
forge gate analyze:post --change <n>
forge change show <n>
```

The gate pairs requirements with tasks in both directions. `forge change show`
confirms the change is no longer blocked on anything else.

## Exit

Every requirement has at least one task, every task names a requirement or is
a chore, the order respects the dependencies, and nothing says TBD. Hand off
to `implement`, one task at a time.
