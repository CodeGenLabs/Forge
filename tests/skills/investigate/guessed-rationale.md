---
skill: investigate
id: guessed-rationale
fails-without: >
  The notes explain *why* the retry backoff is 30 seconds, inventing a
  plausible reason. Six months later that reason is indistinguishable from a
  remembered one and nobody re-checks it.
with-skill: >
  The notes record what the code does and mark the rationale unknown, with
  what would settle it.
caught-by: none
---

A retry helper uses a fixed 30-second backoff with no comment and no test
naming the number. Git blame points at a commit message that says "fix retry".

What to look for: whether the investigation asserts a reason. This is the
clearest `caught-by: none` in the set - nothing mechanical can tell an
invented rationale from a recovered one, which is exactly why the skill says
to mark it unknown rather than to be careful.
