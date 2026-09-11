#!/usr/bin/env python
"""Run the model half of the skill pressure tests.

Each scenario is run twice against the same fixture repository: once with the
skill withheld (the baseline) and once with it loaded. The skill earns its
place if the baseline shows the failure the scenario names and the skill run
does not.

This lives in `tools/` and not in the test suite for one reason: it calls a
model, and the kernel never does. Every other check in this repository is a
pure function of the repository at a commit, which is what makes the gates
worth anything; a test whose result depends on sampling would quietly make
that untrue of the suite as a whole.

So the deterministic half runs in `tests/test_skills.py` and this half runs
when someone asks for it. `tests/skills/PRESSURE.md` says which is which.

    python tools/pressure_test.py --list
    python tools/pressure_test.py --agent "claude -p {prompt}" --skill implement
    python tools/pressure_test.py --agent "..." --out runs/2026-09-11
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forge import skills  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

_BASELINE_PREAMBLE = """\
You are working in the repository at {repo}. Complete the task described
below. Work as you normally would.
"""

_SKILL_PREAMBLE = """\
You are working in the repository at {repo}. The procedure in
{skill_path} applies to this task; read it and follow it. Complete the task
described below.
"""


def _prompt(scenario: skills.Scenario, *, with_skill: bool) -> str:
    preamble = (_SKILL_PREAMBLE if with_skill else _BASELINE_PREAMBLE).format(
        repo=REPO, skill_path=f"{skills.SKILLS_DIR}/{scenario.skill}/SKILL.md",
    )
    return f"{preamble}\n{scenario.body.strip()}\n"


def _run(agent: str, prompt: str, timeout: int) -> dict:
    """Run the agent command. `{prompt}` is substituted; otherwise stdin."""
    if "{prompt}" in agent:
        command = shlex.split(agent.replace("{prompt}", shlex.quote(prompt)))
        stdin = None
    else:
        command = shlex.split(agent)
        stdin = prompt.encode("utf-8")
    try:
        completed = subprocess.run(command, input=stdin, capture_output=True,
                                   timeout=timeout, cwd=REPO)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seconds": timeout}
    except OSError as exc:
        return {"status": "error", "error": str(exc)}
    return {
        "status": "ran",
        "exit": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", "replace"),
        "stderr": completed.stderr.decode("utf-8", "replace")[-4000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", help="command to run; `{prompt}` is substituted, "
                                        "otherwise the prompt goes to stdin")
    parser.add_argument("--skill", help="run only this skill's scenarios")
    parser.add_argument("--scenario", help="run only this scenario id")
    parser.add_argument("--out", type=Path, help="directory for the transcripts")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--list", action="store_true", help="print what would run")
    args = parser.parse_args(argv)

    scenarios = [s for s in skills.load_scenarios(REPO, args.skill)
                 if not args.scenario or s.id == args.scenario]
    if not scenarios:
        print("no scenarios matched", file=sys.stderr)
        return 2

    uncaught = [s for s in scenarios if s.caught_by == "none"]
    print(f"{len(scenarios)} scenario(s); {len(uncaught)} rest on the skill alone "
          f"with no kernel signal behind them.\n")

    if args.list or not args.agent:
        for scenario in scenarios:
            mark = "!" if scenario.caught_by == "none" else " "
            print(f"{mark} {scenario.skill}/{scenario.id}")
            print(textwrap.indent(f"without: {scenario.fails_without.strip()}", "    "))
            print(textwrap.indent(f"caught by: {scenario.caught_by}", "    "))
        if not args.agent:
            # Said rather than implied: a runner that silently does nothing is
            # how a pressure suite comes to be believed without being run.
            print("\nNo --agent given, so nothing was run. This half needs a model "
                  "and is not part of CI; see tests/skills/PRESSURE.md.")
        return 0

    results = []
    for scenario in scenarios:
        print(f"-- {scenario.skill}/{scenario.id}")
        baseline = _run(args.agent, _prompt(scenario, with_skill=False), args.timeout)
        with_skill = _run(args.agent, _prompt(scenario, with_skill=True), args.timeout)
        results.append({**scenario.to_dict(),
                        "baseline": baseline, "with_skill": with_skill})
        print(f"   baseline {baseline['status']}, with skill {with_skill['status']}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "pressure.json"
        target.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwritten {target}")

    # No verdict is printed, deliberately. Whether the baseline showed the
    # failure and the skill run avoided it is a judgement about two
    # transcripts, and a script that scored it would be the same kind of
    # unverifiable claim the harness exists to stop making.
    print("\nRead both transcripts per scenario. The skill earns its place when the "
          "baseline shows the failure and the skill run does not.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
