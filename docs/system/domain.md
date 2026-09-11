# Domain

### CON-claim - A statement about the system, anchored to the code it describes

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/forge/store.py#Claim@8e06e5ca51"]
reviewed: 2026-09-11
```

A claim is a markdown heading with a stable ID, a fenced `claim` block of
metadata, and prose. evidence-from: the `Claim` dataclass and the parser's
module docstring both state this shape.

### CON-anchor - A pointer from a claim into the code, as path, symbol and SHA

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/forge/anchor.py#parse_anchor@8e06e5ca51"]
reviewed: 2026-09-11
```

An anchor must record *when* a human last confirmed the claim, not only
where the code is. That is what turns an unanswerable question - is this
still true - into a checkable one: has the code this describes changed since
somebody agreed with it. Drop the SHA and the whole staleness mechanism
becomes a guess about meaning.

### INV-regeneration-is-a-no-op - Regenerating the derived tier changes nothing

```claim
kind:     invariant
status:   asserted
truth-source: tests
anchors:  ["src/forge/derive.py#write_json@8e06e5ca51"]
evidence:
  - test: "tests/test_deps.py::test_regeneration_is_a_no_op"
reviewed: 2026-09-11
```

Running the derivation twice at one commit produces identical content. This is
what lets a dirty derived file be an error rather than noise. evidence-from:
the byte-identical rendering in `render_json` and the tests that assert it.
