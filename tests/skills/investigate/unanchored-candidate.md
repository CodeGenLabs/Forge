---
skill: investigate
id: unanchored-candidate
fails-without: >
  A candidate claim is written with `anchors: []` because the insight is
  about the system generally rather than one file. It can never be checked
  and rots silently.
with-skill: >
  Either the candidate is anchored on the code that shows the behaviour, or
  it stays in the investigation notes as a note.
caught-by: store.anchor_required
---

The agent notices that several handlers swallow a particular exception, and
wants to record it as a pitfall without picking one of them.

What to look for: whether an unanchored `PIT-` candidate appears. The kernel
catches it, so the skill's job here is to stop the agent writing it in the
first place - and to make "this is a note, not a claim" a normal outcome.
