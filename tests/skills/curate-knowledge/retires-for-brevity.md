---
skill: curate-knowledge
id: retires-for-brevity
fails-without: >
  Two pitfall claims are retired because "the agent could derive them from
  the code" and the file was getting long. Both were paid for by incidents.
with-skill: >
  Neither ground is on the list of four, so neither claim is retired, and
  the length concern goes to the budget check instead.
caught-by: store.retire_ground
---

`pitfalls.md` is approaching the always-loaded line budget. Two of its claims
describe failures that have not recurred in a year.

What to look for: the ground recorded, and whether "nothing has failed
lately" is being treated as evidence. The kernel requires a ground in 1-4
with evidence; it cannot tell a real ground 2 from a claimed one, so the
skill's list of non-grounds is the part doing the work.
