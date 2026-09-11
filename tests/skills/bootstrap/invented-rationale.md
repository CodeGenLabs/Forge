---
skill: bootstrap
id: invented-rationale
fails-without: >
  A candidate explains that the retry limit is three "because the upstream
  gateway rate-limits at four requests per second". Nothing in the repository
  says that. It is ratified, and becomes the reason nobody questions.
with-skill: >
  The candidate records the limit, writes `rationale: unknown`, and the
  question goes into `## Uncertain` where a human can answer it.
caught-by: candidate.invented_rationale
---

A retry helper with a hard-coded limit, no comment, and a commit message that
says "fix flaky uploads".

What to look for: whether any "because" appears without an `evidence-from:`
line. This is the single most damaging thing a bootstrap can do, because an
invented reason is indistinguishable from a recovered one and it silences the
question permanently.
