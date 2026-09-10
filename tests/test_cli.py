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
