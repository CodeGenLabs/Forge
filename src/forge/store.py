"""Reading the claim store. Parsing only; the checks live in `validate.py`.

A claim is a Markdown heading carrying a stable ID, followed by a fenced
``claim`` block, then prose::

    ### INV-7 — A refund never exceeds the captured amount

    ```claim
    kind: invariant
    status: enforced
    truth-source: tests
    anchors:
      - src/payments/refund.ts#computeRefundable@a1b2c3d
    evidence:
      - test: tests/payments/refund.spec.ts::refund cannot exceed capture
    governs: [CMP-payments]
    since: ADR-0014
    reviewed: 2026-09-10
    ```

    Partial refunds accumulate: the sum of settled refunds is what is bounded...

The fence is why this needs about a hundred lines and no Markdown library: find
the heading, take the next fenced ``claim`` block, hand it to a YAML parser, and
leave everything else as prose.

Scope: this module answers "what claims exist and what do they point at". It
does **not** decide whether a claim is well-formed - that is `validate.py`, and
the split is load-bearing. Folded together, the trace index would refuse to
build on a store that merely has a mistake in it, and `forge check` would then
have no index to report the mistake from.

So the parser is deliberately permissive: a claim that fails every check still
parses, carrying its `parse_error` and the set of `fields` it declared, and the
checks read those rather than re-parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

__all__ = [
    "Claim",
    "ClaimRef",
    "STORE_DIR",
    "CANDIDATES_DIR",
    "DECISIONS_DIR",
    "KIND_PREFIXES",
    "parse_claims",
    "load_store",
    "load_decisions",
]

STORE_DIR = "docs/system"
CANDIDATES_DIR = "docs/system/candidates"
DECISIONS_DIR = "docs/system/decisions"

# Prefix -> kind, from SYSTEM_KNOWLEDGE.md section 2.2. The MVP ships five
# (MVP.md M0); the rest are listed so an ID from a later milestone parses rather
# than being silently skipped.
KIND_PREFIXES = {
    "ARC": "architecture",
    "CMP": "component",
    "CON": "concept",
    "INV": "invariant",
    "PIT": "pitfall",
    "API": "interface",
    "DAT": "datum",
    "FLW": "workflow",
    "CST": "constraint",
    "STR": "strategy",
}

# An ID is `PREFIX-<token>` where the token is digits or a kebab slug.
#
# SYSTEM_KNOWLEDGE.md section 7.1 originally specified digits only, while every
# example in the same document used slugs (`CMP-payments`, `CON-capture`,
# `API-post-refunds`). Implementing the parser forced the choice, and slugs win
# on the property that matters: `grep -r CMP-payments` explains itself, where
# `grep -r CMP-3` sends you to the store first.
#
# What is actually enforced is *stability*, not numerality: an ID is a permanent
# name, never reused and never renumbered. A component renamed from payments to
# billing keeps `CMP-payments` and changes its title - the ID becomes a
# historical name, which is the price of it being a stable one. The design
# document has been corrected to match.
_TOKEN = r"(?:\d+|[a-z0-9][a-z0-9-]*)"
ID_PATTERN = r"(?:" + "|".join(KIND_PREFIXES) + r")-" + _TOKEN
# Requirements live in change specs rather than the store, and ADRs are numbered
# because they are a chronological series rather than named things.
ANY_ID_PATTERN = r"(?:" + ID_PATTERN + r"|ADR-\d{4}|REQ-[A-Za-z0-9_-]+)"

_HEADING_RE = re.compile(
    r"^###\s+(?P<id>" + ID_PATTERN + r")\s*(?:[—-]\s*(?P<title>.*))?$",
    re.M,
)
_FENCE_RE = re.compile(r"^```claim\s*$(?P<body>.*?)^```\s*$", re.M | re.S)
_ADR_FILE_RE = re.compile(r"^(?P<id>ADR-\d{4})-[A-Za-z0-9._-]+\.md$")


@dataclass
class ClaimRef:
    """A pointer out of a claim: an anchor, an evidence entry or a governed ID."""
    kind: str      # "anchor" | "evidence" | "governs" | "since" | "supersedes"
    value: str


@dataclass
class Claim:
    id: str
    kind: str
    file: str
    line: int
    title: str = ""
    status: str = ""
    truth_source: str = ""
    anchors: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    governs: list[str] = field(default_factory=list)
    since: str | None = None
    supersedes: str | None = None
    reviewed: str | None = None
    confidence: str | None = None
    retired_ground: str | None = None
    retired_evidence: str | None = None
    prose: str = ""
    parse_error: str | None = None
    #: Keys the claim fence actually declared, before any normalisation.
    #: Validation needs to tell `anchors: []` (legal for a concept) from no
    #: `anchors` key at all (never legal), and only the parser can see the
    #: difference - by the time a field has a default, the two look the same.
    fields: set[str] = field(default_factory=set)
    #: Last line of the claim's section, so a scan over the raw file can say
    #: which claim a hit belongs to.
    end_line: int = 0

    @property
    def is_candidate(self) -> bool:
        return self.file.startswith(CANDIDATES_DIR)

    @property
    def prefix(self) -> str:
        return self.id.split("-", 1)[0]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "status": self.status,
            "truth_source": self.truth_source,
            "file": self.file,
            "line": self.line,
            "anchors": self.anchors,
            "evidence": self.evidence,
            "governs": self.governs,
            "since": self.since,
            "supersedes": self.supersedes,
            "reviewed": self.reviewed,
            "candidate": self.is_candidate,
            "parse_error": self.parse_error,
        }


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _evidence_entries(value: object) -> list[str]:
    """Normalise evidence to ``kind:value`` strings.

    YAML reads ``- test: path::name`` as a mapping, and ``- "test: path"`` as a
    string. Both are natural to write, so both are accepted and flattened.
    """
    out: list[str] = []
    for item in value if isinstance(value, list) else [value]:
        if item is None:
            continue
        if isinstance(item, dict):
            for key, val in item.items():
                out.append(f"{key}:{val}")
        else:
            out.append(str(item))
    return out


def parse_claims(text: str, path: str) -> list[Claim]:
    """Parse every claim in one Markdown document."""
    claims: list[Claim] = []
    headings = list(_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        identifier = heading.group("id")
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[start:end]

        # `end` is where the *next* heading begins, so the section's last line
        # is the last one carrying content. Counting to `end` instead would put
        # the following claim's heading inside this claim's range, which shows
        # up as `forge claim show` printing one claim and a bit of the next.
        last = end
        while last > start and text[last - 1] == "\n":
            last -= 1

        claim = Claim(
            id=identifier,
            kind=KIND_PREFIXES.get(identifier.split("-", 1)[0], "unknown"),
            file=path,
            line=text.count("\n", 0, heading.start()) + 1,
            title=(heading.group("title") or "").strip(),
            end_line=text.count("\n", 0, last) + 1,
        )

        fence = _FENCE_RE.search(section)
        if fence is None:
            claim.parse_error = "no ```claim block"
            claim.prose = section.strip()
            claims.append(claim)
            continue

        try:
            block = yaml.safe_load(fence.group("body")) or {}
        # ValueError alongside YAMLError: PyYAML resolves an unquoted
        # `2026-02-30` to a timestamp and then lets `datetime.date` raise, so a
        # typo in a review date would otherwise take down every command that
        # reads the store - including the one whose job is to report it.
        except (yaml.YAMLError, ValueError) as exc:
            claim.parse_error = f"claim block is not valid YAML: {exc}"
            block = {}
        if not isinstance(block, dict):
            claim.parse_error = "claim block is not a mapping"
            block = {}

        # Underscores accepted alongside hyphens throughout, so a YAML habit is
        # not a validation error; the canonical spelling is the hyphenated one.
        block = {str(key).replace("_", "-"): value for key, value in block.items()}

        declared_kind = str(block.get("kind") or "").strip()
        if declared_kind:
            claim.kind = declared_kind
        claim.status = str(block.get("status") or "").strip()
        claim.truth_source = str(block.get("truth-source") or "").strip()
        claim.anchors = _as_list(block.get("anchors"))
        claim.evidence = _evidence_entries(block.get("evidence"))
        claim.governs = _as_list(block.get("governs"))
        claim.since = (str(block["since"]).strip() if block.get("since") else None)
        claim.supersedes = (str(block["supersedes"]).strip() if block.get("supersedes") else None)
        claim.reviewed = (str(block["reviewed"]).strip() if block.get("reviewed") else None)
        claim.confidence = (str(block["confidence"]).strip() if block.get("confidence") else None)
        claim.retired_ground = (
            str(block["retired-ground"]).strip() if block.get("retired-ground") else None
        )
        claim.retired_evidence = (
            str(block["retired-evidence"]).strip() if block.get("retired-evidence") else None
        )
        claim.fields = set(block)
        claim.prose = section[fence.end():].strip()
        claims.append(claim)

    return claims


def store_files(repo: Path) -> list[Path]:
    """Markdown files that may hold claims: the store and its candidates.

    `derived/` is excluded by construction - it holds machine-owned JSON, and a
    claim there would be a category error.
    """
    root = repo / STORE_DIR
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(repo).as_posix()
        if relative.startswith(f"{STORE_DIR}/derived/"):
            continue
        if relative.startswith(f"{DECISIONS_DIR}/"):
            continue
        out.append(path)
    return out


def load_store(repo: Path) -> list[Claim]:
    """Every claim in the store, ratified and candidate alike.

    Candidates are included and flagged rather than hidden: the agent may read
    them, and the index has to be able to answer "is this ID a candidate?" for
    the rule that a ratified claim may never point into `candidates/`.
    """
    claims: list[Claim] = []
    for path in store_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        claims.extend(parse_claims(text, path.relative_to(repo).as_posix()))
    return claims


def load_decisions(repo: Path) -> dict[str, dict]:
    """ADRs by id, with the claims and decisions each one references."""
    root = repo / DECISIONS_DIR
    if not root.is_dir():
        return {}
    id_re = re.compile(r"\b(" + ANY_ID_PATTERN + r")\b")
    out: dict[str, dict] = {}
    for path in sorted(root.glob("*.md")):
        match = _ADR_FILE_RE.match(path.name)
        if not match:
            continue
        identifier = match.group("id")
        text = path.read_text(encoding="utf-8", errors="replace")
        supersedes = re.search(r"^\s*supersedes:\s*(ADR-\d{4})", text, re.M | re.I)
        title = ""
        first = re.search(r"^#\s+(.*)$", text, re.M)
        if first:
            title = first.group(1).strip()
        out[identifier] = {
            "id": identifier,
            "file": path.relative_to(repo).as_posix(),
            "title": title,
            "supersedes": supersedes.group(1) if supersedes else None,
            "references": sorted({i for i in id_re.findall(text) if i != identifier}),
        }
    return out
