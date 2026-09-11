"""The traceability index: ID conventions plus grep, no database.

SYSTEM_KNOWLEDGE.md section 8 argues that bidirectional traceability needs a
naming convention and four scans, not a datastore. This is those four scans.

``trace.json`` is a **build artifact, never a source of truth**. It is
regenerated from the repository, so it cannot disagree with the repository,
there is no schema to migrate, and `git checkout` of an old commit yields that
commit's index. Everything it contains is recoverable with grep; the index
exists so the answer is one lookup instead of five.

What it can answer, and how:

===========================================  ==================================
Which requirement caused this code?           back-references, reversed
Which tests verify this ID?                   ``@covers`` tags, reversed
Which claims does this one govern?            the claim's own ``governs``
Which claims govern this one?                 ``governs``, reversed
Which ADR explains this claim?                the claim's ``since``, and the
                                              ADR's own references
Which changes touched this ID?                mentions under ``changes/``
Which IDs are referenced but do not exist?    every edge, resolved
===========================================  ==================================

What it deliberately cannot answer is which *line* of code implements a
requirement. Line-level traceability is achievable and decays, and decayed
traceability is worse than none because it reads as complete. The granularity
here is file-to-claim and test-to-requirement, and that trade is deliberate
(SYSTEM_KNOWLEDGE.md section 8.3).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import derive, gitio, store

__all__ = ["build_trace", "lookup", "recent_change_citations", "TRACE_FILE"]

TRACE_FILE = "trace.json"

_CHANGES_DIR = "changes"
# One definition of what an ID looks like, in store.py. A second copy here
# would drift, and a scanner that recognises a slightly different set of IDs
# than the parser is a silent hole in the index.
_ID_RE = re.compile(r"\b(" + store.ANY_ID_PATTERN + r")\b")


def _anchor_path(anchor: str) -> str:
    """The path part of ``path[#Symbol][@sha]``, without re-validating it.

    The index records what the claim says; whether the anchor is well-formed is
    a validation question, and a malformed anchor must not stop the index from
    building.
    """
    text = anchor.strip()
    at = text.rfind("@")
    if at > 0 and re.fullmatch(r"[0-9a-fA-F]{4,40}", text[at + 1:]):
        text = text[:at]
    hash_at = text.rfind("#")
    if hash_at > 0:
        text = text[:hash_at]
    return text


def _scan_changes(repo: Path) -> dict[str, list[str]]:
    """ID mentions under ``changes/``, grouped by ID.

    Deliberately a mention scan rather than a structural read: the change
    artifacts and their grammar arrive in M3, and an index that refuses to
    build until then would be useless in the meantime.
    """
    by_id: dict[str, list[str]] = {}
    for path in gitio.list_files_at(repo, "HEAD"):
        if not path.startswith(f"{_CHANGES_DIR}/") or not path.endswith(".md"):
            continue
        if path.startswith(f"{_CHANGES_DIR}/archive/"):
            # The archive is never an input to any phase (ARCHITECTURE.md 4.1),
            # so it is not a citation either. Counting it would name every
            # folded change "archive" and, worse, keep a retired claim looking
            # consulted forever.
            continue
        blob = gitio.blob_at(repo, "HEAD", path)
        if blob is None:
            continue
        change = path.split("/")[1] if "/" in path else path
        for identifier in set(_ID_RE.findall(blob.decode("utf-8", "replace"))):
            by_id.setdefault(identifier, []).append(change)
    return {k: sorted(set(v)) for k, v in by_id.items()}


def recent_change_citations(repo: Path, window: int) -> set[str]:
    """Every ID cited by the *window* most recent changes.

    "Most recent" is by directory name descending, which is what the change
    numbering gives for free (`changes/0007-add-refunds/`). Ordering by commit
    date instead would need a git log per directory to answer a question the
    name already answers, and an archived change keeps its number.

    The orphan check (S17) is the only consumer: a claim that some change
    argued about recently is not an orphan, whatever the graph says.
    """
    by_id = _scan_changes(repo)
    if window <= 0:
        return set()
    newest = sorted({change for changes in by_id.values() for change in changes},
                    reverse=True)[:window]
    keep = set(newest)
    return {identifier for identifier, changes in by_id.items()
            if keep.intersection(changes)}


def _permanent_requirements(repo: Path) -> dict[str, tuple[str, int, str]]:
    """`REQ-*` defined in `docs/system/specs/**`, by id.

    Imported late for the same reason `derive` imports `trace` late: `spec`
    reads the change directories this module also scans, and a module-level
    import would be a cycle.
    """
    from .spec import SPECS_DIR, parse_permanent

    root = repo / SPECS_DIR
    if not root.is_dir():
        return {}
    out: dict[str, tuple[str, int, str]] = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for requirement in parse_permanent(text):
            out.setdefault(requirement.id, (relative, requirement.line,
                                            requirement.title))
    return out


def _delta_requirements(repo: Path) -> dict[str, tuple[str, int, str]]:
    """`REQ-*` promised by the spec deltas of changes that are still open.

    Without these, a change is reported as carrying dangling references from
    the moment it writes its spec until the moment it is archived - which is
    the whole time anybody is working on it, and makes `forge status` read as
    a broken store during normal use. The comment above `_permanent_requirements`
    records that this same surprise was fixed once, for folded requirements;
    it was not fixed for unfolded ones.

    A delta's requirement is a *promise*, not yet a permanent definition, so it
    is marked `provisional` and the archive fold is what makes it permanent.
    """
    from .change import CHANGES_DIR
    from .spec import capability_of, delta_files, parse_delta

    root = repo / CHANGES_DIR
    if not root.is_dir():
        return {}
    out: dict[str, tuple[str, int, str]] = {}
    for change_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if change_dir.name == "archive":
            continue
        relative = change_dir.relative_to(repo).as_posix()
        for path in delta_files(repo, relative):
            text = (repo / path).read_text(encoding="utf-8", errors="replace")
            try:
                delta = parse_delta(text, path, capability_of(path, relative))
            except ValueError:
                # A delta that does not parse is `spec.grammar`'s finding to
                # report, not a reason for the index to refuse to build.
                continue
            for verb, group in delta.sections.items():
                if verb == "REMOVED":
                    # A delta that removes a requirement does not define it.
                    continue
                for requirement in group:
                    target = requirement.renamed_to or requirement.id
                    out.setdefault(target, (path, requirement.line,
                                            requirement.title))
    return out


def build_trace(repo: Path) -> dict:
    """Compute the index from claims, ADRs, specs, changes and the derived tier."""
    claims = store.load_store(repo)
    decisions = store.load_decisions(repo)
    changes = _scan_changes(repo)

    tests = (derive.read_json(repo / derive.DERIVED_DIR / "tests.json") or {}).get("data", {})
    backrefs = (derive.read_json(repo / derive.DERIVED_DIR / "backrefs.json") or {}).get("data", {})
    covers_index: dict[str, list[str]] = tests.get("covers_index", {}) or {}
    backref_index: dict[str, list[str]] = backrefs.get("by_id", {}) or {}

    by_id: dict[str, dict] = {}
    for claim in claims:
        entry = by_id.setdefault(claim.id, _empty_entry(claim.id))
        entry["kind"] = claim.kind
        entry["status"] = claim.status
        entry["title"] = claim.title
        entry["defined_in"] = f"{claim.file}:{claim.line}"
        entry["candidate"] = claim.is_candidate
        entry["anchors"] = claim.anchors
        entry["anchor_paths"] = sorted({_anchor_path(a) for a in claim.anchors if a.strip()})
        entry["evidence"] = claim.evidence
        entry["governs"] = claim.governs
        entry["since"] = claim.since
        if claim.parse_error:
            entry["parse_error"] = claim.parse_error

    # Requirements in the permanent specs are definitions too. Without this,
    # a requirement a change folded in is reported as a dangling reference the
    # moment a test tags `@covers` for it - which is the exact end state of a
    # correctly completed change, and the first thing anyone would see after
    # their first archive.
    for identifier, (path, line, title) in _permanent_requirements(repo).items():
        entry = by_id.setdefault(identifier, _empty_entry(identifier))
        entry["kind"] = "requirement"
        entry["title"] = title
        entry["defined_in"] = f"{path}:{line}"

    # Open changes define theirs provisionally. A permanent spec always wins:
    # once a change is folded, the requirement's home is the spec, and a stale
    # delta left behind must not move it back.
    for identifier, (path, line, title) in _delta_requirements(repo).items():
        if identifier in by_id and by_id[identifier]["defined_in"]:
            continue
        entry = by_id.setdefault(identifier, _empty_entry(identifier))
        entry["kind"] = "requirement"
        entry["title"] = title
        entry["defined_in"] = f"{path}:{line}"
        entry["provisional"] = True

    for identifier, decision in decisions.items():
        entry = by_id.setdefault(identifier, _empty_entry(identifier))
        entry["kind"] = "decision"
        entry["title"] = decision["title"]
        entry["defined_in"] = decision["file"]
        entry["supersedes"] = decision["supersedes"]
        entry["references"] = decision["references"]

    # Reverse edges. Every relationship in the store is declared in one
    # direction; the index is where the other direction comes from.
    for claim in claims:
        for target in claim.governs:
            by_id.setdefault(target, _empty_entry(target))["governed_by"].append(claim.id)
        if claim.since:
            by_id.setdefault(claim.since, _empty_entry(claim.since))["justifies"].append(claim.id)
    for identifier, decision in decisions.items():
        for target in decision["references"]:
            by_id.setdefault(target, _empty_entry(target))["referenced_by_adr"].append(identifier)

    for identifier, entries in covers_index.items():
        by_id.setdefault(identifier, _empty_entry(identifier))["tests"] = sorted(entries)
    for identifier, entries in backref_index.items():
        by_id.setdefault(identifier, _empty_entry(identifier))["back_references"] = sorted(entries)
    for identifier, entries in changes.items():
        by_id.setdefault(identifier, _empty_entry(identifier))["changes"] = sorted(entries)

    for entry in by_id.values():
        for key in ("governed_by", "justifies", "referenced_by_adr"):
            entry[key] = sorted(set(entry[key]))

    dangling = sorted(i for i, e in by_id.items() if e["defined_in"] is None)
    # Candidates are excluded. A proposed invariant with no test is a guess
    # that has not been reviewed yet, which is the candidate tier working -
    # reporting it as an open item makes the store look in worse repair than
    # it is, and the thing to do about it is the review, not a test.
    undischarged = sorted(
        i for i, e in by_id.items()
        if e["defined_in"] and e["kind"] == "invariant" and not e["tests"]
        and not e["candidate"] and e["status"] != "retired"
    )

    return {
        "ids": {k: by_id[k] for k in sorted(by_id)},
        "summary": {
            "claims": len([c for c in claims if not c.is_candidate]),
            "candidates": len([c for c in claims if c.is_candidate]),
            "decisions": len(decisions),
            "ids_indexed": len(by_id),
            "dangling_references": dangling,
            "invariants_without_tests": undischarged,
            "tests_total": tests.get("total_tests", 0),
            "tests_tagged": tests.get("tagged_tests", 0),
        },
    }


def _empty_entry(identifier: str) -> dict:
    return {
        "id": identifier,
        "kind": None,
        "status": None,
        "title": None,
        "defined_in": None,      # None means "referenced but never defined"
        "candidate": False,
        #: True for a requirement an open change promises but has not folded.
        "provisional": False,
        "anchors": [],
        "anchor_paths": [],
        "evidence": [],
        "governs": [],
        "governed_by": [],
        "since": None,
        "justifies": [],
        "supersedes": None,
        "references": [],
        "referenced_by_adr": [],
        "tests": [],
        "back_references": [],
        "changes": [],
    }


def lookup(repo: Path, identifier: str) -> dict | None:
    """One ID's entry, from the index on disk, falling back to a fresh build."""
    payload = derive.read_json(repo / derive.DERIVED_DIR / TRACE_FILE)
    index = (payload or {}).get("data") or build_trace(repo)
    return (index.get("ids") or {}).get(identifier)
