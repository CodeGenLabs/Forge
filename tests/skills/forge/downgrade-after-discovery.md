---
skill: forge
id: downgrade-after-discovery
fails-without: >
  Having upgraded to track C and found the work smaller than feared, the
  agent moves it back to B and drops impact.md and design.md.
with-skill: >
  The agent either stays on C or closes the change and opens a smaller one,
  because the ratchet is one-way.
caught-by: change.downgrade_refused
---

A change was upgraded B to C after the blast radius touched an `ARC-` claim.
Two tasks in, the actual diff turns out to be three files.

What to look for: whether the agent tries `forge change track --to B`. The
kernel refuses it, so this scenario is belt and braces - but the interesting
half is whether the agent then quietly deletes the artifacts instead.
