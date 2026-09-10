"""M1 measurement: how noisy is anchor-based staleness detection on real history?

MVP.md gates M2-M5 on this number. The design bets that a claim anchored to
`path#Symbol@sha` can be checked mechanically without drowning a reviewer in
false positives. If a routine refactor produces fifteen spurious drift entries,
the ledger becomes noise and gets ignored - and an ignored ledger is worse than
no ledger, because it looks like coverage.

**How "spurious" is decided.** Not by judgement. Two classes of false positive
have mechanical ground truth, and those are the two this harness measures:

* **formatting** - git itself says the file changed only by whitespace
  (``git diff --ignore-all-space --ignore-blank-lines`` is empty). A reviewer
  sent to look at that has nothing to see, so any non-fresh verdict is wrong.
* **rename** - git's similarity detection reports ``R100``: the file moved with
  its content byte-identical. Any non-fresh verdict is wrong.

Deliberately *not* measured, because there is no ground truth without a human:
comment-only edits inside an otherwise-changed file, and semantically neutral
refactors (extract variable, reorder independent statements). Those are
excluded from the false-positive rates and the limitation is reported with the
result rather than hidden by it.

Usage::

    python tools/measure_anchors.py --repo ../some-repo --commits 200 --anchors 30
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forge import gitio  # noqa: E402
from forge.anchor import Anchor, Status, classify  # noqa: E402
from forge.fingerprint import (  # noqa: E402
    _iter_declarations,
    grammar_for_path,
    language_for_path,
)

# Directories whose churn says nothing about a hand-maintained codebase.
_SKIP_SEGMENTS = {
    "node_modules", "vendor", "dist", "build", ".venv", "venv",
    "__pycache__", "third_party", "testdata", "fixtures", "generated",
}


def _interesting(path: str) -> bool:
    if language_for_path(path) is None:
        return False
    parts = path.split("/")
    return not any(seg in _SKIP_SEGMENTS for seg in parts)


@dataclass
class TrackedAnchor:
    anchor: Anchor            # follows renames as the replay advances
    original: Anchor          # as written at the base commit, never mutated
    language: str
    alive: bool = True
    retired_at: str | None = None
    retired_reason: str = ""
    history: list[dict] = field(default_factory=list)


def list_files(repo: Path, rev: str) -> list[str]:
    out = gitio.git(repo, "ls-tree", "-r", "--name-only", gitio.validate_rev(rev))
    return [line.strip() for line in out.splitlines() if line.strip()]


def touched_paths(repo: Path, rev: str) -> tuple[set[str], dict[str, int]]:
    """Paths touched by a commit, plus similarity scores for renames.

    Both sides of a rename are returned, so an anchor still holding the old name
    is recognised as affected by the commit that moved it.
    """
    out = gitio.git(
        repo, "show", "--first-parent", "-M", "--name-status", "--format=",
        gitio.validate_rev(rev), check=False,
    )
    paths: set[str] = set()
    renames: dict[str, int] = {}
    for line in out.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            similarity = int(status[1:] or 0)
            old, new = parts[1], parts[2]
            paths.update({old, new})
            renames[new] = similarity
            renames[old] = similarity
        else:
            paths.add(parts[1])
    return paths, renames


def pick_anchors(
    repo: Path,
    base_rev: str,
    churned: Counter[str],
    *,
    count: int,
    rng: random.Random,
) -> list[TrackedAnchor]:
    """Select anchors at *base_rev*, biased toward files that actually change.

    Anchoring only to quiet files would measure nothing: every verdict would be
    ``fresh`` and the false-positive rate would be trivially zero. Biasing
    toward churn measures the population a real claim store cares about, and
    that bias is stated in the report rather than buried.
    """
    candidates = [p for p in list_files(repo, base_rev) if _interesting(p)]
    candidates.sort(key=lambda p: (-churned.get(p, 0), p))
    hot = [p for p in candidates if churned.get(p, 0) > 0]
    cold = [p for p in candidates if churned.get(p, 0) == 0]
    rng.shuffle(cold)
    ordered = hot + cold

    picked: list[TrackedAnchor] = []
    for path in ordered:
        if len(picked) >= count:
            break
        grammar = grammar_for_path(path)
        lang = language_for_path(path)
        if grammar is None or lang is None:
            continue
        blob = gitio.blob_at(repo, base_rev, path)
        if blob is None or len(blob) > 400_000:
            continue
        try:
            from tree_sitter import Parser

            tree = Parser(grammar.language).parse(blob)
            names = [
                name for name, node in _iter_declarations(tree.root_node, lang)
                if node.end_byte - node.start_byte > 40  # skip one-line stubs
            ]
        except Exception:
            continue
        if not names:
            continue
        symbol = names[min(len(names) - 1, rng.randrange(0, min(3, len(names))))]
        chosen = Anchor(path=path, symbol=symbol, sha=None, raw=f"{path}#{symbol}")
        picked.append(TrackedAnchor(anchor=chosen, original=chosen, language=lang))
    return picked


def measure(repo: Path, *, commits: int, anchors: int, seed: int) -> dict:
    rng = random.Random(seed)
    started = time.time()

    revs = gitio.rev_list(repo, head="HEAD", count=commits + 1, reverse=True)
    if len(revs) < 3:
        raise SystemExit(f"{repo} has too little history ({len(revs)} commits)")
    base_rev, *rest = revs

    # Which files change during the window? Used only to bias anchor selection.
    churn: Counter[str] = Counter()
    step_touched: list[tuple[str, set[str], dict[str, int]]] = []
    for rev in rest:
        paths, renames = touched_paths(repo, rev)
        step_touched.append((rev, paths, renames))
        for p in paths:
            if _interesting(p):
                churn[p] += 1

    tracked = pick_anchors(repo, base_rev, churn, count=anchors, rng=rng)
    if not tracked:
        raise SystemExit(f"{repo}: no anchorable declarations found at {base_rev[:8]}")

    per_step = Counter()
    fp_formatting = 0
    fp_formatting_pop = 0
    fp_rename = 0
    fp_rename_pop = 0
    errors = 0
    evaluations = 0
    touching_steps = 0

    previous = base_rev
    for rev, paths, renames in step_touched:
        step_hit = False
        for item in tracked:
            if not item.alive:
                continue
            path = item.anchor.path
            if path not in paths:
                continue
            step_hit = True
            evaluations += 1

            whitespace_only = gitio.diff_is_whitespace_only(repo, previous, rev, path)
            pure_rename = renames.get(path, 0) == 100

            try:
                result = classify(repo, item.anchor, baseline=previous, head=rev)
            except Exception as exc:  # a broken file or an unreadable blob
                errors += 1
                item.history.append({"rev": rev, "error": str(exc)[:200]})
                continue

            per_step[result.status.value] += 1
            item.history.append({
                "rev": rev,
                "status": result.status.value,
                "whitespace_only": whitespace_only,
                "pure_rename": pure_rename,
                "detail": result.detail,
            })

            if whitespace_only:
                fp_formatting_pop += 1
                if result.status is not Status.FRESH:
                    fp_formatting += 1
            if pure_rename:
                fp_rename_pop += 1
                if result.status is not Status.FRESH:
                    fp_rename += 1

            if result.status is Status.MISSING:
                item.alive = False
                item.retired_at = rev
                item.retired_reason = result.detail
            elif result.moved:
                # Follow the move so later steps compare the right file.
                new_path, _ = gitio.resolve_path_at(
                    repo, path, target_rev=rev, other_rev=previous
                )
                if new_path and new_path != path:
                    item.anchor = Anchor(
                        path=new_path, symbol=item.anchor.symbol,
                        sha=None, raw=f"{new_path}#{item.anchor.symbol}",
                    )
        if step_hit:
            touching_steps += 1
        previous = rev

    # Cumulative view: what a ledger sees when the baseline is the last human
    # confirmation, many commits back.
    head_rev = revs[-1]
    cumulative = Counter()
    for item in tracked:
        try:
            res = classify(repo, item.original, baseline=base_rev, head=head_rev)
            cumulative[res.status.value] += 1
        except Exception:
            cumulative["error"] += 1

    noisy = per_step["stale"] + per_step["missing"]
    return {
        "repo": str(repo),
        "head": head_rev,
        "base": base_rev,
        "seed": seed,
        "elapsed_seconds": round(time.time() - started, 1),
        "commits_replayed": len(step_touched),
        "commits_touching_an_anchor": touching_steps,
        "anchors": len(tracked),
        "anchors_by_language": dict(Counter(t.language for t in tracked)),
        "anchor_list": [str(t.original) for t in tracked],
        "evaluations": evaluations,
        "errors": errors,
        "per_step_status": dict(per_step),
        "retired": [
            {"anchor": str(t.anchor), "at": t.retired_at, "why": t.retired_reason}
            for t in tracked if not t.alive
        ],
        "false_positives": {
            "formatting": {"population": fp_formatting_pop, "false_positive": fp_formatting},
            "rename": {"population": fp_rename_pop, "false_positive": fp_rename},
        },
        "noise_rate": {
            "stale_or_missing_per_touching_commit": (
                round(noisy / touching_steps, 3) if touching_steps else 0.0
            ),
            "shifted_per_touching_commit": (
                round(per_step["shifted"] / touching_steps, 3) if touching_steps else 0.0
            ),
        },
        "cumulative_from_base": dict(cumulative),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--commits", type=int, default=200)
    parser.add_argument("--anchors", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        raise SystemExit(f"{repo} is not a git repository")

    report = measure(repo, commits=args.commits, anchors=args.anchors, seed=args.seed)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    fp = report["false_positives"]
    print(f"repo                      {report['repo']}")
    print(f"commits replayed          {report['commits_replayed']} "
          f"({report['commits_touching_an_anchor']} touched an anchor)")
    print(f"anchors                   {report['anchors']} {report['anchors_by_language']}")
    print(f"evaluations               {report['evaluations']} (errors {report['errors']})")
    print(f"per-step verdicts         {report['per_step_status']}")
    print(f"formatting-only changes   {fp['formatting']['population']} "
          f"-> false positives {fp['formatting']['false_positive']}")
    print(f"pure renames (R100)       {fp['rename']['population']} "
          f"-> false positives {fp['rename']['false_positive']}")
    print(f"stale+missing / touching  {report['noise_rate']['stale_or_missing_per_touching_commit']}")
    print(f"shifted / touching        {report['noise_rate']['shifted_per_touching_commit']}")
    print(f"cumulative base..head     {report['cumulative_from_base']}")
    print(f"retired mid-replay        {len(report['retired'])}")
    print(f"elapsed                   {report['elapsed_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
