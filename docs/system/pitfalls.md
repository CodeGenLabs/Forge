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
anchors:  ["src/forge/impact.py@79b07211f8"]
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

### PIT-bullet-continuation-lines - A wrapped bullet is one item, not one line

```claim
kind:     pitfall
status:   asserted
truth-source: code
anchors:  ["src/forge/bootstrap.py#_bullets@cd62b56feb"]
reviewed: 2026-09-11
```

Markdown authors wrap long bullets. A parser that matches `^[-*] (.*)$` keeps the
first physical line and silently discards the rest, so an item reads as a shorter,
different item - never as an error. This has now been hit twice in this kernel, in
two unrelated parsers: `## Uncertain` questions were truncated at their first line
during M5, and `tasks.md` entries lose any `REQ-` id written on a continuation line,
which makes `trace.requirement_task_coverage` block with a page of errors that are
all wrong. `_bullets` is the join; `Change.tasks()` has not adopted it.

The second occurrence is the reason this is written down. The first was found,
fixed, and never recorded, so nothing stopped the same line-based match being
written again three days later in a different file.
