"""Anchors: parsing, and deterministic staleness classification.

An anchor binds a claim to a place in the code::

    src/payments/refund.ts#computeRefundable@a1b2c3d
    src/domain/@a1b2c3d                        (directory anchor: the tree hash)
    src/payments/refund.ts                     (baseline resolved from the claim file)

Grammar: ``path[#Symbol][@sha]``.

Classification answers one question, and it is important to be precise about
which one: **has the code this claim describes changed since the recorded
baseline?** It does *not* answer "is the claim still true" - nothing can, and
arXiv:2604.03447 measured how badly a model does when asked. What this buys is
the exact set of claims a reviewer needs to look at, computed from git and
tree-sitter with no model call.

One deviation from SYSTEM_KNOWLEDGE.md section 5.1, deliberate: ``coarse`` is a
*flag*, not a fifth status. A coarse comparison still yields fresh or stale, so
folding it into the status would lose the verdict. Likewise ``shifted`` is
promoted to a first-class status (body changed, signature intact) because that
is the distinction that keeps the ledger quiet enough to be read - see
OPEN_QUESTIONS.md Q2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import gitio
from .fingerprint import find_symbol, fingerprint_source, symbol_appears_textually

__all__ = ["Anchor", "AnchorError", "Status", "AnchorResult", "ClaimDrift",
           "parse_anchor", "classify", "classify_store"]

_SHA_RE = re.compile(r"\A[0-9a-fA-F]{4,40}\Z")
_SYMBOL_RE = re.compile(r"\A[A-Za-z_$][A-Za-z0-9_$]*(\.[A-Za-z_$][A-Za-z0-9_$]*)*\Z")


class AnchorError(ValueError):
    """An anchor string could not be parsed, or is internally inconsistent."""


class Status(str, Enum):
    FRESH = "fresh"        #: fingerprint unchanged since the baseline
    SHIFTED = "shifted"    #: body changed, signature intact - weaker signal
    STALE = "stale"        #: signature changed, or a non-symbol anchor changed
    MISSING = "missing"    #: the anchored path or symbol is gone - blocking


@dataclass(frozen=True)
class Anchor:
    path: str
    symbol: str | None = None
    sha: str | None = None
    raw: str = ""

    @property
    def is_dir(self) -> bool:
        return self.path.endswith("/")

    def __str__(self) -> str:
        out = self.path
        if self.symbol:
            out += f"#{self.symbol}"
        if self.sha:
            out += f"@{self.sha}"
        return out


def parse_anchor(text: str) -> Anchor:
    """Parse ``path[#Symbol][@sha]``.

    Parsed from the right, and a trailing ``@x`` is only treated as a revision
    when it looks like an object name. That is what keeps scoped package paths
    such as ``packages/@acme/core/src/index.ts`` working: the text after the
    last ``@`` is not hex, so it stays part of the path.
    """
    if not isinstance(text, str):
        raise AnchorError("anchor must be a string")
    raw = text.strip()
    if not raw:
        raise AnchorError("anchor must not be empty")

    rest = raw
    sha: str | None = None
    at = rest.rfind("@")
    if at > 0:
        candidate = rest[at + 1:]
        if _SHA_RE.match(candidate):
            sha = candidate.lower()
            rest = rest[:at]

    symbol: str | None = None
    hash_at = rest.rfind("#")
    if hash_at > 0:
        symbol = rest[hash_at + 1:]
        rest = rest[:hash_at]
        if not _SYMBOL_RE.match(symbol):
            raise AnchorError(f"symbol {symbol!r} is not a plain (optionally dotted) identifier")

    try:
        path = gitio.validate_repo_path(rest)
    except gitio.InvalidPath as exc:
        raise AnchorError(str(exc)) from exc

    if path.endswith("/") and symbol:
        raise AnchorError("a directory anchor cannot name a symbol")

    return Anchor(path=path, symbol=symbol, sha=sha, raw=raw)


@dataclass
class AnchorResult:
    anchor: Anchor
    status: Status
    baseline: str
    head: str
    coarse: bool = False
    symbol_unresolved: bool = False
    # Where the anchored file actually lived at each end. Named for the two
    # revisions rather than "from"/"to", which invites reading them backwards:
    # an earlier version set renamed_from to the *head* path and renamed_to to
    # the *baseline* path, and printed a self-contradicting message.
    baseline_path: str | None = None
    head_path: str | None = None
    # True when the move was found by content identity because git's rename
    # detection missed it - see _relocate.
    relocated: bool = False
    baseline_digest: str | None = None
    head_digest: str | None = None
    detail: str = ""

    @property
    def changed(self) -> bool:
        return self.status in (Status.SHIFTED, Status.STALE, Status.MISSING)

    @property
    def moved(self) -> bool:
        """True when a rename was followed between the two revisions."""
        return bool(
            self.baseline_path and self.head_path
            and self.baseline_path != self.head_path
        )

    def to_dict(self) -> dict:
        return {
            "anchor": str(self.anchor),
            "path": self.anchor.path,
            "symbol": self.anchor.symbol,
            "status": self.status.value,
            "baseline": self.baseline,
            "head": self.head,
            "coarse": self.coarse,
            "symbol_unresolved": self.symbol_unresolved,
            "baseline_path": self.baseline_path,
            "head_path": self.head_path,
            "moved": self.moved,
            "relocated": self.relocated,
            "detail": self.detail,
        }


def classify(
    repo: Path,
    anchor: Anchor,
    *,
    baseline: str | None = None,
    head: str = "HEAD",
) -> AnchorResult:
    """Classify one anchor between two revisions.

    *baseline* defaults to the anchor's own recorded ``@sha``. Passing it
    explicitly is what the measurement harness does to replay history.
    """
    base_rev = baseline or anchor.sha
    if not base_rev:
        raise AnchorError(
            f"anchor {anchor.raw!r} has no @sha and no baseline was supplied"
        )
    base_rev = gitio.validate_rev(base_rev)
    head_rev = gitio.validate_rev(head)

    if anchor.is_dir:
        return _classify_directory(repo, anchor, base_rev, head_rev)
    return _classify_file(repo, anchor, base_rev, head_rev)


def _classify_directory(repo: Path, anchor: Anchor, base_rev: str, head_rev: str) -> AnchorResult:
    base_hash = gitio.tree_hash_at(repo, base_rev, anchor.path)
    head_hash = gitio.tree_hash_at(repo, head_rev, anchor.path)
    if head_hash is None:
        return AnchorResult(
            anchor=anchor, status=Status.MISSING, baseline=base_rev, head=head_rev,
            detail=f"directory {anchor.path} does not exist at head",
        )
    if base_hash is None:
        return AnchorResult(
            anchor=anchor, status=Status.MISSING, baseline=base_rev, head=head_rev,
            detail=f"directory {anchor.path} did not exist at the baseline",
        )
    status = Status.FRESH if base_hash == head_hash else Status.STALE
    return AnchorResult(
        anchor=anchor, status=status, baseline=base_rev, head=head_rev,
        baseline_digest=base_hash, head_digest=head_hash,
        detail="tree hash comparison",
    )


def _relocate(
    repo: Path, anchor: Anchor, base_rev: str, head_rev: str
) -> tuple[str | None, str]:
    """Find where the anchored code went when git's rename detection missed it.

    Git decides a rename by content similarity, default 50%. A move combined
    with a large edit falls under that and is reported as add + delete, so the
    anchor cannot follow it and reports ``missing`` - the blocking status. The
    M1 measurement hit this on three Go files where rewriting the doc comments
    cut the file from 510 bytes to 161 and git measured 13% similarity
    (docs/measurements/M1-anchor-stability.md section 3.1).

    Lowering the threshold globally was rejected: it trades a visible false
    positive for invisible wrong matches between unrelated files. Instead this
    searches by *content identity* rather than similarity - a candidate is only
    accepted when its fingerprint matches the baseline exactly, and only when
    the match is unique. An ambiguous or absent match stays ``missing``.

    Returns ``(head_path, detail)``; head_path is None when nothing matched.
    """
    base_blob = gitio.blob_at(repo, base_rev, anchor.path)
    if base_blob is None:
        return None, ""

    if anchor.symbol:
        base_sym = find_symbol(base_blob, anchor.path, anchor.symbol)
        if base_sym is None:
            return None, ""
        # git grep is a C implementation over the tree; this is far cheaper than
        # parsing every file at head.
        candidates = gitio.grep_files_at(repo, head_rev, anchor.symbol.split(".")[-1])
        exact, loose = [], []
        for candidate in candidates:
            blob = gitio.blob_at(repo, head_rev, candidate)
            if blob is None:
                continue
            found = find_symbol(blob, candidate, anchor.symbol)
            if found is None:
                continue
            if found.full_digest == base_sym.full_digest:
                exact.append(candidate)
            elif found.signature_digest == base_sym.signature_digest:
                loose.append(candidate)
        matches, kind = (exact, "identical") if exact else (loose, "matching-signature")
        if len(matches) == 1:
            return matches[0], f"relocated by {kind} content to {matches[0]}"
        if len(matches) > 1:
            return None, f"relocation ambiguous: {len(matches)} candidates at head"
        return None, ""

    base_digest, _coarse = fingerprint_source(base_blob, anchor.path)
    basename = anchor.path.rsplit("/", 1)[-1]
    matches = []
    for candidate in gitio.list_files_at(repo, head_rev):
        if candidate.rsplit("/", 1)[-1] != basename:
            continue
        blob = gitio.blob_at(repo, head_rev, candidate)
        if blob is None:
            continue
        if fingerprint_source(blob, candidate)[0] == base_digest:
            matches.append(candidate)
    if len(matches) == 1:
        return matches[0], f"relocated by identical content to {matches[0]}"
    if len(matches) > 1:
        return None, f"relocation ambiguous: {len(matches)} candidates at head"
    return None, ""


def _classify_file(repo: Path, anchor: Anchor, base_rev: str, head_rev: str) -> AnchorResult:
    relocated_detail = ""
    head_path, _ = gitio.resolve_path_at(
        repo, anchor.path, target_rev=head_rev, other_rev=base_rev
    )
    if head_path is None:
        head_path, relocated_detail = _relocate(repo, anchor, base_rev, head_rev)
    if head_path is None:
        return AnchorResult(
            anchor=anchor, status=Status.MISSING, baseline=base_rev, head=head_rev,
            detail=relocated_detail
            or f"{anchor.path} does not exist at head under any followed name",
        )

    if relocated_detail:
        # We found the file by content, not by git's rename detection, so git
        # cannot map it back either. The baseline path is the anchor's own.
        base_path = anchor.path
    else:
        base_path, _ = gitio.resolve_path_at(
            repo, head_path, target_rev=base_rev, other_rev=head_rev
        )
    if base_path is None:
        return AnchorResult(
            anchor=anchor, status=Status.MISSING, baseline=base_rev, head=head_rev,
            head_path=head_path,
            detail=f"{anchor.path} did not exist at the baseline; the anchor postdates its @sha",
        )

    base_blob = gitio.blob_at(repo, base_rev, base_path)
    head_blob = gitio.blob_at(repo, head_rev, head_path)
    if base_blob is None or head_blob is None:
        return AnchorResult(
            anchor=anchor, status=Status.MISSING, baseline=base_rev, head=head_rev,
            detail="path resolved to a tree, not a blob",
        )

    result = AnchorResult(
        anchor=anchor, status=Status.FRESH, baseline=base_rev, head=head_rev,
        baseline_path=base_path, head_path=head_path,
        relocated=bool(relocated_detail),
    )

    if anchor.symbol:
        base_sym = find_symbol(base_blob, base_path, anchor.symbol)
        head_sym = find_symbol(head_blob, head_path, anchor.symbol)
        if base_sym is not None and head_sym is not None:
            result.baseline_digest = base_sym.full_digest
            result.head_digest = head_sym.full_digest
            result.detail = f"symbol {anchor.symbol} ({head_sym.node_type})"
            if base_sym.full_digest == head_sym.full_digest:
                result.status = Status.FRESH
            elif base_sym.signature_digest == head_sym.signature_digest:
                result.status = Status.SHIFTED
            else:
                result.status = Status.STALE
            return result

        # The symbol could not be located on at least one side. If its name has
        # vanished from the file entirely, it really is gone. Otherwise this is a
        # limit of our declaration table, not a change in the code, and reporting
        # `missing` (a blocking status) would poison the ledger.
        if not symbol_appears_textually(head_blob, anchor.symbol):
            result.status = Status.MISSING
            result.detail = f"symbol {anchor.symbol} not found at head"
            return result
        result.symbol_unresolved = True
        result.detail = (
            f"symbol {anchor.symbol} present but not resolvable by the declaration "
            f"table; compared the whole file instead"
        )

    base_digest, base_coarse = fingerprint_source(base_blob, base_path)
    head_digest, head_coarse = fingerprint_source(head_blob, head_path)
    result.coarse = base_coarse or head_coarse
    result.baseline_digest = base_digest
    result.head_digest = head_digest
    if not result.detail:
        result.detail = "whole-file comparison" + (" (coarse)" if result.coarse else "")
    result.status = Status.FRESH if base_digest == head_digest else Status.STALE
    return result


# ---------------------------------------------------------------------------
# The store-wide scan
# ---------------------------------------------------------------------------
#
# `classify` answers the question for one anchor the caller already knows
# about. That is the wrong shape for every real consumer: the ledger, `forge
# verify` and a pre-commit hook all need the set of claims whose code has
# moved, and none of them can name the anchors in advance. This is the loop
# that turns the per-anchor engine M1 measured into that set.
#
# Nothing here re-implements anchor parsing or classification. A second parser
# that disagreed slightly with `parse_anchor` about what an anchor is would be
# a silent hole in exactly the mechanism this file exists to make trustworthy.

#: Worst-first. The reducer below picks the maximum, so the order is the
#: definition of "worse" and lives in exactly one place.
_SEVERITY = {Status.FRESH: 0, Status.SHIFTED: 1, Status.STALE: 2, Status.MISSING: 3}


@dataclass
class ClaimDrift:
    """One claim's drift: the worst status among its anchors, and the why.

    Reported per claim rather than per anchor because a human acts on claims.
    A five-anchor claim reported as five findings is five decisions about one
    question, and a report nobody finishes reading is the failure mode
    OPEN_QUESTIONS.md Q10 says kills a knowledge harness.
    """
    claim_id: str
    kind: str
    title: str
    file: str
    line: int
    #: Whether this claim's staleness is somebody's obligation. False for a
    #: candidate - nobody has agreed to it yet - and for a retired claim,
    #: which describes something the project has stopped asserting. Both are
    #: still scanned and reported; neither fails the command.
    obligating: bool
    results: list[AnchorResult]
    #: (anchor text, message) for anchors that could not be classified at all.
    errors: list[tuple[str, str]]

    @property
    def status(self) -> Status | None:
        """The worst status among the anchors, or None if there are none."""
        if not self.results:
            return None
        return max((r.status for r in self.results), key=lambda s: _SEVERITY[s])

    @property
    def changed(self) -> bool:
        return any(r.changed for r in self.results) or bool(self.errors)

    @property
    def culprits(self) -> list[AnchorResult]:
        """Only the anchors that produced the worst status."""
        worst = self.status
        return [r for r in self.results if r.status is worst] if worst else []

    def to_dict(self) -> dict:
        return {
            "claim": self.claim_id,
            "kind": self.kind,
            "title": self.title,
            "defined_in": f"{self.file}:{self.line}",
            "obligating": self.obligating,
            "status": self.status.value if self.status else None,
            "changed": self.changed,
            "anchors": [r.to_dict() for r in self.results],
            "errors": [{"anchor": a, "message": m} for a, m in self.errors],
        }


def _anchor_touches(anchor: Anchor, paths: frozenset[str]) -> bool:
    """Whether *anchor* points inside *paths*, a set of repo-relative files."""
    if anchor.is_dir:
        prefix = anchor.path if anchor.path.endswith("/") else anchor.path + "/"
        return any(p.startswith(prefix) for p in paths)
    return anchor.path in paths


def classify_store(
    repo: Path,
    *,
    head: str = "HEAD",
    paths: frozenset[str] | None = None,
) -> list[ClaimDrift]:
    """Classify every anchor of every claim in the store, grouped by claim.

    *paths* narrows the scan to claims with at least one anchor inside that set
    of repo-relative files - the form a pre-commit hook can afford, since it
    fingerprints only what the diff touched. A claim with no matching anchor is
    not classified and does not appear in the result at all; that is the
    difference between "checked and fine" and "not checked", and collapsing the
    two is how a cheap scan starts reading like a complete one.

    A malformed anchor is recorded in the claim's ``errors`` and the walk
    continues. `trace.py` settled this rule for the index and it holds here for
    the same reason: whether an anchor is well-formed is `forge check`'s
    question, and a scan that dies on one bad anchor says nothing about the
    other thirty-nine.

    This function opens no file for writing. Reporting drift and resolving it
    are separate acts and only the second one is a human's.
    """
    from . import store as _store   # local: store imports nothing from forge,
                                    # but keeping the edge out of module scope
                                    # keeps anchor.py loadable on its own.

    out: list[ClaimDrift] = []
    for claim in _store.load_store(repo):
        results: list[AnchorResult] = []
        errors: list[tuple[str, str]] = []
        matched = False
        for text in claim.anchors:
            if not text.strip():
                continue
            try:
                anchor = parse_anchor(text)
            except AnchorError as exc:
                # An unparseable anchor cannot be filtered by path either, so
                # it is reported whatever `paths` says: silently dropping it
                # under `--changed` would hide a real defect behind a flag.
                errors.append((text, str(exc)))
                matched = True
                continue
            if paths is not None and not _anchor_touches(anchor, paths):
                continue
            matched = True
            try:
                results.append(classify(repo, anchor, head=head))
            except (AnchorError, gitio.GitError, gitio.InvalidRevision) as exc:
                # A claim whose @sha names a commit this clone does not have -
                # a shallow checkout, or a rebased branch - is a fact about the
                # scan, not about the code. It is recorded and the walk goes on.
                errors.append((text, str(exc)))
        if paths is not None and not matched:
            continue
        out.append(ClaimDrift(
            claim_id=claim.id,
            kind=claim.kind,
            title=claim.title,
            file=claim.file,
            line=claim.line,
            obligating=not claim.is_candidate and claim.status != "retired",
            results=results,
            errors=errors,
        ))
    return out
