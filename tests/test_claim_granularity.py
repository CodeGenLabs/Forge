"""Per-claim, not per-file: which claims a diff actually touched.

Every test here comes from one incident. The first real change taken through
the lifecycle appended a single new claim to `docs/system/pitfalls.md`, and the
claim-touch rule then demanded that the three unrelated claims already in that
file be re-filed as `Updated`. The only ways through were to write `Updated`
about claims nobody updated, or to split every claim into its own file - which
is the rubber-stamping OPEN_QUESTIONS.md Q3 asks about, arriving by the front
door on the very first change.
"""

from __future__ import annotations

from datetime import date

import pytest

from forge import change, gitio, impact, store

TODAY = date(2026, 9, 11)

PITFALLS = """\
# Pitfalls

### PIT-one - the first trap

```claim
kind:     pitfall
status:   asserted
truth-source: code
anchors:  ["src/a.py"]
reviewed: 2026-09-01
```

Prose about the first trap, long enough to read like a claim.

### PIT-two - the second trap

```claim
kind:     pitfall
status:   asserted
truth-source: code
anchors:  ["src/b.py"]
reviewed: 2026-09-01
```

Prose about the second trap, long enough to read like a claim.
"""

NEW_CLAIM = """
### PIT-three - the trap this change learned

```claim
kind:     pitfall
status:   asserted
truth-source: code
anchors:  ["src/c.py"]
reviewed: 2026-09-11
```

Prose about the third trap, long enough to read like a claim.
"""


@pytest.fixture
def shared_file(repo):
    """Two claims sharing one file, and a change open against them."""
    from forge.cli import main

    repo.write("src/a.py", "def a():\n    return 1\n")
    repo.write("src/b.py", "def b():\n    return 2\n")
    repo.write("src/c.py", "def c():\n    return 3\n")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/pitfalls.md", PITFALLS)
    repo.commit("two claims in one file")
    change.new_change(repo.root, "learn something", today=TODAY)
    repo.commit("open a change")
    return repo


def touched(repo) -> dict:
    item = change.find_change(repo.root, "1")
    return {t.id: t for t in
            impact.compute_impact(repo.root, item).touched.values()}


# ---------------------------------------------------------------------------
# The incident
# ---------------------------------------------------------------------------

def test_appending_a_claim_does_not_touch_its_neighbours(shared_file):
    """The whole point. Adding PIT-three edits pitfalls.md, but PIT-one and
    PIT-two keep their definitions, so the account owes nothing about them."""
    text = (shared_file.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    shared_file.write("docs/system/pitfalls.md", text + NEW_CLAIM)

    hits = touched(shared_file)
    assert "PIT-three" in hits
    assert "PIT-one" not in hits
    assert "PIT-two" not in hits


def test_editing_a_claim_body_touches_that_claim(shared_file):
    """The rule still has to fire when it should: the mechanism is narrowed,
    not removed."""
    text = (shared_file.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    shared_file.write("docs/system/pitfalls.md",
                      text.replace("Prose about the second trap",
                                   "Completely different prose about the second trap"))

    hits = touched(shared_file)
    assert "PIT-two" in hits
    assert any("own definition" in r for r in hits["PIT-two"].reasons)
    assert "PIT-one" not in hits


def test_editing_a_claim_fence_touches_that_claim(shared_file):
    text = (shared_file.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    shared_file.write("docs/system/pitfalls.md",
                      text.replace("reviewed: 2026-09-01\n```\n\nProse about the first",
                                   "reviewed: 2026-09-11\n```\n\nProse about the first"))

    hits = touched(shared_file)
    assert "PIT-one" in hits
    assert "PIT-two" not in hits


def test_a_new_claim_may_be_filed_under_new(shared_file):
    """`New` counts as an account of a definition edit. Without it the rule
    rejects every change that records a piece of knowledge, which is the single
    most common thing a change should do."""
    assert "New" in impact.CHANGING


# ---------------------------------------------------------------------------
# The primitive underneath
# ---------------------------------------------------------------------------

def test_changed_line_ranges_reports_only_the_edited_lines(repo):
    repo.write("f.txt", "\n".join(f"line {i}" for i in range(1, 21)) + "\n")
    base = repo.commit("twenty lines")
    lines = (repo.root / "f.txt").read_text(encoding="utf-8").split("\n")
    lines[9] = "line ten, edited"
    repo.write("f.txt", "\n".join(lines))

    ranges = gitio.changed_line_ranges(repo.root, base, "f.txt")
    assert ranges == [(10, 10)]


def test_changed_line_ranges_reports_an_added_file_whole(repo):
    """A file with no baseline has no hunks. Reporting nothing there would
    quietly answer "you changed none of it"."""
    repo.write("seed.txt", "x\n")
    base = repo.commit("a baseline that does not contain the new file")
    repo.write("added.txt", "one\ntwo\nthree\n")

    ranges = gitio.changed_line_ranges(repo.root, base, "added.txt")
    assert ranges == [(1, 4)]


def test_changed_line_ranges_is_empty_for_an_untouched_file(repo):
    repo.write("f.txt", "unchanged\n")
    base = repo.commit("one file")
    assert gitio.changed_line_ranges(repo.root, base, "f.txt") == []


def test_overlap_falls_back_to_the_heading_line_alone(shared_file):
    """A claim with no recorded end_line falls back to its heading, never to
    the whole file - that would restore the behaviour this replaces, in the
    case where the parser already knows something is wrong."""
    assert impact._overlaps([(5, 5)], 5, 0) is True
    assert impact._overlaps([(6, 9)], 5, 0) is False


# ---------------------------------------------------------------------------
# A claim's prose ends where its section does
# ---------------------------------------------------------------------------

WITH_TRAILING_SECTION = """\
# Domain

### CON-one - the first concept

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/a.py"]
reviewed: 2026-09-01
```

Prose belonging to CON-one, long enough to read like a real claim.

## Uncertain

- Whether the retry budget is per request or per session. Nobody could say.
- Whether the cache is allowed to serve a stale row during a migration.
"""


def test_a_trailing_section_is_not_part_of_the_last_claim(repo):
    """It was. Thirty lines of open questions were absorbed into the last
    claim's prose, counted against the always-loaded budget as claim text, and
    pushed its `end_line` past its real end."""
    claims = store.parse_claims(WITH_TRAILING_SECTION, "docs/system/domain.md")
    (claim,) = claims
    assert "## Uncertain" not in claim.prose
    assert "retry budget" not in claim.prose
    assert claim.prose.strip().endswith("like a real claim.")


def test_the_end_line_stops_at_the_section_break(repo):
    """`end_line` decides whether a diff edited this claim's own definition, so
    an overshoot demands an account for a change to an unrelated section."""
    (claim,) = store.parse_claims(WITH_TRAILING_SECTION, "docs/system/domain.md")
    lines = WITH_TRAILING_SECTION.split("\n")
    assert lines[claim.end_line - 1].strip().endswith("like a real claim.")


def test_editing_a_trailing_section_does_not_touch_the_claim(shared_file):
    """The end-to-end consequence, on the rule that cares."""
    target = shared_file.root / "docs/system/pitfalls.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n## Uncertain\n\n- One open question nobody has answered.\n",
        encoding="utf-8", newline="\n")
    shared_file.commit("add an Uncertain section")

    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace("One open question nobody has answered.",
                                   "A different open question entirely."),
                      encoding="utf-8", newline="\n")
    assert "PIT-two" not in touched(shared_file)


def test_a_claim_before_another_claim_is_unaffected(repo):
    """The narrowing must not break the ordinary case."""
    text = WITH_TRAILING_SECTION.replace(
        "## Uncertain",
        "### CON-two - the second concept\n\n```claim\n"
        "kind:     concept\nstatus:   asserted\ntruth-source: decision\n"
        'anchors:  ["src/b.py"]\nreviewed: 2026-09-01\n```\n\nProse for two.\n\n## Uncertain')
    claims = store.parse_claims(text, "docs/system/domain.md")
    assert [c.id for c in claims] == ["CON-one", "CON-two"]
    assert "Prose for two." in claims[1].prose
    assert "## Uncertain" not in claims[1].prose


# ---------------------------------------------------------------------------
# The base a change is measured from
# ---------------------------------------------------------------------------

def test_a_second_change_is_not_measured_from_the_first(repo):
    """`first_commit_touching` used `--follow`. Rename detection matched one
    change's `.forge.yaml` to the previous change's, which `forge archive` had
    moved into `changes/archive/`, and followed the history back to where that
    was added. Every change after the first then measured itself from an
    earlier change's creation commit."""
    from forge.cli import main

    repo.write("src/a.py", "def a():\n    return 1\n")
    main(["init", "--repo", str(repo.root)])
    repo.commit("a scaffolded project")

    change.new_change(repo.root, "the first change", today=TODAY)
    repo.write("src/a.py", "def a():\n    return 2\n")
    first = repo.commit("open and do the first change")

    # Archive moves the first change's `.forge.yaml`, which is what created the
    # rename for git to detect.
    archive = repo.root / "changes/archive/2026-09-11-0001-the-first-change"
    archive.parent.mkdir(parents=True, exist_ok=True)
    (repo.root / "changes/0001-the-first-change").rename(archive)
    repo.commit("archive the first change")

    change.new_change(repo.root, "the second change", today=TODAY)
    repo.commit("open the second change")

    item = change.find_change(repo.root, "2")
    assert impact.resolve_base(repo.root, item) != gitio.rev_parse(repo.root, first)


def test_first_commit_touching_reports_the_path_it_was_asked_about(repo):
    repo.write("one.txt", "first\n")
    a = repo.commit("add one.txt")
    repo.write("two.txt", "second\n")
    repo.commit("add two.txt")

    assert gitio.first_commit_touching(repo.root, "one.txt") == gitio.rev_parse(repo.root, a)


# ---------------------------------------------------------------------------
# A carriage return is not an edit
# ---------------------------------------------------------------------------

def test_rewriting_a_file_with_the_other_line_endings_is_not_an_edit(repo):
    """Any editor or script that rewrites a store file with CRLF otherwise
    marks every claim in it as edited, and the claim-touch rule then demands an
    account for all of them - the rubber-stamping R1 removed, through a third
    door."""
    target = repo.root / "notes.md"
    target.write_bytes(b"alpha\nbeta\ngamma\n")
    base = repo.commit("LF")
    target.write_bytes(b"alpha\r\nbeta\r\ngamma\r\n")

    assert gitio.changed_line_ranges(repo.root, base, "notes.md") == []


def test_a_real_edit_beside_a_line_ending_change_is_still_seen(repo):
    """The narrowing must not swallow the edit it is meant to isolate."""
    target = repo.root / "notes.md"
    target.write_bytes(b"alpha\nbeta\ngamma\n")
    base = repo.commit("LF")
    target.write_bytes(b"alpha\r\nBETA\r\ngamma\r\n")

    assert gitio.changed_line_ranges(repo.root, base, "notes.md") == [(2, 2)]


def test_reindenting_a_line_is_still_an_edit(repo):
    """`--ignore-cr-at-eol`, not `-w`: reindenting a claim's body is an edit
    to it."""
    target = repo.root / "notes.md"
    target.write_bytes(b"alpha\nbeta\n")
    base = repo.commit("flush left")
    target.write_bytes(b"alpha\n    beta\n")

    assert gitio.changed_line_ranges(repo.root, base, "notes.md") == [(2, 2)]
