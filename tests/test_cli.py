"""Exit codes are the contract.

`forge drift` is meant to compose as a gate, so the codes matter more than the
text: 0 every anchor fresh, 1 something needs a look, 2 the invocation was
wrong. A gate that exits 0 on a usage error is worse than no gate.
"""

from __future__ import annotations

import json

import pytest

from forge.cli import main


@pytest.fixture
def project(repo):
    repo.write(
        "src/pay.ts",
        "export function refundable(a: number, b: number): number {\n"
        "  return a - b;\n"
        "}\n",
    )
    return repo, repo.commit("initial")


def test_fresh_exits_zero(project, capsys):
    repo, base = project
    repo.write("other.md", "unrelated\n")
    repo.commit("touch something else")
    code = main(["drift", "src/pay.ts#refundable", "--repo", str(repo.root), "--baseline", base])
    assert code == 0
    assert "fresh" in capsys.readouterr().out


def test_changed_exits_one(project, capsys):
    repo, base = project
    repo.write(
        "src/pay.ts",
        "export function refundable(a: number, b: number, c: number): number {\n"
        "  return a - b;\n"
        "}\n",
    )
    repo.commit("add a parameter")
    code = main(["drift", "src/pay.ts#refundable", "--repo", str(repo.root), "--baseline", base])
    assert code == 1
    assert "stale" in capsys.readouterr().out


def test_bad_anchor_exits_two(project, capsys):
    repo, base = project
    code = main(["drift", "../escape.ts", "--repo", str(repo.root), "--baseline", base])
    assert code == 2
    assert "traverse outside the repository" in capsys.readouterr().err


def test_rejected_revision_exits_two_without_reaching_git(project, capsys):
    repo, _base = project
    # Written as --baseline=VALUE so argparse hands the string through instead
    # of rejecting it as a missing argument: the point is that *our* validation
    # stops it, not argparse's.
    code = main([
        "drift", "src/pay.ts#refundable", "--repo", str(repo.root),
        "--baseline=--upload-pack=evil",
    ])
    assert code == 2
    assert "hex characters" in capsys.readouterr().err


def test_non_repo_exits_two(tmp_path, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    code = main(["drift", "a.ts", "--repo", str(plain), "--baseline", "HEAD"])
    assert code == 2
    assert "not a git repository" in capsys.readouterr().err


def test_json_output_is_parseable(project, capsys):
    repo, base = project
    repo.write(
        "src/pay.ts",
        "export function refundable(a: number, b: number): number {\n"
        "  return Math.max(0, a - b);\n"
        "}\n",
    )
    repo.commit("clamp")
    code = main([
        "drift", "src/pay.ts#refundable", "--repo", str(repo.root),
        "--baseline", base, "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["status"] == "shifted"
    assert payload[0]["symbol"] == "refundable"


def test_fingerprint_is_stable_across_runs(tmp_path, capsys):
    target = tmp_path / "a.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")
    assert main(["fingerprint", str(target)]) == 0
    first = capsys.readouterr().out.split()[0]
    assert main(["fingerprint", str(target)]) == 0
    assert capsys.readouterr().out.split()[0] == first


def test_doctor_reports_the_toolchain(capsys):
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "grammars" in out and "git" in out


# --------------------------------------------------------------------------
# M2 commands
# --------------------------------------------------------------------------

STORE_CLAIM = """\
### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:
  - src/pay.py#refundable
evidence:
  - test: tests/test_pay.py::test_bounded
reviewed: 2026-09-10
```

Partial refunds accumulate: what is bounded is the sum of settled refunds, not
each refund on its own. An attempt over the remaining balance must be rejected
at the domain boundary rather than clamped.
"""


@pytest.fixture
def stored(repo):
    repo.write("src/pay.py", "def refundable(a, b):  # forge:INV-7\n    return a - b\n")
    repo.write("tests/test_pay.py", "# @covers INV-7\ndef test_bounded():\n    assert True\n")
    repo.write("docs/system/domain.md", STORE_CLAIM)
    repo.commit("a store")
    return repo


def test_sync_then_check_is_clean(stored, capsys):
    assert main(["sync", "derived", "--repo", str(stored.root)]) == 0
    assert "updated" in capsys.readouterr().out
    assert main(["check", "--repo", str(stored.root)]) == 0
    out = capsys.readouterr().out
    assert "ok - no issues" in out
    # A clean report that hides what it declined to check is not trustworthy.
    assert "Not yet checked" in out


def test_sync_warns_when_the_content_commit_has_not_happened_yet(stored, capsys):
    """The tier is generated from HEAD, so syncing with tracked content still
    uncommitted produces a tier that is stale the moment it is written.

    The advice to commit the tier separately was always printed; it did not say
    that HEAD was not yet what the author meant, and the order was got wrong
    twice on this repository before the condition was named.
    """
    stored.write("src/pay.py", "def capture(x):\n    return x + 1\n")
    assert main(["sync", "derived", "--repo", str(stored.root)]) == 0
    out = capsys.readouterr().out
    assert "1 tracked file(s) differ from HEAD" in out
    assert "src/pay.py" in out

    stored.commit("the content commit that should have come first")
    main(["sync", "derived", "--repo", str(stored.root)])
    assert "differ from HEAD" not in capsys.readouterr().out


def test_sync_does_not_count_the_tier_it_just_wrote(stored, capsys):
    """`docs/system/derived/` is uncommitted by construction after a sync that
    changed anything - warning about it would fire on every clean run."""
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    main(["sync", "derived", "--repo", str(stored.root)])
    assert "differ from HEAD" not in capsys.readouterr().out


def test_check_reports_a_hand_edited_derived_file(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    target = stored.root / "docs/system/derived/inventory.json"
    payload = target.read_text(encoding="utf-8").replace('"files_tracked": 3', '"files_tracked": 999')
    target.write_text(payload, encoding="utf-8")

    assert main(["check", "--repo", str(stored.root)]) == 1
    out = capsys.readouterr().out
    assert "derived.dirty" in out
    assert "forge sync derived" in out


def test_check_reports_a_dangling_reference(stored, capsys):
    stored.write("src/other.py", "# forge:CMP-nowhere\nX = 1\n")
    stored.commit("reference a claim nobody defined")
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()

    assert main(["check", "--repo", str(stored.root)]) == 1
    out = capsys.readouterr().out
    assert "trace.dangling_reference" in out and "CMP-nowhere" in out


def test_trace_prints_both_directions(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    assert main(["trace", "INV-7", "--repo", str(stored.root)]) == 0
    out = capsys.readouterr().out
    assert "docs/system/domain.md:1" in out
    assert "src/pay.py#refundable" in out
    assert "tests/test_pay.py::test_bounded" in out
    assert "src/pay.py:1" in out


def test_trace_json_is_parseable(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    assert main(["trace", "INV-7", "--repo", str(stored.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "INV-7" and payload["kind"] == "invariant"


def test_trace_of_an_unknown_id_exits_one(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    assert main(["trace", "INV-404", "--repo", str(stored.root)]) == 1
    assert "not in the index" in capsys.readouterr().err


def test_status_fits_on_one_screen(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    capsys.readouterr()
    assert main(["status", "--repo", str(stored.root)]) == 0
    lines = [line for line in capsys.readouterr().out.split("\n") if line.strip()]
    assert len(lines) <= 24, "status must stay readable at a glance"
    assert any("1 ratified" in line for line in lines)


def test_status_reports_the_derived_tier_stale_when_content_moved(stored, capsys):
    main(["sync", "derived", "--repo", str(stored.root)])
    stored.write("src/ledger.py", "# forge:INV-7\ndef settle():\n    return None\n")
    stored.commit("a file the inventory has never seen")
    capsys.readouterr()
    main(["status", "--repo", str(stored.root)])
    out = capsys.readouterr().out
    assert "stale" in out
    # A status line that reports a problem without naming the fix trains people
    # to ignore it.
    assert "forge sync derived" in out


def test_a_body_only_edit_does_not_make_the_derived_tier_stale(stored, capsys):
    """The derived tier is a census, not a drift detector. Rewriting a function
    body changes nothing it records - same file, same line count, same
    back-reference - so calling it stale would be a false alarm, and a tier
    that cries stale on every commit gets resynced without being read. Whether
    that edit invalidated INV-7 is `forge drift`'s question."""
    main(["sync", "derived", "--repo", str(stored.root)])
    stored.write("src/pay.py", "def refundable(a, b):  # forge:INV-7\n    return max(0, a - b)\n")
    stored.commit("clamp")
    capsys.readouterr()
    main(["status", "--repo", str(stored.root)])
    assert "stale" not in capsys.readouterr().out


def test_status_stays_current_after_the_derived_tier_is_committed(stored, capsys):
    """The treadmill case. Committing the derived tier moves HEAD past the
    commit stamped inside it, so an age comparison would call the files stale
    the instant they became correct - and no amount of regenerating could
    settle it. Content is the truth; the stamp is provenance beside it."""
    main(["sync", "derived", "--repo", str(stored.root)])
    stored.commit("chore: sync derived tier")
    capsys.readouterr()
    main(["status", "--repo", str(stored.root)])
    out = capsys.readouterr().out
    assert "current" in out
    assert "stale" not in out
    assert main(["check", "--repo", str(stored.root)]) == 0


def test_output_is_ascii_only(stored, capsys):
    """The target console is cp1252; a non-ASCII glyph renders as a question
    mark, and a tool whose own output is unreadable on its platform is broken."""
    main(["sync", "derived", "--repo", str(stored.root)])
    main(["status", "--repo", str(stored.root)])
    main(["check", "--repo", str(stored.root)])
    captured = capsys.readouterr()
    for stream in (captured.out, captured.err):
        assert stream.isascii(), f"non-ascii in output: {stream!r}"
