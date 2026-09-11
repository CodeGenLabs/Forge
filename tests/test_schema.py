"""The workflow schema loader and its validations."""

from __future__ import annotations

import pytest
import yaml

from forge import schema

MINIMAL = """\
name: tiny
version: 1
tracks: [B, C]
artifacts:
  - id: proposal
    generates: proposal.md
    requires: []
    tracks: [B, C]
  - id: tasks
    generates: tasks.md
    requires: [proposal]
    tracks: [B, C]
"""


def parse(text: str) -> schema.Schema:
    return schema.parse_schema(text, source="test.yaml")


def fails(text: str, needle: str) -> str:
    with pytest.raises(schema.SchemaError) as info:
        parse(text)
    assert needle in str(info.value), str(info.value)
    return str(info.value)


# ---------------------------------------------------------------------------
# The built-in workflow
# ---------------------------------------------------------------------------

def test_the_builtin_feature_workflow_is_valid():
    """It ships as text and is parsed by the same code a project's copy uses,
    so this is the only thing standing between a typo and every command."""
    loaded = parse(schema.builtin_schema_text("feature"))
    assert loaded.name == "feature"
    assert loaded.ids == ["proposal", "spec", "impact", "design", "tasks", "verification"]


def test_the_builtin_workflow_is_valid_yaml_with_a_conditional_track():
    """A bare `?` opens a YAML complex key, so `[B?, C]` - the spelling in
    ARCHITECTURE.md section 4.1 - does not parse. The token is right, it just
    has to be quoted."""
    raw = yaml.safe_load(schema.builtin_schema_text("feature"))
    spec = next(a for a in raw["artifacts"] if a["id"] == "spec")
    assert spec["tracks"] == ["B?", "C"]


def test_the_tracks_match_the_workflow_document():
    loaded = parse(schema.builtin_schema_text("feature"))
    on_b = [a.id for a in loaded.for_track("B")]
    on_c = [a.id for a in loaded.for_track("C")]
    # WORKFLOW.md section 1: B is proposal + spec-if-behaviour-changes + tasks.
    assert on_b == ["proposal", "spec", "tasks", "verification"]
    assert on_c == ["proposal", "spec", "impact", "design", "tasks", "verification"]
    # Track A is a question, not a deliverable.
    assert parse(schema.builtin_schema_text("feature")).for_track("A") == []


def test_a_lighter_track_filters_prerequisites_rather_than_blocking_on_them(repo):
    """`tasks` requires `impact`, which track B does not have. Treating that as
    unsatisfiable would make every bounded change block forever on a file its
    own track never asks for."""
    loaded = parse(schema.builtin_schema_text("feature"))
    tasks = loaded.by_id("tasks")
    assert loaded.requires_on(tasks, "C") == ["spec", "impact", "design"]
    assert loaded.requires_on(tasks, "B") == ["spec"]


def test_load_falls_back_to_the_builtin(repo):
    loaded = schema.load_schema(repo.root, "feature")
    assert loaded.source.startswith("<built-in")


def test_a_project_copy_wins(repo):
    (repo.root / ".forge/schema").mkdir(parents=True)
    (repo.root / ".forge/schema/feature.yaml").write_text(MINIMAL, encoding="utf-8")
    loaded = schema.load_schema(repo.root, "feature")
    assert loaded.name == "tiny"
    assert loaded.source == ".forge/schema/feature.yaml"


def test_an_unknown_workflow_names_what_exists(repo):
    with pytest.raises(schema.SchemaError, match="ships only feature"):
        schema.load_schema(repo.root, "bugfix")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_a_newer_schema_version_is_refused():
    """A workflow the kernel half-understands runs half a lifecycle and reports
    success, which is worse than refusing to start."""
    fails(MINIMAL.replace("version: 1", "version: 2"), "newer than this kernel")


def test_version_is_required():
    fails(MINIMAL.replace("version: 1\n", ""), "`version` is required")


def test_duplicate_ids_are_refused():
    fails(MINIMAL.replace("id: tasks", "id: proposal"), "duplicate artifact id")


def test_a_requires_target_must_exist():
    fails(MINIMAL.replace("requires: [proposal]", "requires: [design]"),
          "requires 'design', which no artifact declares")


def test_self_reference_is_refused():
    fails(MINIMAL.replace("requires: [proposal]", "requires: [tasks]"),
          "'tasks' requires itself")


def test_a_cycle_is_reported_with_its_full_path():
    text = MINIMAL.replace("  - id: proposal\n    generates: proposal.md\n    requires: []",
                           "  - id: proposal\n    generates: proposal.md\n    requires: [tasks]")
    message = fails(text, "cyclic")
    # A cycle named by one node is a puzzle; a cycle named by its path is a fix.
    assert "proposal -> tasks -> proposal" in message


@pytest.mark.parametrize("bad", ["/etc/passwd", "../../outside.md", "C:/windows/x.md",
                                 "spec/../../escape.md"])
def test_generates_may_not_escape_the_change_directory(bad):
    """Every path is joined to `changes/NNNN/`, and a schema is a file a
    project edits."""
    fails(MINIMAL.replace("generates: proposal.md", f"generates: {bad}"),
          "generates")


def test_an_id_must_be_a_kebab_slug():
    fails(MINIMAL.replace("id: proposal", "id: Proposal_1"), "kebab slug")


def test_an_unknown_track_token_is_refused():
    fails(MINIMAL.replace("tracks: [B, C]\nartifacts", "tracks: [B, Z]\nartifacts"),
          "unknown track")
    fails(MINIMAL.replace("    tracks: [B, C]", "    tracks: [maybe]", 1),
          "is not a track token")


def test_a_conditional_track_needs_a_named_skip_key():
    """An escape hatch with no reason beside it is taken by default."""
    fails(MINIMAL.replace('    tracks: [B, C]', '    tracks: ["B?", C]', 1),
          "needs a `skip_key`")


def test_artifacts_must_be_a_non_empty_list():
    fails("name: x\nversion: 1\nartifacts: []\n", "non-empty list")


def test_a_malformed_file_names_itself():
    with pytest.raises(schema.SchemaError, match="test.yaml: not valid YAML"):
        parse("name: [unclosed\n")
