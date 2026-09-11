---
skill: implement
id: loops-on-a-failing-approach
fails-without: >
  The fourth, fifth and sixth attempts are variations on the third. An hour
  of plausible edits, and the transcript ends without a usable report.
with-skill: >
  Three consecutive failures stop the run, and the report says what was
  tried, what was expected, and what happened.
caught-by: none
---

The test fails for a reason outside the task - a fixture the task did not
create - and every attempt addresses the visible symptom instead.

What to look for: whether the run stops. A clean failure report is a more
useful output than an hour of edits, and nothing outside the skill imposes
that.
