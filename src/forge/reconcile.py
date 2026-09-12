"""The recovery path: what happened to the store while nobody was looking.

OPEN_QUESTIONS.md Q10 recommends two things and the pre-commit hook is only the
first. The hook catches drift as it is created, and it **will** be bypassed -
`--no-verify`, a colleague's commits, a dependency bot, a branch merged from
somewhere else, or a repository that adopts the harness after years of history.
Q10 is explicit that the hook needs a recovery path beside it, because the
alternative is the wall of findings that ends in harness bankruptcy.

What this adds over `forge drift --store`, which already reports every stale
claim: **attribution**. A scan says a claim is stale. Only the history says
which commit did it and what that commit thought it was doing - and a reviewer
choosing between "the code is wrong" and "the decision changed" is asking
precisely that question. A list of forty stale claims is a wall; the same forty
with "changed by `a1b2c3d`, *fix: stop clamping refunds*" beside them is a
review.

It records nothing by default. Reading a range and writing to the ledger are
different acts, and the second one is somebody deciding to take the backlog on.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path

from . import anchor, gitio, ledger

__all__ = ["Cause", "Reconciliation", "reconcile"]


@dataclass
class Cause:
    """One claim's drift, and the commits in range that reached its anchors."""
    drift: anchor.ClaimDrift
    commits: list[tuple[str, str, str]] = field(default_factory=list)
    recorded: str | None = None      # the ledger entry id, if one is open

    @property
    def claim_id(self) -> str:
        return self.drift.claim_id

    @property
    def authors(self) -> list[str]:
        """Distinct authors, in the order the commits are reported."""
        seen: list[str] = []
        for _, author, _ in self.commits:
            if author not in seen:
                seen.append(author)
        return seen

    def to_dict(self) -> dict:
        return {
            **self.drift.to_dict(),
            "recorded": self.recorded,
            "commits": [{"sha": s, "author": a, "subject": m}
                        for s, a, m in self.commits],
        }


@dataclass
class Reconciliation:
    base: str
    head: str
    causes: list[Cause]
    #: Claims that are stale with no commit in range to blame. Reported apart,
    #: because "this drifted before the window you asked about" is a different
    #: answer from "nobody touched it" and sending a reviewer to look for a
    #: cause that is not there wastes the attention this command exists to save.
    unattributed: list[Cause] = field(default_factory=list)
    #: Claims nothing could be said about - an anchor with no `@sha`, a commit
    #: this clone does not have. Not drift, and not a reviewer's problem.
    unclassifiable: list[Cause] = field(default_factory=list)

    @property
    def obligating(self) -> list[Cause]:
        return [c for c in self.causes if c.drift.obligating]

    def to_dict(self) -> dict:
        return {
            "base": self.base,
            "head": self.head,
            "causes": [c.to_dict() for c in self.causes],
            "unattributed": [c.to_dict() for c in self.unattributed],
            "unclassifiable": [c.to_dict() for c in self.unclassifiable],
        }


def _anchor_paths(drift: anchor.ClaimDrift) -> list[str]:
    paths: list[str] = []
    for result in drift.results:
        path = result.anchor.path.rstrip("/")
        if path and path not in paths:
            paths.append(path)
        # A file that moved is two paths to ask the history about: the name it
        # has now, and the name the commit that moved it used.
        for moved in (result.baseline_path, result.head_path):
            if moved and moved not in paths:
                paths.append(moved)
    return paths


def reconcile(repo: Path, base: str, head: str = "HEAD") -> Reconciliation:
    """Every claim not fresh at *head*, with the commits in range that caused it.

    The scan is against *head*, not against the range: a claim is stale or it is
    not, and the range only explains why. Asking the other way round - which
    claims did this range touch - would report a claim whose anchor was edited
    and then edited back, which is a claim that is fine.
    """
    base = gitio.rev_parse(repo, base)
    head_sha = gitio.rev_parse(repo, head)
    open_by_claim = {e.claim: e.id for e in ledger.open_entries(repo)}

    causes: list[Cause] = []
    unattributed: list[Cause] = []
    unclassifiable: list[Cause] = []
    for drift in anchor.classify_store(repo, head=head):
        if not drift.changed:
            continue
        # A claim whose anchors could not be classified at all has not drifted;
        # nothing is known about it either way. Every candidate carries this,
        # because a candidate is never stamped with a `@sha` - so without the
        # split, the four candidates a review rejected would appear in every
        # reconcile from now until somebody deleted them, under a heading that
        # said they had drifted.
        if not drift.results and drift.errors:
            unclassifiable.append(Cause(drift=drift, commits=[]))
            continue
        commits = gitio.commits_touching(repo, base, head_sha, _anchor_paths(drift))
        cause = Cause(drift=drift, commits=commits,
                      recorded=open_by_claim.get(drift.claim_id))
        (causes if commits else unattributed).append(cause)
    return Reconciliation(base=base, head=head_sha, causes=causes,
                          unattributed=unattributed, unclassifiable=unclassifiable)


def record(repo: Path, result: Reconciliation, *,
           today: _dt.date | None = None) -> list[ledger.Entry]:
    """Open a ledger entry for every obligating claim that has none.

    Delegated to `ledger.record` rather than reimplemented, so a batch from a
    range and a single entry from a hook are the same kind of thing and carry
    the same fields. `ledger.record` is idempotent by claim, which is what makes
    running this twice on an overlapping range safe.
    """
    # `unclassifiable` is excluded: an entry saying "we could not tell" is an
    # open item nobody can close, which is how a ledger stops being read.
    wanted = result.causes + result.unattributed
    drifts = [c.drift for c in wanted]
    causes = {c.claim_id: [f"{sha[:10]} {author} - {subject}"
                           for sha, author, subject in c.commits]
              for c in wanted if c.commits}
    return ledger.record(repo, drifts, today=today, causes=causes)
