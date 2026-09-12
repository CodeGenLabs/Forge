# Drift ledger

> Machine-appended, human-resolved. `forge drift record` writes an entry when a
> claim's anchors stop matching what a human confirmed; `forge drift resolve`
> records what that means. The kernel never edits a claim to match the code -
> see SYSTEM_KNOWLEDGE.md section 6.
>
> Verdicts: **V1** the code is wrong. **V2** the claim was never true. **V3** the
> decision changed, and an ADR records it. **V4** the claim is under-specified.

## D-001 - PIT-regex-across-newlines stale

```drift
claim: PIT-regex-across-newlines
detected: '2026-09-11'
detected_by: forge drift
signal: stale
anchors_changed:
- src/forge/impact.py@8e06e5ca51 (stale)
proposed_verdict: V1
proposed_reasoning: The signature changed, so the code this claim describes is not in the
  shape a human confirmed. Proposed V1 because that is the only reading the fingerprint supports
  on its own; the other three are judgements.
status: resolved
verdict: confirmed
resolved: '2026-09-11'
evidence: re-confirmed at 79b07211f8; anchors restamped, prose unchanged
```

## D-002 - PIT-regex-across-newlines stale

```drift
claim: PIT-regex-across-newlines
detected: '2026-09-12'
detected_by: forge drift
signal: stale
anchors_changed:
- src/forge/impact.py@79b07211f8 (stale)
proposed_verdict: confirm
proposed_reasoning: 'Evidence test (tests/test_impact.py::test_the_reason_never_swallows_the_next_line)
  passed (exit 0). The property still holds despite code movement. Proposed confirm: safe
  to restamp with `forge drift confirm <id>`.'
status: resolved
verdict: confirmed
resolved: '2026-09-12'
evidence: re-confirmed at 00ac35f233; anchors restamped, prose unchanged
```

## D-003 - PIT-derived-self-reference shifted

```drift
claim: PIT-derived-self-reference
detected: '2026-09-12'
detected_by: forge drift
signal: shifted
anchors_changed:
- src/forge/derive.py#build_inventory@8e06e5ca51 (shifted)
proposed_reasoning: The body changed and the signature did not. Often harmless; the question
  is whether the property the claim asserts survived.
status: resolved
verdict: confirmed
resolved: '2026-09-12'
evidence: re-confirmed at ec22a88bdd; anchors restamped, prose unchanged
```
