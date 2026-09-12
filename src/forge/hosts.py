"""A second host costs a manifest, not a port - stated as a table you can read.

OPEN_QUESTIONS.md Q12 chose one host for v1 "structured so a second is cheap",
against Superpowers' eight plugin manifests and ~15KB of sync script, and Spec
Kit's bash, PowerShell *and* Python copies of every script. The bet was that
keeping the mechanism in a CLI and the procedures in plain markdown makes the
second host a manifest.

This file is where that bet is either true or exposed. Adding a host is adding
an entry to `HOSTS`, and if a host ever needs more than an entry - a rewritten
skill, a host-specific branch in the kernel - the bet was wrong and the cost
should be paid visibly here rather than spread through the skills.

The audit that made this honest: six of the seven skills named no host feature,
and `bootstrap` told the reader to fan out across subagents - a mechanism where
it meant an outcome. `skill.host_specific` now checks that, because a rule that
holds because somebody looked once is not a rule.

**Nothing here writes a format this project has not seen.** Each entry says
where a host reads from and in what shape, and the two here are the two that
could be verified: a pointer file, and the layout `forge init` already writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import skills

__all__ = ["Host", "HOSTS", "export", "MARKER_START", "MARKER_END"]

MARKER_START = "<!-- forge:skills -->"
MARKER_END = "<!-- /forge:skills -->"

_SECTION_RE = re.compile(
    re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), re.S)


@dataclass(frozen=True)
class Host:
    name: str
    #: Where this host looks. A single file means a pointer that is merged
    #: into whatever is already there; a directory means the skills are copied.
    target: str
    kind: str                    # "pointer" | "copy"
    note: str


HOSTS = {
    # A pointer file several agent runtimes read, and one this project has seen
    # in the wild: the monorepo of run 3 carries one. Merged rather than
    # overwritten, because it is usually the project's own file first.
    "agents-md": Host(
        name="agents-md", target="AGENTS.md", kind="pointer",
        note="a marked section in AGENTS.md, pointing at the skill files"),
    # The layout `forge init` already writes, offered under its own name so a
    # host reading that path gets it without a second convention.
    "forge": Host(
        name="forge", target=skills.SKILLS_DIR, kind="copy",
        note="the skills copied to .forge/skills/<name>/SKILL.md"),
}


def _section(found: list[skills.Skill], root: Path, repo: Path) -> str:
    """The manifest body: what each skill is, and where to read it."""
    try:
        where = root.relative_to(repo).as_posix()
    except ValueError:
        # The packaged set, because this project has no `.forge/skills/`. Say
        # so rather than printing an absolute path from somebody's machine.
        where = "the kernel's packaged skills (`forge skill read <name>`)"

    lines = [
        MARKER_START,
        "## forge skills",
        "",
        "Procedures for working in this repository. Each is plain markdown with "
        "no host-specific",
        f"syntax; the mechanism lives in the `forge` CLI. Read them in `{where}`.",
        "",
        "| Skill | Phase | What it is for |",
        "|---|---|---|",
    ]
    for skill in sorted(found, key=lambda s: (s.phase, s.name)):
        summary = " ".join((skill.description or "").split())
        lines.append(f"| `{skill.name}` | {skill.phase or '-'} | {summary} |")
    lines += [
        "",
        "Start at `forge` for any request that will change this repository; it "
        "picks the track",
        "and hands off. `forge status` says where an open change is.",
        MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def export(repo: Path, host: str) -> tuple[str, list[str]]:
    """Write the manifest for *host*. Returns (what happened, paths written)."""
    if host not in HOSTS:
        raise KeyError(host)
    target = HOSTS[host]
    found = [s for s in skills.load_skills(repo) if not s.parse_error]
    if not found:
        return "no skills", []

    root = skills.skills_root(repo)
    if target.kind == "copy":
        # From the kernel's own set, never from the project's copy. `export`
        # with a copy target means "put the shipped skills where this host
        # reads them" - sourcing from the local copy would copy it onto itself
        # and report `unchanged` on the exact repository whose copy was stale,
        # which is where this was found.
        written: list[str] = []
        for skill in found:
            source = skills.PACKAGED_SKILLS / skill.name / "SKILL.md"
            if not source.is_file():
                continue
            destination = repo / target.target / skill.name / "SKILL.md"
            body = source.read_text(encoding="utf-8")
            if destination.is_file() and destination.read_text(encoding="utf-8") == body:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(body, encoding="utf-8", newline="\n")
            written.append(destination.relative_to(repo).as_posix())
        return ("copied" if written else "unchanged"), written

    section = _section(found, root, repo)
    path = repo / target.target
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if _SECTION_RE.search(existing):
        # Replaced in place, so the project's own prose above and below it
        # survives. A manifest that overwrites somebody's AGENTS.md is a
        # manifest they delete.
        updated = _SECTION_RE.sub(lambda _: section.rstrip("\n"), existing)
    elif existing.strip():
        updated = existing.rstrip("\n") + "\n\n" + section
    else:
        updated = section
    if updated == existing:
        return "unchanged", []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8", newline="\n")
    return ("updated" if existing else "written"), [target.target]
