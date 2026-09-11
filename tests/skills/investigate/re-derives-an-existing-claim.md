---
skill: investigate
id: re-derives-an-existing-claim
fails-without: >
  The agent reads three files to work out what "settlement" means here, and
  writes a candidate concept claim - duplicating `CON-settlement`, which
  already exists and has been reviewed by a human.
with-skill: >
  `forge trace CON-settlement` answers it in one command, and the
  investigation budget goes to the part that is genuinely unknown.
caught-by: store.id_unique
---

The request is about settlement timing. The store already defines
`CON-settlement` and `INV-refund-cap`.

What to look for: whether any `forge trace` runs before the code is read.
The duplicate ID is caught, but the wasted budget is not, and on a large
investigation that is the whole cost.
