"""Q12's bet, made falsifiable: a second host costs a manifest, not a port.

OPEN_QUESTIONS.md Q12 chose one host for v1 "structured so a second is cheap",
against Superpowers' eight plugin manifests plus ~15KB of sync script. The bet
rests on one consequence it names: **a skill must never depend on a
host-specific feature**.

That held for six of the seven skills. `bootstrap` told its reader to fan out
across subagents - a mechanism where it meant an outcome, and one a host
without subagents cannot follow. `skill.host_specific` exists so the next one
is caught by a check rather than by somebody remembering to look.
"""

from __future__ import annotations

import pytest

from forge import hosts, skills
from forge.cli import main


@pytest.fixture
def project(repo):
    repo.write("src/app.py", "def go():\n    return 1\n")
    main(["init", "--repo", str(repo.root)])
    repo.commit("a scaffolded project")
    return repo


# ---------------------------------------------------------------------------
# The rule the bet rests on
# ---------------------------------------------------------------------------

def test_every_shipped_skill_is_host_neutral():
    """The audit, kept. Six of seven passed it the first time it was run."""
    from pathlib import Path

    found = skills.load_skills(Path("."))
    assert found, "the packaged skills must be loadable from this repository"
    offenders = {
        s.name: skills._HOST_SPECIFIC_RE.findall(s.body)
        for s in found if skills._HOST_SPECIFIC_RE.search(s.body)
    }
    assert offenders == {}


@pytest.mark.parametrize("phrase", [
    "one subagent per topic",
    "ask Claude to summarise",
    "register an MCP server",
    "add a slash command",
])
def test_the_rule_catches_a_host_feature(phrase):
    assert skills._HOST_SPECIFIC_RE.search(phrase)


@pytest.mark.parametrize("phrase", [
    "the agent writes the file",
    "a subagenda item",
    "the model decides",
    "run the command",
])
def test_the_rule_leaves_ordinary_prose_alone(phrase):
    """`agent` and `model` are deliberately absent: a skill is written for an
    agent, and saying so is not a dependency on one host."""
    assert not skills._HOST_SPECIFIC_RE.search(phrase)


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def test_a_pointer_manifest_names_every_skill(project):
    outcome, written = hosts.export(project.root, "agents-md")
    assert outcome == "written" and written == ["AGENTS.md"]

    text = (project.root / "AGENTS.md").read_text(encoding="utf-8")
    for skill in skills.load_skills(project.root):
        assert f"`{skill.name}`" in text


def test_it_merges_into_a_file_the_project_already_owns(project):
    """A manifest that overwrites somebody's AGENTS.md is a manifest they
    delete. The monorepo this was exercised on carries its own, in Vietnamese."""
    target = project.root / "AGENTS.md"
    target.write_text("# AGENTS.md\n\nNhững điều quan trọng nhất.\n",
                      encoding="utf-8", newline="\n")

    hosts.export(project.root, "agents-md")
    text = target.read_text(encoding="utf-8")
    assert "Những điều quan trọng nhất." in text
    assert hosts.MARKER_START in text


def test_re_exporting_replaces_the_section_and_nothing_else(project):
    target = project.root / "AGENTS.md"
    target.write_text("# Ours\n\nkeep me\n", encoding="utf-8", newline="\n")
    hosts.export(project.root, "agents-md")
    first = target.read_text(encoding="utf-8")

    assert hosts.export(project.root, "agents-md")[0] == "unchanged"
    assert target.read_text(encoding="utf-8") == first
    assert first.count(hosts.MARKER_START) == 1
    assert "keep me" in first


def test_a_copy_host_writes_the_kernels_skills(project):
    outcome, written = hosts.export(project.root, "forge")
    # `forge init` already wrote them, so there is nothing to do.
    assert outcome == "unchanged" and written == []


def test_a_copy_host_refreshes_a_stale_local_skill(project):
    """`forge init` copies the skills out and they drift in silence. Sourcing
    from the local copy would copy it onto itself and report `unchanged` on
    exactly the repository whose copy was stale."""
    local = project.root / skills.SKILLS_DIR / "bootstrap" / "SKILL.md"
    local.write_text(local.read_text(encoding="utf-8") + "\nan edit\n",
                     encoding="utf-8", newline="\n")

    outcome, written = hosts.export(project.root, "forge")
    assert outcome == "copied"
    assert written == [f"{skills.SKILLS_DIR}/bootstrap/SKILL.md"]
    assert "an edit" not in local.read_text(encoding="utf-8")


def test_an_unknown_host_is_refused(project):
    with pytest.raises(KeyError):
        hosts.export(project.root, "nonesuch")


def test_claude_host_copies_skills(project):
    outcome, written = hosts.export(project.root, "claude")
    assert outcome == "copied"
    assert any(p.startswith(".claude/skills/") for p in written)
    for skill in skills.load_skills(project.root):
        dest = project.root / ".claude/skills" / skill.name / "SKILL.md"
        assert dest.is_file()


def test_antigravity_host_copies_skills(project):
    outcome, written = hosts.export(project.root, "antigravity")
    assert outcome == "copied"
    assert any(p.startswith(".agent/skills/") for p in written)
    for skill in skills.load_skills(project.root):
        dest = project.root / ".agent/skills" / skill.name / "SKILL.md"
        assert dest.is_file()


def test_codex_host_is_alias_for_agents_md(project):
    outcome, written = hosts.export(project.root, "codex")
    assert outcome == "written"
    assert written == ["AGENTS.md"]
    text = (project.root / "AGENTS.md").read_text(encoding="utf-8")
    assert hosts.MARKER_START in text


def test_forge_install_cli(project, capsys):
    rc = main(["install", "--host", "claude", "--repo", str(project.root)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "copied" in captured.out
    assert ".claude/skills" in captured.out
    assert (project.root / ".claude/skills/forge/SKILL.md").is_file()


# ---------------------------------------------------------------------------
# Knowing a copy has drifted
# ---------------------------------------------------------------------------

def test_an_unedited_copy_reads_as_a_copy(project):
    skill = next(s for s in skills.load_skills(project.root) if s.name == "forge")
    assert skills.copy_state(project.root, skill) == "copy"


def test_an_edited_copy_reads_as_stale(project):
    local = project.root / skills.SKILLS_DIR / "forge" / "SKILL.md"
    local.write_text(local.read_text(encoding="utf-8") + "\nan edit\n",
                     encoding="utf-8", newline="\n")

    skill = next(s for s in skills.load_skills(project.root) if s.name == "forge")
    assert skills.copy_state(project.root, skill) == "stale"


def test_line_endings_alone_are_not_a_difference(project):
    """Otherwise a project on the other platform has every copied skill
    reported as diverged."""
    local = project.root / skills.SKILLS_DIR / "forge" / "SKILL.md"
    local.write_bytes(local.read_text(encoding="utf-8").replace("\n", "\r\n")
                      .encode("utf-8"))

    skill = next(s for s in skills.load_skills(project.root) if s.name == "forge")
    assert skills.copy_state(project.root, skill) == "copy"


def test_this_repository_owns_its_skills():
    """The one project that ships them has not inherited anything."""
    from pathlib import Path

    skill = next(s for s in skills.load_skills(Path(".")) if s.name == "forge")
    assert skills.copy_state(Path("."), skill) == "own"
