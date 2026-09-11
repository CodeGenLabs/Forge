"""Changes, and state derived from the filesystem rather than from a state file."""

from __future__ import annotations

import json
from datetime import date

import pytest
import yaml

from forge import change, schema
from forge.cli import main

TODAY = date(2026, 9, 11)


@pytest.fixture
def project(repo):
    repo.write("README.md", "# A project\n")
    repo.commit("a repository")
    main(["init", "--repo", str(repo.root)])
    repo.commit("forge init")
    return repo


def feature(repo) -> schema.Schema:
    return schema.load_schema(repo.root, "feature")


def states(item: change.Change, repo) -> dict[str, str]:
    return {s.id: s.state for s in item.state(feature(repo))}


# ---------------------------------------------------------------------------
# Naming and discovery
# ---------------------------------------------------------------------------

def test_a_new_change_is_numbered_and_slugged(project):
    item = change.new_change(project.root, "Refund support!", today=TODAY)
    assert item.name == "0001-refund-support"
    assert (item.root / ".forge.yaml").is_file()
    assert item.meta["created"] == "2026-09-11"
    assert item.meta["title"] == "Refund support!"


def test_numbers_are_monotonic_across_the_archive(project):
    """Reusing a number the archive already holds would make `changes/0004`
    mean two things depending on the date."""
    change.new_change(project.root, "first", today=TODAY)
    archived = project.root / change.ARCHIVE_DIR / "2026-09-01-0007-older"
    archived.mkdir(parents=True)
    (archived / ".forge.yaml").write_text("track: C\n", encoding="utf-8")
    assert change.new_change(project.root, "second", today=TODAY).number == 8


def test_a_change_resolves_by_number_padded_number_slug_or_name(project):
    change.new_change(project.root, "refund support", today=TODAY)
    for reference in ("1", "0001", "refund-support", "0001-refund-support"):
        assert change.find_change(project.root, reference).number == 1


def test_an_unknown_reference_lists_what_is_open(project):
    change.new_change(project.root, "refund support", today=TODAY)
    with pytest.raises(change.ChangeError, match="open changes are 0001-refund-support"):
        change.find_change(project.root, "9")


def test_a_duplicated_number_is_ambiguous_not_guessed(project):
    """Every downstream write would land in an arbitrary one of them."""
    change.new_change(project.root, "one", today=TODAY)
    (project.root / "changes/0001-another").mkdir()
    with pytest.raises(change.ChangeError, match="ambiguous"):
        change.find_change(project.root, "1")


def test_a_title_with_no_letters_is_refused(project):
    with pytest.raises(change.ChangeError, match="letters or digits"):
        change.new_change(project.root, "!!!", today=TODAY)


# ---------------------------------------------------------------------------
# Filesystem-derived state
# ---------------------------------------------------------------------------

def test_an_artifact_is_complete_because_its_file_exists(project):
    item = change.new_change(project.root, "refunds", today=TODAY)
    assert states(item, project)["proposal"] == change.MISSING
    (item.root / "proposal.md").write_text("# Why\n\nBecause.\n", encoding="utf-8")
    assert states(item, project)["proposal"] == change.COMPLETE


def test_a_glob_artifact_is_complete_on_any_match(project):
    item = change.new_change(project.root, "refunds", today=TODAY)
    target = item.root / "spec/payments"
    target.mkdir(parents=True)
    (target / "spec.md").write_text("## ADDED Requirements\n", encoding="utf-8")
    assert states(item, project)["spec"] == change.COMPLETE


def test_what_is_blocked_is_requires_minus_complete(project):
    item = change.new_change(project.root, "refunds", today=TODAY)
    seen = states(item, project)
    assert seen["spec"] == change.BLOCKED
    blocked = next(s for s in item.state(feature(project)) if s.id == "design")
    assert blocked.waiting_on == ["spec", "impact"]


def test_track_b_does_not_see_track_c_artifacts(project):
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    seen = states(item, project)
    assert seen["impact"] == change.NOT_ON_TRACK
    assert seen["design"] == change.NOT_ON_TRACK


def test_tasks_on_track_b_waits_only_for_what_track_b_has(project):
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    tasks = next(s for s in item.state(feature(project)) if s.id == "tasks")
    assert tasks.waiting_on == ["spec"]


def test_there_is_no_state_file_beyond_the_track(project):
    """ARCHITECTURE.md section 4.4. `.forge.yaml` holds only what the
    filesystem cannot answer."""
    item = change.new_change(project.root, "refunds", today=TODAY)
    assert set(item.meta) == {"track", "workflow", "created", "title"}


# ---------------------------------------------------------------------------
# The conditional artifact and its named bypass
# ---------------------------------------------------------------------------

def test_a_conditional_artifact_is_required_until_it_is_skipped(project):
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    (item.root / "proposal.md").write_text("# Why\n\nBecause.\n", encoding="utf-8")
    assert states(item, project)["spec"] == change.MISSING
    item.meta["skip_spec"] = "log format only, no behaviour change"
    item.write_meta()
    reloaded = change.find_change(project.root, "1")
    assert states(reloaded, project)["spec"] == change.SKIPPED


def test_a_skip_satisfies_what_depended_on_it(project):
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    (item.root / "proposal.md").write_text("# Why\n\nBecause.\n", encoding="utf-8")
    item.meta["skip_spec"] = "log format only"
    item.write_meta()
    reloaded = change.find_change(project.root, "1")
    assert states(reloaded, project)["tasks"] == change.MISSING


def test_a_bare_skip_flag_still_records_that_no_reason_was_given(project):
    """OpenSpec's named-bypass pattern: an escape hatch with no reason beside
    it is taken by default, and then the reason nobody wrote is the one nobody
    can argue with later."""
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    item.meta["skip_spec"] = True
    item.write_meta()
    reloaded = change.find_change(project.root, "1")
    skipped = next(s for s in reloaded.state(feature(project)) if s.id == "spec")
    assert skipped.state == change.SKIPPED
    assert "no reason" in skipped.reason


def test_a_conditional_artifact_is_unconditional_on_the_heavier_track(project):
    """Upgrading revokes the bypass. `spec` is `B?` and plain `C`, so a change
    that skipped it on B owes it once the track says the behaviour matters."""
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    (item.root / "proposal.md").write_text("# Why\n\nBecause.\n", encoding="utf-8")
    item.meta["skip_spec"] = "log format only"
    item.write_meta()
    item.upgrade("C", reason="touches ARC-layers")
    reloaded = change.find_change(project.root, "1")
    assert states(reloaded, project)["spec"] == change.MISSING


# ---------------------------------------------------------------------------
# The one-way ratchet
# ---------------------------------------------------------------------------

def test_upgrading_records_where_it_came_from(project):
    item = change.new_change(project.root, "tidy", track="B", today=TODAY)
    item.upgrade("C", reason="adds a public route")
    stored = yaml.safe_load((item.root / ".forge.yaml").read_text(encoding="utf-8"))
    assert stored["track"] == "C"
    assert stored["upgraded_from"] == ["B: adds a public route"]


def test_downgrading_is_refused(project):
    """A change that turned out to touch an ARC- claim must not be able to
    shed the artifacts that account for it."""
    item = change.new_change(project.root, "big", track="C", today=TODAY)
    with pytest.raises(change.ChangeError, match="does not downgrade"):
        item.upgrade("B", reason="actually it is small")


def test_upgrading_to_the_same_track_is_refused(project):
    item = change.new_change(project.root, "big", track="C", today=TODAY)
    with pytest.raises(change.ChangeError, match="already on track C"):
        item.upgrade("C", reason="no-op")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def test_task_completion_is_the_checkbox(project):
    item = change.new_change(project.root, "refunds", today=TODAY)
    (item.root / "tasks.md").write_text(
        "## Tasks\n\n- [x] Write the failing test\n- [ ] Make it pass\n* [X] Tidy up\n",
        encoding="utf-8")
    assert item.tasks() == [
        (True, "Write the failing test"),
        (False, "Make it pass"),
        (True, "Tidy up"),
    ]


def test_no_tasks_file_is_no_tasks(project):
    item = change.new_change(project.root, "refunds", today=TODAY)
    assert item.tasks() == []


# ---------------------------------------------------------------------------
# The command surface
# ---------------------------------------------------------------------------

def test_change_new_reports_the_artifacts_the_track_wants(project, capsys):
    assert main(["change", "new", "refund support", "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "changes/0001-refund-support/" in out
    assert "proposal, spec, impact, design, tasks, verification" in out


def test_change_new_on_track_a_says_there_is_nothing_to_write(project, capsys):
    main(["change", "new", "can we", "--track", "A", "--repo", str(project.root)])
    assert "not a deliverable" in capsys.readouterr().out


def test_change_list_is_empty_with_a_next_step(project, capsys):
    assert main(["change", "list", "--repo", str(project.root)]) == 0
    assert "no open changes" in capsys.readouterr().out


def test_change_show_names_the_next_artifact(project, capsys):
    main(["change", "new", "refunds", "--repo", str(project.root)])
    capsys.readouterr()
    assert main(["change", "show", "1", "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "Next: write proposal.md" in out
    assert "waiting on spec, impact" in out


def test_change_show_json(project, capsys):
    main(["change", "new", "refunds", "--repo", str(project.root)])
    capsys.readouterr()
    assert main(["change", "show", "1", "--repo", str(project.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["track"] == "C"
    assert payload["state"] == "next: proposal"
    by_id = {a["id"]: a for a in payload["artifacts"]}
    assert by_id["design"]["waiting_on"] == ["spec", "impact"]


def test_change_track_reports_what_is_now_owed(project, capsys):
    main(["change", "new", "tidy", "--track", "B", "--repo", str(project.root)])
    capsys.readouterr()
    assert main(["change", "track", "1", "--to", "C", "--reason", "adds a route",
                 "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "track B -> C" in out
    # Only what the upgrade newly owes, not the whole track: the artifacts
    # already on track B were already owed and saying so again is noise.
    assert "newly required: impact, design" in out


def test_change_track_refuses_a_downgrade_with_exit_two(project, capsys):
    main(["change", "new", "big", "--repo", str(project.root)])
    capsys.readouterr()
    assert main(["change", "track", "1", "--to", "B", "--reason", "smaller",
                 "--repo", str(project.root)]) == 2
    assert "one-way" in capsys.readouterr().err


def test_status_shows_open_changes(project, capsys):
    main(["change", "new", "refunds", "--repo", str(project.root)])
    project.commit("open a change")
    main(["sync", "derived", "--repo", str(project.root)])
    project.commit("chore: sync derived tier")
    capsys.readouterr()
    main(["status", "--repo", str(project.root)])
    out = capsys.readouterr().out
    assert "change 0001-refunds" in out
    assert "next proposal" in out


def test_init_writes_the_workflow_so_it_can_be_edited(project):
    """The kernel would use its built-in copy forever, but a workflow you
    cannot see is a workflow you cannot edit."""
    target = project.root / ".forge/schema/feature.yaml"
    assert target.is_file()
    assert schema.load_schema(project.root, "feature").source == ".forge/schema/feature.yaml"
