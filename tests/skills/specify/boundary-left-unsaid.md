---
skill: specify
id: boundary-left-unsaid
fails-without: >
  "A refund never exceeds the captured amount" is written with one happy-path
  scenario. Whether an over-balance request is rejected or clamped is never
  stated, and the implementation picks one.
with-skill: >
  The requirement says which, and a scenario covers it, because that is the
  detail most often left out and most often implemented wrong.
caught-by: none
---

The user asks for refunds with a cap. They do not say what happens when
somebody asks for more than the cap.

What to look for: whether any scenario covers the boundary, and whether the
requirement says what it is quantified over - each refund, or their sum. The
grammar requires a scenario; it cannot require a useful one.
