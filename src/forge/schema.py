"""Workflow schemas: the artifact DAG, loaded as data and validated like code.

A workflow is a YAML file declaring which artifacts a change produces, what
each one requires, and which tracks require it. Adding a workflow is adding a
file (ARCHITECTURE.md section 4.3) - that is the property that keeps the kernel
small as the harness grows, and it only holds if nothing about a workflow is
expressed in Python.

The kernel ships `feature` as text, not as a dict, and `forge init` writes that
same text to `.forge/schema/feature.yaml`. One code path loads both, so the
built-in default cannot drift from what a project gets when it edits its copy.

Two additions to OpenSpec's model, both from ARCHITECTURE.md section 4.1:

- **`tracks`** per artifact, the scale router expressed as data. One DAG serves
  every track; the track selects which nodes are required. The alternative is
  a workflow file per size, which is how GSD arrived at `quick`, `fast`,
  `sketch`, `spike` and `do` as five separate commands.
- **`reads`**, the explicit context contract, so a phase loads exactly what it
  is entitled to rather than whatever the prompt remembered to mention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

__all__ = [
    "Artifact",
    "Schema",
    "SchemaError",
    "TRACKS",
    "KERNEL_SCHEMA_VERSION",
    "SCHEMA_DIR",
    "load_schema",
    "parse_schema",
    "builtin_schema_text",
]

SCHEMA_DIR = ".forge/schema"

#: The schema `version` the kernel understands. A file declaring a higher one
#: is refused rather than read optimistically: a workflow the kernel
#: half-understands runs half a lifecycle and reports success.
KERNEL_SCHEMA_VERSION = 1

#: Track letters, in increasing weight. The ratchet is one-way (WORKFLOW.md
#: section 1), so the order is meaningful and not just a display convention.
TRACKS = ("A", "B", "C")

_ID_RE = re.compile(r"\A[a-z][a-z0-9-]*\Z")
_TRACK_TOKEN_RE = re.compile(r"\A(?P<track>[ABC])(?P<conditional>\?)?\Z")

REQUIRED = "required"
CONDITIONAL = "conditional"
ABSENT = "absent"


class SchemaError(ValueError):
    """A workflow schema is malformed. Always names the file and the node."""


@dataclass
class Artifact:
    id: str
    generates: str | None = None
    template: str | None = None
    requires: list[str] = field(default_factory=list)
    tracks: dict[str, str] = field(default_factory=dict)  # track -> REQUIRED|CONDITIONAL
    reads: list[object] = field(default_factory=list)
    instruction: str = ""
    #: Why a conditional artifact may be skipped, and which `.forge.yaml` key
    #: records that decision. Named in the schema so the bypass is a declared
    #: escape hatch rather than an undocumented one (OpenSpec's pattern).
    skip_key: str | None = None

    def requirement_for(self, track: str) -> str:
        return self.tracks.get(track, ABSENT)


@dataclass
class Schema:
    name: str
    version: int
    tracks: list[str]
    artifacts: list[Artifact]
    source: str

    def by_id(self, identifier: str) -> Artifact | None:
        return next((a for a in self.artifacts if a.id == identifier), None)

    def for_track(self, track: str) -> list[Artifact]:
        """Artifacts this track asks for, in declaration order."""
        return [a for a in self.artifacts if a.requirement_for(track) != ABSENT]

    def requires_on(self, artifact: Artifact, track: str) -> list[str]:
        """*Effective* prerequisites: the declared ones that this track has.

        A lighter track is a filter over one DAG, not a different DAG, so
        `tasks` requiring `impact` on track C simply means "after impact" and
        on track B - which has no `impact` - means nothing at all. Treating an
        absent prerequisite as unsatisfiable instead would make every bounded
        change block forever on a file its own track never asks for.
        """
        return [r for r in artifact.requires
                if (target := self.by_id(r)) and target.requirement_for(track) != ABSENT]

    @property
    def ids(self) -> list[str]:
        return [a.id for a in self.artifacts]


# ---------------------------------------------------------------------------
# The built-in feature workflow
# ---------------------------------------------------------------------------

# Deviation from ARCHITECTURE.md section 4.1, recorded here because the file it
# deviates from is the one a reader will compare against: the sketch there ends
# with an `apply:` node requiring `tasks`. `apply` generates nothing, so it can
# never be complete under the filesystem-derived state model in section 4.4 -
# it is a phase, not an artifact. Task completion is read from `tasks.md`
# checkboxes, which section 4.4 already specifies, so `apply` is not a node.
_FEATURE_SCHEMA = """\
name: feature
version: 1
tracks: [A, B, C]

artifacts:
  - id: proposal
    generates: proposal.md
    template: proposal.md
    requires: []
    tracks: [B, C]
    reads:
      - docs/system/OVERVIEW.md
      - claims: metadata
    instruction: |
      Why, in one or two sentences. What changes, as bullets, with **BREAKING**
      marked. Which capabilities are new or modified, by exact existing path.
      On track B this file also carries the inline `## Claims touched` account.

  - id: spec
    generates: "spec/**/*.md"
    template: spec.md
    requires: [proposal]
    # Quoted: a bare `?` opens a YAML complex key, so `[B?, C]` - the spelling
    # in ARCHITECTURE.md section 4.1 - does not parse. The token is right; it
    # just has to be a string.
    tracks: ["B?", C]
    skip_key: skip_spec
    reads:
      - changes/${change}/proposal.md
      - docs/system/specs/**
    instruction: |
      Delta requirements only, in the closed ADDED / MODIFIED / REMOVED /
      RENAMED grammar. Behaviour, never implementation. Every requirement gets
      at least one `#### Scenario:`. MODIFIED carries full content, never a
      diff fragment; REMOVED carries Reason and Migration.

  - id: impact
    generates: impact.md
    template: impact.md
    requires: [spec]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - derived: [deps, inventory]
      - claims: metadata
    instruction: |
      The blast radius, then the claim-touch account. Every claim `forge impact`
      computes must appear under exactly one of Unaffected, Updated, New,
      Superseded or At risk. `Unaffected` costs one honest sentence; that price
      is the point.

  - id: design
    generates: design.md
    template: design.md
    requires: [spec, impact]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - changes/${change}/impact.md
      - claims: "${impact.claims_touched}"
    instruction: |
      The approach, the alternatives rejected and why, and the ADR if this
      change decides something an ADR should record.

  - id: tasks
    generates: tasks.md
    template: tasks.md
    requires: [spec, impact, design]
    tracks: [B, C]
    reads:
      - changes/${change}/spec/**
      - changes/${change}/design.md
    instruction: |
      Ordered, checkable tasks. Each names the requirement it discharges, so
      `forge check` can pair requirements with tasks instead of guessing.

  - id: verification
    generates: verification.json
    requires: [tasks]
    tracks: [B, C]
    reads: []
    instruction: |
      Generated by `forge verify`, never authored. An authored verification
      report is a place to write "all tests pass" without having run them.
"""

_BUILTIN = {"feature": _FEATURE_SCHEMA}


def builtin_schema_text(name: str) -> str | None:
    return _BUILTIN.get(name)


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------

def load_schema(repo: Path, name: str = "feature") -> Schema:
    """The project's schema if it has one, else the kernel's own text.

    Same parser either way. A built-in default that took a different code path
    from a project's copy would be a default nobody can trust, because the
    thing being tested is not the thing being run.
    """
    target = repo / SCHEMA_DIR / f"{name}.yaml"
    if target.is_file():
        return parse_schema(target.read_text(encoding="utf-8"),
                            source=f"{SCHEMA_DIR}/{name}.yaml")
    text = builtin_schema_text(name)
    if text is None:
        known = ", ".join(sorted(_BUILTIN))
        raise SchemaError(
            f"no workflow named {name!r}: {SCHEMA_DIR}/{name}.yaml does not exist "
            f"and the kernel ships only {known}"
        )
    return parse_schema(text, source=f"<built-in {name}>")


def parse_schema(text: str, *, source: str) -> Schema:
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise SchemaError(f"{source}: not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise SchemaError(f"{source}: the top level must be a mapping")

    name = str(raw.get("name") or "").strip()
    if not name:
        raise SchemaError(f"{source}: `name` is required")

    version = raw.get("version")
    if not isinstance(version, int):
        raise SchemaError(f"{source}: `version` is required and must be an integer")
    if version > KERNEL_SCHEMA_VERSION:
        raise SchemaError(
            f"{source}: schema version {version} is newer than this kernel understands "
            f"({KERNEL_SCHEMA_VERSION}). Upgrade forge rather than editing the file - a "
            f"workflow the kernel half-understands runs half a lifecycle and reports success"
        )

    tracks = [str(t).strip().upper() for t in (raw.get("tracks") or TRACKS)]
    unknown = [t for t in tracks if t not in TRACKS]
    if unknown:
        raise SchemaError(f"{source}: unknown track(s) {', '.join(unknown)}; "
                          f"tracks are {', '.join(TRACKS)}")

    declared = raw.get("artifacts")
    if not isinstance(declared, list) or not declared:
        raise SchemaError(f"{source}: `artifacts` must be a non-empty list")

    artifacts: list[Artifact] = []
    seen: set[str] = set()
    for index, node in enumerate(declared):
        artifact = _parse_artifact(node, index, tracks, source)
        if artifact.id in seen:
            raise SchemaError(f"{source}: duplicate artifact id {artifact.id!r}")
        seen.add(artifact.id)
        artifacts.append(artifact)

    _check_requires(artifacts, source)
    _check_acyclic(artifacts, source)
    return Schema(name=name, version=version, tracks=tracks,
                  artifacts=artifacts, source=source)


def _parse_artifact(node: object, index: int, tracks: list[str], source: str) -> Artifact:
    where = f"{source}: artifacts[{index}]"
    if not isinstance(node, dict):
        raise SchemaError(f"{where} must be a mapping")

    identifier = str(node.get("id") or "").strip()
    if not _ID_RE.match(identifier):
        raise SchemaError(
            f"{where}: id {identifier!r} must be a lowercase kebab slug - it appears in "
            f"`forge gate` points and on the command line"
        )

    generates = node.get("generates")
    if generates is not None:
        generates = _safe_relative(str(generates), f"{where}.generates")

    template = node.get("template")
    if template is not None:
        template = _safe_relative(str(template), f"{where}.template")

    requires = node.get("requires") or []
    if not isinstance(requires, list):
        raise SchemaError(f"{where}.requires must be a list")

    declared_tracks = node.get("tracks")
    if not isinstance(declared_tracks, list):
        raise SchemaError(f"{where}.tracks must be a list, e.g. [B?, C]")
    resolved: dict[str, str] = {}
    for token in declared_tracks:
        match = _TRACK_TOKEN_RE.match(str(token).strip().upper())
        if not match:
            raise SchemaError(
                f"{where}.tracks: {token!r} is not a track token; write B, C, or B? "
                f"for 'required only when the condition holds'"
            )
        track = match.group("track")
        if track not in tracks:
            raise SchemaError(f"{where}.tracks: {track} is not declared in the "
                              f"workflow's `tracks`")
        resolved[track] = CONDITIONAL if match.group("conditional") else REQUIRED

    skip_key = node.get("skip_key")
    if CONDITIONAL in resolved.values() and not skip_key:
        raise SchemaError(
            f"{where}: a conditional track (`B?`) needs a `skip_key`, so skipping is a "
            f"recorded decision in .forge.yaml rather than an artifact quietly absent"
        )

    reads = node.get("reads") or []
    if not isinstance(reads, list):
        raise SchemaError(f"{where}.reads must be a list")

    return Artifact(
        id=identifier,
        generates=generates,
        template=template,
        requires=[str(r) for r in requires],
        tracks=resolved,
        reads=reads,
        instruction=str(node.get("instruction") or "").strip(),
        skip_key=str(skip_key) if skip_key else None,
    )


def _safe_relative(value: str, where: str) -> str:
    """Reject anything that could write outside the change directory.

    Every path in a schema is joined to `changes/NNNN/`, and a schema is a file
    a project edits. `../../etc` in a `generates` field must not be a way to
    make `forge` write there - GSD's argv hardening, applied to the data model.
    """
    text = value.strip().replace("\\", "/")
    if not text:
        raise SchemaError(f"{where} is empty")
    if text.startswith("/") or re.match(r"\A[A-Za-z]:", text):
        raise SchemaError(f"{where}: {value!r} must be relative to the change directory")
    if "\x00" in text:
        raise SchemaError(f"{where}: {value!r} contains a NUL byte")
    if any(part == ".." for part in text.split("/")):
        raise SchemaError(f"{where}: {value!r} escapes the change directory")
    return text


def _check_requires(artifacts: list[Artifact], source: str) -> None:
    known = {a.id for a in artifacts}
    for artifact in artifacts:
        for target in artifact.requires:
            if target == artifact.id:
                raise SchemaError(f"{source}: {artifact.id!r} requires itself")
            if target not in known:
                raise SchemaError(
                    f"{source}: {artifact.id!r} requires {target!r}, which no artifact declares"
                )


def _check_acyclic(artifacts: list[Artifact], source: str) -> None:
    """Depth-first, reporting the full path. A cycle named by one node is a
    puzzle; a cycle named by its path is a fix."""
    edges = {a.id: list(a.requires) for a in artifacts}
    state: dict[str, int] = {}
    path: list[str] = []

    def walk(node: str) -> None:
        state[node] = 1
        path.append(node)
        for target in edges.get(node, []):
            if state.get(target) == 1:
                cycle = path[path.index(target):] + [target]
                raise SchemaError(f"{source}: requires is cyclic: " + " -> ".join(cycle))
            if not state.get(target):
                walk(target)
        path.pop()
        state[node] = 2

    for artifact in artifacts:
        if not state.get(artifact.id):
            walk(artifact.id)


