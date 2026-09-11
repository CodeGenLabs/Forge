---
skill: plan-tasks
id: migration-ordered-late
fails-without: >
  The migration is listed last, after the tasks that read the new column.
  Every one of them fails, and the failure looks like a code bug.
with-skill: >
  The migration comes first and is marked blocking, because nothing after it
  can even be started correctly.
caught-by: none
---

The change adds a column and three call sites that read it.

What to look for: the order. Requirement coverage is satisfied either way -
the kernel pairs requirements with tasks but has no opinion about sequence -
so this is the skill's own contribution and nothing catches it.
