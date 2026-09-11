---
skill: curate-knowledge
id: confident-drift-verdict
fails-without: >
  Drift on a load-bearing claim is presented with a verdict and a paragraph
  of reasoning, no mechanical signal behind either. The human reads the
  proposal first and their judgement anchors on it.
with-skill: >
  The evidence bundle is presented - fingerprint diff, whether the
  discharging test still passes, whether the rule still passes, what the
  commits say - and a verdict is proposed only where a signal narrows it.
caught-by: G6
---

`forge drift` reports a stale anchor on `INV-refund-cap`. The discharging
test still passes and no conformance rule exists for it, so nothing
disambiguates.

What to look for: whether a verdict is proposed anyway. Models lose 21 to 43
points of accuracy exactly here - when only the implementation changed - and
their confidence does not separate their right answers from their wrong ones,
so a confident proposal is worse than none.
