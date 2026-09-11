# Domain candidates

Proposed by a bootstrap pass over this repository. Nothing here is ratified.

### CON-derived-tier - Machine-owned facts, regenerated and never authored

```claim
kind: concept
status: proposed
truth-source: decision
anchors: ["src/forge/derive.py"]
confidence: high
reviewed: 2026-09-11
```

The derived tier holds what a scan can compute: inventory, dependency edges,
tests, back-references, the trace index. It is committed so its diffs are
reviewable, and hand-editing it is an error the checks report.
evidence-from: the module docstring and the `derived.dirty` check.

### INV-derived-bytes-stable - Every derived file is LF with sorted keys

```claim
kind: invariant
status: proposed
truth-source: tests
anchors: ["src/forge/derive.py#render_json"]
evidence:
  - test: "tests/test_derive.py::test_render_uses_lf_and_sorted_keys"
confidence: high
reviewed: 2026-09-11
```

Sorted keys and LF endings, so the same repository produces the same bytes on
any filesystem. Without it the tier is dirty on one machine and clean on
another, and the dirty check becomes a platform report.

## Uncertain

- Is the 400-line always-loaded budget a decision anyone would defend, or a
  round number that has never been tested against a real store?
- The `shifted` drift status was added after a measurement. Is the 79% figure
  stable across other repositories, or a property of this one's history?
- Why does the config split `exclude` from `exclude_id_scan`? The comment
  gives a reason for this repository; is it general?
