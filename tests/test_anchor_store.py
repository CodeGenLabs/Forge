"""`classify_store`: drift asked of the whole claim store, grouped by claim.

The per-anchor engine is measured in `tests/test_anchor.py` and in
`docs/measurements/M1-anchor-stability.md`. What is tested here is the loop on
top of it: which claims get scanned, how several anchors reduce to one verdict,
who is obligated by the answer, and that asking the question changes nothing.
"""

from __future__ import annotations

from forge import anchor
from forge.anchor import Status


def claim_file(repo, path: str, body: str) -> None:
    repo.write(path, body)


def one_claim(sha: str, *, ident: str = "CON-x", status: str = "asserted",
              anchors: str = "src/app.py#greet") -> str:
    return (
        f"# Domain\n\n"
        f"### {ident} - a title for {ident}\n\n"
        "```claim\n"
        "kind:     concept\n"
        f"status:   {status}\n"
        "truth-source: decision\n"
        f'anchors:  ["{anchors}@{sha}"]\n'
        "reviewed: 2026-09-11\n"
        "```\n\n"
        "Prose that says something about the system.\n"
    )


def seed(repo, source: str = "def greet():\n    return 'hi'\n") -> str:
    repo.write("src/app.py", source)
    return repo.commit("the code a claim will point at")


# ---------------------------------------------------------------------------
# REQ-drift-store-scan
# ---------------------------------------------------------------------------

def test_a_fresh_store_reports_every_claim_fresh(repo):
    base = seed(repo)
    claim_file(repo, "docs/system/domain.md", one_claim(base))
    repo.commit("a claim")

    drifts = anchor.classify_store(repo.root)
    assert [d.claim_id for d in drifts] == ["CON-x"]
    assert drifts[0].status is Status.FRESH
    assert drifts[0].changed is False


def test_a_moved_symbol_makes_its_claim_not_fresh(repo):
    base = seed(repo)
    claim_file(repo, "docs/system/domain.md", one_claim(base))
    repo.commit("a claim")
    repo.write("src/app.py", "def greet(name):\n    return f'hi {name}'\n")
    repo.commit("the signature changed")

    (drift,) = anchor.classify_store(repo.root)
    assert drift.changed is True
    assert drift.status is Status.STALE
    assert [str(r.anchor) for r in drift.culprits] == [f"src/app.py#greet@{base}"]


def test_a_claim_is_as_stale_as_its_worst_anchor(repo):
    """Three anchors, one stale: one finding, at the worst status, naming only
    the anchor that caused it. Reporting per anchor would make a five-anchor
    claim five decisions about one question."""
    repo.write("src/app.py", "def greet():\n    return 'hi'\n")
    repo.write("src/other.py", "def calm():\n    return 0\n")
    repo.write("src/third.py", "def still():\n    return 1\n")
    base = repo.commit("three modules")
    repo.write("docs/system/domain.md",
               "# Domain\n\n### CON-x - a title for CON-x\n\n"
               "```claim\n"
               "kind:     concept\n"
               "status:   asserted\n"
               "truth-source: decision\n"
               f'anchors:  ["src/app.py#greet@{base}", "src/other.py#calm@{base}", '
               f'"src/third.py#still@{base}"]\n'
               "reviewed: 2026-09-11\n"
               "```\n\nProse.\n")
    repo.commit("a claim with three anchors")
    repo.write("src/other.py", "def calm(loudly):\n    return 0\n")
    repo.commit("only the middle one moved")

    (drift,) = anchor.classify_store(repo.root)
    assert drift.status is Status.STALE
    assert len(drift.results) == 3
    assert [r.anchor.path for r in drift.culprits] == ["src/other.py"]


def test_a_malformed_anchor_does_not_abort_the_walk(repo):
    """One bad anchor must not make the scan silent about every other claim -
    the rule `trace.py` already settled for the index."""
    base = seed(repo)
    repo.write("docs/system/domain.md",
               one_claim(base, ident="CON-good")
               + "\n### CON-bad - a title for CON-bad\n\n"
                 "```claim\n"
                 "kind:     concept\n"
                 "status:   asserted\n"
                 "truth-source: decision\n"
                 'anchors:  ["src/app.py#not a symbol@abc123"]\n'
                 "reviewed: 2026-09-11\n"
                 "```\n\nProse.\n")
    repo.commit("one good claim and one malformed anchor")

    drifts = {d.claim_id: d for d in anchor.classify_store(repo.root)}
    assert drifts["CON-good"].status is Status.FRESH
    assert drifts["CON-bad"].results == []
    assert drifts["CON-bad"].errors
    assert drifts["CON-bad"].changed is True


def test_an_anchor_with_no_sha_is_an_error_not_a_crash(repo):
    """Bootstrap candidates are written without a `@sha`. The scan has to say
    so rather than raise, or a freshly sealed store cannot be scanned at all."""
    seed(repo)
    repo.write("docs/system/domain.md",
               "# Domain\n\n### CON-x - a title for CON-x\n\n"
               "```claim\n"
               "kind:     concept\n"
               "status:   asserted\n"
               "truth-source: decision\n"
               'anchors:  ["src/app.py#greet"]\n'
               "reviewed: 2026-09-11\n"
               "```\n\nProse.\n")
    repo.commit("an unstamped anchor")

    (drift,) = anchor.classify_store(repo.root)
    assert drift.status is None
    assert "no @sha" in drift.errors[0][1]


# ---------------------------------------------------------------------------
# Who is obligated
# ---------------------------------------------------------------------------

def test_a_candidate_is_scanned_but_does_not_obligate(repo):
    base = seed(repo)
    claim_file(repo, "docs/system/candidates/domain.md",
               one_claim(base, ident="CON-p", status="proposed"))
    repo.commit("a candidate")
    repo.write("src/app.py", "def greet(name):\n    return name\n")
    repo.commit("the code moved under it")

    (drift,) = anchor.classify_store(repo.root)
    assert drift.changed is True
    assert drift.obligating is False


def test_a_retired_claim_is_scanned_but_does_not_obligate(repo):
    """A retired claim describes something the project stopped asserting.
    Restamping it means nothing, and an open item nobody can close is how a
    signal gets ignored."""
    base = seed(repo)
    repo.write("docs/system/domain.md",
               "# Domain\n\n### INV-x - a title for INV-x\n\n"
               "```claim\n"
               "kind:     invariant\n"
               "status:   retired\n"
               "retired-ground: 2\n"
               "retired-evidence: the rule it named is enforced by the type system now\n"
               "truth-source: tests\n"
               f'anchors:  ["src/app.py#greet@{base}"]\n'
               "reviewed: 2026-09-11\n"
               "```\n\nProse.\n")
    repo.commit("a retired claim")
    repo.write("src/app.py", "def greet(name):\n    return name\n")
    repo.commit("the code moved under it")

    (drift,) = anchor.classify_store(repo.root)
    assert drift.changed is True
    assert drift.obligating is False


# ---------------------------------------------------------------------------
# REQ-drift-changed-only
# ---------------------------------------------------------------------------

def test_the_filter_keeps_claims_anchoring_a_changed_file(repo):
    base = seed(repo)
    claim_file(repo, "docs/system/domain.md", one_claim(base))
    repo.commit("a claim")

    kept = anchor.classify_store(repo.root, paths=frozenset({"src/app.py"}))
    assert [d.claim_id for d in kept] == ["CON-x"]


def test_the_filter_drops_claims_anchoring_untouched_files(repo):
    """A claim with no matching anchor is absent from the result, not present
    and fresh: "not checked" and "checked and fine" are different answers."""
    base = seed(repo)
    claim_file(repo, "docs/system/domain.md", one_claim(base))
    repo.commit("a claim")

    assert anchor.classify_store(repo.root, paths=frozenset({"README.md"})) == []


def test_the_filter_matches_inside_a_directory_anchor(repo):
    base = seed(repo)
    repo.write("docs/system/domain.md",
               "# Domain\n\n### CON-x - a title for CON-x\n\n"
               "```claim\n"
               "kind:     concept\n"
               "status:   asserted\n"
               "truth-source: decision\n"
               f'anchors:  ["src/@{base}"]\n'
               "reviewed: 2026-09-11\n"
               "```\n\nProse.\n")
    repo.commit("a directory anchor")

    assert anchor.classify_store(repo.root, paths=frozenset({"src/app.py"}))
    assert anchor.classify_store(repo.root, paths=frozenset({"README.md"})) == []


def test_a_malformed_anchor_survives_the_filter(repo):
    """An unparseable anchor cannot be matched against a path set, so dropping
    it under `--changed` would hide a real defect behind a flag."""
    seed(repo)
    repo.write("docs/system/domain.md",
               "# Domain\n\n### CON-x - a title for CON-x\n\n"
               "```claim\n"
               "kind:     concept\n"
               "status:   asserted\n"
               "truth-source: decision\n"
               'anchors:  ["src/app.py#not a symbol@abc123"]\n'
               "reviewed: 2026-09-11\n"
               "```\n\nProse.\n")
    repo.commit("a malformed anchor")

    (drift,) = anchor.classify_store(repo.root, paths=frozenset({"README.md"}))
    assert drift.errors


# ---------------------------------------------------------------------------
# REQ-drift-never-rewrites
# ---------------------------------------------------------------------------

def test_a_scan_over_a_stale_store_writes_nothing(repo):
    """Reporting drift and resolving it are separate acts, and only the second
    one is a human's. The kernel contains no command that rewrites a claim to
    match the code, and this is the test that keeps it that way."""
    base = seed(repo)
    claim_file(repo, "docs/system/domain.md", one_claim(base))
    repo.commit("a claim")
    repo.write("src/app.py", "def greet(name):\n    return name\n")
    repo.commit("the code moved, the claim did not")

    before = {p: p.read_bytes() for p in sorted(
        (repo.root / "docs").rglob("*")) if p.is_file()}
    assert before, "the fixture must have written at least one store file"

    (drift,) = anchor.classify_store(repo.root)
    assert drift.changed is True

    after = {p: p.read_bytes() for p in sorted(
        (repo.root / "docs").rglob("*")) if p.is_file()}
    assert after == before
