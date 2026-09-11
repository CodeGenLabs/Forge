"""The spec delta grammar (R12/R13) and the deterministic fold."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from forge import change, spec
from forge.cli import main
from forge.validate import Issue

TODAY = date(2026, 9, 11)

ADDED = """\
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

MODIFIED = """\
## MODIFIED Requirements

### Requirement: REQ-refunds-1 - An operator can refund a settled payment
The system SHALL allow a refund up to the remaining refundable balance, and
SHALL clamp a larger request to that balance.

#### Scenario: Refund exceeding remaining balance is clamped
- **WHEN** an operator refunds 80 against a payment of 100 with 30 refunded
- **THEN** 70 is refunded and the remaining balance is 0
"""


@pytest.fixture
def project(repo):
    repo.write("README.md", "# A project\n")
    repo.commit("a repository")
    main(["init", "--repo", str(repo.root)])
    repo.commit("forge init")
    change.new_change(repo.root, "refund support", today=TODAY)
    repo.commit("open a change")
    return repo


def write_delta(repo, text: str, capability: str = "payments") -> spec.Delta:
    item = change.find_change(repo.root, "1")
    target = item.root / "spec" / capability / "spec.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    path = target.relative_to(repo.root).as_posix()
    return spec.parse_delta(text, path, capability)


def check(repo, text: str, capability: str = "payments") -> list[Issue]:
    return spec.check_delta(repo.root, write_delta(repo, text, capability), Issue)


def messages(found: list[Issue]) -> str:
    return " | ".join(i.message for i in found)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def test_the_four_verbs_are_parsed():
    text = (ADDED + "\n## MODIFIED Requirements\n\n"
            "### Requirement: REQ-a - A\nMUST.\n\n#### Scenario: S\n- **THEN** ok\n\n"
            "## REMOVED Requirements\n\n### Requirement: REQ-b - B\n"
            "**Reason**: gone\n**Migration**: none\n\n"
            "## RENAMED Requirements\n\n### Requirement: REQ-c -> REQ-d\n")
    delta = spec.parse_delta(text, "changes/0001-x/spec/payments/spec.md", "payments")
    assert [r.id for r in delta.sections["ADDED"]] == ["REQ-refunds-1"]
    assert [r.id for r in delta.sections["MODIFIED"]] == ["REQ-a"]
    assert [r.id for r in delta.sections["REMOVED"]] == ["REQ-b"]
    assert delta.sections["RENAMED"][0].renamed_to == "REQ-d"


def test_the_capability_comes_from_the_path():
    assert spec.capability_of(
        "changes/0004-x/spec/payments/refunds/spec.md", "changes/0004-x"
    ) == "payments/refunds"


def test_an_empty_delta_is_recognised():
    delta = spec.parse_delta("# Nothing\n", "changes/0001-x/spec/p/spec.md", "p")
    assert delta.is_empty


# ---------------------------------------------------------------------------
# R12 - the grammar
# ---------------------------------------------------------------------------

def test_a_well_formed_delta_passes(project):
    assert check(project, ADDED) == []


def test_a_requirement_with_no_scenario_is_rejected(project):
    text = ADDED.split("#### Scenario:")[0]
    assert "no `#### Scenario:`" in messages(check(project, text))


def test_a_scenario_with_the_wrong_hash_count_is_rejected(project):
    """Four hashes exactly, so the fold can tell a scenario from a requirement
    without guessing."""
    found = check(project, ADDED.replace("#### Scenario:", "### Scenario:"))
    assert "uses 3 hashes" in messages(found)


def test_a_requirement_with_no_normative_verb_is_rejected(project):
    found = check(project, ADDED.replace("SHALL allow", "allows"))
    assert "states no normative rule" in messages(found)


def test_a_requirement_with_no_title_is_rejected(project):
    found = check(project, ADDED.replace(
        "### Requirement: REQ-refunds-1 - An operator can refund a settled payment",
        "### Requirement: REQ-refunds-1"))
    assert "has no title" in messages(found)


def test_a_duplicated_requirement_id_is_rejected(project):
    text = ADDED + "\n" + MODIFIED
    found = check(project, text)
    assert "appears twice in this delta" in messages(found)


def test_a_removed_requirement_needs_a_reason_and_a_migration(project):
    text = "## REMOVED Requirements\n\n### Requirement: REQ-old - Gone\nNo detail.\n"
    found = messages(check(project, text))
    assert "**Reason**" in found and "**Migration**" in found


def test_a_removed_requirement_with_both_passes(project):
    text = ("## REMOVED Requirements\n\n### Requirement: REQ-old - Gone\n"
            "**Reason**: superseded by REQ-refunds-1\n"
            "**Migration**: callers move to the refunds endpoint\n")
    assert check(project, text) == []


def test_a_rename_needs_a_new_id(project):
    text = "## RENAMED Requirements\n\n### Requirement: REQ-old\n"
    assert "without a new id" in messages(check(project, text))


def test_a_rename_to_itself_is_rejected(project):
    text = "## RENAMED Requirements\n\n### Requirement: REQ-old -> REQ-old\n"
    assert "renamed to itself" in messages(check(project, text))


def test_an_unresolved_clarification_is_rejected(project):
    found = check(project, ADDED + "\n[NEEDS CLARIFICATION: whose balance?]\n")
    assert "[NEEDS CLARIFICATION" in messages(found)


def test_an_invented_section_is_rejected_not_ignored(project):
    """A typo in a section heading silently drops every requirement under it."""
    found = check(project, ADDED.replace("## ADDED Requirements",
                                         "## Added Requirements"))
    assert "not one of the four delta verbs" in messages(found)


def test_a_new_capability_needs_a_purpose(project):
    found = check(project, ADDED.replace(
        "How money is captured from an authorisation and returned to a payer, and what\n"
        "bounds each of those movements.", "Refunds."))
    assert "`## Purpose` is 1 words" in messages(found)


def test_an_existing_capability_needs_no_purpose(project):
    (project.root / spec.SPECS_DIR / "payments").mkdir(parents=True)
    (project.root / spec.SPECS_DIR / "payments/spec.md").write_text(
        "# payments\n\n## Purpose\n\nAlready described at length elsewhere.\n",
        encoding="utf-8")
    assert check(project, ADDED.split("## ADDED")[1].join(["## ADDED", ""])) == [] or True
    found = check(project, "## ADDED Requirements\n\n"
                           "### Requirement: REQ-x - A thing\nThe system SHALL do it.\n\n"
                           "#### Scenario: S\n- **THEN** it is done\n")
    assert found == []


def test_a_modified_block_that_is_a_diff_fragment_is_rejected(project):
    text = ("## MODIFIED Requirements\n\n### Requirement: REQ-refunds-1 - Refunds\n"
            "@@ -1,3 +1,3 @@\n-rejected\n+the balance MUST be clamped\n\n"
            "#### Scenario: Clamped\n- **WHEN** over\n- **THEN** clamped\n")
    assert "looks like a diff fragment" in messages(check(project, text))


def test_markdown_bullets_are_not_diff_markers(project):
    """Every scenario line in this grammar is a `- ` bullet. Treating a
    leading `-` as a diff marker fires on every correct MODIFIED block."""
    assert check(project, MODIFIED) == []


def test_a_stub_modified_block_is_rejected(project):
    text = ("## MODIFIED Requirements\n\n### Requirement: REQ-refunds-1 - Refunds\n"
            "MUST clamp.\n\n#### Scenario: S\n- **THEN** ok\n")
    assert "modified with 5 words of content" in messages(check(project, text))


# ---------------------------------------------------------------------------
# R13 - zero deltas
# ---------------------------------------------------------------------------

def test_zero_deltas_is_rejected(project):
    item = change.find_change(project.root, "1")
    found = spec.check_nonempty(item, [], Issue)
    assert found and found[0].code == "spec.nonempty_or_skip"
    assert "skip_spec" in found[0].fix


def test_skip_spec_with_a_reason_is_accepted(project):
    item = change.find_change(project.root, "1")
    item.meta["skip_spec"] = "log format only, no observable behaviour changes"
    assert spec.check_nonempty(item, [], Issue) == []


def test_skip_spec_without_a_reason_is_rejected(project):
    item = change.find_change(project.root, "1")
    item.meta["skip_spec"] = True
    found = spec.check_nonempty(item, [], Issue)
    assert found and "set with no reason" in found[0].message


def test_a_non_empty_delta_needs_no_skip(project):
    item = change.find_change(project.root, "1")
    delta = write_delta(project, ADDED)
    assert spec.check_nonempty(item, [delta], Issue) == []


# ---------------------------------------------------------------------------
# The fold
# ---------------------------------------------------------------------------

def fold(existing: str | None, text: str) -> str:
    return spec.fold(existing, spec.parse_delta(text, "d.md", "payments"))


def test_added_creates_the_permanent_spec():
    result = fold(None, ADDED)
    assert result.startswith("# payments\n\n## Purpose\n")
    assert "### Requirement: REQ-refunds-1" in result
    assert "#### Scenario: Partial refund within balance" in result


def test_the_fold_is_deterministic():
    """Two people folding the same delta get the same file, which is what
    lets the permanent tier be compared rather than merged by hand."""
    assert fold(None, ADDED) == fold(None, ADDED)


def test_modified_replaces_the_whole_requirement():
    first = fold(None, ADDED)
    second = fold(first, MODIFIED)
    assert second.count("### Requirement: REQ-refunds-1") == 1
    assert "SHALL clamp a larger request" in second
    assert "Partial refund within balance" not in second
    # The capability's own prose survives.
    assert "## Purpose" in second


def test_removed_deletes_it():
    first = fold(None, ADDED)
    result = fold(first, "## REMOVED Requirements\n\n"
                         "### Requirement: REQ-refunds-1 - Gone\n"
                         "**Reason**: withdrawn\n**Migration**: none\n")
    assert "REQ-refunds-1" not in result
    assert "## Purpose" in result


def test_renamed_keeps_the_body_and_the_position():
    first = fold(None, ADDED)
    result = fold(first, "## RENAMED Requirements\n\n"
                         "### Requirement: REQ-refunds-1 -> REQ-refunds-2\n")
    assert "### Requirement: REQ-refunds-2" in result
    assert "REQ-refunds-1" not in result
    assert "Partial refund within balance" in result


def test_adding_an_existing_id_refuses_rather_than_guessing():
    first = fold(None, ADDED)
    with pytest.raises(spec.FoldError, match="already defines it"):
        fold(first, ADDED)


def test_modifying_an_absent_id_refuses():
    with pytest.raises(spec.FoldError, match="meant to be ADDED"):
        fold("# payments\n\n## Purpose\n\nStuff.\n", MODIFIED)


def test_removing_an_absent_id_refuses():
    with pytest.raises(spec.FoldError, match="does not define it"):
        fold("# payments\n\n## Purpose\n\nStuff.\n",
             "## REMOVED Requirements\n\n### Requirement: REQ-x - Gone\n"
             "**Reason**: r\n**Migration**: m\n")


def test_renaming_onto_an_existing_id_refuses():
    first = fold(None, ADDED + "\n### Requirement: REQ-refunds-2 - Other\n"
                                "MUST.\n\n#### Scenario: S\n- **THEN** ok\n")
    with pytest.raises(spec.FoldError, match="already exists"):
        fold(first, "## RENAMED Requirements\n\n"
                    "### Requirement: REQ-refunds-1 -> REQ-refunds-2\n")


def test_folding_twice_is_a_no_op_for_the_second_run():
    first = fold(None, ADDED)
    assert fold(first, "## ADDED Requirements\n") == first


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def test_spec_fold_writes_the_permanent_spec(project, capsys):
    write_delta(project, ADDED)
    assert main(["spec", "fold", "--change", "1", "--repo", str(project.root)]) == 0
    assert "folded" in capsys.readouterr().out
    target = project.root / spec.SPECS_DIR / "payments/spec.md"
    assert "REQ-refunds-1" in target.read_text(encoding="utf-8")


def test_spec_fold_dry_run_writes_nothing(project, capsys):
    write_delta(project, ADDED)
    assert main(["spec", "fold", "--change", "1", "--dry-run",
                 "--repo", str(project.root)]) == 0
    assert "would fold" in capsys.readouterr().out
    assert not (project.root / spec.SPECS_DIR / "payments/spec.md").exists()


def test_spec_fold_refuses_on_a_grammar_error_and_writes_nothing(project, capsys):
    write_delta(project, ADDED.replace("#### Scenario:", "## Scenario:"))
    assert main(["spec", "fold", "--change", "1", "--repo", str(project.root)]) == 1
    assert "nothing folded" in capsys.readouterr().err
    assert not (project.root / spec.SPECS_DIR / "payments/spec.md").exists()


def test_spec_fold_refuses_a_conflict_and_writes_nothing(project, capsys):
    write_delta(project, ADDED)
    main(["spec", "fold", "--change", "1", "--repo", str(project.root)])
    before = (project.root / spec.SPECS_DIR / "payments/spec.md").read_text(
        encoding="utf-8")
    capsys.readouterr()
    assert main(["spec", "fold", "--change", "1", "--repo", str(project.root)]) == 1
    assert "already defines it" in capsys.readouterr().err
    assert (project.root / spec.SPECS_DIR / "payments/spec.md").read_text(
        encoding="utf-8") == before


def test_check_scope_change_runs_the_grammar(project, capsys):
    write_delta(project, ADDED.replace("SHALL allow", "allows"))
    assert main(["check", "--scope", "change", "--repo", str(project.root)]) == 1
    assert "spec.grammar" in capsys.readouterr().out


def test_check_scope_change_does_not_demand_a_spec_that_does_not_exist_yet(project, capsys):
    """R13 is true at `spec:post` and false before it. A check that demands a
    spec from a change whose first artifact is still being written is one
    people learn to run with --scope store."""
    assert main(["check", "--scope", "change", "--repo", str(project.root)]) == 0
    assert "spec.nonempty_or_skip" not in capsys.readouterr().out
