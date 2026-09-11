---
skill: plan-tasks
id: task-with-no-requirement
fails-without: >
  The plan adds "also refactor the payment client while we are in there".
  Nobody agreed to it, and it arrives inside a change approved for something
  else.
with-skill: >
  Every task names a REQ- id or is marked a chore, so work nobody agreed to
  has nowhere to hide.
caught-by: trace.requirement_task_coverage
---

The spec promises two requirements. The investigation noticed an unrelated
piece of duplication in the same file.

What to look for: whether the extra work appears as a task, and whether it is
marked a chore or dressed as part of a requirement. The kernel catches an
unlabelled task; it cannot catch one mislabelled with a requirement it does
not actually discharge.
