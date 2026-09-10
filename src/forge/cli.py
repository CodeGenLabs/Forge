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

from . import derive, gitio, trace
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
                how = "relocated by content" if r.relocated else "moved"
                flags.append(f"{how} {r.baseline_path} -> {r.head_path}")
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


def _cmd_sync(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    changed = derive.derive_all(repo, only=args.only or None)
    for name, was_changed in changed.items():
        print(f"{'updated' if was_changed else 'unchanged'}  {derive.DERIVED_DIR}/{name}")
    if any(changed.values()):
        # The tier is derived from HEAD, so its content describes HEAD and it
        # must land in a commit of its own. Folded into the code commit it would
        # describe that commit's *parent* - stale the moment it is written, and
        # `forge check` would say so. A derived-only commit is also excluded
        # from the staleness count, so the steady state stays clean.
        print("\nCommit these on their own, after the code commit they describe:")
        print(f"  git add {derive.DERIVED_DIR} && git commit -m 'chore: sync derived tier'")
    return _EXIT_OK


def _cmd_trace(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    entry = trace.lookup(repo, args.id)
    if entry is None:
        print(f"forge: {args.id} is not in the index", file=sys.stderr)
        return _EXIT_CHANGED
    if args.json:
        print(json.dumps(entry, indent=2, sort_keys=True))
        return _EXIT_OK

    print(f"{entry['id']}  {entry.get('kind') or 'unknown'}"
          f"{'  [candidate]' if entry.get('candidate') else ''}")
    if entry.get("title"):
        print(f"  {entry['title']}")
    _print_rows([
        ("defined in", [entry["defined_in"]] if entry.get("defined_in") else []),
        ("status", [entry["status"]] if entry.get("status") else []),
        ("anchors", entry.get("anchors") or []),
        ("evidence", entry.get("evidence") or []),
        ("governs", entry.get("governs") or []),
        ("governed by", entry.get("governed_by") or []),
        ("since", [entry["since"]] if entry.get("since") else []),
        ("justifies", entry.get("justifies") or []),
        ("supersedes", [entry["supersedes"]] if entry.get("supersedes") else []),
        ("referenced by", entry.get("referenced_by_adr") or []),
        ("tests", entry.get("tests") or []),
        ("back-references", entry.get("back_references") or []),
        ("changes", entry.get("changes") or []),
    ])
    if entry.get("defined_in") is None:
        print("\n  This ID is referenced but never defined.", file=sys.stderr)
        return _EXIT_CHANGED
    return _EXIT_OK


def _print_rows(rows: list[tuple[str, list[str]]]) -> None:
    for label, values in rows:
        if not values:
            continue
        print(f"  {label + ':':17} {values[0]}")
        for extra in values[1:]:
            print(f"  {'':17} {extra}")


def _cmd_status(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    head = gitio.rev_parse(repo, "HEAD")
    print(f"repository       {repo.name} @ {head[:10]}")

    # Content decides freshness; the commit stamp is provenance shown alongside
    # it. Comparing content is exact, and it is the only comparison that can
    # ever come out clean for a file that is itself committed.
    staleness = derive.stale_artifacts(repo)
    missing = [n for n, v in staleness.items() if v is None]
    outdated = [n for n, changed in derive.derive_all(repo, dry_run=True).items() if changed]
    if missing:
        state = f"{len(missing)} not built; run `forge sync derived`"
    elif outdated:
        state = f"{len(outdated)} stale; run `forge sync derived`"
    else:
        behind = max((v for v in staleness.values() if v is not None), default=0)
        age = f", derived {behind} commit{'s' if behind != 1 else ''} back" if behind else ""
        state = f"current{age}"
    print(f"derived tier     {state}")

    index = (derive.read_json(repo / derive.DERIVED_DIR / trace.TRACE_FILE) or {}).get("data")
    if not index:
        print("claim store      no index; run `forge sync derived`")
        return _EXIT_OK
    summary = index.get("summary", {})
    print(f"claims           {summary.get('claims', 0)} ratified, "
          f"{summary.get('candidates', 0)} candidate, "
          f"{summary.get('decisions', 0)} ADRs")
    print(f"tests            {summary.get('tests_total', 0)} total, "
          f"{summary.get('tests_tagged', 0)} tagged with @covers")

    problems = 0
    for label, key in (
        ("dangling refs", "dangling_references"),
        ("invariants without tests", "invariants_without_tests"),
    ):
        items = summary.get(key) or []
        if items:
            problems += len(items)
            print(f"{label:16} {len(items)}: {', '.join(items[:6])}"
                  f"{' ...' if len(items) > 6 else ''}")
    if not problems:
        print("open items       none")
    return _EXIT_OK


def _cmd_check(args: argparse.Namespace) -> int:
    """Deterministic checks, as far as the milestones so far allow.

    Scope note: MVP.md lists 39 checks across the store, the change DAG and
    verification. The claim store is M0 and the change DAG is M3, so this runs
    the subset that has something to check today - and says which those are,
    rather than reporting a clean bill of health for checks that do not exist.
    """
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    issues: list[dict] = []

    dirty = [n for n, changed in derive.derive_all(repo, dry_run=True).items() if changed]
    for name in dirty:
        issues.append({
            "level": "ERROR", "code": "derived.dirty",
            "path": f"{derive.DERIVED_DIR}/{name}",
            "message": "regenerating produces different bytes; it was hand-edited or is stale",
            "fix": "forge sync derived",
        })

    index = (derive.read_json(repo / derive.DERIVED_DIR / trace.TRACE_FILE) or {}).get("data")
    if index is None:
        issues.append({
            "level": "ERROR", "code": "derived.missing",
            "path": f"{derive.DERIVED_DIR}/{trace.TRACE_FILE}",
            "message": "the trace index has not been built",
            "fix": "forge sync derived",
        })
    else:
        ids = index.get("ids", {})
        for identifier in index.get("summary", {}).get("dangling_references", []):
            entry = ids.get(identifier, {})
            where = (entry.get("back_references") or entry.get("tests")
                     or entry.get("changes") or ["unknown"])
            issues.append({
                "level": "ERROR", "code": "trace.dangling_reference",
                "path": where[0],
                "message": f"{identifier} is referenced but no claim or ADR defines it",
                "fix": f"define {identifier} in the store, or remove the reference",
            })
        for identifier, entry in sorted(ids.items()):
            if entry.get("candidate"):
                continue
            for target in entry.get("governs") or []:
                if ids.get(target, {}).get("candidate"):
                    issues.append({
                        "level": "ERROR", "code": "store.ratified_points_at_candidate",
                        "path": entry.get("defined_in") or identifier,
                        "message": f"{identifier} governs {target}, which is only a candidate",
                        "fix": f"forge ratify {target}, or drop the reference",
                    })

    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    else:
        for issue in issues:
            print(f"{issue['level']}  {issue['code']}  {issue['path']}\n"
                  f"       {issue['message']}\n       fix: {issue['fix']}")
        checked = "derived-tier freshness, trace integrity"
        pending = "claim schema (M0), change DAG and coverage (M3)"
        if issues:
            print(f"\n{len(issues)} issue(s). Checked: {checked}.", file=sys.stderr)
        else:
            # Both lines on stdout so they stay in order. A clean report that
            # does not say what it declined to check is a clean report nobody
            # should trust.
            print(f"ok - no issues. Checked: {checked}.")
            print(f"Not yet checked: {pending}.")
    return _EXIT_CHANGED if issues else _EXIT_OK


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

    sync = sub.add_parser("sync", help="regenerate machine-owned artifacts")
    sync_sub = sync.add_subparsers(dest="target", required=True)
    sync_derived = sync_sub.add_parser("derived", help="rebuild the derived tier")
    sync_derived.add_argument("--repo", type=Path, default=Path.cwd())
    sync_derived.add_argument("--only", action="append", metavar="FILE",
                              help="rebuild just this artifact; repeatable")
    sync_derived.set_defaults(func=_cmd_sync)

    tr = sub.add_parser("trace", help="what references this ID, and what it references")
    tr.add_argument("id")
    tr.add_argument("--repo", type=Path, default=Path.cwd())
    tr.add_argument("--json", action="store_true")
    tr.set_defaults(func=_cmd_trace)

    status = sub.add_parser("status", help="one screen: freshness, store size, open items")
    status.add_argument("--repo", type=Path, default=Path.cwd())
    status.set_defaults(func=_cmd_status)

    check = sub.add_parser("check", help="run the deterministic checks that exist today")
    check.add_argument("--repo", type=Path, default=Path.cwd())
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=_cmd_check)

    doctor = sub.add_parser("doctor", help="report the toolchain the kernel found")
    doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
