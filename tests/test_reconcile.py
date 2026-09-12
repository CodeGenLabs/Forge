"""`forge reconcile`: what drifted while nobody was looking, and who did it.

The pre-commit hook catches drift as it is created and **will** be bypassed -
`--no-verify`, a colleague's commits, a dependency bot, or a repository that
adopts the harness after years of history. OPEN_QUESTIONS.md Q10 is explicit
that the hook needs a recovery path beside it.

What these tests pin is the thing that makes a recovery path usable:
attribution. A list of forty stale claims is a wall. The same forty with the
commit that did it, and what that commit said it was doing, is a review.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from forge import gitio, ledger, reconcile
from forge.cli import main

TODAY = _dt.date(2026, 9, 12)

CODE = "def greet():\n    return 'hi'\n"
OTHER = "def calm():\n    return 0\n"


def claim_text(sha: str) -> str:
    return (
        "# Domain\n\n### CON-greet - the greeting's shape\n\n"
        "```claim\n"
        "kind:     concept\n"
        "status:   asserted\n"
        "truth-source: code\n"
        f'anchors:  ["src/app.py#greet@{sha}"]\n'
        "reviewed: 2026-09-01\n"
        "```\n\n"
        "Prose about the greeting, long enough to read like a real claim.\n"
    )


@pytest.fixture
def bypassed(repo):
    """A claim, then somebody else's commit that broke its anchor."""
    repo.write("src/app.py", CODE)
    repo.write("src/other.py", OTHER)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    mark = repo.commit("a claim")

    repo.write("src/app.py", "def greet(name):\n    return f'hi {name}'\n")
    repo._git("add", "-A")
    repo._git("-c", "user.name=Alice", "-c", "user.email=alice@example.com",
              "commit", "-q", "-m", "feat: greet by name")
    repo.mark = mark
    return repo


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def test_the_commit_that_caused_the_drift_is_named(bypassed):
    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    (cause,) = result.causes
    assert cause.claim_id == "CON-greet"
    assert [subject for _, _, subject in cause.commits] == ["feat: greet by name"]
    assert cause.authors == ["Alice"]


def test_a_fresh_store_reconciles_to_nothing(repo):
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    mark = repo.commit("a claim")
    repo.write("README.md", "unrelated\n")
    repo.commit("something that touches no anchor")

    result = reconcile.reconcile(repo.root, mark)
    assert result.causes == [] and result.unattributed == []


def test_drift_from_before_the_range_is_reported_apart(bypassed):
    """"This drifted before the window you asked about" is a different answer
    from "nobody touched it", and sending a reviewer to look for a cause that
    is not there wastes the attention this command exists to save."""
    later = bypassed.commit("a commit that touches nothing")

    result = reconcile.reconcile(bypassed.root, later)
    assert result.causes == []
    assert [c.claim_id for c in result.unattributed] == ["CON-greet"]


def test_an_unclassifiable_claim_is_not_reported_as_drift(bypassed):
    """A candidate is never stamped with a `@sha`, so every rejected candidate
    would otherwise appear in every reconcile from now on, under a heading
    saying it had drifted."""
    (bypassed.root / "docs/system/candidates").mkdir(parents=True, exist_ok=True)
    (bypassed.root / "docs/system/candidates/scan.md").write_text(
        "# Candidates\n\n### CON-maybe - something a scan guessed\n\n"
        "```claim\nkind: concept\nstatus: proposed\ntruth-source: code\n"
        'anchors: ["src/other.py"]\nconfidence: low\nreviewed: 2026-09-01\n```\n\n'
        "Prose about the guess, long enough to read like a claim.\n",
        encoding="utf-8", newline="\n")
    bypassed.commit("a rejected candidate stays readable")

    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    assert [c.claim_id for c in result.unclassifiable] == ["CON-maybe"]
    assert "CON-maybe" not in [c.claim_id for c in result.causes]


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

def test_it_records_nothing_unless_asked(bypassed):
    """Reading a range and taking the backlog on are different acts."""
    reconcile.reconcile(bypassed.root, bypassed.mark)
    assert ledger.load_ledger(bypassed.root) == []


def test_recording_carries_the_cause_into_the_ledger(bypassed):
    """The report had the attribution and the record did not, which left the
    one thing this command adds out of the artifact that survives."""
    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    (entry,) = reconcile.record(bypassed.root, result, today=TODAY)

    assert entry.claim == "CON-greet"
    assert entry.caused_by and "Alice" in entry.caused_by[0]
    assert "feat: greet by name" in entry.caused_by[0]

    # And it survives a round trip through the file.
    (reloaded,) = ledger.load_ledger(bypassed.root)
    assert reloaded.caused_by == entry.caused_by


def test_recording_twice_opens_nothing_new(bypassed):
    """Ranges overlap - somebody reconciles weekly and the windows touch. A
    second entry for the same claim is how a ledger stops being read."""
    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    assert len(reconcile.record(bypassed.root, result, today=TODAY)) == 1

    again = reconcile.reconcile(bypassed.root, bypassed.mark)
    assert reconcile.record(bypassed.root, again, today=TODAY) == []


def test_an_already_recorded_claim_says_so(bypassed):
    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    reconcile.record(bypassed.root, result, today=TODAY)

    again = reconcile.reconcile(bypassed.root, bypassed.mark)
    assert again.causes[0].recorded == "D-001"


def test_an_unclassifiable_claim_gets_no_entry(bypassed):
    """An entry saying "we could not tell" is an open item nobody can close."""
    (bypassed.root / "docs/system/candidates").mkdir(parents=True, exist_ok=True)
    (bypassed.root / "docs/system/candidates/scan.md").write_text(
        "# Candidates\n\n### CON-maybe - something a scan guessed\n\n"
        "```claim\nkind: concept\nstatus: proposed\ntruth-source: code\n"
        'anchors: ["src/other.py"]\nconfidence: low\nreviewed: 2026-09-01\n```\n\n'
        "Prose about the guess, long enough to read like a claim.\n",
        encoding="utf-8", newline="\n")
    bypassed.commit("a rejected candidate")

    result = reconcile.reconcile(bypassed.root, bypassed.mark)
    opened = reconcile.record(bypassed.root, result, today=TODAY)
    assert [e.claim for e in opened] == ["CON-greet"]


# ---------------------------------------------------------------------------
# The primitive underneath
# ---------------------------------------------------------------------------

def test_commits_touching_reports_author_and_subject(bypassed):
    found = gitio.commits_touching(bypassed.root, bypassed.mark, "HEAD",
                                   ["src/app.py"])
    assert [(a, s) for _, a, s in found] == [("Alice", "feat: greet by name")]


def test_commits_touching_ignores_other_paths(bypassed):
    assert gitio.commits_touching(bypassed.root, bypassed.mark, "HEAD",
                                  ["src/other.py"]) == []


def test_commits_touching_with_no_paths_asks_nothing(bypassed):
    assert gitio.commits_touching(bypassed.root, bypassed.mark, "HEAD", []) == []


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def test_the_command_exits_one_when_a_verdict_is_owed(bypassed):
    assert main(["reconcile", "--since", bypassed.mark,
                 "--repo", str(bypassed.root)]) == 1


def test_the_command_exits_zero_when_nothing_is_owed(repo):
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    mark = repo.commit("a claim")

    assert main(["reconcile", "--since", mark, "--repo", str(repo.root)]) == 0
