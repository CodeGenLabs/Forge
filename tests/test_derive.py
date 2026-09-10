"""The derived tier: determinism first, content second.

Determinism is not a nicety here. `forge check` reports a hand-edited or stale
derived file by regenerating it and comparing bytes, so any non-determinism —
a timestamp, an unsorted dict, a platform newline — turns that check into a
permanent false alarm and it gets disabled. Most of these tests are about that.
"""

from __future__ import annotations

import json

import pytest

from forge import derive


@pytest.fixture
def project(repo):
    repo.write("pyproject.toml", """\
[project]
name = "demo"
requires-python = ">=3.11"
dependencies = ["requests>=2.0", "pyyaml"]

[project.scripts]
demo = "demo.cli:main"
""")
    repo.write("src/demo/__init__.py", "")
    repo.write("src/demo/cli.py", "def main():\n    return 0\n")
    repo.write("src/demo/pay.py", "def refundable(a, b):\n    return a - b\n")
    repo.write("tests/test_pay.py", """\
from demo.pay import refundable


# @covers INV-7 REQ-refunds-1
def test_refund_is_bounded():
    assert refundable(100, 30) == 70


def test_untagged():
    assert True
""")
    repo.write("README.md", "# demo\n")
    repo.commit("initial")
    return repo


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------

def test_envelope_carries_no_timestamp(project):
    """The design document sketched `generated_at`; it cannot exist.

    A timestamp makes every regeneration differ, so "regeneration is a no-op"
    and "a dirty derived file is an error" could never both hold. The commit id
    is the provenance that matters.
    """
    payload = derive.envelope(project.root, "test", "forge", {"x": 1})
    assert "generated_at" not in payload
    assert "generated_from_commit" in payload
    assert payload["generated_from_commit"] == project.head


def test_render_is_byte_identical_across_calls(project):
    payload = derive.envelope(project.root, "test", "forge", derive.build_inventory(project.root))
    assert derive.render_json(payload) == derive.render_json(payload)


def test_render_uses_lf_and_sorted_keys(project):
    payload = {"b": 1, "a": {"d": 2, "c": 3}}
    rendered = derive.render_json(payload)
    assert b"\r\n" not in rendered
    assert rendered.endswith(b"\n")
    assert rendered.index(b'"a"') < rendered.index(b'"b"')
    assert rendered.index(b'"c"') < rendered.index(b'"d"')


def test_regeneration_is_a_no_op(project):
    first = derive.derive_all(project.root)
    assert all(first.values()), "first build should write every artifact"
    assert not any(derive.derive_all(project.root).values())


def test_dry_run_reports_without_writing(project):
    derive.derive_all(project.root)
    target = project.root / derive.DERIVED_DIR / "inventory.json"
    before = target.read_bytes()

    target.write_bytes(b'{"tampered": true}\n')
    assert derive.derive_all(project.root, dry_run=True)["inventory.json"] is True
    assert target.read_bytes() == b'{"tampered": true}\n', "dry run must not write"

    derive.derive_all(project.root)
    assert target.read_bytes() == before


def test_only_limits_what_is_rebuilt(project):
    derive.derive_all(project.root)
    changed = derive.derive_all(project.root, only=["inventory.json"])
    assert set(changed) == {"inventory.json"}


# --------------------------------------------------------------------------
# inventory.json
# --------------------------------------------------------------------------

def test_inventory_counts_and_labels(project):
    data = derive.build_inventory(project.root)
    assert data["by_language"]["python"]["files"] == 4
    assert data["by_language"]["markdown"]["files"] == 1
    assert data["by_language"]["toml"]["files"] == 1
    assert data["files_tracked"] == data["files_considered"]


def test_inventory_resolves_a_console_script_to_a_file(project):
    """`demo.cli:main` is a module and a function, not something to open."""
    assert derive.build_inventory(project.root)["entry_points"] == ["src/demo/cli.py"]


def test_inventory_finds_test_files(project):
    assert derive.build_inventory(project.root)["test_files"] == ["tests/test_pay.py"]


def test_inventory_records_declared_dependencies(project):
    stack = derive.build_inventory(project.root)["stack"]
    assert set(stack["python"]["packages"]) == {"requests", "pyyaml"}
    assert stack["python"]["packages"]["requests"]["declared"] == "requests>=2.0"
    # Nothing was resolved, and the record says so rather than implying a pin.
    assert stack["python"]["packages"]["requests"]["resolved"] is None


def test_inventory_ignores_vendored_directories(project):
    project.write("node_modules/dep/index.js", "module.exports = 1;\n")
    project.commit("add a dependency tree")
    data = derive.build_inventory(project.root)
    assert data["files_considered"] < data["files_tracked"]
    assert not any("node_modules" in p for p in data["test_files"])


# --------------------------------------------------------------------------
# tests.json
# --------------------------------------------------------------------------

def test_covers_tags_are_extracted_and_indexed(project):
    data = derive.build_tests(project.root)
    entry = data["files"]["tests/test_pay.py"]
    names = {t["name"]: t["covers"] for t in entry["tests"]}
    assert names["test_refund_is_bounded"] == ["INV-7", "REQ-refunds-1"]
    assert names["test_untagged"] == []
    assert entry["untagged"] == 1
    assert data["covers_index"]["INV-7"] == ["tests/test_pay.py::test_refund_is_bounded"]


def test_a_tag_does_not_leak_past_the_next_declaration(project):
    """Association is by proximity, so it must stop at the previous test."""
    project.write("tests/test_two.py", """\
# @covers INV-1
def test_first():
    assert True


def test_second():
    assert True
""")
    project.commit("two tests, one tag")
    data = derive.build_tests(project.root)
    names = {t["name"]: t["covers"] for t in data["files"]["tests/test_two.py"]["tests"]}
    assert names["test_first"] == ["INV-1"]
    assert names["test_second"] == []


def test_same_line_tag_is_picked_up(project):
    project.write("tests/test_inline.py", "def test_x():  # @covers INV-2\n    assert True\n")
    project.commit("inline tag")
    data = derive.build_tests(project.root)
    assert data["files"]["tests/test_inline.py"]["tests"][0]["covers"] == ["INV-2"]


# --------------------------------------------------------------------------
# backrefs.json
# --------------------------------------------------------------------------

def test_backrefs_are_found_in_code(project):
    project.write("src/demo/rules.py", "# forge:ARC-3 domain must not import web\nX = 1\n")
    project.commit("add a rule")
    data = derive.build_backrefs(project.root)
    assert data["by_id"]["ARC-3"] == ["src/demo/rules.py:1"]


def test_backrefs_ignore_prose(project):
    """A design document that demonstrates the convention must not create edges.

    Found on this repository: `comment: 'forge:ARC-3'` inside an example, and a
    literal `grep -r "forge:REQ-refunds-3"`, both produced index entries for
    claims that were never meant to exist. Citing an ID in prose is normal;
    only code and rule files declare that they enforce one.
    """
    project.write("docs/design.md", "Tag the rule `forge:ARC-99` to bind it.\n")
    project.commit("document the convention")
    assert "ARC-99" not in derive.build_backrefs(project.root)["by_id"]


# --------------------------------------------------------------------------
# Staleness
# --------------------------------------------------------------------------

def test_staleness_is_counted_in_commits_not_seconds(project):
    derive.derive_all(project.root)
    assert set(derive.stale_artifacts(project.root).values()) == {0}

    project.write("src/demo/pay.py", "def refundable(a, b):\n    return max(0, a - b)\n")
    project.commit("clamp")
    project.write("README.md", "# demo\n\nmore\n")
    project.commit("docs")

    behind = derive.stale_artifacts(project.root)
    assert set(behind.values()) == {2}


def test_absent_artifact_reports_unknown_rather_than_zero(project):
    assert set(derive.stale_artifacts(project.root).values()) == {None}


def test_unreadable_artifact_reports_unknown(project):
    derive.derive_all(project.root)
    (project.root / derive.DERIVED_DIR / "inventory.json").write_text("{ not json", encoding="utf-8")
    assert derive.stale_artifacts(project.root)["inventory.json"] is None


def test_artifacts_are_valid_json_with_the_schema_marker(project):
    derive.derive_all(project.root)
    for artifact in derive.ARTIFACTS:
        payload = json.loads(
            (project.root / derive.DERIVED_DIR / artifact.name).read_text(encoding="utf-8")
        )
        assert payload["$schema"] == derive.SCHEMA
        assert "data" in payload


def test_the_derived_tier_does_not_describe_itself(project):
    """Counting its own JSON would make the inventory a description of the
    describer, and every sync would change the count it just wrote."""
    derive.derive_all(project.root)
    project.commit("commit the derived tier")
    data = derive.build_inventory(project.root)
    assert not any(p.startswith(derive.DERIVED_DIR) for p in data["test_files"])
    assert "json" not in data["by_language"], "derived JSON leaked into the inventory"


def test_committing_the_derived_tier_does_not_make_it_stale(project):
    """A file cannot carry the id of the commit that contains it.

    Committing a freshly derived artifact necessarily stamps it with the parent
    commit. If that counted as staleness, the steady state would be permanently
    one commit behind and regenerating would produce another such commit - a
    treadmill. Only commits touching something *outside* the tier count.
    """
    derive.derive_all(project.root)
    project.commit("commit the derived tier")
    assert set(derive.stale_artifacts(project.root).values()) == {0}


def test_a_real_change_still_registers_as_stale(project):
    derive.derive_all(project.root)
    project.commit("commit the derived tier")
    project.write("src/demo/pay.py", "def refundable(a, b):\n    return max(0, a - b)\n")
    project.commit("clamp")
    assert set(derive.stale_artifacts(project.root).values()) == {1}
