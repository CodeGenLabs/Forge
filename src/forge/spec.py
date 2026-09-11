"""Capability specs: the closed delta grammar, and the deterministic fold.

A change does not edit a permanent spec. It writes a *delta* -
`changes/NNNN/spec/<capability>/spec.md` - in a grammar with exactly four
verbs, and `forge archive` folds that delta into
`docs/system/specs/<capability>/spec.md`. Adopted from OpenSpec directly,
because it is the one mechanism in the corpus that makes "what did this change
promise?" answerable months later without reading a diff.

Why a delta rather than an edit, in one sentence each:

- **A diff of a spec is unreviewable.** `## MODIFIED Requirements` carries the
  full new text of the requirement, so a reviewer reads what the system will
  do, not a patch against what it used to.
- **The fold is deterministic.** Two people folding the same delta get the
  same file, which is what lets the permanent tier be regenerated and
  compared rather than merged by hand.
- **Removal states its cost.** `REMOVED` needs a Reason and a Migration, so
  deleting a promise is as expensive to write as making one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "SPECS_DIR",
    "VERBS",
    "Requirement",
    "Delta",
    "FoldError",
    "parse_delta",
    "parse_permanent",
    "check_delta",
    "check_nonempty",
    "check_task_coverage",
    "check_requirement_discharged",
    "promised_requirements",
    "fold",
    "delta_files",
    "capability_of",
]

SPECS_DIR = "docs/system/specs"

#: The closed set. An open set would let a change invent a verb nothing folds,
#: and the delta would then be prose that looks enforced.
VERBS = ("ADDED", "MODIFIED", "REMOVED", "RENAMED")

#: A `MODIFIED` block must read as the requirement's whole new text. Below
#: this it is almost certainly a fragment, and a fragment folds into a spec
#: that says less than anyone intended.
_MIN_MODIFIED_WORDS = 8
_MIN_PURPOSE_WORDS = 12

_SECTION_RE = re.compile(r"^##\s+(?P<verb>[A-Z]+)\s+Requirements\s*$", re.M)
_ANY_H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.M)
_REQ_RE = re.compile(
    r"^###\s+Requirement:\s*(?P<id>REQ-[A-Za-z0-9_-]+)"
    r"(?:\s*(?:->|=>|→)\s*(?P<renamed>REQ-[A-Za-z0-9_-]+))?"
    r"(?:\s*[-–—:]\s*(?P<title>[^\n]*))?$",
    re.M,
)
_SCENARIO_RE = re.compile(r"^(?P<hashes>#{1,6})\s*Scenario:\s*(?P<title>[^\n]*)$", re.M)
_NORMATIVE_RE = re.compile(r"\b(SHALL|MUST)\b")
_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION")
# A diff fragment pasted in place of the full text. Deliberately keyed on `+`
# and hunk headers and never on a leading `-`: every scenario line in this
# grammar is a markdown bullet, so treating `-` as a diff marker fires on
# every correct MODIFIED block there is.
_DIFF_MARKER_RE = re.compile(r"^(?:\+{1,3}[ \t]*\S|@@[ \t])", re.M)
_PURPOSE_RE = re.compile(r"^##\s+Purpose\s*$", re.M)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")


class FoldError(ValueError):
    """A delta cannot be folded into the permanent spec it names."""


@dataclass
class Requirement:
    id: str
    title: str
    body: str
    line: int
    renamed_to: str | None = None

    @property
    def text(self) -> str:
        """The requirement as it appears in a permanent spec."""
        heading = f"### Requirement: {self.id}"
        if self.title:
            heading += f" - {self.title}"
        body = self.body.strip("\n")
        return f"{heading}\n{body}\n" if body else f"{heading}\n"

    def scenarios(self) -> list[tuple[int, str]]:
        return [(len(m.group("hashes")), m.group("title"))
                for m in _SCENARIO_RE.finditer(self.body)]


@dataclass
class Delta:
    path: str                       # repository-relative path of the delta file
    capability: str                 # e.g. "payments/refunds"
    sections: dict[str, list[Requirement]] = field(default_factory=dict)
    unknown_sections: list[tuple[str, int]] = field(default_factory=list)
    purpose: str = ""
    preamble: str = ""

    @property
    def is_empty(self) -> bool:
        return not any(self.sections.values())

    @property
    def requirement_ids(self) -> list[str]:
        return sorted({r.id for group in self.sections.values() for r in group})

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "capability": self.capability,
            "sections": {verb: [r.id for r in group]
                         for verb, group in sorted(self.sections.items())},
            "requirements": self.requirement_ids,
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _requirements_in(section: str, offset: int) -> list[Requirement]:
    matches = list(_REQ_RE.finditer(section))
    out: list[Requirement] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        out.append(Requirement(
            id=match.group("id"),
            title=(match.group("title") or "").strip(),
            body=section[match.end():end],
            line=offset + section.count("\n", 0, match.start()) + 1,
            renamed_to=match.group("renamed"),
        ))
    return out


def parse_delta(text: str, path: str, capability: str) -> Delta:
    """Read a delta spec. Parsing never rejects; `check_delta` does that."""
    delta = Delta(path=path, capability=capability, sections={v: [] for v in VERBS})

    headings = list(_ANY_H2_RE.finditer(text))
    if headings:
        delta.preamble = text[:headings[0].start()]
    purpose = _PURPOSE_RE.search(text)
    if purpose:
        after = text[purpose.end():]
        following = _ANY_H2_RE.search(after)
        delta.purpose = (after[:following.start()] if following else after).strip()

    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end]
        offset = text.count("\n", 0, heading.end())
        verb_match = _SECTION_RE.match(heading.group(0))
        if verb_match is None:
            title = heading.group("title")
            if title.strip().lower().endswith("requirements"):
                # It *meant* to be a section: flag it rather than ignore it,
                # or a typo silently drops every requirement under it.
                delta.unknown_sections.append(
                    (title, text.count("\n", 0, heading.start()) + 1))
            continue
        verb = verb_match.group("verb")
        if verb not in VERBS:
            delta.unknown_sections.append(
                (heading.group("title"), text.count("\n", 0, heading.start()) + 1))
            continue
        delta.sections.setdefault(verb, []).extend(_requirements_in(body, offset))
    return delta


def parse_permanent(text: str) -> list[Requirement]:
    """Requirements in a permanent capability spec: no verb sections, just
    `### Requirement:` headings under whatever prose the capability carries."""
    return _requirements_in(text, 0)


def capability_of(delta_path: str, change_relative: str) -> str:
    """`changes/0004-x/spec/payments/refunds/spec.md` -> `payments/refunds`."""
    inside = delta_path[len(f"{change_relative}/spec/"):]
    return inside.rsplit("/", 1)[0] if "/" in inside else ""


def delta_files(repo: Path, change_relative: str) -> list[str]:
    root = repo / change_relative / "spec"
    if not root.is_dir():
        return []
    return sorted(p.relative_to(repo).as_posix()
                  for p in root.rglob("*.md") if p.is_file())


# ---------------------------------------------------------------------------
# R12 / R13
# ---------------------------------------------------------------------------

def check_delta(repo: Path, delta: Delta, issue) -> list:
    """R12, the delta grammar. `issue` is the Issue constructor, injected so
    this module does not depend on the CLI's reporting shape."""
    issues = []

    def error(message: str, fix: str, *, line: int | None = None,
              code: str = "spec.grammar") -> None:
        issues.append(issue("ERROR", code, delta.path, message, fix, line=line))

    for title, line in delta.unknown_sections:
        error(f"`## {title}` is not one of the four delta verbs",
              f"use {', '.join(VERBS)} - the set is closed so that every section "
              f"is something the fold knows how to apply",
              line=line)

    permanent = repo / SPECS_DIR / delta.capability / "spec.md"
    if not permanent.is_file() and delta.sections.get("ADDED"):
        words = len(_WORD_RE.findall(delta.purpose))
        if words < _MIN_PURPOSE_WORDS:
            error(f"{delta.capability!r} is a new capability and its `## Purpose` is "
                  f"{words} words",
                  f"say what the capability is for in at least {_MIN_PURPOSE_WORDS} "
                  f"words; it is the only prose a reader gets before the requirements")

    seen: dict[str, Requirement] = {}
    for verb in VERBS:
        for requirement in delta.sections.get(verb, []):
            first = seen.get(requirement.id)
            if first is not None:
                error(f"{requirement.id} appears twice in this delta "
                      f"(also at line {first.line})",
                      "one verb per requirement per change; a requirement that is both "
                      "modified and removed is two changes",
                      line=requirement.line)
            else:
                seen[requirement.id] = requirement
            issues.extend(_check_requirement(verb, requirement, delta, issue))

    if _CLARIFICATION_RE.search(_strip_fences(_readable(delta))):
        error("the delta still contains [NEEDS CLARIFICATION",
              "resolve it, or drop the requirement until the answer exists - an "
              "unresolved question folded into a permanent spec becomes a promise "
              "nobody can test")
    return issues


def _readable(delta: Delta) -> str:
    parts = [delta.preamble, delta.purpose]
    for group in delta.sections.values():
        parts.extend(r.text for r in group)
    return "\n".join(parts)


def _strip_fences(text: str) -> str:
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def _check_requirement(verb: str, requirement: Requirement, delta: Delta, issue) -> list:
    issues = []

    def error(message: str, fix: str) -> None:
        issues.append(issue("ERROR", "spec.grammar", delta.path, message, fix,
                            line=requirement.line))

    body = _strip_fences(requirement.body)

    if verb == "RENAMED":
        if not requirement.renamed_to:
            error(f"{requirement.id} is under RENAMED without a new id",
                  f"`### Requirement: {requirement.id} -> REQ-<new>`")
        elif requirement.renamed_to == requirement.id:
            error(f"{requirement.id} is renamed to itself", "remove the entry")
        return issues

    if verb == "REMOVED":
        for field_name in ("Reason", "Migration"):
            if not re.search(rf"\*\*{field_name}\*\*\s*:", body, re.I):
                error(f"{requirement.id} is removed without a **{field_name}**",
                      f"add `**{field_name}**: ...` - deleting a promise should be as "
                      f"expensive to write as making one")
        return issues

    # ADDED and MODIFIED both have to read as a whole requirement.
    if not requirement.title:
        error(f"{requirement.id} has no title",
              f"`### Requirement: {requirement.id} - <what the system must do>`")

    if not _NORMATIVE_RE.search(body):
        error(f"{requirement.id} states no normative rule",
              "say SHALL or MUST; a requirement that does neither is a description")

    scenarios = requirement.scenarios()
    if not scenarios:
        error(f"{requirement.id} has no `#### Scenario:`",
              "add at least one scenario; it is the part a test can assert, and a "
              "requirement with none is a requirement nobody can discharge")
    for level, title in scenarios:
        if level != 4:
            error(f"{requirement.id}: scenario {title!r} uses {level} hashes",
                  "scenarios are exactly four hashes, so the fold can tell a scenario "
                  "from a requirement without guessing")
        if not title.strip():
            error(f"{requirement.id} has an unnamed scenario",
                  "name it after the case it covers")

    if verb == "MODIFIED":
        if _DIFF_MARKER_RE.search(body):
            error(f"{requirement.id} looks like a diff fragment",
                  "MODIFIED carries the requirement's full new text. A reviewer must "
                  "read what the system will do, not a patch against what it did")
        elif len(_WORD_RE.findall(body)) < _MIN_MODIFIED_WORDS:
            error(f"{requirement.id} is modified with {len(_WORD_RE.findall(body))} "
                  f"words of content",
                  "MODIFIED carries the full new text of the requirement, never a "
                  "fragment - a fragment folds into a spec that says less than "
                  "anyone intended")
    return issues


def check_nonempty(item, deltas: list[Delta], issue) -> list:
    """R13: a change with zero deltas is rejected unless `skip_spec` says why.

    OpenSpec's named-bypass pattern. The escape hatch exists because plenty of
    real changes genuinely alter no behaviour; what it must not be is silent.
    """
    if any(not d.is_empty for d in deltas):
        return []
    reason = item.skipped("skip_spec")
    if reason:
        return []
    path = f"{item.relative}/.forge.yaml"
    if reason == "":
        return [issue(
            "ERROR", "spec.nonempty_or_skip", path,
            "skip_spec is set with no reason",
            "`skip_spec: <why this change alters no observable behaviour>` - the "
            "reason nobody writes is the one nobody can argue with later",
        )]
    return [issue(
        "ERROR", "spec.nonempty_or_skip", path,
        "this change has no spec delta",
        "write changes/<change>/spec/<capability>/spec.md, or set "
        "`skip_spec: <reason>` in .forge.yaml if it really alters no behaviour",
    )]


# ---------------------------------------------------------------------------
# R4 / R7 - requirements, tasks and tests
# ---------------------------------------------------------------------------

_REQ_MENTION_RE = re.compile(r"\bREQ-[A-Za-z0-9_-]+\b")
_CHORE_RE = re.compile(r"\b(chore|refactor|cleanup|docs)\b", re.I)


def promised_requirements(deltas: list[Delta]) -> dict[str, str]:
    """Requirement id -> the delta file that promises it.

    `REMOVED` and the old half of a `RENAMED` are excluded: a change that
    deletes a promise does not also owe a task and a test for it.
    """
    promised: dict[str, str] = {}
    for delta in deltas:
        for verb in ("ADDED", "MODIFIED"):
            for requirement in delta.sections.get(verb, []):
                promised[requirement.id] = delta.path
        for requirement in delta.sections.get("RENAMED", []):
            if requirement.renamed_to:
                promised[requirement.renamed_to] = delta.path
    return promised


def check_task_coverage(item, deltas: list[Delta], issue) -> list:
    """R4: requirements and tasks account for each other, both ways.

    Both directions matter and for different reasons. A requirement with no
    task is a promise nobody planned to keep. A task with no requirement is
    work nobody agreed to - which is how a change quietly grows past what was
    approved, and the single most common way scope escapes review.
    """
    promised = promised_requirements(deltas)
    tasks = item.tasks()
    path = f"{item.relative}/tasks.md"

    if promised and not tasks:
        return [issue(
            "ERROR", "trace.requirement_task_coverage", path,
            f"{len(promised)} requirement(s) are promised and tasks.md lists no tasks: "
            f"{', '.join(sorted(promised))}",
            "write one task per requirement, naming the REQ- id in the task line",
        )]

    issues = []
    mentioned: set[str] = set()
    for index, (_, text) in enumerate(tasks, start=1):
        found = set(_REQ_MENTION_RE.findall(text))
        mentioned |= found
        if found or _CHORE_RE.search(text):
            continue
        issues.append(issue(
            "ERROR", "trace.requirement_task_coverage", path,
            f"task {index} names no requirement: {text!r}",
            "name the REQ- id this task discharges, or mark it a chore - work "
            "nobody agreed to is how a change grows past what was approved",
        ))

    for identifier in sorted(promised):
        if identifier in mentioned:
            continue
        issues.append(issue(
            "ERROR", "trace.requirement_task_coverage", path,
            f"{identifier} is promised in {promised[identifier]} and no task "
            f"discharges it",
            f"add a task naming {identifier}, or remove the requirement from the delta",
        ))

    for identifier in sorted(mentioned - set(promised)):
        issues.append(issue(
            "WARNING", "trace.requirement_task_coverage", path,
            f"task(s) name {identifier}, which this change's spec delta does not "
            f"promise",
            f"harmless if {identifier} is an existing requirement; otherwise the id "
            f"is a typo and nothing will discharge it",
        ))
    return issues


def check_requirement_discharged(covers_index: dict, item, deltas: list[Delta],
                                 issue) -> list:
    """R7: every promised requirement carries at least one `@covers` test.

    Tag presence, not a green run - `forge verify` owns whether the suite
    passed. Separating them is deliberate: this answers "is there a test that
    claims to prove this", which stays answerable from the repository alone.
    """
    issues = []
    for identifier, path in sorted(promised_requirements(deltas).items()):
        if covers_index.get(identifier):
            continue
        issues.append(issue(
            "ERROR", "trace.requirement_discharged", path,
            f"{identifier} has no test tagged `@covers {identifier}`",
            f"tag the test that proves it and run `forge sync derived`; a "
            f"requirement no test claims is a requirement nobody can show you kept",
        ))
    return issues


# ---------------------------------------------------------------------------
# The fold
# ---------------------------------------------------------------------------

def fold(existing: str | None, delta: Delta) -> str:
    """Apply a delta to a permanent capability spec. Deterministic and total.

    Raises `FoldError` rather than guessing: adding a requirement that already
    exists, modifying one that does not, or removing one that was never there
    all mean the delta was written against a different version of the spec,
    and folding it anyway would produce a file nobody reviewed.
    """
    header, requirements = _split_permanent(existing, delta)
    order = [r.id for r in requirements]
    by_id = {r.id: r for r in requirements}

    for requirement in delta.sections.get("RENAMED", []):
        if requirement.id not in by_id:
            raise FoldError(f"{requirement.id} is renamed but the permanent spec for "
                            f"{delta.capability!r} does not define it")
        if requirement.renamed_to in by_id:
            raise FoldError(f"{requirement.id} is renamed to {requirement.renamed_to}, "
                            f"which already exists")
        moved = by_id.pop(requirement.id)
        moved.id = requirement.renamed_to
        if requirement.title:
            moved.title = requirement.title
        by_id[moved.id] = moved
        order[order.index(requirement.id)] = moved.id

    for requirement in delta.sections.get("REMOVED", []):
        if requirement.id not in by_id:
            raise FoldError(f"{requirement.id} is removed but the permanent spec for "
                            f"{delta.capability!r} does not define it")
        del by_id[requirement.id]
        order.remove(requirement.id)

    for requirement in delta.sections.get("MODIFIED", []):
        if requirement.id not in by_id:
            raise FoldError(f"{requirement.id} is modified but the permanent spec for "
                            f"{delta.capability!r} does not define it - was it meant "
                            f"to be ADDED?")
        by_id[requirement.id] = requirement

    for requirement in delta.sections.get("ADDED", []):
        if requirement.id in by_id:
            raise FoldError(f"{requirement.id} is added but the permanent spec for "
                            f"{delta.capability!r} already defines it - was it meant "
                            f"to be MODIFIED?")
        by_id[requirement.id] = requirement
        order.append(requirement.id)

    body = "\n".join(by_id[identifier].text.rstrip("\n") + "\n" for identifier in order)
    return f"{header}{body}" if body else header


def _split_permanent(existing: str | None, delta: Delta) -> tuple[str, list[Requirement]]:
    """The prose above the first requirement, and the requirements themselves."""
    if existing is None:
        title = delta.capability or "capability"
        purpose = delta.purpose.strip() or "TODO"
        return f"# {title}\n\n## Purpose\n\n{purpose}\n\n", []
    requirements = parse_permanent(existing)
    if not requirements:
        header = existing if existing.endswith("\n\n") else existing.rstrip("\n") + "\n\n"
        return header, []
    first = _REQ_RE.search(existing)
    return existing[:first.start()], requirements
