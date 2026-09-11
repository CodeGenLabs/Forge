---
skill: bootstrap
id: confident-architecture-claims
fails-without: >
  The scan emits thirty `CMP-` and `ARC-` candidates describing the directory
  structure in confident prose. Most are restatements, several are wrong, and
  a human approving in batches of thirty approves the wrong ones.
with-skill: >
  Pitfalls and concepts are front-loaded, architecture is left to the first
  change that touches it, and the total is capped at forty.
caught-by: store.derivable_smell
---

A monorepo with eight top-level packages, conventional layout, no existing
documentation. The directory names are suggestive and mostly accurate.

What to look for: the ratio of `CMP-`/`ARC-` candidates to `PIT-`/`CON-`. The
derivable-claim linter catches prose that is its own anchors rearranged, but
it cannot catch a component claim that is *plausible and wrong* about
responsibility, and responsibility is the part `ls` cannot tell you.
