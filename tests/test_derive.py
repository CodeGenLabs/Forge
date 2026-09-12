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


# --------------------------------------------------------------------------
# Project configuration
# --------------------------------------------------------------------------

def test_exclude_id_scan_keeps_the_file_but_drops_its_ids(project):
    """The two exclusion keys exist because conflating them costs a project its
    own test statistics in order to silence a few fixtures."""
    project.write(".forge/config.yaml", 'derive:\n  exclude_id_scan:\n    - "tests/*"\n')
    project.commit("exclude fixture ids")

    data = derive.build_tests(project.root)
    assert data["total_tests"] == 2, "the tests must still be counted"
    assert data["tagged_tests"] == 0, "their @covers tags must not be harvested"
    assert data["covers_index"] == {}


def test_exclude_drops_the_file_entirely(project):
    project.write(".forge/config.yaml", 'derive:\n  exclude:\n    - "tests/*"\n')
    project.commit("exclude tests outright")
    assert derive.build_inventory(project.root)["test_files"] == []


def test_a_directory_pattern_covers_its_subtree(project):
    """`tests/*` is what a person writes for "the tests"; fnmatch alone would
    not match a nested path, and a config that does not behave the way it reads
    is a trap."""
    project.write("tests/unit/test_deep.py", "# @covers INV-5\ndef test_deep():\n    assert True\n")
    project.write(".forge/config.yaml", 'derive:\n  exclude_id_scan:\n    - "tests/*"\n')
    project.commit("nested test plus exclusion")
    assert derive.build_tests(project.root)["covers_index"] == {}


def test_a_malformed_config_falls_back_to_defaults(project):
    """A tool that refuses to start because its optional config has a typo is
    worse than one that starts with defaults and says so."""
    from forge.config import load_config

    project.write(".forge/config.yaml", "derive: [this is not a mapping\n")
    project.commit("break the config")
    config = load_config(project.root)
    assert config.error is not None
    assert config.exclude == [] and config.exclude_id_scan == []
    # And the tier still builds.
    assert derive.build_inventory(project.root)["files_tracked"] > 0


def test_no_config_is_not_an_error(project):
    from forge.config import load_config

    config = load_config(project.root)
    assert config.source is None and config.error is None


# --------------------------------------------------------------------------
# AST-confirmed comment harvesting (R5 / F11)
# --------------------------------------------------------------------------

def test_covers_in_string_literals_are_ignored(project):
    """String literals in fixtures must not be harvested as active coverage tags."""
    project.write("tests/test_fixture.py", '''\
TESTS = """\\
# @covers INV-fake-fixture
def test_fake():
    assert True
"""

# @covers REQ-real
def test_real():
    assert True
''')
    project.commit("fixture strings vs real comments")
    data = derive.build_tests(project.root)
    entry = data["files"]["tests/test_fixture.py"]
    covers_map = {t["name"]: t["covers"] for t in entry["tests"]}
    assert covers_map.get("test_real") == ["REQ-real"]
    assert "INV-fake-fixture" not in data["covers_index"]
    assert data["covers_index"].get("REQ-real") == ["tests/test_fixture.py::test_real"]


def test_backrefs_in_string_literals_are_ignored(project):
    """forge:<ID> strings inside code string literals must not be indexed."""
    project.write("src/demo/rules.py", '''\
# forge:ARC-real
RULE_TEMPLATE = "forge:ARC-fake-string"

def check():
    s = "forge:ARC-also-fake"
    return True
''')
    project.commit("code backrefs")
    data = derive.build_backrefs(project.root)
    assert "ARC-real" in data["by_id"]
    assert "ARC-fake-string" not in data["by_id"]
    assert "ARC-also-fake" not in data["by_id"]


def test_typescript_comments_vs_literals(project):
    """TypeScript/TSX comments are confirmed via AST, ignoring string literals."""
    project.write("tests/service.test.ts", '''\
const FIXTURE = `
// @covers REQ-ts-fake
test("fake", () => {});
`;

/*
 * @covers REQ-ts-real
 */
test("real", () => {
    const s = "// @covers REQ-ts-fake-inline";
});
''')
    project.commit("ts comments vs literals")
    data = derive.build_tests(project.root)
    assert "REQ-ts-real" in data["covers_index"]
    assert "REQ-ts-fake" not in data["covers_index"]
    assert "REQ-ts-fake-inline" not in data["covers_index"]


def test_go_comments_vs_literals(project):
    """Go comments are confirmed via AST, ignoring raw string literals."""
    project.write("pkg_test.go", '''\
package demo

const fixture = `
// @covers REQ-go-fake
func TestFake(t *testing.T) {}
`

// @covers REQ-go-real
func TestReal(t *testing.T) {
    s := "// @covers REQ-go-fake-inline"
}
''')
    project.commit("go comments vs literals")
    data = derive.build_tests(project.root)
    assert "REQ-go-real" in data["covers_index"]
    assert "REQ-go-fake" not in data["covers_index"]
    assert "REQ-go-fake-inline" not in data["covers_index"]

