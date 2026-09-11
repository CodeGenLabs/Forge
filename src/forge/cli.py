"""The kernel's command surface, as far as the milestones so far need it.

Scope note: [MVP.md](../../MVP.md) lists a larger `forge drift` that reads anchors out of the claim
store. This exposes the anchor engine directly instead - enough to check the
milestone by hand and to script against. `drift resolve`, `drift waive` and
`reanchor` write to the drift ledger, which does not exist yet, so they are not
here.

The kernel never calls a language model. Every output is reproducible from the
repository at a commit, which is what makes gates built on it trustworthy.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil as _shutil
import sys
from pathlib import Path

from . import (change, derive, gates, gitio, impact, instructions, scaffold, schema,
               spec, store, trace, validate, verify)
from .anchor import AnchorError, Status, classify, parse_anchor
from .fingerprint import available_languages, fingerprint_source
from .validate import Issue

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

    # Content decides freshness; the commit stamp is provenance shown alongside
    # it. Comparing content is exact, and it is the only comparison that can
    # ever come out clean for a file that is itself committed.
    staleness = derive.stale_artifacts(repo)
    missing = [n for n, v in staleness.items() if v is None]
    outdated = [n for n, changed in derive.derive_all(repo, dry_run=True).items() if changed]
    behind = max((v for v in staleness.values() if v is not None), default=0)
    if missing:
        state = f"{len(missing)} not built; run `forge sync derived`"
    elif outdated:
        state = f"{len(outdated)} stale; run `forge sync derived`"
    else:
        age = f", derived {behind} commit{'s' if behind != 1 else ''} back" if behind else ""
        state = f"current{age}"

    index = (derive.read_json(repo / derive.DERIVED_DIR / trace.TRACE_FILE) or {}).get("data")

    if args.json:
        print(json.dumps({
            "repository": repo.name,
            "head": head,
            "derived": {
                "not_built": sorted(missing),
                "stale": sorted(outdated),
                "commits_behind": behind,
            },
            "summary": (index or {}).get("summary"),
        }, indent=2, sort_keys=True))
        return _EXIT_OK

    print(f"repository       {repo.name} @ {head[:10]}")
    print(f"derived tier     {state}")
    if not index:
        print("claim store      no index; run `forge sync derived`")
        return _EXIT_OK
    summary = index.get("summary", {})
    print(f"claims           {summary.get('claims', 0)} ratified, "
          f"{summary.get('candidates', 0)} candidate, "
          f"{summary.get('decisions', 0)} ADRs")
    print(f"tests            {summary.get('tests_total', 0)} total, "
          f"{summary.get('tests_tagged', 0)} tagged with @covers")

    open_changes = change.list_changes(repo)
    if open_changes:
        for item in open_changes:
            try:
                loaded = schema.load_schema(repo, item.workflow)
            except schema.SchemaError as exc:
                print(f"change {item.name:22} unreadable workflow: {exc}")
                continue
            nxt = item.next_artifact(loaded)
            tasks = item.tasks()
            done = sum(1 for is_done, _ in tasks if is_done)
            progress = f"{done}/{len(tasks)} tasks" if tasks else "no tasks yet"
            where = f"next {nxt.id}" if nxt else "artifacts complete"
            print(f"change {item.name:22} track {item.track}  {where}, {progress}")

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


SCOPES = ("store", "derived", "trace", "change")


def _check_change(repo: Path, reference: str | None) -> list[Issue]:
    """R5 and R6 over one change, or over every open change."""
    try:
        items = ([change.find_change(repo, reference)] if reference
                 else change.list_changes(repo))
    except change.ChangeError as exc:
        return [Issue("ERROR", "change.unknown", change.CHANGES_DIR, str(exc),
                      "forge change list")]

    issues: list[Issue] = []
    for item in items:
        try:
            schema.load_schema(repo, item.workflow)
        except schema.SchemaError as exc:
            issues.append(Issue(
                "ERROR", "change.workflow", f"{item.relative}/.forge.yaml", str(exc),
                f"name a workflow the kernel can load; `workflow: feature` is the default",
            ))
            continue
        computed = impact.compute_impact(repo, item)
        issues.extend(impact.check_claim_touch(repo, item, computed, Issue))
        for delta in _deltas_of(repo, item):
            issues.extend(spec.check_delta(repo, delta, Issue))
        # R13 - "a change with zero deltas is rejected" - is deliberately not
        # here. It is true at `spec:post` and false before it, and a check
        # that demands a spec from a change whose first artifact is still
        # being written is a check people learn to run with --scope store.
    return issues


def _deltas_of(repo: Path, item: change.Change) -> list[spec.Delta]:
    deltas = []
    for path in spec.delta_files(repo, item.relative):
        deltas.append(spec.parse_delta(
            (repo / path).read_text(encoding="utf-8", errors="replace"),
            path, spec.capability_of(path, item.relative),
        ))
    return deltas


def _tier_is_built(repo: Path) -> bool:
    directory = repo / derive.DERIVED_DIR
    return any((directory / artifact.name).exists() for artifact in derive.ARTIFACTS)


def _check_derived(repo: Path) -> list[Issue]:
    if not _tier_is_built(repo):
        # One line, not one per artifact. A freshly initialised repository is
        # the common case here, and four identical errors carrying the same fix
        # reads as breakage rather than as a next step.
        return [Issue(
            "ERROR", "derived.not_built", derive.DERIVED_DIR,
            "the derived tier has never been built, so nothing that reads it can be checked",
            "forge sync derived",
        )]
    issues = []
    for name, changed in derive.derive_all(repo, dry_run=True).items():
        if changed:
            issues.append(Issue(
                "ERROR", "derived.dirty", f"{derive.DERIVED_DIR}/{name}",
                "regenerating produces different bytes; it was hand-edited or is stale",
                "forge sync derived",
            ))
    return issues


def _check_trace(repo: Path) -> list[Issue]:
    index = (derive.read_json(repo / derive.DERIVED_DIR / trace.TRACE_FILE) or {}).get("data")
    if index is None:
        return [Issue(
            "ERROR", "derived.missing", f"{derive.DERIVED_DIR}/{trace.TRACE_FILE}",
            "the trace index has not been built", "forge sync derived",
        )]
    issues = []
    ids = index.get("ids", {})
    for identifier in index.get("summary", {}).get("dangling_references", []):
        entry = ids.get(identifier, {})
        where = (entry.get("back_references") or entry.get("tests")
                 or entry.get("changes") or ["unknown"])
        issues.append(Issue(
            "ERROR", "trace.dangling_reference", where[0],
            f"{identifier} is referenced but no claim or ADR defines it",
            f"define {identifier} in the store, or remove the reference",
            claim=identifier,
        ))
    return issues


def _cmd_check(args: argparse.Namespace) -> int:
    """Deterministic checks, as far as the milestones so far allow.

    Scope note: MVP.md lists 39 checks. The store's 18 and the derived tier's
    are here; the change DAG's are M3. A clean report names what it declined to
    check, because one that does not is a clean report nobody should trust.
    """
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    scopes = tuple(args.scope) if args.scope else SCOPES
    issues: list[Issue] = []
    if "derived" in scopes:
        issues.extend(_check_derived(repo))
    if "trace" in scopes and not ("derived" in scopes and not _tier_is_built(repo)):
        # An unbuilt tier is already reported by the derived scope; saying it
        # again from here would be the same fix printed twice.
        issues.extend(_check_trace(repo))
    if "store" in scopes:
        issues.extend(validate.check_store(repo))
    if "change" in scopes:
        issues.extend(_check_change(repo, args.change))

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level != "ERROR"]

    if args.json:
        print(json.dumps({
            "ok": not errors,
            "command": "forge check",
            "scopes": list(scopes),
            "summary": {"errors": len(errors), "warnings": len(warnings)},
            "issues": [i.to_dict() for i in issues],
        }, indent=2))
        return _EXIT_CHANGED if errors else _EXIT_OK

    for issue in issues:
        where = issue.path + (f":{issue.line}" if issue.line else "")
        tag = f"  [{issue.claim}]" if issue.claim else ""
        print(f"{issue.level:7} {issue.code:28} {where}{tag}\n"
              f"        {issue.message}\n        fix: {issue.fix}")

    checked = ", ".join({
        "store": "claim store (S1-S18)",
        "derived": "derived-tier freshness",
        "trace": "trace integrity",
        "change": "the claim-touch account",
    }[scope] for scope in SCOPES if scope in scopes)
    pending = "the gates, which are point-in-time: `forge gate <point>`"
    if issues:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). "
              f"Checked: {checked}.", file=sys.stderr)
        if not errors:
            # Warnings alone must not fail a gate: S13-S17 are heuristics, and
            # a heuristic that blocks a commit gets switched off within a week.
            print(f"Not yet checked: {pending}.")
    else:
        print(f"ok - no issues. Checked: {checked}.")
        print(f"Not yet checked: {pending}.")
    return _EXIT_CHANGED if errors else _EXIT_OK


def _cmd_init(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    created, skipped = scaffold.scaffold(repo)
    for relative in created:
        print(f"created    {relative}")
    for relative in skipped:
        print(f"kept       {relative}")
    if not created:
        print("\nNothing to create; the scaffold is already here.")
        return _EXIT_OK
    print(
        "\nThe scaffold holds no claims on purpose. Writing plausible ones for a\n"
        "codebase nobody has read is the failure the candidates tier exists to\n"
        "prevent, so claims arrive one at a time:\n"
        "  forge claim new invariant --append\n"
        "  forge sync derived\n"
        "  forge check"
    )
    return _EXIT_OK


def _cmd_claim_new(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    try:
        text = scaffold.claim_template(args.kind, args.id, args.title)
    except ValueError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    if not args.append:
        # Printed, not written, unless asked. A generator that edits the store
        # on every invocation makes `forge claim new` something you hesitate to
        # run, and the point of a template is to be cheap to look at.
        print(text, end="")
        return _EXIT_OK

    target = repo / store.STORE_DIR / scaffold.KIND_FILE[args.kind]
    if not target.exists():
        print(f"forge: {target.relative_to(repo).as_posix()} does not exist; "
              f"run `forge init` first", file=sys.stderr)
        return _EXIT_USAGE
    existing = target.read_text(encoding="utf-8")
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    target.write_text(existing + separator + text, encoding="utf-8", newline="\n")
    relative = target.relative_to(repo).as_posix()
    print(f"appended to {relative}")
    # Said plainly, because the next thing that happens is a failing check and
    # it should not look like a bug.
    print("\nIt will fail `forge check` until the {placeholders} are filled in.\n"
          "That is the checklist, not a defect.")
    return _EXIT_OK


def _cmd_claim_show(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    claims = [c for c in store.load_store(repo) if c.id == args.id]
    if not claims:
        print(f"forge: no claim defines {args.id}", file=sys.stderr)
        return _EXIT_CHANGED

    if args.json:
        print(json.dumps([c.to_dict() for c in claims], indent=2, sort_keys=True))
        return _EXIT_CHANGED if len(claims) > 1 else _EXIT_OK

    for claim in claims:
        print(f"{claim.file}:{claim.line}")
        text = (repo / claim.file).read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")[claim.line - 1:claim.end_line]
        while lines and not lines[-1].strip():
            lines.pop()
        print("\n".join(lines))
    if len(claims) > 1:
        # Not an error the command can fix, but the reader has to know which of
        # the two they are looking at before they act on either.
        print(f"\n{args.id} is defined {len(claims)} times; `forge check` says so as "
              f"store.id_unique", file=sys.stderr)
        return _EXIT_CHANGED
    return _EXIT_OK


def _load_schema(repo: Path, name: str) -> schema.Schema | None:
    try:
        return schema.load_schema(repo, name)
    except schema.SchemaError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return None


def _cmd_change_new(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        created = change.new_change(repo, args.title, track=args.track,
                                    workflow=args.workflow)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    loaded = _load_schema(repo, created.workflow)
    if loaded is None:
        return _EXIT_USAGE
    print(f"created    {created.relative}/")
    print(f"track      {created.track}")
    wanted = [a.id for a in loaded.for_track(created.track)]
    print(f"artifacts  {', '.join(wanted) if wanted else 'none - track A is a question, '
                                                        'not a deliverable'}")
    return _EXIT_OK


def _cmd_change_list(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    changes = change.list_changes(repo)
    if args.json:
        print(json.dumps([_change_summary(repo, c) for c in changes], indent=2))
        return _EXIT_OK
    if not changes:
        print("no open changes. `forge change new \"<title>\"` starts one.")
        return _EXIT_OK
    for item in changes:
        summary = _change_summary(repo, item)
        print(f"{item.name:32} track {item.track}  {summary['state']}")
    return _EXIT_OK


def _change_summary(repo: Path, item: change.Change) -> dict:
    loaded = schema.load_schema(repo, item.workflow)
    states = item.state(loaded)
    pending = [s for s in states if s.state in (change.MISSING, change.BLOCKED)]
    tasks = item.tasks()
    return {
        "name": item.name,
        "track": item.track,
        "workflow": item.workflow,
        "state": "complete" if not pending else f"next: {item.next_artifact(loaded).id}"
                 if item.next_artifact(loaded) else "blocked",
        "artifacts": [s.to_dict() for s in states],
        "tasks": {"total": len(tasks), "done": sum(1 for done, _ in tasks if done)},
        "upgraded_from": item.upgraded_from,
    }


def _cmd_change_show(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, args.change)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    loaded = _load_schema(repo, item.workflow)
    if loaded is None:
        return _EXIT_USAGE

    if args.json:
        print(json.dumps(_change_summary(repo, item), indent=2))
        return _EXIT_OK

    print(f"{item.name}   track {item.track}   workflow {item.workflow}")
    if item.meta.get("title"):
        print(f"  {item.meta['title']}")
    for entry in item.upgraded_from:
        print(f"  upgraded from {entry}")
    print()
    marks = {
        change.COMPLETE: "[x]", change.MISSING: "[ ]", change.BLOCKED: "[-]",
        change.SKIPPED: "[~]", change.NOT_ON_TRACK: "   ",
    }
    for state in item.state(loaded):
        detail = ""
        if state.state == change.BLOCKED:
            detail = f"  waiting on {', '.join(state.waiting_on)}"
        elif state.state == change.SKIPPED:
            detail = f"  skipped: {state.reason}"
        elif state.state == change.NOT_ON_TRACK:
            detail = f"  not on track {item.track}"
        print(f"  {marks[state.state]} {state.id:14}{detail}")

    tasks = item.tasks()
    if tasks:
        print(f"\n  tasks          {sum(1 for done, _ in tasks if done)}/{len(tasks)} done")
    nxt = item.next_artifact(loaded)
    if nxt:
        print(f"\nNext: write {nxt.artifact.generates} "
              f"(`forge instructions {nxt.id} --change {item.number}`)")
    return _EXIT_OK


def _cmd_change_track(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, args.change)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    loaded = _load_schema(repo, item.workflow)
    if loaded is None:
        return _EXIT_USAGE

    before = item.track
    # Taken before the upgrade, so the report can name what the upgrade
    # *added*. Listing the whole track instead would bury the two artifacts
    # that are actually new among the four that were already owed.
    settled = {s.id for s in item.state(loaded)
               if s.state not in (change.MISSING, change.BLOCKED)}
    try:
        item.upgrade(args.to, reason=args.reason)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    print(f"{item.name}: track {before} -> {item.track}")
    added = [s.id for s in item.state(loaded)
             if s.state in (change.MISSING, change.BLOCKED) and s.id in settled]
    if added:
        print(f"newly required: {', '.join(added)}")
    return _EXIT_OK


def _cmd_impact(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, args.change)
        computed = impact.compute_impact(repo, item, base=args.base)
    except (change.ChangeError, gitio.GitError, gitio.InvalidRevision) as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    if args.json:
        print(json.dumps(computed.to_dict(), indent=2))
        return _EXIT_OK

    print(f"{computed.change}   base {computed.base[:10]}")
    print(f"\nBlast radius   {len(computed.changed_files)} changed, "
          f"{len(computed.reverse_deps)} reached by import")
    for path in computed.changed_files:
        print(f"  changed   {path}")
    for path in computed.reverse_deps:
        print(f"  imports   {path}")

    if not computed.touched:
        print("\nClaims touched  none")
        return _EXIT_OK
    print(f"\nClaims touched  {len(computed.touched)} - every one needs a heading "
          f"in impact.md")
    for identifier in sorted(computed.touched):
        entry = computed.touched[identifier]
        print(f"  {identifier:20} {entry.reasons[0]}")
        for extra in entry.reasons[1:]:
            print(f"  {'':20} {extra}")
    return _EXIT_OK


def _fold_change(repo: Path, item: change.Change, *, dry_run: bool) -> tuple[int, list[str]]:
    """Fold every delta of *item* into the permanent specs. Returns (exit, lines).

    Validates the *rebuilt* spec before writing, not just the delta: a delta
    can be individually well-formed and still fold into a file that has two
    requirements with one id, and the moment to catch that is before the
    permanent tier is touched.
    """
    lines: list[str] = []
    deltas = _deltas_of(repo, item)
    if not deltas:
        return _EXIT_OK, ["no spec deltas to fold"]

    planned: list[tuple[Path, str]] = []
    for delta in deltas:
        target = repo / spec.SPECS_DIR / delta.capability / "spec.md"
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        try:
            rebuilt = spec.fold(existing, delta)
        except spec.FoldError as exc:
            print(f"forge: {delta.path}: {exc}", file=sys.stderr)
            return _EXIT_CHANGED, lines

        rebuilt_issues = _rebuilt_issues(delta, rebuilt, target, repo)
        if rebuilt_issues:
            for issue in rebuilt_issues:
                print(f"forge: {issue}", file=sys.stderr)
            return _EXIT_CHANGED, lines

        verbs = ", ".join(f"{len(v)} {k.lower()}"
                          for k, v in sorted(delta.sections.items()) if v)
        relative = target.relative_to(repo).as_posix()
        if existing == rebuilt:
            lines.append(f"unchanged  {relative}")
        else:
            lines.append(f"{'would fold' if dry_run else 'folded'}   {relative}  ({verbs})")
            planned.append((target, rebuilt))

    if not dry_run:
        for target, content in planned:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
    return _EXIT_OK, lines


def _rebuilt_issues(delta: spec.Delta, rebuilt: str, target: Path, repo: Path) -> list[str]:
    requirements = spec.parse_permanent(rebuilt)
    problems = []
    seen: set[str] = set()
    for requirement in requirements:
        if requirement.id in seen:
            problems.append(
                f"{target.relative_to(repo).as_posix()} would define "
                f"{requirement.id} twice after folding {delta.path}"
            )
        seen.add(requirement.id)
        if not requirement.scenarios():
            problems.append(
                f"{target.relative_to(repo).as_posix()}: {requirement.id} would have "
                f"no scenario after the fold"
            )
    return problems


def _cmd_spec_fold(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, args.change)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    deltas = _deltas_of(repo, item)
    grammar = [i for delta in deltas for i in spec.check_delta(repo, delta, Issue)]
    if grammar:
        for issue in grammar:
            print(f"{issue.level}  {issue.code}  {issue.path}"
                  f"{f':{issue.line}' if issue.line else ''}\n"
                  f"        {issue.message}\n        fix: {issue.fix}")
        print(f"\n{len(grammar)} grammar error(s); nothing folded.", file=sys.stderr)
        return _EXIT_CHANGED

    code, lines = _fold_change(repo, item, dry_run=args.dry_run)
    for line in lines:
        print(line)
    return code


def _resolve_change(repo: Path, reference: str | None) -> change.Change | None | int:
    if reference is None:
        return None
    try:
        return change.find_change(repo, reference)
    except change.ChangeError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE


def _cmd_gate(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    item = _resolve_change(repo, args.change)
    if isinstance(item, int):
        return item

    results = gates.run_gate(repo, args.point, item)
    if not results:
        known = ", ".join(gates.points(repo))
        print(f"forge: no gate is declared at {args.point!r}; points are {known}",
              file=sys.stderr)
        return _EXIT_USAGE

    if args.json:
        print(json.dumps({
            "point": args.point,
            "change": item.name if item else None,
            "blocked": any(r.blocks for r in results),
            "gates": [r.to_dict() for r in results],
        }, indent=2))
        return _EXIT_CHANGED if any(r.blocks for r in results) else _EXIT_OK

    for result in results:
        if result.passed and result.available:
            verdict = "pass"
        elif not result.available:
            verdict = "unproven"
        else:
            verdict = "BLOCK" if result.blocks else "warn"
        print(f"{verdict:8} {result.gate.check}")
        for issue in result.issues:
            where = issue.path + (f":{issue.line}" if issue.line else "")
            print(f"         {issue.level} {where}: {issue.message}")
            print(f"         fix: {issue.fix}")

    if any(r.blocks for r in results):
        print(f"\n{args.point} is blocked.", file=sys.stderr)
        return _EXIT_CHANGED
    return _EXIT_OK


def _cmd_verify(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    item = _resolve_change(repo, args.change)
    if isinstance(item, int) or item is None:
        return item if isinstance(item, int) else _EXIT_USAGE

    report = verify.verify(repo, item, waived=tuple(args.waive or ()),
                           run_commands=not args.no_run)
    target = verify.write_verification(repo, item, report)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['change']} @ {report['commit'][:10]}")
        for name, gate in report["gates"].items():
            detail = gate.get("reason") or gate.get("cmd") or ""
            print(f"  {gate['status']:12} {name:18} {detail}")
        print(f"\nverdict: {report['verdict']}")
        if report["verdict"] != "pass":
            # Said plainly, because "one of eight" is the whole point and a
            # reader who only sees a red line will assume the tests failed.
            print("Tests passing is one of eight conditions, not the condition.")
        if report.get("pending"):
            # A pass with pending conditions is not a full verification, and
            # the report must say so where the verdict is read, not only in
            # the JSON.
            print(f"still unchecked by this kernel: {', '.join(report['pending'])}")
        print(f"written  {target.relative_to(repo).as_posix()}")
    return _EXIT_OK if report["verdict"] == "pass" else _EXIT_CHANGED


def _cmd_archive(args: argparse.Namespace) -> int:
    """Fold the spec deltas, then move the change into the archive.

    Ordered, and it refuses on the first failure (SYSTEM_KNOWLEDGE.md 9.3).
    Archiving a change whose promises were never folded loses them: the
    archive is never an input to any phase, so anything still only recorded
    there is gone in practice.
    """
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    item = _resolve_change(repo, args.change)
    if isinstance(item, int) or item is None:
        return item if isinstance(item, int) else _EXIT_USAGE

    blocking: list[Issue] = []
    for point in ("spec:post", "impact:post", "analyze:post"):
        for result in gates.run_gate(repo, point, item):
            if result.blocks:
                blocking.extend(result.errors)
    report = verify.read_verification(repo, item)
    if report is None or report.get("verdict") != "pass":
        blocking.append(Issue(
            "ERROR", "verify.definition_of_done",
            f"{item.relative}/{verify.VERIFICATION_FILE}",
            "no passing verification report"
            if report is None else f"verification verdict is {report.get('verdict')!r}",
            f"forge verify --change {item.number}",
        ))

    if blocking and not args.force:
        for issue in blocking:
            print(f"{issue.level}  {issue.code}  {issue.path}\n"
                  f"       {issue.message}\n       fix: {issue.fix}")
        print(f"\n{len(blocking)} blocker(s); nothing archived. "
              f"--force records the archive anyway and says so.", file=sys.stderr)
        return _EXIT_CHANGED

    code, lines = _fold_change(repo, item, dry_run=args.dry_run)
    for line in lines:
        print(line)
    if code != _EXIT_OK:
        return code

    stamp = args.date or _dt.date.today().isoformat()
    destination = repo / change.ARCHIVE_DIR / f"{stamp}-{item.name}"
    if destination.exists():
        print(f"forge: {destination.relative_to(repo).as_posix()} already exists",
              file=sys.stderr)
        return _EXIT_USAGE
    if args.dry_run:
        print(f"would move  {item.relative} -> "
              f"{destination.relative_to(repo).as_posix()}")
        return _EXIT_OK

    if blocking and args.force:
        item.meta["archived_with_blockers"] = [i.code for i in blocking]
        item.write_meta()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _shutil.move(str(item.root), str(destination))
    print(f"archived    {destination.relative_to(repo).as_posix()}")
    print("\nNow: `forge sync derived` and commit. The archive is never an input "
          "to any phase, so anything in it that still matters belongs in the "
          "permanent tier.")
    return _EXIT_OK


def _cmd_instructions(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    item = _resolve_change(repo, args.change)
    if isinstance(item, int) or item is None:
        return item if isinstance(item, int) else _EXIT_USAGE
    try:
        resolved = instructions.resolve(repo, item, args.artifact)
    except (instructions.InstructionError, schema.SchemaError) as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    if args.json:
        print(json.dumps(resolved, indent=2, sort_keys=True))
        return _EXIT_OK

    print(f"{resolved['artifact']}  ->  {resolved['generates'] or '(generated)'}")
    print(f"  track {resolved['track']}, {resolved['required']}")
    if resolved["blocked_by"]:
        print(f"  blocked by: {', '.join(resolved['blocked_by'])}")
    if resolved["template"]:
        print(f"  template: {resolved['template']}")
    reads = resolved["reads"]
    for path in reads["files"]:
        print(f"  read      {path}")
    for path in reads["derived"]:
        print(f"  read      {path}")
    claims = reads.get("claims") or {}
    if claims.get("mode") == "metadata":
        print(f"  read      {len(claims['entries'])} claim(s), metadata only")
    elif claims.get("entries"):
        print(f"  read      {len(claims['entries'])} claim body/bodies: "
              f"{', '.join(e['id'] for e in claims['entries'])}")
    for item_text in resolved["unresolved"]:
        print(f"  MISSING   {item_text}")
    if resolved["instruction"]:
        print(f"\n{resolved['instruction']}")
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
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=_cmd_status)

    check = sub.add_parser(
        "check",
        help="run the deterministic checks that exist today",
        description="Exit 0 when no ERROR was found, 1 when one was, 2 on a usage "
                    "error. Warnings never fail: S13-S17 are heuristics about "
                    "writing quality, and a heuristic that blocks a commit gets "
                    "switched off within a week.",
    )
    check.add_argument("--repo", type=Path, default=Path.cwd())
    check.add_argument("--scope", action="append", choices=SCOPES,
                       help="limit to one scope; repeatable. Default: all of them")
    check.add_argument("--change", help="limit the change scope to one change")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=_cmd_check)

    init = sub.add_parser(
        "init",
        help="scaffold .forge/ and the docs/system/ skeleton",
        description="Writes empty, titled store files and the adoption ADR. Never "
                    "overwrites, so running it again after a version bump is safe.",
    )
    init.add_argument("--repo", type=Path, default=Path.cwd())
    init.set_defaults(func=_cmd_init)

    claim = sub.add_parser("claim", help="create or read one claim")
    claim_sub = claim.add_subparsers(dest="claim_command", required=True)

    claim_new = claim_sub.add_parser(
        "new",
        help="print a claim template for one kind",
        description="The template carries {placeholders} and therefore fails "
                    "`forge check` until they are filled in. That is the checklist.",
    )
    claim_new.add_argument("kind", choices=sorted(scaffold.KIND_FILE))
    claim_new.add_argument("--id", help="the claim ID, e.g. INV-refund-cap")
    claim_new.add_argument("--title", help="the heading, stating the claim itself")
    claim_new.add_argument("--append", action="store_true",
                           help="append to the store file this kind belongs in")
    claim_new.add_argument("--repo", type=Path, default=Path.cwd())
    claim_new.set_defaults(func=_cmd_claim_new)

    claim_show = claim_sub.add_parser("show", help="print one claim as it is written")
    claim_show.add_argument("id")
    claim_show.add_argument("--repo", type=Path, default=Path.cwd())
    claim_show.add_argument("--json", action="store_true")
    claim_show.set_defaults(func=_cmd_claim_show)

    chg = sub.add_parser("change", help="open, inspect and re-track a change")
    chg_sub = chg.add_subparsers(dest="change_command", required=True)

    chg_new = chg_sub.add_parser(
        "new",
        help="open a change directory",
        description="Track C is the default. WORKFLOW.md section 1: 'it's too simple "
                    "to need a spec' is itself the signal to take the heavier track, "
                    "and what scales down with simplicity is artifact size, never "
                    "approval.",
    )
    chg_new.add_argument("title")
    chg_new.add_argument("--track", default="C", choices=list(schema.TRACKS))
    chg_new.add_argument("--workflow", default="feature")
    chg_new.add_argument("--repo", type=Path, default=Path.cwd())
    chg_new.set_defaults(func=_cmd_change_new)

    chg_list = chg_sub.add_parser("list", help="open changes and where each one is")
    chg_list.add_argument("--repo", type=Path, default=Path.cwd())
    chg_list.add_argument("--json", action="store_true")
    chg_list.set_defaults(func=_cmd_change_list)

    chg_show = chg_sub.add_parser("show", help="one change: artifacts, tasks, next step")
    chg_show.add_argument("change")
    chg_show.add_argument("--repo", type=Path, default=Path.cwd())
    chg_show.add_argument("--json", action="store_true")
    chg_show.set_defaults(func=_cmd_change_show)

    chg_track = chg_sub.add_parser(
        "track",
        help="upgrade a change to a heavier track",
        description="One-way. Nothing downgrades: a change that turned out to touch an "
                    "ARC- claim must not be able to shed the artifacts that account "
                    "for it.",
    )
    chg_track.add_argument("change")
    chg_track.add_argument("--to", required=True, choices=list(schema.TRACKS))
    chg_track.add_argument("--reason", required=True,
                           help="what was discovered that made the change bigger")
    chg_track.add_argument("--repo", type=Path, default=Path.cwd())
    chg_track.set_defaults(func=_cmd_change_track)

    imp = sub.add_parser(
        "impact",
        help="blast radius and the computed claim-touch set",
        description="Every claim this change reaches must be accounted for in "
                    "impact.md under exactly one heading. That is what makes "
                    "'which documentation must change?' a set operation rather "
                    "than a judgement call.",
    )
    imp.add_argument("--change", required=True)
    imp.add_argument("--base", help="override the commit the change started from")
    imp.add_argument("--repo", type=Path, default=Path.cwd())
    imp.add_argument("--json", action="store_true")
    imp.set_defaults(func=_cmd_impact)

    spc = sub.add_parser("spec", help="work with capability specs")
    spc_sub = spc.add_subparsers(dest="spec_command", required=True)
    spc_fold = spc_sub.add_parser(
        "fold",
        help="apply a change's spec deltas to the permanent specs",
        description="Deterministic: two people folding the same delta get the same "
                    "file. The rebuilt spec is validated before anything is written.",
    )
    spc_fold.add_argument("--change", required=True)
    spc_fold.add_argument("--dry-run", action="store_true")
    spc_fold.add_argument("--repo", type=Path, default=Path.cwd())
    spc_fold.set_defaults(func=_cmd_spec_fold)

    gate = sub.add_parser(
        "gate",
        help="run the gates declared at one lifecycle point",
        description="Exit 1 when a blocking gate fails. A check the kernel does not "
                    "implement reports `unproven` and never passes - a gate that "
                    "succeeds because nobody wrote its check is evidence of a check "
                    "that did not happen.",
    )
    gate.add_argument("point", metavar="POINT",
                      help=f"one of {', '.join(gates.POINTS)}")
    gate.add_argument("--change")
    gate.add_argument("--repo", type=Path, default=Path.cwd())
    gate.add_argument("--json", action="store_true")
    gate.set_defaults(func=_cmd_gate)

    ver = sub.add_parser(
        "verify",
        help="produce verification.json - evidence, not an opinion",
        description="Eleven recorded conditions, of which tests passing is one. "
                    "Generated, never authored: an authored verification report is a "
                    "place to write 'all tests pass' without having run them.",
    )
    ver.add_argument("--change", required=True)
    ver.add_argument("--waive", action="append", choices=list(verify.WAIVABLE),
                     help="record a waiver for a waivable condition; repeatable")
    ver.add_argument("--no-run", action="store_true",
                     help="skip build/test commands and record them as unproven")
    ver.add_argument("--repo", type=Path, default=Path.cwd())
    ver.add_argument("--json", action="store_true")
    ver.set_defaults(func=_cmd_verify)

    arch = sub.add_parser(
        "archive",
        help="fold the spec deltas and move the change into the archive",
        description="Refuses on the first blocker. Archiving a change whose promises "
                    "were never folded loses them: the archive is never an input to "
                    "any phase.",
    )
    arch.add_argument("--change", required=True)
    arch.add_argument("--dry-run", action="store_true")
    arch.add_argument("--force", action="store_true",
                      help="archive despite blockers, recording which ones in "
                           ".forge.yaml")
    arch.add_argument("--date", help="the archive date stamp (default: today)")
    arch.add_argument("--repo", type=Path, default=Path.cwd())
    arch.set_defaults(func=_cmd_archive)

    instr = sub.add_parser(
        "instructions",
        help="resolve one artifact's `reads` contract",
        description="What a phase is entitled to read is a property of the workflow "
                    "schema, not of the prompt. A phase that wants more changes the "
                    "schema, where the change is visible.",
    )
    instr.add_argument("artifact")
    instr.add_argument("--change", required=True)
    instr.add_argument("--repo", type=Path, default=Path.cwd())
    instr.add_argument("--json", action="store_true")
    instr.set_defaults(func=_cmd_instructions)

    doctor = sub.add_parser("doctor", help="report the toolchain the kernel found")
    doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
