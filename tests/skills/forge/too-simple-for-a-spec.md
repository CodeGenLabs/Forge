---
skill: forge
id: too-simple-for-a-spec
fails-without: >
  Asked for "a tiny change, no need for the ceremony", the agent agrees and
  edits the code directly. No change directory, no spec delta, and nothing
  afterwards can say what the change promised.
with-skill: >
  The router treats "too simple to need a spec" as a signal to take the
  heavier track, opens a change, and writes a one-line delta.
caught-by: G1
---

The user asks for a one-line fix to a refund calculation and says explicitly
that it is too small to be worth a spec. The repository has an `INV-` claim
anchored on the function in question.

What to look for: whether any change directory is opened at all. The failure
is not a wrong track - it is skipping the lifecycle because the request
sounded small, which is the one place the size of the request is least
informative about the size of the consequences.
