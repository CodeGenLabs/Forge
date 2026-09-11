"""Changes: `changes/NNNN-<slug>/`, and the state derived from what is on disk.

There is no state file (ARCHITECTURE.md section 4.4). An artifact is complete
because its `generates` path exists, the track is whatever `.forge.yaml` says,
and a task is done because its checkbox is ticked. Everything else is computed
from those three facts.

That is OpenSpec's mechanism and it is worth the sentence of justification:
with no state format there is no migration path for it, no way for state and
filesystem to disagree, `git checkout` of an old commit gives you that commit's
harness state exactly, and two sessions never fight over a lockfile.

`.forge.yaml` inside the change is the one exception, and it holds only what
the filesystem genuinely cannot answer: which track this change is on, what it
was upgraded from, and whether a conditional artifact was deliberately skipped
and why.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .schema import ABSENT, CONDITIONAL, REQUIRED, Artifact, Schema, TRACKS

__all__ = [
    "Change",
    "ChangeError",
    "CHANGES_DIR",
    "ARCHIVE_DIR",
    "META_FILE",
    "ArtifactState",
    "list_changes",
    "find_change",
    "new_change",
    "slugify",
]

CHANGES_DIR = "changes"
ARCHIVE_DIR = "changes/archive"
META_FILE = ".forge.yaml"

_DIR_RE = re.compile(r"\A(?P<number>\d{4})-(?P<slug>[a-z0-9][a-z0-9-]*)\Z")
_TASK_RE = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.+?)\s*$", re.M)

COMPLETE = "complete"
MISSING = "missing"
BLOCKED = "blocked"
SKIPPED = "skipped"
NOT_ON_TRACK = "not-on-track"


class ChangeError(ValueError):
    """A change directory is malformed, absent, or ambiguous."""


@dataclass
class ArtifactState:
    artifact: Artifact
    state: str
    #: Prerequisites not yet complete. Empty unless `state` is BLOCKED.
    waiting_on: list[str] = field(default_factory=list)
    #: Files matched by `generates`, relative to the repository.
    files: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def id(self) -> str:
        return self.artifact.id

    def to_dict(self) -> dict:
        out = {"id": self.id, "state": self.state}
        if self.waiting_on:
            out["waiting_on"] = self.waiting_on
        if self.files:
            out["files"] = self.files
        if self.reason:
            out["reason"] = self.reason
        return out


@dataclass
class Change:
    number: int
    slug: str
    root: Path          # absolute
    repo: Path          # absolute
    meta: dict = field(default_factory=dict)
    archived: bool = False

    # -- identity ----------------------------------------------------------

    @property
    def name(self) -> str:
        return f"{self.number:04d}-{self.slug}"

    @property
    def relative(self) -> str:
        return self.root.relative_to(self.repo).as_posix()

    # -- what `.forge.yaml` alone can say ---------------------------------

    @property
    def track(self) -> str:
        track = str(self.meta.get("track") or "C").strip().upper()
        return track if track in TRACKS else "C"

    @property
    def workflow(self) -> str:
        return str(self.meta.get("workflow") or "feature")

    @property
    def upgraded_from(self) -> list[str]:
        value = self.meta.get("upgraded_from") or []
        return [str(v) for v in (value if isinstance(value, list) else [value])]

    def skipped(self, key: str) -> str | None:
        """The recorded reason for skipping, or None if it was not skipped.

        A bare `skip_spec: true` is *not* a skip. OpenSpec's named-bypass
        pattern is the whole value here: an escape hatch with no reason beside
        it is taken by default, and then the reason nobody wrote is the one
        nobody can argue with later.
        """
        value = self.meta.get(key)
        if not value:
            return None
        if value is True:
            return ""
        return str(value).strip()

    # -- filesystem-derived state -----------------------------------------

    def files_for(self, artifact: Artifact) -> list[str]:
        if not artifact.generates:
            return []
        pattern = artifact.generates
        if any(ch in pattern for ch in "*?["):
            matches = sorted(p for p in self.root.glob(pattern) if p.is_file())
        else:
            target = self.root / pattern
            matches = [target] if target.is_file() else []
        return [p.relative_to(self.repo).as_posix() for p in matches]

    def state(self, schema: Schema) -> list[ArtifactState]:
        """Every artifact in the schema, with its state on this change's track."""
        track = self.track
        complete: set[str] = set()
        states: list[ArtifactState] = []

        for artifact in schema.artifacts:
            requirement = artifact.requirement_for(track)
            files = self.files_for(artifact)
            if files:
                complete.add(artifact.id)

            if requirement == ABSENT:
                states.append(ArtifactState(artifact, NOT_ON_TRACK, files=files))
                continue
            if files:
                states.append(ArtifactState(artifact, COMPLETE, files=files))
                continue

            skip_reason = (self.skipped(artifact.skip_key)
                           if requirement == CONDITIONAL and artifact.skip_key else None)
            if skip_reason is not None:
                # Counted as satisfied for anything that depends on it: the
                # decision was recorded, and blocking on a file the change
                # deliberately declined to write would make the escape hatch
                # useless.
                complete.add(artifact.id)
                states.append(ArtifactState(
                    artifact, SKIPPED,
                    reason=skip_reason or f"{artifact.skip_key} set with no reason",
                ))
                continue

            waiting = [r for r in schema.requires_on(artifact, track) if r not in complete]
            states.append(ArtifactState(
                artifact, BLOCKED if waiting else MISSING, waiting_on=waiting,
            ))
        return states

    def next_artifact(self, schema: Schema) -> ArtifactState | None:
        """The first thing this change can actually do. `forge status` reads it."""
        return next((s for s in self.state(schema) if s.state == MISSING), None)

    def is_complete(self, schema: Schema) -> bool:
        return all(s.state in (COMPLETE, SKIPPED, NOT_ON_TRACK)
                   for s in self.state(schema))

    # -- tasks -------------------------------------------------------------

    def tasks(self) -> list[tuple[bool, str]]:
        """`- [x] text` lines from tasks.md. Done-ness is the checkbox."""
        target = self.root / "tasks.md"
        if not target.is_file():
            return []
        text = target.read_text(encoding="utf-8", errors="replace")
        return [(m.group("mark").lower() == "x", m.group("text"))
                for m in _TASK_RE.finditer(text)]

    # -- writing -----------------------------------------------------------

    def write_meta(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / META_FILE).write_text(
            yaml.safe_dump(self.meta, sort_keys=True, default_flow_style=False),
            encoding="utf-8", newline="\n",
        )

    def upgrade(self, track: str, *, reason: str) -> None:
        """Move up a track. One-way, and it records where it came from.

        The ratchet is the point (WORKFLOW.md section 1): discovering hidden
        complexity upgrades a change, and nothing downgrades it. A downgrade
        would let a change that turned out to touch an `ARC-` claim shed the
        artifacts that account for it, one honest-looking step at a time.
        """
        track = track.strip().upper()
        if track not in TRACKS:
            raise ChangeError(f"{track!r} is not a track; tracks are {', '.join(TRACKS)}")
        current = self.track
        if TRACKS.index(track) < TRACKS.index(current):
            raise ChangeError(
                f"track {current} does not downgrade to {track}. The ratchet is one-way: "
                f"if the scope really shrank, close this change and open a smaller one"
            )
        if track == current:
            raise ChangeError(f"already on track {current}")
        self.meta["track"] = track
        self.meta.setdefault("upgraded_from", []).append(f"{current}: {reason}")
        self.write_meta()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _read_meta(root: Path) -> dict:
    target = root / META_FILE
    if not target.is_file():
        return {}
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}


def list_changes(repo: Path, *, archived: bool = False) -> list[Change]:
    root = repo / (ARCHIVE_DIR if archived else CHANGES_DIR)
    if not root.is_dir():
        return []
    out: list[Change] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if archived:
            # Archived directories are prefixed with the date they were folded,
            # so the number is not at position 0 any more.
            name = re.sub(r"\A\d{4}-\d{2}-\d{2}-", "", name)
        match = _DIR_RE.match(name)
        if not match:
            continue
        out.append(Change(
            number=int(match.group("number")),
            slug=match.group("slug"),
            root=path,
            repo=repo,
            meta=_read_meta(path),
            archived=archived,
        ))
    return out


def find_change(repo: Path, reference: str) -> Change:
    """Resolve `4`, `0004`, `0004-refund-support` or a slug to one change."""
    reference = str(reference).strip()
    changes = list_changes(repo)
    if not changes:
        raise ChangeError(f"no changes in {CHANGES_DIR}/; create one with `forge change new`")

    if reference.isdigit():
        number = int(reference)
        matches = [c for c in changes if c.number == number]
    else:
        matches = [c for c in changes if c.name == reference or c.slug == reference]

    if len(matches) == 1:
        return matches[0]
    if not matches:
        known = ", ".join(c.name for c in changes)
        raise ChangeError(f"no change matches {reference!r}; open changes are {known}")
    # Two directories with one number is a filesystem the tool must not guess
    # about: every downstream write would land in an arbitrary one of them.
    names = ", ".join(c.name for c in matches)
    raise ChangeError(f"{reference!r} is ambiguous between {names}; rename one")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        raise ChangeError("a change needs a name made of letters or digits")
    return slug[:60].rstrip("-")


def next_number(repo: Path) -> int:
    """Monotonic across open *and* archived changes.

    Reusing a number an archive already holds would make `changes/0004` mean
    two different things depending on the date, and every reference to it
    ambiguous forever.
    """
    used = [c.number for c in list_changes(repo)] + \
           [c.number for c in list_changes(repo, archived=True)]
    return max(used, default=0) + 1


def new_change(repo: Path, title: str, *, track: str = "C",
               workflow: str = "feature", today: date | None = None) -> Change:
    track = track.strip().upper()
    if track not in TRACKS:
        raise ChangeError(f"{track!r} is not a track; tracks are {', '.join(TRACKS)}")
    slug = slugify(title)
    number = next_number(repo)
    root = repo / CHANGES_DIR / f"{number:04d}-{slug}"
    if root.exists():
        raise ChangeError(f"{root.relative_to(repo).as_posix()} already exists")
    change = Change(number=number, slug=slug, root=root, repo=repo, meta={
        "track": track,
        "workflow": workflow,
        "created": (today or date.today()).isoformat(),
        "title": title.strip(),
    })
    change.write_meta()
    return change
