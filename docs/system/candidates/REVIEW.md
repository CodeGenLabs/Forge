# Candidate review

Every verdict below starts at `reject`, and that is the posture, not a
placeholder. Baseline completeness is not the goal; baseline
trustworthiness is. Twelve ratified claims plus a complete derived tier
is a good outcome, and forty half-checked ones is a liability that
surfaces six months later when one of them is wrong.

Verdicts: `ratify`, `edit`, `reject`, `defer`. `edit` means ratify
after you change the prose; make the edit in the candidate file itself.

Cap in force: 40 ratified claims from this bootstrap.

## Batch 1

- [ratify] PIT-derived-self-reference (pitfall, confidence high) - A census that counts its own output never settles  (pitfall, confidence high) - A census that counts its own output never settles  (pitfall, confidence high) - A census that counts its own output never settles
      anchors: src/forge/derive.py#build_inventory
      defined: docs/system/candidates/pitfalls.md:3
- [ratify] PIT-regex-across-newlines (pitfall, confidence high) - `\s*` crosses the newline and eats the next line  (pitfall, confidence high) - `\s*` crosses the newline and eats the next line  (pitfall, confidence high) - `\s*` crosses the newline and eats the next line
      anchors: src/forge/impact.py
      defined: docs/system/candidates/pitfalls.md:19
- [ratify] PIT-markdown-bullet-is-not-a-diff (pitfall, confidence high) - A leading dash is not a diff marker  (pitfall, confidence high) - A leading dash is not a diff marker  (pitfall, confidence high) - A leading dash is not a diff marker
      anchors: src/forge/spec.py
      defined: docs/system/candidates/pitfalls.md:35
- [ratify] CON-claim (concept, confidence high) - A statement about the system, anchored to the code it describes  (concept, confidence high) - A statement about the system, anchored to the code it describes  (concept, confidence high) - A statement about the system, anchored to the code it describes
      anchors: src/forge/store.py#Claim
      defined: docs/system/candidates/domain.md:5
- [ratify] CON-anchor (concept, confidence high) - A pointer from a claim into the code, as path, symbol and SHA  (concept, confidence high) - A pointer from a claim into the code, as path, symbol and SHA  (concept, confidence high) - A pointer from a claim into the code, as path, symbol and SHA
      anchors: src/forge/anchor.py#parse_anchor
      defined: docs/system/candidates/domain.md:20
- [reject] CON-derived-tier (concept, confidence high) - Machine-owned facts, regenerated and never authored  (concept, confidence high) - Machine-owned facts, regenerated and never authored  (concept, confidence high) - Machine-owned facts, regenerated and never authored
      anchors: src/forge/derive.py
      defined: docs/system/candidates/domain.md:36
- [ratify] INV-regeneration-is-a-no-op (invariant, confidence high) - Regenerating the derived tier changes nothing  (invariant, confidence high) - Regenerating the derived tier changes nothing  (invariant, confidence high) - Regenerating the derived tier changes nothing
      anchors: src/forge/derive.py#write_json
      defined: docs/system/candidates/domain.md:52
- [reject] INV-derived-bytes-stable (invariant, confidence high) - Every derived file is LF with sorted keys  (invariant, confidence high) - Every derived file is LF with sorted keys  (invariant, confidence high) - Every derived file is LF with sorted keys
      anchors: src/forge/derive.py#render_json
      defined: docs/system/candidates/domain.md:69

## Questions the scan could not answer

These are worth more than most of the candidates above. A scan
that says what it could not determine is telling you where to
look; one that quietly fills the gap is not.

From `docs/system/candidates/domain.md`:
- Is the 400-line always-loaded budget a decision anyone would defend, or a round number that has never been tested against a real store?
- The `shifted` drift status was added after a measurement. Is the 79% figure stable across other repositories, or a property of this one's history?
- Why does the config split `exclude` from `exclude_id_scan`? The comment gives a reason for this repository; is it general?

From `docs/system/candidates/pitfalls.md`:
- Are there pitfalls from using the harness, as opposed to from building it? Every candidate here was earned while writing the tool, which is not the same population as using it.
