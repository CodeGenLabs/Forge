"""Skills: procedures written as markdown, and the five rules they must obey.

A skill is the only part of the harness that a model reads and acts on. That
makes it the part most likely to rot, because prose has no compiler - which is
the failure this whole project is about. So the five rules from
ARCHITECTURE.md section 4.2 are checked here, mechanically, and `forge skill
check` is a gate like any other.

The rules, and why each is checkable rather than advisory:

1. **≤ 250 lines.** Above that the procedure is doing too much. Superpowers'
   two longest skills (568 and 679 lines) are its two least crisp, and length
   is the one property of a prompt that correlates with nothing good.
2. **Kernel-first.** Anything computable is a command, not a paragraph. A
   skill that re-derives `forge check` in prose is a second implementation
   that nothing tests, so `requires-kernel` must name real commands and each
   must actually appear in the body.
3. **No compulsion language.** No all-caps imperatives, no "you have no
   choice". If a step needs that, it needs a gate - and a gate is enforced
   where shouting is not.
4. **Announce on entry.** One line, so the transcript records which procedure
   ran. Without it there is no way to tell afterwards whether the skill fired.
5. **Pressure-tested.** Scenarios in `tests/skills/<name>/`, with the failure
   the skill prevents written down. The honest limit is recorded in
   `PRESSURE.md`: the deterministic half runs here, the model-in-the-loop half
   does not run in CI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

__all__ = [
    "Skill",
    "Scenario",
    "SKILLS_DIR",
    "SCENARIOS_DIR",
    "MAX_LINES",
    "KERNEL_SIGNALS",
    "load_skills",
    "parse_skill",
    "check_skills",
    "load_scenarios",
    "check_scenarios",
]

#: Where a project keeps its own skills. A copy here wins over the packaged
#: set, whole: a project that edits one skill has forked the set, and merging
#: an edited copy with a shipped one per-file would mean a project's `forge`
#: router silently gaining steps from a version bump.
SKILLS_DIR = ".forge/skills"

#: The skills that ship with the kernel. This repository has no
#: `.forge/skills/`, so it lints and runs the packaged set - which is the only
#: way the shipped skills get tested rather than a copy of them.
PACKAGED_SKILLS = Path(__file__).resolve().parent / "_skills"

SCENARIOS_DIR = "tests/skills"
MAX_LINES = 250

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<body>.*?)\r?\n---\r?\n", re.S)
_NAME_RE = re.compile(r"\A[a-z][a-z0-9-]*\Z")
_COMMAND_RE = re.compile(r"\bforge\s+[a-z][a-z-]*(?:\s+[a-z][a-z-]*)?")

# All-caps runs of two or more words, which is what compulsion looks like in
# practice. Single acronyms and the ID prefixes are not compulsion, so the
# pattern needs two adjacent words to fire; `REQ-`/`INV-` style tokens and the
# delta verbs are named exceptions because they are vocabulary.
_SHOUT_RE = re.compile(r"\b[A-Z]{3,}(?:[ \t]+[A-Z]{2,}){1,}\b")
_SHOUT_ALLOWED = frozenset({
    "ADDED", "MODIFIED", "REMOVED", "RENAMED", "REQUIREMENTS",
    "SHALL", "MUST", "WHEN", "THEN", "GIVEN", "AND", "TODO", "ADR", "REQ",
    "JSON", "YAML", "DAG", "TDD", "API", "URL", "CI",
})
_COMPULSION_PHRASES = (
    re.compile(r"\byou (?:have no choice|must not ever|are forbidden)\b", re.I),
    re.compile(r"\b(?:never|always) under any circumstances\b", re.I),
    re.compile(r"\bthis is (?:critical|mandatory|non-negotiable)\b", re.I),
)

#: Host features a skill must not depend on. Named products and the mechanisms
#: only some hosts have; `agent` and `model` are deliberately absent, because a
#: skill is written for an agent and saying so is not a dependency.
_HOST_SPECIFIC_RE = re.compile(
    r"(?i)\b(sub-?agents?|claude|anthropic|cursor|copilot|codex|windsurf|"
    r"aider|slash commands?|MCP servers?|the Task tool)\b")

_ANNOUNCE_RE = re.compile(r"^##\s+Announce\b", re.M | re.I)


@dataclass
class Skill:
    name: str
    path: str
    phase: str = ""
    requires_kernel: list[str] = field(default_factory=list)
    reads: str = ""
    writes: list[str] = field(default_factory=list)
    description: str = ""
    body: str = ""
    lines: int = 0
    parse_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "path": self.path, "phase": self.phase,
            "requires_kernel": self.requires_kernel, "reads": self.reads,
            "writes": self.writes, "lines": self.lines,
            "description": self.description,
        }


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def parse_skill(text: str, path: str) -> Skill:
    """Frontmatter plus body. Parsing never rejects; `check_skills` does."""
    name = PurePosixPath(path).parent.name
    skill = Skill(name=name, path=path, lines=text.count("\n") + 1)

    match = _FRONTMATTER_RE.match(text)
    if match is None:
        skill.parse_error = "no YAML frontmatter"
        skill.body = text
        return skill

    try:
        meta = yaml.safe_load(match.group("body")) or {}
    except yaml.YAMLError as exc:
        skill.parse_error = f"frontmatter is not valid YAML: {exc}"
        meta = {}
    if not isinstance(meta, dict):
        skill.parse_error = "frontmatter is not a mapping"
        meta = {}

    meta = {str(k).replace("_", "-"): v for k, v in meta.items()}
    skill.name = str(meta.get("name") or name).strip()
    skill.phase = str(meta.get("phase") or "").strip()
    skill.requires_kernel = _as_list(meta.get("requires-kernel"))
    skill.reads = str(meta.get("reads") or "").strip()
    skill.writes = _as_list(meta.get("writes"))
    skill.description = str(meta.get("description") or "").strip()
    skill.body = text[match.end():]
    return skill


def skills_root(repo: Path) -> Path:
    """The project's skills if it has any, else the ones that ship."""
    local = repo / SKILLS_DIR
    if local.is_dir() and any(local.glob("*/SKILL.md")):
        return local
    return PACKAGED_SKILLS


def load_skills(repo: Path) -> list[Skill]:
    root = skills_root(repo)
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.glob("*/SKILL.md")):
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            # The packaged set lives outside the repository; name it by what
            # it is rather than by an absolute path that differs per machine
            # and would make every issue message unstable.
            relative = f"<packaged>/{path.parent.name}/SKILL.md"
        out.append(parse_skill(path.read_text(encoding="utf-8", errors="replace"),
                               relative))
    return out


def _strip_fences(text: str) -> str:
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def check_skills(repo: Path, issue, known_commands: set[str] | None = None) -> list:
    """The five rules. `issue` is the Issue constructor, injected."""
    issues = []
    skills = load_skills(repo)
    seen: dict[str, Skill] = {}

    for skill in skills:
        def error(message: str, fix: str, *, line: int | None = None,
                  code: str = "skill.invalid") -> None:
            issues.append(issue("ERROR", code, skill.path, message, fix, line=line))

        if skill.parse_error:
            error(skill.parse_error,
                  "the file opens with `---`, a YAML mapping, and `---` on its own line")
            continue

        if not _NAME_RE.match(skill.name):
            error(f"name {skill.name!r} is not a lowercase kebab slug",
                  "it is how the skill is invoked, so it has to be typeable")
        elif skill.name != PurePosixPath(skill.path).parent.name:
            error(f"name {skill.name!r} does not match its directory "
                  f"{PurePosixPath(skill.path).parent.name!r}",
                  "rename one; a skill found by directory and invoked by name must "
                  "agree with itself")
        first = seen.setdefault(skill.name, skill)
        if first is not skill:
            error(f"{skill.name!r} is also defined at {first.path}",
                  "one skill per name")

        if not skill.description:
            error("no `description` in the frontmatter",
                  "one line saying when to use it - a host router has nothing else "
                  "to match against")

        # 1. length
        if skill.lines > MAX_LINES:
            error(f"{skill.lines} lines, over the {MAX_LINES}-line budget",
                  "split it, or move the computable half into the kernel. Length is "
                  "the one property of a prompt that correlates with nothing good",
                  code="skill.too_long")

        # 2. kernel-first
        body = _strip_fences(skill.body)
        for command in skill.requires_kernel:
            if known_commands is not None and _subcommand(command) not in known_commands:
                error(f"requires-kernel names {command!r}, which is not a forge command",
                      f"use one the kernel has; `forge --help` lists them",
                      code="skill.unknown_command")
            if command not in skill.body:
                error(f"requires-kernel names {command!r} and the body never uses it",
                      "either call it or stop declaring it - a contract nothing "
                      "honours is worse than none",
                      code="skill.unused_command")

        # 3. no compulsion
        for match in _SHOUT_RE.finditer(body):
            words = set(match.group(0).split())
            if words <= _SHOUT_ALLOWED:
                continue
            error(f"shouting: {match.group(0)!r}",
                  "say it once in normal prose. If it needs emphasis to hold, it "
                  "needs a gate - and a gate is enforced where shouting is not",
                  code="skill.compulsion")
        for pattern in _COMPULSION_PHRASES:
            found = pattern.search(body)
            if found:
                error(f"compulsion language: {found.group(0)!r}",
                      "state the reason instead; a rule with a reason survives "
                      "paraphrase, and a rule with volume does not",
                      code="skill.compulsion")

        # 4. host-neutral
        #
        # OPEN_QUESTIONS.md Q12 decided one host for v1, "structured so a
        # second is cheap", and named the single consequence that makes it
        # cheap: a skill must never depend on a host-specific feature. That
        # held for six of the seven skills and not for `bootstrap`, which told
        # the reader to fan out across subagents - a mechanism where it meant
        # an outcome, and one a host without subagents cannot follow.
        #
        # A rule that holds because somebody checked once is not a rule.
        for match in _HOST_SPECIFIC_RE.finditer(body):
            error(f"names a host feature: {match.group(0)!r}",
                  "say what must be true, not which mechanism produces it - a "
                  "skill that names one host's feature is a skill the next host "
                  "cannot run, and Q12's whole bet is that a second host costs a "
                  "manifest rather than a port",
                  code="skill.host_specific")

        # 5. announce on entry
        if not _ANNOUNCE_RE.search(skill.body):
            error("no `## Announce` section",
                  "one line the skill prints on entry, so the transcript records "
                  "which procedure ran",
                  code="skill.no_announce")

        # 6. pressure-tested - but only what this project actually wrote.
        # An unmodified copy of a shipped skill is pressure-tested where it
        # ships; asking every project to re-write those scenarios would make
        # `forge init` produce six warnings on its first run, and six
        # warnings nobody can act on is how a warning class gets ignored.
        scenarios = repo / SCENARIOS_DIR / skill.name
        if _is_shipped_verbatim(repo, skill):
            continue
        if not scenarios.is_dir() or not any(scenarios.glob("*.md")):
            issues.append(issue(
                "WARNING", "skill.untested", skill.path,
                f"no scenarios in {SCENARIOS_DIR}/{skill.name}/",
                "write the failure this skill prevents. A pressure test is the only "
                "reason to believe a prompt does anything",
            ))
    return issues


def copy_state(repo: Path, skill: Skill) -> str:
    """`own` if this project wrote it, `copy` if unedited, `stale` if behind.

    `forge init` copies the skills out and they then drift from the kernel in
    silence - the monorepo of run 3 was still telling its reader to fan out
    across subagents a day after the kernel stopped saying so, and nothing
    anywhere said the copy was behind. `stale` is not a fault; a project is
    entitled to pin a procedure. It is a fact the reader is entitled to.
    """
    packaged = PACKAGED_SKILLS / skill.name / "SKILL.md"
    local = repo / skill.path
    if not packaged.is_file():
        return "own"
    if PACKAGED_SKILLS.is_relative_to(repo.resolve()):
        return "own"
    if not local.is_file():
        return "copy"

    def normalised(path: Path) -> str:
        # Line endings are not an edit. Without this, a project on the
        # other platform has every copied skill reported as diverged.
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")

    return "copy" if normalised(local) == normalised(packaged) else "stale"


def _is_shipped_verbatim(repo: Path, skill: Skill) -> bool:
    """True when this is the kernel's own skill, unedited.

    Compared by content rather than by location: a project that copied a
    skill out with `forge init` and never touched it has not taken on the
    duty of testing it, and a project that edited one has.
    """
    packaged = PACKAGED_SKILLS / skill.name / "SKILL.md"
    if not packaged.is_file():
        return False
    if PACKAGED_SKILLS.is_relative_to(repo.resolve()):
        # This repository *is* where they ship. Nothing is inherited here, so
        # the duty to test them is not inherited either - otherwise the one
        # project that owns the skills is the one project exempt from
        # testing them.
        return False
    local = repo / skill.path
    source = local if local.is_file() else packaged
    return (source.read_text(encoding="utf-8").replace("\r\n", "\n")
            == packaged.read_text(encoding="utf-8").replace("\r\n", "\n"))


def _subcommand(command: str) -> str:
    """`forge check --scope store` -> `check`."""
    parts = command.split()
    return parts[1] if len(parts) > 1 and parts[0] == "forge" else command


# ---------------------------------------------------------------------------
# Pressure-test scenarios
# ---------------------------------------------------------------------------

#: Every signal a scenario may name as the thing that catches its failure.
#: Issue codes the kernel emits, plus the gate points, plus the honest
#: `none` - and `none` is the interesting value: it marks a behaviour that
#: rests on the prompt alone, with nothing mechanical behind it. Those are the
#: ones to be sceptical of, so they are named rather than hidden.
KERNEL_SIGNALS = frozenset({
    "none",
    # store
    "store.id_format", "store.id_unique", "store.claim_fence",
    "store.required_fields", "store.anchor_required", "store.evidence_required",
    "store.adr_required", "store.governs_dag", "store.placeholder",
    "store.candidate_isolation", "store.prose_present", "store.anchor_missing",
    "store.derivable_smell", "store.listing_smell", "store.stack_fact_smell",
    "store.budget", "store.orphan", "store.retire_ground",
    # change and trace
    "trace.claim_touch_complete", "trace.claim_touch_extra",
    "trace.superseded_has_adr", "trace.requirement_task_coverage",
    "trace.requirement_discharged", "trace.dangling_reference",
    "spec.grammar", "spec.nonempty_or_skip",
    # candidates
    "candidate.no_anchor", "candidate.no_confidence",
    "candidate.invented_rationale", "candidate.unproven_invariant",
    # derived and verification
    "derived.dirty", "derived.not_built", "derived.freshness",
    "verify.definition_of_done", "repo.clean",
    # skills
    "skill.too_long", "skill.compulsion", "skill.no_announce",
    "skill.host_specific",
    "skill.unused_command", "skill.unknown_command", "skill.untested",
    # the change model itself
    "change.downgrade_refused", "change.track_upgrade",
    # human gates, which are signals too - just not mechanical ones
    "G1", "G2", "G3", "G4", "G5", "G6",
})


@dataclass
class Scenario:
    skill: str
    id: str
    path: str
    fails_without: str = ""
    with_skill: str = ""
    caught_by: str = ""
    body: str = ""
    parse_error: str | None = None

    def to_dict(self) -> dict:
        return {"skill": self.skill, "id": self.id, "path": self.path,
                "fails_without": self.fails_without, "with_skill": self.with_skill,
                "caught_by": self.caught_by}


def load_scenarios(repo: Path, skill: str | None = None) -> list[Scenario]:
    root = repo / SCENARIOS_DIR
    if not root.is_dir():
        return []
    out: list[Scenario] = []
    for path in sorted(root.glob("*/*.md")):
        owner = path.parent.name
        if skill and owner != skill:
            continue
        relative = path.relative_to(repo).as_posix()
        out.append(_parse_scenario(
            path.read_text(encoding="utf-8", errors="replace"), relative, owner))
    return out


def _parse_scenario(text: str, path: str, owner: str) -> Scenario:
    scenario = Scenario(skill=owner, id=PurePosixPath(path).stem, path=path)
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        scenario.parse_error = "no YAML frontmatter"
        scenario.body = text
        return scenario
    try:
        meta = yaml.safe_load(match.group("body")) or {}
    except yaml.YAMLError as exc:
        scenario.parse_error = f"frontmatter is not valid YAML: {exc}"
        meta = {}
    if not isinstance(meta, dict):
        scenario.parse_error = "frontmatter is not a mapping"
        meta = {}
    meta = {str(k).replace("_", "-"): v for k, v in meta.items()}
    scenario.skill = str(meta.get("skill") or owner).strip()
    scenario.id = str(meta.get("id") or scenario.id).strip()
    scenario.fails_without = str(meta.get("fails-without") or "").strip()
    scenario.with_skill = str(meta.get("with-skill") or "").strip()
    scenario.caught_by = str(meta.get("caught-by") or "").strip()
    scenario.body = text[match.end():]
    return scenario


def check_scenarios(repo: Path, issue) -> list:
    """The scenarios are data, so they are checked like data.

    The valuable check is `caught-by`: a scenario has to name the kernel
    signal that would catch its failure, or say `none`. That ties each claim a
    skill makes to a mechanism, and it surfaces the claims with no mechanism
    at all - which is the set worth being sceptical about, and the set that
    grows quietly if nobody is counting.
    """
    issues = []
    names = {s.name for s in load_skills(repo)}
    seen: set[tuple[str, str]] = set()

    for scenario in load_scenarios(repo):
        def error(message: str, fix: str) -> None:
            issues.append(issue("ERROR", "skill.scenario", scenario.path, message, fix))

        if scenario.parse_error:
            error(scenario.parse_error,
                  "a scenario opens with `---`, a YAML mapping and `---`")
            continue
        if names and scenario.skill not in names:
            error(f"names skill {scenario.skill!r}, which does not exist",
                  f"one of {', '.join(sorted(names))}")
        if (scenario.skill, scenario.id) in seen:
            error(f"duplicate scenario id {scenario.id!r} for {scenario.skill}",
                  "ids are how a run is reported; give it a different one")
        seen.add((scenario.skill, scenario.id))

        for field_name, value in (("fails-without", scenario.fails_without),
                                  ("with-skill", scenario.with_skill)):
            if not value:
                error(f"no `{field_name}`",
                      "a scenario that does not say what changes is not a test")

        if not scenario.caught_by:
            error("no `caught-by`",
                  f"name the signal that catches this failure, or `none` if nothing "
                  f"does - `none` is a legitimate answer and the honest one")
        elif scenario.caught_by not in KERNEL_SIGNALS:
            error(f"caught-by {scenario.caught_by!r} is not a signal the kernel emits",
                  "use an issue code, a human gate (G1-G6), or `none`")

        if len(scenario.body.strip().split("\n")) < 3:
            error("the scenario body is shorter than three lines",
                  "describe the situation concretely enough that two people would "
                  "set up the same test")
    return issues
