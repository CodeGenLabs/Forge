"""The kernel's command surface, as far as M1 needs it.

Scope note: [MVP.md](../../MVP.md) lists a larger `forge drift` that reads anchors out of the claim
store. The store is M0 and was skipped, so this exposes the anchor engine
directly — enough to check the milestone by hand and to script against, and no
more. `drift resolve`, `drift waive` and `reanchor` need the store and the
ledger, so they are not here yet.

The kernel never calls a language model. Every output is reproducible from the
repository at a commit, which is what makes gates built on it trustworthy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import gitio
from .anchor import AnchorError, Status, classify, parse_anchor
from .fingerprint import available_languages, fingerprint_source

_EXIT_OK = 0
_EXIT_CHANGED = 1      # a drift signal, not an error - scriptable as a gate
_EXIT_USAGE = 2


def _cmd_drift(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    results = []
    for raw in args.anchor:
        try:
            anchor = parse_anchor(raw)
            result = classify(repo, anchor, baseline=args.baseline, head=args.head)
        except (AnchorError, gitio.GitError, gitio.InvalidRevision, gitio.InvalidPath) as exc:
            print(f"forge: {raw}: {exc}", file=sys.stderr)
            return _EXIT_USAGE
        results.append(result)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        width = max((len(str(r.anchor)) for r in results), default=0)
        for r in results:
            flags = []
            if r.coarse:
                flags.append("coarse")
            if r.symbol_unresolved:
                flags.append("symbol-unresolved")
            if r.moved:
                flags.append(f"moved {r.baseline_path} -> {r.head_path}")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            print(f"{str(r.anchor):{width}}  {r.status.value:8}  {r.detail}{suffix}")

    changed = [r for r in results if r.status is not Status.FRESH]
    if changed and not args.json:
        hard = [r for r in changed if r.status in (Status.STALE, Status.MISSING)]
        print(
            f"\n{len(results)} anchor(s): {len(results) - len(changed)} fresh, "
            f"{len(changed) - len(hard)} shifted, {len(hard)} needing a verdict",
            file=sys.stderr,
        )
    return _EXIT_CHANGED if changed else _EXIT_OK


def _cmd_fingerprint(args: argparse.Namespace) -> int:
    for path in args.path:
        try:
            source = path.read_bytes()
        except OSError as exc:
            print(f"forge: {path}: {exc}", file=sys.stderr)
            return _EXIT_USAGE
        digest, coarse = fingerprint_source(source, path.as_posix())
        print(f"{digest}  {'coarse' if coarse else 'ast   '}  {path}")
    return _EXIT_OK


def _cmd_doctor(args: argparse.Namespace) -> int:
    langs = available_languages()
    print(f"python           {sys.version.split()[0]}")
    print(f"grammars         {', '.join(langs) if langs else 'none (all anchors will be coarse)'}")
    try:
        version = gitio.git(Path.cwd(), "--version").strip()
    except gitio.GitError as exc:
        print(f"git              unavailable: {exc}")
        return _EXIT_USAGE
    print(f"git              {version.removeprefix('git version ')}")
    return _EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="forge",
        description="Anchored system knowledge with deterministic staleness detection.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    drift = sub.add_parser(
        "drift",
        help="classify anchors between two revisions",
        description="Exit code 0 when every anchor is fresh, 1 when any is not, "
                    "2 on a usage error - so it composes as a gate.",
    )
    drift.add_argument("anchor", nargs="+", help="path[#Symbol][@sha]")
    drift.add_argument("--repo", type=Path, default=Path.cwd())
    drift.add_argument("--baseline", help="overrides each anchor's @sha")
    drift.add_argument("--head", default="HEAD")
    drift.add_argument("--json", action="store_true")
    drift.set_defaults(func=_cmd_drift)

    fp = sub.add_parser("fingerprint", help="print the normalised fingerprint of a file")
    fp.add_argument("path", nargs="+", type=Path)
    fp.set_defaults(func=_cmd_fingerprint)

    doctor = sub.add_parser("doctor", help="report the toolchain the kernel found")
    doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
