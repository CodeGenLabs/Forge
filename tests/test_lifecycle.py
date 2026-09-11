"""Gates, verification and the archive fold - and the M3 acceptance run.

The end-to-end test at the bottom is the milestone's acceptance criterion:
create a change, write artifacts by hand, watch each gate fail for the right
reason and then pass, verify, archive, and finish with `forge check` clean.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from forge import change, derive, gates, spec, verify
from forge.cli import main

TODAY = date(2026, 9, 11)

PAY = '''\
# forge:CMP-payments
def refundable(captured, settled):  # forge:INV-refund-cap
    return captured - settled
'''

TESTS = '''\
# @covers INV-refund-cap
def test_bounded():
    assert True
'''

COMPONENT = """\

### CMP-payments - Capture, refund and their money arithmetic

```claim
kind: component
status: asserted
truth-source: decision
anchors: ["src/pay.py"]
reviewed: 2026-09-01
```

Owns every decision about how much money may move and when. It must reject an
overdraw at its boundary rather than clamping.
"""

INVARIANT = """\

### INV-refund-cap - A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors: ["src/pay.py#refundable"]
evidence:
  - test: "tests/test_pay.py::test_bounded"
reviewed: 2026-09-01
```

Partial refunds accumulate: what is bounded is the sum of settled refunds. An
attempt over the balance must be rejected at the boundary.
"""

DELTA = """\
## Purpose

How money is captured from an authorisation and returned to a payer, and what
bounds each of those movements.

## ADDED Requirements

### Requirement: REQ-refunds-1 - An operator can refund a settled payment
The system SHALL allow a refund against any settled payment up to its remaining
refundable balance.

#### Scenario: Partial refund within balance
- **WHEN** an operator refunds 30 against a payment of 100 with no prior refunds
- **THEN** the refund settles and the remaining refundable balance is 70
"""

ACCOUNT = """\
# Impact

## Claims touched

### Unaffected
- CMP-payments - the new function lands inside the existing component boundary

### Updated
- INV-refund-cap - the bound is now enforced by a guard in refund()
"""

TASKS = """\
## Tasks

- [x] Write the failing test for the over-balance case (REQ-refunds-1)
- [x] Add the guard in refund() (REQ-refunds-1)
- [ ] chore: tidy the imports
"""

COMMANDS = """\

commands:
  build: python -c "pass"
  typecheck: python -c "pass"
  lint: python -c "pass"
  test: python -c "pass"
"""


def append(repo, path: str, text: str) -> None:
    target = repo.root / path
    target.write_text(target.read_text(encoding="utf-8") + text, encoding="utf-8")


def sync(repo) -> None:
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")


@pytest.fixture
def project(repo):
    repo.write("src/pay.py", PAY)
    repo.write("tests/test_pay.py", TESTS)
    main(["init", "--repo", str(repo.root)])
    append(repo, "docs/system/components.md", COMPONENT)
    append(repo, "docs/system/domain.md", INVARIANT)
    append(repo, ".forge/config.yaml", COMMANDS)
    repo.commit("a project with two claims")
    sync(repo)
    change.new_change(repo.root, "refund support", today=TODAY)
    repo.commit("open a change")
    sync(repo)
    return repo


def item(repo) -> change.Change:
    return change.find_change(repo.root, "1")


def write(repo, name: str, text: str) -> None:
    target = item(repo).root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def run(repo, point: str, reference: str | None = "1") -> list[gates.GateResult]:
    return gates.run_gate(repo.root, point,
                          change.find_change(repo.root, reference) if reference else None)


# ---------------------------------------------------------------------------
# The gate table
# ---------------------------------------------------------------------------

def test_the_default_table_matches_the_architecture_document(repo):
    table = gates.load_gates(repo.root)
    assert [(g.point, g.check) for g in table] == [
        ("investigate:pre", "derived.freshness"),
        ("spec:post", "store.spec_grammar"),
        ("impact:post", "trace.claim_touch_complete"),
        ("analyze:post", "trace.requirement_task_coverage"),
        ("implement:pre", "derived.freshness"),
        ("implement:task:post", "task.scope_and_covers"),
        ("verify:post", "verify.definition_of_done"),
        ("verify:post", "drift.rules_conformance"),
        ("sync:pre", "store.valid"),
        ("converge:post", "repo.clean"),
    ]


def test_a_project_can_replace_the_table(project):
    (project.root / ".forge/config.yaml").write_text(
        "gates:\n  - point: spec:post\n    check: store.valid\n    blocking: false\n",
        encoding="utf-8")
    table = gates.load_gates(project.root)
    assert len(table) == 1
    assert table[0].blocking is False


def test_an_unimplemented_check_never_passes_silently(project):
    """A gate that succeeds because nobody wrote its check is worse than no
    gate: it is evidence of a check that did not happen."""
    results = run(project, "implement:task:post")
    assert len(results) == 1
    assert results[0].available is False
    assert "proves nothing" in results[0].issues[0].message
    assert "M4" in results[0].issues[0].message


def test_an_unimplemented_check_does_not_block_either(project):
    """It cannot be acted on, so blocking on it would stop every lifecycle at
    this milestone. It is reported as unproven instead."""
    assert not any(r.blocks for r in run(project, "implement:task:post"))


def test_a_non_blocking_gate_still_reports_what_it_found(project):
    """`blocking` decides the exit code, never whether the reader is told."""
    project.write("src/other.py", "x = 1\n")
    project.commit("make the derived tier stale")
    results = run(project, "investigate:pre", reference=None)
    assert results[0].errors
    assert not results[0].blocks


def test_the_same_check_at_a_later_point_does_block(project):
    """`derived.freshness` is advisory at `investigate:pre` and blocking at
    `implement:pre`: reading a stale index while exploring costs little, and
    writing code against one costs a lot."""
    project.write("src/other.py", "x = 1\n")
    project.commit("make the derived tier stale")
    assert run(project, "implement:pre")[0].blocks


def test_an_unknown_point_is_a_usage_error(project, capsys):
    assert main(["gate", "nope:post", "--change", "1",
                 "--repo", str(project.root)]) == 2
    assert "no gate is declared" in capsys.readouterr().err


def test_a_change_scoped_check_without_a_change_says_so(project):
    results = run(project, "impact:post", reference=None)
    assert results[0].errors[0].code == "gate.needs_change"


# ---------------------------------------------------------------------------
# The gates in sequence
# ---------------------------------------------------------------------------

def test_spec_post_blocks_until_a_delta_exists(project):
    assert run(project, "spec:post")[0].blocks
    write(project, "spec/payments/spec.md", DELTA)
    assert not run(project, "spec:post")[0].blocks


def test_spec_post_accepts_a_named_skip(project):
    changed = item(project)
    changed.meta["skip_spec"] = "log format only, no observable behaviour changes"
    changed.write_meta()
    assert not run(project, "spec:post")[0].blocks


def test_impact_post_blocks_until_every_claim_is_accounted_for(project):
    project.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    assert run(project, "impact:post")[0].blocks
    write(project, "impact.md", ACCOUNT)
    assert not run(project, "impact:post")[0].blocks


def test_analyze_post_blocks_until_tasks_discharge_the_requirements(project):
    write(project, "spec/payments/spec.md", DELTA)
    result = run(project, "analyze:post")[0]
    assert result.blocks
    assert "REQ-refunds-1" in result.errors[0].message
    write(project, "tasks.md", TASKS)
    assert not run(project, "analyze:post")[0].blocks


def test_a_task_naming_no_requirement_blocks(project):
    """Work nobody agreed to is how a change grows past what was approved."""
    write(project, "spec/payments/spec.md", DELTA)
    write(project, "tasks.md", TASKS + "- [ ] Also rewrite the scheduler\n")
    result = run(project, "analyze:post")[0]
    assert result.blocks
    assert "names no requirement" in result.errors[-1].message


def test_a_chore_task_needs_no_requirement(project):
    write(project, "spec/payments/spec.md", DELTA)
    write(project, "tasks.md", TASKS)
    assert not run(project, "analyze:post")[0].blocks


def test_converge_post_blocks_on_a_dirty_tree(project):
    """An archive taken over a dirty tree records a state that never existed."""
    project.write("src/scratch.py", "x = 1\n")
    assert run(project, "converge:post")[0].blocks


def test_converge_post_passes_on_a_clean_tree(project):
    assert not run(project, "converge:post")[0].blocks


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def test_verify_records_every_condition_not_just_the_tests(project):
    write(project, "spec/payments/spec.md", DELTA)
    report = verify.verify(project.root, item(project))
    assert set(report["gates"]) == set(verify.CONDITIONS)


def test_an_undeclared_command_is_unavailable_and_blocks_the_verdict(project):
    """Guessing `npm test` because a package.json exists is how a report goes
    green for a suite that never ran."""
    (project.root / ".forge/config.yaml").write_text("version: 1\n", encoding="utf-8")
    report = verify.verify(project.root, item(project))
    assert report["gates"]["tests"]["status"] == "unavailable"
    assert report["verdict"] == "unproven"


def test_a_kernel_owed_condition_is_pending_and_does_not_block(project):
    """The line is who owes the work. A project waiting on a ledger the
    harness has not shipped cannot act on the finding at all, and a verdict
    nobody can reach is one people route around."""
    report = verify.verify(project.root, item(project))
    assert report["gates"]["drift"]["status"] == "pending"
    assert report["pending"] == ["debt", "drift", "no_new_skips"]
    assert report["verdict"] == "pass"


def test_an_undischarged_requirement_fails_verification(project):
    write(project, "spec/payments/spec.md", DELTA)
    report = verify.verify(project.root, item(project))
    assert report["gates"]["requirement_cover"]["undischarged"] == ["REQ-refunds-1"]
    assert report["verdict"] == "fail"


def test_a_tagged_test_discharges_it(project):
    write(project, "spec/payments/spec.md", DELTA)
    project.write("tests/test_pay.py",
                  TESTS + "\n\n# @covers REQ-refunds-1\ndef test_over():\n    assert True\n")
    project.commit("tag the test")
    sync(project)
    report = verify.verify(project.root, item(project))
    assert report["gates"]["requirement_cover"]["status"] == "pass"


def test_a_failing_command_fails_the_verdict_and_keeps_its_output(project):
    (project.root / ".forge/config.yaml").write_text(
        "version: 1\n\ncommands:\n  build: python -c \"import sys; "
        "sys.stderr.write('boom\\n'); sys.exit(3)\"\n",
        encoding="utf-8")
    report = verify.verify(project.root, item(project))
    assert report["gates"]["build"]["status"] == "fail"
    assert report["gates"]["build"]["exit"] == 3
    assert "boom" in report["gates"]["build"]["tail"]


def test_an_unaccounted_claim_fails_verification(project):
    project.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    report = verify.verify(project.root, item(project))
    assert report["gates"]["claim_touch"]["status"] == "fail"
    assert "INV-refund-cap" in report["gates"]["claim_touch"]["unaccounted"]


def test_no_run_records_the_commands_as_unproven(project):
    report = verify.verify(project.root, item(project), run_commands=False)
    assert report["gates"]["tests"]["status"] == "unavailable"
    assert "--no-run" in report["gates"]["tests"]["reason"]


def test_a_waiver_is_recorded_in_the_report(project):
    report = verify.verify(project.root, item(project), waived=("drift",))
    assert report["gates"]["drift"]["status"] == "waived"
    assert report["waived"] == ["drift"]


def test_verify_writes_the_report(project, capsys):
    assert main(["verify", "--change", "1", "--repo", str(project.root)]) == 0
    target = item(project).root / verify.VERIFICATION_FILE
    assert json.loads(target.read_text(encoding="utf-8"))["verdict"] == "pass"
    out = capsys.readouterr().out
    assert "still unchecked by this kernel" in out


def test_verify_post_reads_the_report(project):
    result = next(r for r in run(project, "verify:post")
                  if r.gate.check == "verify.definition_of_done")
    assert result.blocks
    main(["verify", "--change", "1", "--repo", str(project.root)])
    result = next(r for r in run(project, "verify:post")
                  if r.gate.check == "verify.definition_of_done")
    assert not result.blocks


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------

def test_archive_refuses_without_a_passing_verification(project, capsys):
    write(project, "spec/payments/spec.md", DELTA)
    write(project, "tasks.md", TASKS)
    assert main(["archive", "--change", "1", "--repo", str(project.root)]) == 1
    assert "nothing archived" in capsys.readouterr().err
    assert item(project).root.is_dir()


def test_archive_folds_then_moves(project, capsys):
    _complete(project)
    assert main(["archive", "--change", "1", "--date", "2026-09-11",
                 "--repo", str(project.root)]) == 0
    folded = project.root / spec.SPECS_DIR / "payments/spec.md"
    assert "REQ-refunds-1" in folded.read_text(encoding="utf-8")
    archived = project.root / change.ARCHIVE_DIR / "2026-09-11-0001-refund-support"
    assert archived.is_dir()
    assert not (project.root / "changes/0001-refund-support").exists()


def test_archive_dry_run_changes_nothing(project, capsys):
    _complete(project)
    assert main(["archive", "--change", "1", "--dry-run",
                 "--repo", str(project.root)]) == 0
    assert "would move" in capsys.readouterr().out
    assert not (project.root / spec.SPECS_DIR / "payments/spec.md").exists()
    assert item(project).root.is_dir()


def test_force_records_which_blockers_were_overridden(project):
    write(project, "spec/payments/spec.md", DELTA)
    write(project, "tasks.md", TASKS)
    assert main(["archive", "--change", "1", "--force", "--date", "2026-09-11",
                 "--repo", str(project.root)]) == 0
    archived = project.root / change.ARCHIVE_DIR / "2026-09-11-0001-refund-support"
    meta = (archived / ".forge.yaml").read_text(encoding="utf-8")
    assert "archived_with_blockers" in meta


def test_an_archived_number_is_never_reused(project):
    _complete(project)
    main(["archive", "--change", "1", "--date", "2026-09-11",
          "--repo", str(project.root)])
    assert change.new_change(project.root, "next thing", today=TODAY).number == 2


def test_the_archive_is_not_a_citation(project):
    """It is never an input to any phase, so counting it would keep a retired
    claim looking consulted forever."""
    _complete(project)
    main(["archive", "--change", "1", "--date", "2026-09-11",
          "--repo", str(project.root)])
    project.commit("archive the change")
    sync(project)
    index = (derive.read_json(project.root / derive.DERIVED_DIR / "trace.json")
             or {})["data"]["ids"]
    assert "archive" not in json.dumps(index.get("CMP-payments", {}).get("changes", []))


# ---------------------------------------------------------------------------
# The M3 acceptance run
# ---------------------------------------------------------------------------

def _complete(project) -> None:
    """Take the change all the way to a passing verification."""
    write(project, "spec/payments/spec.md", DELTA)
    write(project, "impact.md", ACCOUNT)
    write(project, "tasks.md", TASKS)
    project.write("tests/test_pay.py",
                  TESTS + "\n\n# @covers REQ-refunds-1\ndef test_over():\n    assert True\n")
    project.commit("implement and tag")
    sync(project)
    main(["verify", "--change", "1", "--repo", str(project.root)])


def test_the_acceptance_case(project, capsys):
    """M3's acceptance: each gate fails for the right reason, then passes;
    verify; archive; the spec delta folds; `forge check` is clean."""
    # Each gate blocks for its own reason before its artifact exists.
    assert run(project, "spec:post")[0].blocks
    write(project, "spec/payments/spec.md", DELTA)
    assert not run(project, "spec:post")[0].blocks

    project.write("src/pay.py", PAY + "\n\ndef refund(c, s, n):\n"
                                      "    if n > c - s:\n        raise ValueError\n"
                                      "    return n\n")
    assert run(project, "impact:post")[0].blocks
    write(project, "impact.md", ACCOUNT)
    assert not run(project, "impact:post")[0].blocks

    assert run(project, "analyze:post")[0].blocks
    write(project, "tasks.md", TASKS)
    assert not run(project, "analyze:post")[0].blocks

    project.write("tests/test_pay.py",
                  TESTS + "\n\n# @covers REQ-refunds-1\ndef test_over():\n    assert True\n")
    project.commit("implement and tag")
    sync(project)

    capsys.readouterr()
    assert main(["verify", "--change", "1", "--repo", str(project.root)]) == 0
    assert not run(project, "sync:pre")[0].blocks

    assert main(["archive", "--change", "1", "--date", "2026-09-11",
                 "--repo", str(project.root)]) == 0
    project.commit("archive the change")
    sync(project)

    capsys.readouterr()
    assert main(["check", "--repo", str(project.root)]) == 0, capsys.readouterr().out
    assert not run(project, "converge:post", reference=None)[0].blocks

    # The promise now lives in the permanent tier, and the index knows it.
    assert main(["trace", "REQ-refunds-1", "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "docs/system/specs/payments/spec.md" in out
    assert "tests/test_pay.py::test_over" in out


def test_a_folded_requirement_is_not_a_dangling_reference(project):
    """The first thing anyone sees after their first archive, if the index
    does not treat a permanent spec as a definition."""
    _complete(project)
    main(["archive", "--change", "1", "--date", "2026-09-11",
          "--repo", str(project.root)])
    project.commit("archive")
    sync(project)
    summary = (derive.read_json(project.root / derive.DERIVED_DIR / "trace.json")
               or {})["data"]["summary"]
    assert summary["dangling_references"] == []
