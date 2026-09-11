---
skill: forge
id: hidden-migration
fails-without: >
  A request phrased as "add a nullable column" is classified track B, because
  it touches one table and reads as routine. The migration lands with no
  design and no ADR.
with-skill: >
  The router checks the four forced signals, sees a migration, and takes
  track C regardless of how the request was phrased.
caught-by: G1
---

The user asks to add a column and backfill it. Nothing in the phrasing
suggests risk; the word "migration" never appears.

What to look for: whether the track decision cites the signal rather than the
size. A track chosen from how a request sounds is a track chosen from how
carefully the user phrased it.
