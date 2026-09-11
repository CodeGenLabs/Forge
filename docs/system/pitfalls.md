# Pitfalls

### PIT-derived-self-reference - A census that counts its own output never settles

```claim
kind:     pitfall
status:   asserted
truth-source: decision
anchors:  ["src/forge/derive.py#build_inventory@8e06e5ca51"]
reviewed: 2026-09-11
```

A derived file cannot carry the id of the commit that contains it, and a
census that counts its own output moves every time that output is committed.
Both were found the hard way and both made the tier permanently stale.
evidence-from: two corrections recorded in SYSTEM_KNOWLEDGE.md section 2.3.

### PIT-regex-across-newlines - `\s*` crosses the newline and eats the next line

```claim
kind:     pitfall
status:   asserted
truth-source: decision
anchors:  ["src/forge/impact.py@8e06e5ca51"]
reviewed: 2026-09-11
```

Using `\s*` between a captured id and its trailing text swallows the
following line, so "you gave no reason" silently became "the next heading is
your reason". Horizontal whitespace only, in every line-shaped pattern here.
evidence-from: the bug found by the claim-touch reason test.

### PIT-markdown-bullet-is-not-a-diff - A leading dash is not a diff marker

```claim
kind:     pitfall
status:   asserted
truth-source: decision
anchors:  ["src/forge/spec.py@8e06e5ca51"]
reviewed: 2026-09-11
```

Every scenario line in the spec delta grammar is a `- ` bullet, so keying a
diff-fragment check on `^[+-]` rejects every correct MODIFIED block. Key on
`+` and hunk headers instead. evidence-from: the check firing on its own
fixture during M3.

## Uncertain

- Are there pitfalls from using the harness, as opposed to from building it?
  Every candidate here was earned while writing the tool, which is not the
  same population as using it.
