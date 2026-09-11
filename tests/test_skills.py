"""The five skill rules, and the scenarios that pressure-test them.

The deterministic half of M4. The model half lives in
`tools/pressure_test.py` and does not run here, for the reason recorded in
`tests/skills/PRESSURE.md`: the kernel never calls a model, and a test whose
result depends on sampling would make that untrue of the suite as a whole.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from forge import skills
from forge.cli import known_subcommands, main
from forge.validate import Issue

REPO = Path(__file__).resolve().parent.parent

VALID = """\
---
name: demo
phase: spec
description: A demonstration skill.
requires-kernel: ["forge check"]
reads: from-dag
writes: ["changes/${change}/demo.md"]
---

# demo

## Announce

> Running `demo`.

## What this does

Runs `forge check` and reports what it says.
"""


def write_skill(repo, name: str, text: str) -> None:
    target = repo.root / skills.SKILLS_DIR / name / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_scenario(repo, skill: str, name: str, text: str) -> None:
    target = repo.root / skills.SCENARIOS_DIR / skill / f"{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def check(repo) -> list[Issue]:
    return skills.check_skills(repo.root, Issue, known_subcommands())


def codes(found: list[Issue]) -> list[str]:
    return [i.code for i in found]


@pytest.fixture
def project(repo):
    repo.write("README.md", "# x\n")
    write_skill(repo, "demo", VALID)
    write_scenario(repo, "demo", "a-case",
                   "---\nskill: demo\nid: a-case\nfails-without: it forgets\n"
                   "with-skill: it remembers\ncaught-by: none\n---\n\n"
                   "A situation.\nDescribed concretely.\nOver several lines.\n")
    repo.commit("a skill")
    return repo


# ---------------------------------------------------------------------------
# This repository's own six skills
# ---------------------------------------------------------------------------

def test_the_shipped_skills_obey_every_rule():
    """The acceptance case. These are the six the MVP ships, and the linter
    is worth nothing if it does not run on them."""
    found = skills.check_skills(REPO, Issue, known_subcommands())
    errors = [i for i in found if i.level == "ERROR"]
    assert errors == [], "\n".join(f"{i.path}: {i.message}" for i in errors)


SHIPPED = [
    "bootstrap", "curate-knowledge", "forge", "implement", "investigate",
    "plan-tasks", "specify",
]


def test_the_mvp_ships_the_seven_skills():
    """Six phase skills plus `bootstrap`. MVP.md M4 lists six; `bootstrap` is
    M5's pass 2, which that milestone specifies as a skill rather than kernel
    code."""
    assert sorted(s.name for s in skills.load_skills(REPO)) == SHIPPED


def test_every_shipped_skill_is_pressure_tested():
    found = skills.check_skills(REPO, Issue, known_subcommands())
    assert [i for i in found if i.code == "skill.untested"] == []


def test_every_shipped_scenario_is_well_formed():
    assert skills.check_scenarios(REPO, Issue) == []


def test_every_skill_has_at_least_two_scenarios():
    """One scenario is an anecdote. The point of the set is to cover more
    than the failure that prompted the skill."""
    counts: dict[str, int] = {}
    for scenario in skills.load_scenarios(REPO):
        counts[scenario.skill] = counts.get(scenario.skill, 0) + 1
    for skill in skills.load_skills(REPO):
        assert counts.get(skill.name, 0) >= 2, skill.name


def test_the_uncaught_scenarios_are_a_minority():
    """`caught-by: none` marks a behaviour resting on the prompt alone. Those
    are legitimate - some things genuinely cannot be checked - but if most of
    a skill suite is uncatchable, the harness is a prompt collection with
    extra steps, and the number is worth watching rather than discovering."""
    scenarios = skills.load_scenarios(REPO)
    uncaught = [s for s in scenarios if s.caught_by == "none"]
    assert len(uncaught) < len(scenarios) / 2, \
        f"{len(uncaught)}/{len(scenarios)} scenarios have no mechanical signal"


def test_every_declared_signal_is_one_the_kernel_emits():
    """A scenario naming a code nothing produces is a claim with no mechanism
    behind it, dressed as one that has."""
    source = "\n".join(
        (REPO / "src/forge" / name).read_text(encoding="utf-8")
        for name in ("validate.py", "impact.py", "spec.py", "gates.py", "cli.py",
                     "skills.py", "verify.py")
    )
    for scenario in skills.load_scenarios(REPO):
        signal = scenario.caught_by
        if signal == "none" or re.fullmatch(r"G[1-6]", signal):
            continue
        assert f'"{signal}"' in source, f"{scenario.path} names {signal}"


# ---------------------------------------------------------------------------
# Rule 1 - length
# ---------------------------------------------------------------------------

def test_a_long_skill_is_rejected(project):
    write_skill(project, "demo", VALID + "\nfiller\n" * skills.MAX_LINES)
    found = [i for i in check(project) if i.code == "skill.too_long"]
    assert found and "correlates with nothing good" in found[0].fix


def test_the_shipped_skills_are_well_under_budget():
    for skill in skills.load_skills(REPO):
        assert skill.lines <= skills.MAX_LINES, f"{skill.name}: {skill.lines}"


# ---------------------------------------------------------------------------
# Rule 2 - kernel-first
# ---------------------------------------------------------------------------

def test_a_declared_command_that_is_never_used_is_rejected(project):
    """A contract nothing honours is worse than none."""
    write_skill(project, "demo",
                VALID.replace('["forge check"]', '["forge check", "forge drift"]'))
    found = [i for i in check(project) if i.code == "skill.unused_command"]
    assert found and "forge drift" in found[0].message


def test_a_command_the_kernel_does_not_have_is_rejected(project):
    write_skill(project, "demo",
                VALID.replace('["forge check"]', '["forge conjure"]')
                     .replace("Runs `forge check`", "Runs `forge conjure`"))
    assert "skill.unknown_command" in codes(check(project))


def test_every_shipped_requires_kernel_entry_is_real():
    known = known_subcommands()
    for skill in skills.load_skills(REPO):
        for command in skill.requires_kernel:
            assert command.split()[1] in known, f"{skill.name}: {command}"


# ---------------------------------------------------------------------------
# Rule 3 - no compulsion
# ---------------------------------------------------------------------------

def test_shouting_is_rejected(project):
    write_skill(project, "demo", VALID.replace("Runs `forge check`",
                                               "ALWAYS RUN THIS FIRST. Runs `forge check`"))
    found = [i for i in check(project) if i.code == "skill.compulsion"]
    assert found and "needs a gate" in found[0].fix


@pytest.mark.parametrize("phrase", [
    "you have no choice",
    "never under any circumstances",
    "this is non-negotiable",
])
def test_compulsion_phrases_are_rejected(project, phrase):
    write_skill(project, "demo", VALID.replace("Runs `forge check`",
                                               f"{phrase}. Runs `forge check`"))
    assert "skill.compulsion" in codes(check(project))


def test_the_delta_verbs_are_not_shouting(project):
    """`ADDED MODIFIED REMOVED` is vocabulary, not volume. A linter that
    cannot tell them apart makes the `specify` skill unwritable."""
    write_skill(project, "demo", VALID.replace(
        "Runs `forge check`", "Sections are ADDED MODIFIED REMOVED. Runs `forge check`"))
    assert "skill.compulsion" not in codes(check(project))


def test_compulsion_inside_a_code_fence_is_not_compulsion(project):
    write_skill(project, "demo", VALID + "\n```\nYOU MUST NOT\n```\n")
    assert "skill.compulsion" not in codes(check(project))


# ---------------------------------------------------------------------------
# Rule 4 - announce
# ---------------------------------------------------------------------------

def test_a_skill_with_no_announce_is_rejected(project):
    write_skill(project, "demo", VALID.replace("## Announce\n\n> Running `demo`.\n", ""))
    found = [i for i in check(project) if i.code == "skill.no_announce"]
    assert found and "transcript" in found[0].fix


# ---------------------------------------------------------------------------
# Rule 5 - pressure-tested
# ---------------------------------------------------------------------------

def test_a_skill_with_no_scenarios_is_a_warning(project):
    write_skill(project, "orphan", VALID.replace("name: demo", "name: orphan"))
    found = [i for i in check(project) if i.code == "skill.untested"]
    assert found and found[0].level == "WARNING"
    # A warning, not an error: a skill written today with its scenarios
    # tomorrow is a normal sequence, and blocking it would mean writing the
    # test for a procedure nobody has read yet.
    assert "only reason to believe a prompt does anything" in found[0].fix


# ---------------------------------------------------------------------------
# Frontmatter and identity
# ---------------------------------------------------------------------------

def test_a_skill_with_no_frontmatter_is_rejected(project):
    write_skill(project, "demo", "# demo\n\n## Announce\n\n> hi\n")
    assert "skill.invalid" in codes(check(project))


def test_a_name_that_disagrees_with_its_directory_is_rejected(project):
    write_skill(project, "demo", VALID.replace("name: demo", "name: other"))
    found = [i for i in check(project) if "does not match its directory" in i.message]
    assert found


def test_a_skill_with_no_description_is_rejected(project):
    write_skill(project, "demo", VALID.replace("description: A demonstration skill.\n", ""))
    found = [i for i in check(project) if "no `description`" in i.message]
    assert found and "host router" in found[0].fix


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def test_a_scenario_must_name_a_signal(project):
    write_scenario(project, "demo", "b-case",
                   "---\nskill: demo\nid: b-case\nfails-without: x\n"
                   "with-skill: y\n---\n\nOne.\nTwo.\nThree.\n")
    found = [i for i in skills.check_scenarios(project.root, Issue)
             if "no `caught-by`" in i.message]
    assert found and "the honest one" in found[0].fix


def test_an_invented_signal_is_rejected(project):
    write_scenario(project, "demo", "b-case",
                   "---\nskill: demo\nid: b-case\nfails-without: x\n"
                   "with-skill: y\ncaught-by: store.vibes\n---\n\nOne.\nTwo.\nThree.\n")
    assert any("not a signal the kernel emits" in i.message
               for i in skills.check_scenarios(project.root, Issue))


def test_a_scenario_for_a_skill_that_does_not_exist_is_rejected(project):
    write_scenario(project, "ghost", "b-case",
                   "---\nskill: ghost\nid: b-case\nfails-without: x\n"
                   "with-skill: y\ncaught-by: none\n---\n\nOne.\nTwo.\nThree.\n")
    assert any("does not exist" in i.message
               for i in skills.check_scenarios(project.root, Issue))


def test_a_scenario_with_no_body_is_rejected(project):
    write_scenario(project, "demo", "b-case",
                   "---\nskill: demo\nid: b-case\nfails-without: x\n"
                   "with-skill: y\ncaught-by: none\n---\n\nThin.\n")
    assert any("shorter than three lines" in i.message
               for i in skills.check_scenarios(project.root, Issue))


# ---------------------------------------------------------------------------
# The command surface
# ---------------------------------------------------------------------------

def test_skill_list(project, capsys):
    assert main(["skill", "list", "--repo", str(project.root)]) == 0
    assert "demo" in capsys.readouterr().out


def test_skill_show(project, capsys):
    assert main(["skill", "show", "demo", "--repo", str(project.root)]) == 0
    assert "## Announce" in capsys.readouterr().out


def test_skill_show_of_an_unknown_name_lists_what_exists(project, capsys):
    assert main(["skill", "show", "nope", "--repo", str(project.root)]) == 2
    assert "found: demo" in capsys.readouterr().err


def test_check_scope_skills(project, capsys):
    write_skill(project, "demo", VALID.replace("Runs `forge check`",
                                               "ALWAYS DO THIS. Runs `forge check`"))
    assert main(["check", "--scope", "skills", "--repo", str(project.root)]) == 1
    assert "skill.compulsion" in capsys.readouterr().out


def test_a_repository_with_no_skills_is_not_an_error(repo):
    repo.write("README.md", "# x\n")
    repo.commit("no skills")
    assert skills.check_skills(repo.root, Issue, known_subcommands()) == []


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------

def test_the_pressure_runner_says_it_did_nothing_without_a_model():
    """A runner that silently does nothing is how a pressure suite comes to
    be believed without being run."""
    completed = subprocess.run(
        [sys.executable, str(REPO / "tools/pressure_test.py"), "--list"],
        capture_output=True, cwd=REPO,
    )
    assert completed.returncode == 0
    out = completed.stdout.decode("utf-8", "replace")
    assert "nothing was run" in out
    assert "PRESSURE.md" in out
    assert "rest on the skill alone" in out


def test_the_pressure_note_exists_and_says_what_does_not_run():
    text = (REPO / "tests/skills/PRESSURE.md").read_text(encoding="utf-8")
    assert "does not run in CI" in text


# ---------------------------------------------------------------------------
# The M4 acceptance run: a track-B change, through the skills' own commands
# ---------------------------------------------------------------------------

_COMMAND_LINE_RE = re.compile(r"^\s*(forge [a-z][^\n`]*)$", re.M)


def _documented_commands(name: str) -> list[str]:
    """Every `forge ...` line a skill puts in a fenced block for the reader
    to run."""
    body = next(s for s in skills.load_skills(REPO) if s.name == name).body
    inside, out = False, []
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if inside and line.strip().startswith("forge "):
            out.append(line.strip())
    return out


def test_every_command_a_skill_tells_you_to_run_exists():
    """A skill is a procedure someone follows literally. A step naming a
    command the kernel does not have is a dead end found at the worst
    possible moment, and nothing else in the suite would catch it."""
    known = known_subcommands()
    for skill in skills.load_skills(REPO):
        for line in _documented_commands(skill.name):
            word = line.split()[1]
            assert word in known, f"{skill.name}: {line!r}"


SOURCE = '# forge:CMP-logging\ndef emit(event):\n    return f"[{event}]"\n'
TESTS = '# @covers CMP-logging\ndef test_emit():\n    assert True\n'
COMPONENT = """\

### CMP-logging - How events reach the log

```claim
kind: component
status: asserted
truth-source: decision
anchors: ["src/log.py"]
reviewed: 2026-09-01
```

Owns the shape of every log line. It must never include a payload field,
because payloads carry cardholder data and the log sink is not in scope for
that.
"""

COMMANDS = """\

commands:
  build: python -c "pass"
  typecheck: python -c "pass"
  lint: python -c "pass"
  test: python -c "pass"
"""


def test_a_track_b_change_runs_end_to_end_through_the_skills(repo, capsys):
    """M4's second acceptance criterion, exercised at the kernel boundary.

    A model following the skills is the half that needs a model; what is
    checkable here is that the sequence the skills prescribe actually works -
    each command in the order they give it, with the arguments they give,
    ending clean."""
    from forge import derive

    repo.write("src/log.py", SOURCE)
    repo.write("tests/test_log.py", TESTS)
    main(["init", "--repo", str(repo.root)])
    for path, text in (("docs/system/components.md", COMPONENT),
                       (".forge/config.yaml", COMMANDS)):
        target = repo.root / path
        target.write_text(target.read_text(encoding="utf-8") + text, encoding="utf-8")
    repo.commit("a project")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    capsys.readouterr()

    # `forge` router: track B, because the change is bounded.
    assert main(["change", "new", "tidy the log prefix", "--track", "B",
                 "--repo", str(repo.root)]) == 0
    assert main(["change", "show", "1", "--repo", str(repo.root)]) == 0
    repo.commit("open the change")

    root = repo.root / "changes/0001-tidy-the-log-prefix"
    (root / "proposal.md").write_text(
        "# Why\n\nThe prefix is inconsistent between emitters.\n\n"
        "## Claims touched\n\n### Unaffected\n"
        "- CMP-logging - the shape of a line is unchanged; only the prefix moves\n",
        encoding="utf-8")

    # `specify`: no observable behaviour changes, so the skip is recorded.
    meta = root / ".forge.yaml"
    meta.write_text(meta.read_text(encoding="utf-8")
                    + "skip_spec: prefix formatting only; no caller can observe it\n",
                    encoding="utf-8")
    assert main(["gate", "spec:post", "--change", "1", "--repo", str(repo.root)]) == 0

    # `plan-tasks`.
    (root / "tasks.md").write_text(
        "## Tasks\n\n- [ ] chore: move the prefix into one helper\n", encoding="utf-8")
    assert main(["gate", "analyze:post", "--change", "1", "--repo", str(repo.root)]) == 0

    # `implement`: one task, then the claim-touch account it owes.
    repo.write("src/log.py", SOURCE.replace('f"[{event}]"', '_prefixed(event)')
               + '\n\ndef _prefixed(event):\n    return f"[{event}]"\n')
    (root / "tasks.md").write_text(
        "## Tasks\n\n- [x] chore: move the prefix into one helper\n", encoding="utf-8")
    (root / "impact.md").write_text(
        "# Impact\n\n## Claims touched\n\n### Unaffected\n"
        "- CMP-logging - the shape of a line is unchanged; only the prefix moves\n",
        encoding="utf-8")
    assert main(["gate", "impact:post", "--change", "1", "--repo", str(repo.root)]) == 0
    repo.commit("implement the task")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")

    # `implement`, last step, then `curate-knowledge`.
    capsys.readouterr()
    assert main(["verify", "--change", "1", "--repo", str(repo.root)]) == 0
    assert main(["gate", "sync:pre", "--change", "1", "--repo", str(repo.root)]) == 0
    assert main(["archive", "--change", "1", "--date", "2026-09-11",
                 "--repo", str(repo.root)]) == 0
    repo.commit("archive")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")

    capsys.readouterr()
    assert main(["check", "--repo", str(repo.root)]) == 0, capsys.readouterr().out
    assert main(["gate", "converge:post", "--repo", str(repo.root)]) == 0


# ---------------------------------------------------------------------------
# Shipped versus project-owned
# ---------------------------------------------------------------------------

def test_a_project_with_no_skills_gets_the_packaged_set(repo):
    """A project that installs forge and never runs `forge init` still has
    the procedures. They are the only part of the harness a model reads."""
    repo.write("README.md", "# x\n")
    repo.commit("no skills")
    assert [s.name for s in skills.load_skills(repo.root)] == SHIPPED


def test_a_project_copy_wins_whole(project):
    """A project that edits one skill has forked the set. Merging per-file
    would mean its `forge` router silently gaining steps from a version
    bump."""
    assert [s.name for s in skills.load_skills(project.root)] == ["demo"]


def test_an_unmodified_copy_needs_no_local_scenarios(repo, capsys):
    """Six warnings on the first `forge init` is how a warning class gets
    ignored, and they would be warnings nobody could act on: the shipped
    skills are pressure-tested where they ship."""
    repo.write("README.md", "# x\n")
    main(["init", "--repo", str(repo.root)])
    repo.commit("forge init")
    capsys.readouterr()
    found = skills.check_skills(repo.root, Issue, known_subcommands())
    assert [i for i in found if i.code == "skill.untested"] == []


def test_an_edited_copy_owes_its_own_scenarios(repo, capsys):
    repo.write("README.md", "# x\n")
    main(["init", "--repo", str(repo.root)])
    target = repo.root / skills.SKILLS_DIR / "implement/SKILL.md"
    target.write_text(target.read_text(encoding="utf-8")
                      + "\n## Local addition\n\nOne extra step for this project.\n",
                      encoding="utf-8")
    repo.commit("fork one skill")
    capsys.readouterr()
    found = [i for i in skills.check_skills(repo.root, Issue, known_subcommands())
             if i.code == "skill.untested"]
    assert [i.path for i in found] == [".forge/skills/implement/SKILL.md"]


def test_this_repository_is_not_exempt_from_testing_its_own_skills():
    """The one project that owns the skills must not be the one project
    excused from pressure-testing them."""
    assert skills.PACKAGED_SKILLS.is_relative_to(REPO)
    found = skills.check_skills(REPO, Issue, known_subcommands())
    assert [i for i in found if i.code == "skill.untested"] == []
    # And it would notice if the scenarios vanished.
    for skill in skills.load_skills(REPO):
        assert (REPO / skills.SCENARIOS_DIR / skill.name).is_dir()
