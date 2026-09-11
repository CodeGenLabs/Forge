# Pressure tests: what runs here, and what does not

Each skill ships scenarios describing a failure it is supposed to prevent.
Superpowers' methodology, adopted because it is the only reason to believe a
prompt does anything - but adopted with its limit stated, because the limit is
real and pretending otherwise would be the exact failure this project is about.

## Two halves

**The deterministic half runs in CI** (`tests/test_skills.py`):

- every skill obeys the five rules in ARCHITECTURE.md section 4.2;
- every scenario parses, names a skill that exists, and has a unique id;
- every scenario names the kernel signal that catches its failure, and that
  signal is one the kernel actually emits.

That last one is the check worth having. A skill can claim to prevent
anything; `caught-by` forces each claim to name the mechanism behind it, and
`caught-by: none` is the honest answer when there is no mechanism. Those are
the claims resting on the prompt alone, and counting them is the point - the
set grows quietly if nobody does.

**The model half does not run in CI.** Running a scenario means running an
agent twice - once without the skill to see the failure, once with it - and
the kernel never calls a model. `tools/pressure_test.py` drives that half
against a configured model command and writes the transcripts; without one it
prints what it would run and exits.

## Reading the results

A scenario with a `caught-by` signal is belt and braces: the skill should
prevent the failure and the kernel catches it if the skill does not. Those are
cheap to trust.

A scenario with `caught-by: none` is the skill doing real work, and it is also
the only kind that can silently stop working. Two responses, in order of
preference: move the check into the kernel so the signal exists, or re-run the
scenario when the skill changes. The first is a permanent improvement and the
second is a habit.

## Adding one

```markdown
---
skill: implement
id: scope-creep
fails-without: what the agent does when the skill is not loaded
with-skill: what it does instead
caught-by: trace.claim_touch_complete   # or `none`
---

The situation, concretely enough that two people would set up the same test.
```
