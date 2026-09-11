# ADR-0001 - Adopt an anchored claim store

- Status: Accepted

## Baseline recorded by `forge bootstrap seal`

- Date: 2026-09-11
- Commit: 8e06e5ca51cce6b3afb75e7b5bb737ef3b014793
- Cap in force: 40 ratified claims from this bootstrap

### Ratified

- PIT-derived-self-reference (pitfall, confidence high) - A census that counts its own output never settles
- PIT-regex-across-newlines (pitfall, confidence high) - `\s*` crosses the newline and eats the next line
- PIT-markdown-bullet-is-not-a-diff (pitfall, confidence high) - A leading dash is not a diff marker
- CON-claim (concept, confidence high) - A statement about the system, anchored to the code it describes
- CON-anchor (concept, confidence high) - A pointer from a claim into the code, as path, symbol and SHA
- INV-regeneration-is-a-no-op (invariant, confidence high) - Regenerating the derived tier changes nothing

### Proposed and not ratified

Recorded because the absence of a claim should be explicit. A store
with no record of its own gaps is ambiguous between "nothing to say
here" and "nobody looked", and those call for opposite responses.

- CON-derived-tier (concept, confidence high) - Machine-owned facts, regenerated and never authored
- INV-derived-bytes-stable (invariant, confidence high) - Every derived file is LF with sorted keys

### Deliberately not attempted

- component boundaries and what each part is responsible for - the directories suggest a shape, the responsibility is a judgement
- which properties are *required* rather than merely currently true
- why any of it is like this; rationale is not in the code
- the traps people keep falling into, which are earned from failures and not from a scan

The first change that touches an area will produce better knowledge
about it than any scan, because the change has a reason, a test, and
a human who cared. Bootstrap's job was to make that change possible,
not to front-load a documentation project.
