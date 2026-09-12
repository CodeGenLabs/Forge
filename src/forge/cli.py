"""The kernel's command surface, as far as the milestones so far need it.

Scope note: `forge drift --store` reads anchors out of the claim store and reports per claim;
`--changed` narrows that to the claims anchoring files in the diff. The bare
positional form stays, exposing the anchor engine directly for scripting and
for checking a measurement by hand. `drift resolve`, `drift waive` and
`reanchor` write to the drift ledger, which does not exist yet, so they are not
here: this module produces the signal and records no verdict about it.

One limit worth stating, because it decides what a hook can do: classification
compares two *committed* revisions, so `--changed` selects claims by the
working diff but still classifies against HEAD. A file edited and not yet
committed is therefore selected and reported fresh.

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

from . import (bootstrap, change, derive, gates, gitio, hooks, hosts, impact,
               instructions, ledger, reconcile as reconcile_mod, scaffold,
               schema, skills, spec, store, trace, validate, verify)
from .anchor import (AnchorError, Status, classify, classify_store,
                     parse_anchor)
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

    if args.anchor and args.anchor[0] in _LEDGER_VERBS:
        return _drift_ledger(repo, args)

    if args.store or args.changed or args.staged:
        if args.anchor:
            print("forge: --store and --changed read the anchors from the claim "
                  "store; do not also name anchors", file=sys.stderr)
            return _EXIT_USAGE
        if args.baseline:
            print("forge: --baseline overrides every anchor's recorded @sha, which "
                  "is meaningless for a store-wide scan - each claim has its own",
                  file=sys.stderr)
            return _EXIT_USAGE
        return _drift_store(repo, args)

    if not args.anchor:
        print("forge: name an anchor, or pass --store to read them from the claim store",
              file=sys.stderr)
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


_LEDGER_VERBS = ("record", "list", "resolve", "waive", "confirm")


def _drift_ledger(repo: Path, args: argparse.Namespace) -> int:
    """`forge drift record | list | resolve <id> | waive <id>`."""
    verb, *rest = args.anchor

    if verb == "record":
        # `--staged` here for the same reason `drift --staged` exists: the hook
        # reports what is about to be committed, and an entry that described
        # HEAD instead would say `shifted` where the hook had just said `stale`.
        # Two answers about one claim, a minute apart.
        head = gitio.INDEX if args.staged else args.head
        added = ledger.record(repo, classify_store(repo, head=head))
        if not added:
            print("no new drift; every claim is either fresh or already in the ledger")
            return _EXIT_OK
        for entry in added:
            print(f"opened   {entry.id}  {entry.claim}  {entry.signal}"
                  + (f"  proposed {entry.proposed_verdict}"
                     if entry.proposed_verdict else ""))
        print(f"\n{len(added)} entry(s) in {ledger.DRIFT_FILE}. The kernel proposes and "
              f"never decides: `forge drift resolve <id> --verdict V1|V2|V3|V4`.",
              file=sys.stderr)
        return _EXIT_CHANGED

    if verb == "list":
        entries = ledger.load_ledger(repo)
        if args.json:
            print(json.dumps([e.to_dict() for e in entries], indent=2))
            return _EXIT_OK
        if not entries:
            print(f"{ledger.DRIFT_FILE} holds no entries")
            return _EXIT_OK
        width = max(len(e.id) for e in entries)
        for entry in entries:
            detail = entry.verdict or entry.waived_until or entry.signal
            print(f"{entry.id:{width}}  {entry.status:8}  {entry.claim}  {detail}")
        still = ledger.open_entries(repo)
        return _EXIT_CHANGED if still else _EXIT_OK

    if not rest:
        print(f"forge: `drift {verb}` needs an entry id, as in "
              f"`forge drift {verb} D-001`", file=sys.stderr)
        return _EXIT_USAGE

    try:
        if verb == "resolve":
            if not args.verdict:
                raise ledger.LedgerError(
                    "resolve needs --verdict: " + ", ".join(
                        f"{k} ({v})" for k, v in ledger.VERDICTS.items()))
            entry = ledger.resolve(repo, rest[0], args.verdict,
                                   evidence=args.evidence, adr=args.adr,
                                   accept_asserted=args.accept_asserted)
            print(f"resolved {entry.id}  {entry.claim}  {entry.verdict} - "
                  f"{ledger.VERDICTS[entry.verdict]}")
            # Said every time, because the one thing this design refuses is the
            # command that would make it unnecessary.
            print("\nThe claim itself is yours to edit. No command here rewrites a "
                  "claim to match the code.", file=sys.stderr)
        elif verb == "confirm":
            entry, restamped = ledger.confirm(repo, rest[0], head=args.head)
            print(f"confirmed {entry.id}  {entry.claim}  restamped "
                  f"{len(restamped)} anchor line(s)")
            for where in restamped:
                print(f"  {where}")
            print("\nNot a verdict. The four say something is wrong somewhere; "
                  "this says a human read it and nothing is.", file=sys.stderr)
        else:
            entry = ledger.waive(repo, rest[0], until=args.until or "",
                                 reason=args.reason or "")
            print(f"waived   {entry.id}  {entry.claim}  until {entry.waived_until}")
    except ledger.LedgerError as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    return _EXIT_OK


def _drift_store(repo: Path, args: argparse.Namespace) -> int:
    """`forge drift --store` / `--changed`: the scan, rendered per claim."""
    paths: frozenset[str] | None = None
    # `--staged` compares against the index, which is the only end a
    # pre-commit hook can usefully ask about: the working tree holds edits
    # nobody is committing, and HEAD is the commit before this one. Without it
    # `--changed` selected by the diff and still classified against HEAD, so it
    # reported the same verdict whether or not anything was staged.
    head = gitio.INDEX if args.staged else args.head
    if args.changed or args.staged:
        try:
            paths = frozenset(gitio.staged_files(repo) if args.staged
                              else gitio.changed_files(repo, args.head))
        except (gitio.GitError, gitio.InvalidRevision) as exc:
            print(f"forge: {exc}", file=sys.stderr)
            return _EXIT_USAGE

    try:
        drifts = classify_store(repo, head=head, paths=paths)
        if args.unrecorded:
            # Drift somebody wrote down is not an emergency; drift nobody
            # noticed is. A pre-commit hook cannot ask for a *verdict* - a
            # verdict points at a commit, and the commit does not exist yet -
            # so what it can ask for is that the signal is not lost.
            open_claims = {e.claim for e in ledger.open_entries(repo)}
            drifts = [d for d in drifts if d.claim_id not in open_claims]
    except gitio.InvalidRevision as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    if args.json:
        print(json.dumps([d.to_dict() for d in drifts], indent=2))
    else:
        _render_drifts(drifts, narrowed=paths is not None)

    return _EXIT_CHANGED if any(d.obligating and d.changed for d in drifts) else _EXIT_OK


def _render_drifts(drifts: list, *, narrowed: bool) -> None:
    obligating = [d for d in drifts if d.obligating]
    aside = [d for d in drifts if not d.obligating]

    if not drifts:
        # "nothing was checked" and "everything checked was fine" are different
        # answers, and printing the same line for both is how a narrowed scan
        # starts reading like a complete one.
        print("no claim anchors the changed files" if narrowed
              else "the store declares no anchors")
        return

    _render_drift_block(obligating, "")
    if aside:
        print("\nnot obligating (candidate or retired) - reported, never failing:")
        _render_drift_block(aside, "  ")

    changed = [d for d in obligating if d.changed]
    scope = "anchoring the changed files" if narrowed else "in the store"
    # Flushed, because the summary goes to stderr and the listing to stdout:
    # without this the two streams interleave and the summary prints above the
    # block it summarises.
    sys.stdout.flush()
    print(f"\n{len(obligating)} claim(s) {scope}: {len(obligating) - len(changed)} fresh, "
          f"{len(changed)} needing a look", file=sys.stderr)


def _render_drift_block(drifts: list, indent: str) -> None:
    if not drifts:
        print(f"{indent}(none)")
        return
    width = max(len(d.claim_id) for d in drifts)
    for d in drifts:
        if d.status:
            status = d.status.value
        else:
            # A claim with anchors that all failed to classify is not the same
            # as a claim with no anchors, and calling both "no-anchors" hides
            # the case a reader has to act on.
            status = "unclassified" if d.errors else "no-anchors"
        print(f"{indent}{d.claim_id:{width}}  {status:11}  {d.title}")
        # Only the anchors that caused the status, and only when it is not
        # fresh: a fresh claim's anchor list is noise, and noise is what stops
        # the report being read at all.
        if d.changed:
            for r in d.culprits:
                print(f"{indent}  {' ' * width}{str(r.anchor)}  {r.detail}")
        for text, message in d.errors:
            print(f"{indent}  {' ' * width}{text}  ERROR {message}")


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

    # Waivers are listed rather than counted silently: a bypass that nobody
    # sees on the one screen everyone reads is a bypass that becomes permanent.
    entries = ledger.load_ledger(repo)
    still_open = ledger.open_entries(repo)
    waived = [e for e in entries if e.status == "waived" and e not in still_open]
    if still_open:
        problems += len(still_open)
        print(f"{'drift':16} {len(still_open)} unresolved: "
              + ", ".join(f"{e.id} ({e.claim})" for e in still_open[:4])
              + (" ..." if len(still_open) > 4 else ""))
    if waived:
        print(f"{'drift waived':16} {len(waived)}: "
              + ", ".join(f"{e.id} until {e.waived_until}" for e in waived[:4]))
    if not problems:
        print("open items       none")
    return _EXIT_OK


SCOPES = ("store", "derived", "trace", "change", "skills", "candidates")


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
    if "skills" in scopes:
        issues.extend(skills.check_skills(repo, Issue, known_subcommands()))
        issues.extend(skills.check_scenarios(repo, Issue))
    if "candidates" in scopes:
        issues.extend(bootstrap.check_candidates(repo, Issue))

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
        "skills": "the skill rules",
        "candidates": "candidate admissibility",
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


def _named_change(args: argparse.Namespace) -> str | None:
    """The change named either way.

    `forge change show 1` was positional while every other change-scoped
    command took `--change`, and `change show` printed the flag form in its own
    "Next:" line - so the tool taught a spelling it then rejected. Both work;
    the flag is the one the rest of the surface uses and the one the hints
    print.
    """
    return getattr(args, "change_flag", None) or getattr(args, "change", None)


def _cmd_change_show(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    named = _named_change(args)
    if not named:
        print("forge: name a change, as `--change 1` or `1`", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, named)
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
        if state.state == change.MISSING and state.reason:
            # A scaffolded-but-unwritten artifact looks identical to an absent
            # one on this screen otherwise, and the difference is exactly what
            # the author needs to know.
            detail = f"  {state.reason}"
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
    named = _named_change(args)
    if not named:
        print("forge: name a change, as `--change 1` or `1`", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, named)
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
    named = _named_change(args)
    if not named:
        print("forge: name a change, as `--change 1` or `1`", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, named)
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

    width = max((len(i) for i in (*computed.touched, *computed.nearby)), default=20)
    if not computed.touched:
        print("\nClaims touched  none")
    else:
        print(f"\nClaims touched  {len(computed.touched)} - every one needs a heading "
              f"in impact.md")
        for identifier in sorted(computed.touched):
            entry = computed.touched[identifier]
            print(f"  {identifier:{width}} {entry.reasons[0]}")
            for extra in entry.reasons[1:]:
                print(f"  {'':{width}} {extra}")

    # Printed under a heading that says plainly it is not owed anything. The
    # import graph is worth reading and is not an obligation; on a codebase
    # with cycles, making it one means every change touches every claim.
    if computed.nearby:
        print(f"\nNearby          {len(computed.nearby)} the diff came close to "
              f"but did not reach - worth reading, no heading owed")
        for identifier in sorted(computed.nearby):
            entry = computed.nearby[identifier]
            print(f"  {identifier:{width}} {entry.reasons[0]}")
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
        if not delta.capability:
            # `spec/<capability>/spec.md` is the layout `capability_of` reads.
            # A flat `spec/<name>.md` yields no capability, and folding it
            # anyway wrote every change's requirements into one
            # `docs/system/specs/spec.md` titled `# capability` - silently,
            # and found only the first time the fold was ever executed.
            print(f"forge: {delta.path}: cannot tell which capability this delta "
                  f"belongs to; move it to "
                  f"{item.relative}/spec/<capability>/spec.md",
                  file=sys.stderr)
            return _EXIT_CHANGED, lines
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
    named = _named_change(args)
    if not named:
        print("forge: name a change, as `--change 1` or `1`", file=sys.stderr)
        return _EXIT_USAGE
    try:
        item = change.find_change(repo, named)
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
                           run_commands=not args.no_run, timeout=args.timeout)
    target = verify.write_verification(repo, item, report)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['change']} @ {report['commit'][:10]}")
        for name, gate in report["gates"].items():
            detail = gate.get("reason") or gate.get("cmd") or ""
            print(f"  {gate['status']:12} {name:18} {detail}")
            # A failing command that says only "fail" sends the reader off to
            # re-run it by hand, which is what happened the first time a
            # monorepo's suite went red here.
            for found in (gate.get("failures") or gate.get("tail") or [])[:6]:
                print(f"  {'':12} {'':18} {found[:160]}")
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


def _scaffold_artifact(repo: Path, item, resolved: dict, name: str) -> str | None | int:
    """Write one artifact's template if it is absent. Returns the path, or None."""
    generates = resolved.get("generates") or ""
    if not generates:
        print(f"forge: {resolved['artifact']} generates nothing to scaffold",
              file=sys.stderr)
        return _EXIT_USAGE

    if any(ch in generates for ch in "*?["):
        # `spec/**/*.md` names a shape, not a file. The capability name is the
        # author's to choose, and guessing it would produce `spec/spec.md` on
        # every change - a name that tells a later reader nothing.
        if not name:
            print(f"forge: {resolved['artifact']} generates {generates}; pass "
                  f"--write NAME to say which file", file=sys.stderr)
            return _EXIT_USAGE
        stem = change.slugify(name)
        if not stem:
            print(f"forge: {name!r} is not a usable file name", file=sys.stderr)
            return _EXIT_USAGE
        # `<capability>/spec.md`, not `<capability>.md`. `spec.capability_of`
        # reads the capability from the directory, so the flat spelling folded
        # every delta into one `docs/system/specs/spec.md` titled `# capability`
        # - found on `requests` the first time the fold was ever executed.
        relative = f"{generates.split('*', 1)[0].rstrip('/')}/{stem}/spec.md"
    else:
        relative = generates
        stem = ""

    # `generates` is already repository-relative, so it is resolved against the
    # repo and not against the change directory. Joining it to `item.root`
    # produced `changes/0002-x/changes/0002-x/proposal.md` - the same mistake
    # the `${change}` substitution made in `instructions.py`.
    target = repo / relative
    if target.exists():
        print(f"forge: {relative} already exists; not overwriting", file=sys.stderr)
        return None

    body = scaffold.change_template(resolved["artifact"], item.slug.replace("-", " "),
                                    stem=stem)
    if body is None:
        print(f"forge: {resolved['artifact']} has no template - it is generated",
              file=sys.stderr)
        return _EXIT_USAGE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")
    return relative


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

    written = None
    if args.write is not None:
        written = _scaffold_artifact(repo, item, resolved, args.write)
        if isinstance(written, int):
            return written

    if args.json:
        print(json.dumps({**resolved, "written": written}, indent=2, sort_keys=True))
        return _EXIT_OK

    print(f"{resolved['artifact']}  ->  {resolved['generates'] or '(generated)'}")
    if written:
        print(f"  wrote     {written}  (delete the template marker once written)")
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


def known_subcommands() -> set[str]:
    """Every `forge <word>` the CLI accepts, read off the parser itself.

    The skill linter checks that a `requires-kernel` entry names a real
    command, and a hand-maintained list of command names would be a second
    source of truth that drifts the first time one is added.
    """
    for action in build_parser()._actions:  # noqa: SLF001 - argparse has no public API
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return set(action.choices)
    return set()


def _cmd_skill_list(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    found = skills.load_skills(repo)
    if args.json:
        print(json.dumps([s.to_dict() for s in found], indent=2))
        return _EXIT_OK
    if not found:
        print(f"no skills in {skills.SKILLS_DIR}/")
        return _EXIT_OK
    behind = 0
    for skill in found:
        state = skills.copy_state(repo, skill)
        # `stale` is not a fault - a project may pin a procedure on purpose -
        # but a copy silently drifting from the kernel is a fact the reader is
        # entitled to. Found when a manifest exported a skill that still told
        # its reader to do something the kernel had stopped saying.
        mark = "  (differs from the shipped skill)" if state == "stale" else ""
        behind += state == "stale"
        print(f"{skill.name:20} {skill.phase or '-':12} {skill.lines:4} lines{mark}")
        if skill.description:
            print(f"{'':20} {' '.join(skill.description.split())}")
    if behind:
        print(f"\n{behind} local copy(s) differ from the kernel's. `forge skill "
              f"export --host forge` overwrites them; editing one is also a "
              f"legitimate answer.", file=sys.stderr)
    return _EXIT_OK


def _cmd_skill_show(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    found = [s for s in skills.load_skills(repo) if s.name == args.name]
    if not found:
        known = ", ".join(s.name for s in skills.load_skills(repo)) or "none"
        print(f"forge: no skill named {args.name!r}; found: {known}", file=sys.stderr)
        return _EXIT_USAGE
    print((repo / found[0].path).read_text(encoding="utf-8"), end="")
    return _EXIT_OK


def _cmd_bootstrap_derive(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    derive.derive_all(repo)
    summary = bootstrap.summarise(repo)
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        return _EXIT_OK

    print(f"repository     {repo.name} @ {summary.head[:10]}")
    print(f"files          {summary.files_considered} described "
          f"({summary.files_tracked} tracked)")
    for name, data in sorted(summary.by_language.items(),
                             key=lambda kv: -kv[1]["lines"])[:6]:
        print(f"  {name:14} {data['files']:4} files  {data['lines']:6} lines")
    print(f"entry points   {', '.join(summary.entry_points) or 'none detected'}")
    print(f"modules        {', '.join(summary.modules) or 'none detected'}")
    print(f"imports        {summary.import_edges} edges, "
          f"{len(summary.import_cycles)} cycle(s)")
    print(f"tests          {summary.tests_declared} declared in "
          f"{summary.test_files} files")
    for name, data in sorted(summary.stack.items()):
        # Not `{data}`. A dict's repr is a debug aid, and this line is the
        # second thing a new user reads: on a monorepo it printed twenty-five
        # packages, single-quoted and `None`-strewn, on one unwrapped line.
        manifest = data.get("manifest") or "?"
        lock = data.get("lockfile") or "no lockfile"
        packages = data.get("packages") or {}
        print(f"stack          {name}  {manifest}, {lock}, {len(packages)} declared")
        pinned = sum(1 for v in packages.values()
                     if isinstance(v, dict) and v.get("resolved"))
        if packages:
            shown = sorted(packages)[:6]
            print(f"{'':15}{', '.join(shown)}"
                  + (f" ... +{len(packages) - len(shown)} more" if len(packages) > 6 else ""))
            print(f"{'':15}{pinned} of {len(packages)} resolved to a version "
                  f"in the lockfile")
        if data.get("requires_python"):
            print(f"{'':15}requires python {data['requires_python']}")
    if summary.commands:
        print("commands       " + ", ".join(f"{k}: {v}"
                                            for k, v in summary.commands.items()))

    # The most useful thing a bootstrap can say is what it did not learn.
    print("\nNot derivable, and deliberately not guessed:")
    for item in summary.not_derivable:
        print(f"  - {item}")
    print("\nNothing above is a claim. Pass 2 proposes candidates (the `bootstrap` "
          "skill),\nand `forge bootstrap review` walks them - rejecting by default.")
    return _EXIT_OK


def _cmd_bootstrap_review(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    target = repo / bootstrap.REVIEW_FILE
    existing = target.read_text(encoding="utf-8") if target.is_file() else None
    sheet = bootstrap.build_review(repo, cap=args.cap, existing=existing)
    if sheet != existing:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sheet, encoding="utf-8", newline="\n")

    verdicts = bootstrap.read_review(sheet)
    if args.json:
        print(json.dumps({"sheet": bootstrap.REVIEW_FILE,
                          "verdicts": [v.__dict__ for v in verdicts]}, indent=2))
        return _EXIT_OK

    print(f"{'wrote' if sheet != existing else 'unchanged'}  {bootstrap.REVIEW_FILE}")
    if not verdicts:
        print("\nNo candidates to review.")
        return _EXIT_OK

    counts: dict[str, int] = {}
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
    print("  " + ", ".join(f"{n} {v}" for v, n in sorted(counts.items())))

    pending = [v for v in verdicts if v.verdict == "reject"][:bootstrap.BATCH_SIZE]
    if pending:
        print(f"\nNext batch of {len(pending)} - edit the verdict in place:")
        for verdict in pending:
            print(f"  {bootstrap.REVIEW_FILE}:{verdict.line}  {verdict.id}")
    print("\nEvery verdict starts at `reject`, and that is the posture rather than "
          "a placeholder.\nTwelve ratified claims plus a complete derived tier is a "
          "good outcome.")
    return _EXIT_OK


def _cmd_bootstrap_seal(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    blocking = bootstrap.check_candidates(repo, Issue)
    ratified_ids = {c.id for c in bootstrap.plan_seal(repo, cap=args.cap).ratified}
    blocking = [i for i in blocking if i.claim in ratified_ids]
    if blocking:
        for issue in blocking:
            print(f"{issue.level}  {issue.code}  {issue.path}:{issue.line}\n"
                  f"       {issue.message}\n       fix: {issue.fix}")
        print(f"\n{len(blocking)} problem(s) in candidates marked for ratification; "
              f"nothing sealed.", file=sys.stderr)
        return _EXIT_CHANGED

    plan = bootstrap.seal(repo, cap=args.cap, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
        return _EXIT_OK

    verb = "would write" if args.dry_run else "wrote"
    for relative in sorted(plan.writes):
        print(f"{verb:12} {relative}")
    print(f"\nratified {len(plan.ratified)}, rejected {len(plan.rejected)}, "
          f"deferred {len(plan.deferred)}")
    if plan.over_cap:
        print(f"over the cap of {args.cap}, left as candidates: "
              f"{', '.join(c.id for c in plan.over_cap)}")
    for verdict in plan.unknown_verdicts:
        print(f"unreadable verdict {verdict.verdict!r} for {verdict.id}, "
              f"treated as reject")
    if not args.dry_run:
        print("\nNow: `forge sync derived`, then `forge check`. Unratified "
              "candidates stay where they are -\nreadable, not citable.")
    return _EXIT_OK


def _cmd_skill_export(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if args.host not in hosts.HOSTS:
        print(f"forge: no host {args.host!r}. Known: "
              + ", ".join(f"{h.name} ({h.note})" for h in hosts.HOSTS.values()),
              file=sys.stderr)
        return _EXIT_USAGE
    outcome, written = hosts.export(repo, args.host)
    print(f"{outcome:10} {hosts.HOSTS[args.host].target}")
    for path in written[:8]:
        print(f"           {path}")
    return _EXIT_OK


def _cmd_reconcile(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE
    try:
        result = reconcile_mod.reconcile(repo, args.since, args.head)
    except (gitio.GitError, gitio.InvalidRevision) as exc:
        print(f"forge: {exc}", file=sys.stderr)
        return _EXIT_USAGE

    if args.record:
        added = reconcile_mod.record(repo, result)
        for entry in added:
            print(f"opened   {entry.id}  {entry.claim}  {entry.signal}")
        print(f"\n{len(added)} entry(s) opened in {ledger.DRIFT_FILE}."
              if added else "no new entries; every drifted claim already has one",
              file=sys.stderr)
        return _EXIT_CHANGED if added else _EXIT_OK

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return _EXIT_CHANGED if result.obligating else _EXIT_OK

    everything = result.causes + result.unattributed + result.unclassifiable
    if not everything:
        print(f"nothing drifted between {result.base[:10]} and {result.head[:10]}")
        return _EXIT_OK

    width = max(len(c.claim_id) for c in everything)
    for cause in result.causes:
        mark = f"[{cause.recorded}]" if cause.recorded else "unrecorded"
        status = cause.drift.status.value if cause.drift.status else "unclassified"
        print(f"{cause.claim_id:{width}}  {status:11}  {mark}")
        for sha, author, subject in cause.commits[:4]:
            print(f"{'':{width}}    {sha[:10]}  {author:16.16}  {subject[:60]}")
        if len(cause.commits) > 4:
            print(f"{'':{width}}    ... and {len(cause.commits) - 4} more")

    if result.unattributed:
        print(f"\ndrifted before {result.base[:10]}, so this range does not "
              f"explain them:")
        for cause in result.unattributed:
            status = cause.drift.status.value if cause.drift.status else "unclassified"
            print(f"  {cause.claim_id:{width}}  {status}")

    if result.unclassifiable:
        print("\ncould not be classified at all - not drift, and not a "
              "reviewer's problem:")
        for cause in result.unclassifiable:
            reason = cause.drift.errors[0][1] if cause.drift.errors else "unknown"
            print(f"  {cause.claim_id:{width}}  {reason[:64]}")

    sys.stdout.flush()
    owed = [c for c in result.obligating if not c.recorded]
    print(f"\n{len(result.obligating)} claim(s) need a verdict, {len(owed)} with no "
          f"ledger entry yet. `forge reconcile --since {args.since} --record` opens "
          f"one for each.", file=sys.stderr)
    return _EXIT_CHANGED if result.obligating else _EXIT_OK


def _cmd_hooks(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        print(f"forge: {repo} is not a git repository", file=sys.stderr)
        return _EXIT_USAGE

    if args.action == "status":
        state, target = hooks.installed_state(repo)
        where = target.relative_to(repo).as_posix() if target.is_relative_to(repo)             else target.as_posix()
        print({
            "absent": f"no {hooks.HOOK_NAME} hook at {where}",
            "ours": f"installed  {where}",
            "theirs": f"a {hooks.HOOK_NAME} hook exists at {where} and this tool "
                      f"did not write it",
        }[state])
        return _EXIT_OK if state != "theirs" else _EXIT_CHANGED

    if args.action == "uninstall":
        outcome, target = hooks.uninstall(repo)
        if outcome == "refused":
            print(f"forge: {target} was not written by this tool; remove it yourself",
                  file=sys.stderr)
            return _EXIT_USAGE
        print(f"{outcome:10} {target.as_posix()}")
        return _EXIT_OK

    outcome, target = hooks.install(repo, command=args.command, force=args.force)
    if outcome == "refused":
        wanted = "\n".join("    " + line for line in
                           hooks.hook_body(args.command).splitlines()[-3:])
        print(f"forge: {target} already exists and this tool did not write it. "
              f"Merge it by hand, or pass --force to replace it:\n\n{wanted}",
              file=sys.stderr)
        return _EXIT_USAGE
    print(f"{outcome:10} {target.as_posix()}")
    if outcome in ("installed", "replaced"):
        print("\nIt runs `forge check --scope store` and `forge drift --staged` on "
              "what you are about to commit.\nNeither runs your tests, and neither "
              "rewrites anything. `git commit --no-verify` skips both.")
    return _EXIT_OK


def _cmd_doctor(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    langs = available_languages()
    print(f"python           {sys.version.split()[0]}")
    print(f"grammars         {', '.join(langs) if langs else 'none (all anchors will be coarse)'}")
    try:
        version = gitio.git(repo, "--version").strip()
    except gitio.GitError as exc:
        print(f"git              unavailable: {exc}")
        return _EXIT_USAGE
    print(f"git              {version.removeprefix('git version ')}")

    # The project's own commands, checked here rather than twenty minutes into
    # its first `forge verify`. On `requests`, bootstrap detected the bare
    # `pytest` and `ruff check .`; neither was on PATH, and the first thing
    # that said so was a verification run that had already taken the suite's
    # full running time to get there.
    declared = verify.commands(repo)
    if not declared:
        print("commands         none declared in .forge/config.yaml")
        # `bootstrap derive` reads these off the project's own manifests and
        # prints them; only `bootstrap seal` writes them to config. Between the
        # two, doctor used to say "none declared" on a repository where derive
        # had just listed four - the same facts, and the tool disagreeing with
        # itself about them.
        detectable = bootstrap.detect_commands(repo)
        if detectable:
            print(f"{'':16} but this project's manifests declare "
                  f"{len(detectable)}: "
                  + ", ".join(f"{k} ({v})" for k, v in sorted(detectable.items())))
            print(f"{'':16} `forge bootstrap seal` writes them, or copy them into "
                  f".forge/config.yaml by hand")
        return _EXIT_OK

    unresolved = 0
    for name in sorted(declared):
        line = declared[name]
        problem = verify.resolve_command(repo, line)
        if problem:
            unresolved += 1
            print(f"{name:16} {line}\n{'':16} {problem}")
        else:
            print(f"{name:16} {line}")
    return _EXIT_CHANGED if unresolved else _EXIT_OK


def build_parser() -> argparse.ArgumentParser:
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
    drift.add_argument("anchor", nargs="*", help="path[#Symbol][@sha]")
    # Not `--store` as the default when no anchor is given: this repository's
    # own tests and measurement tools already script `forge drift <anchor>`,
    # and silently changing what a bare invocation means is the kind of break
    # that is found in somebody's CI. Making it the default is its own change.
    scan = drift.add_mutually_exclusive_group()
    scan.add_argument("--store", action="store_true",
                      help="read every anchor from the claim store")
    scan.add_argument("--changed", action="store_true",
                      help="--store, narrowed to claims anchoring files in the diff")
    drift.add_argument("--unrecorded", action="store_true",
                       help="report only drift with no open ledger entry - what a "
                            "pre-commit hook can honestly demand")
    scan.add_argument("--staged", action="store_true",
                      help="--store, narrowed to what is staged, and compared "
                           "against the index rather than HEAD. The form a "
                           "pre-commit hook needs")
    drift.add_argument("--repo", type=Path, default=Path.cwd())
    drift.add_argument("--baseline", help="overrides each anchor's @sha")
    drift.add_argument("--head", default="HEAD")
    drift.add_argument("--json", action="store_true")
    # The ledger verbs live in the first positional rather than in argparse
    # subparsers, because subparsers would take that slot from `forge drift
    # <anchor>` - a form this repository's own tests and measurement tools
    # already script. `forge drift resolve D-014 --verdict V3` is the spelling
    # SYSTEM_KNOWLEDGE.md section 6 specifies, and it is worth keeping both.
    led = drift.add_argument_group(
        "the drift ledger",
        "forge drift record | list | resolve <id> | confirm <id> | waive <id>")
    led.add_argument("--verdict", help="V1 | V2 | V3 | V4, for `resolve`")
    led.add_argument("--evidence", help="how a V2 or V4 is known")
    led.add_argument("--adr", help="the decision a V3 rests on")
    led.add_argument("--accept-asserted", action="store_true",
                     help="record on purpose that a V4's sharper claim is still "
                          "only asserted")
    led.add_argument("--until", help="when a waiver expires: a date or a commit")
    led.add_argument("--reason", help="why a waiver is justified")
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
    chg_show.add_argument("change", nargs="?",
                           help="the change, by number or slug")
    chg_show.add_argument("--change", dest="change_flag",
                           help="the same thing, spelled the way "
                                "every other command spells it")
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
    chg_track.add_argument("change", nargs="?",
                           help="the change, by number or slug")
    chg_track.add_argument("--change", dest="change_flag",
                           help="the same thing, spelled the way "
                                "every other command spells it")
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
    ver.add_argument("--timeout", type=int, default=None,
                     help="seconds per command; default `commands.timeout` "
                          f"in .forge/config.yaml, else {verify.DEFAULT_TIMEOUT}")
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
    instr.add_argument(
        "--write", nargs="?", const="", metavar="NAME",
        help="also scaffold the artifact file from its template, if absent. "
             "NAME names the file for an artifact that generates a glob "
             "(`--write payments` writes spec/payments.md)")
    instr.add_argument("--repo", type=Path, default=Path.cwd())
    instr.add_argument("--json", action="store_true")
    instr.set_defaults(func=_cmd_instructions)

    skl = sub.add_parser("skill", help="list, read and check the skills")
    skl_sub = skl.add_subparsers(dest="skill_command", required=True)
    skl_list = skl_sub.add_parser("list", help="the skills this project ships")
    skl_list.add_argument("--repo", type=Path, default=Path.cwd())
    skl_list.add_argument("--json", action="store_true")
    skl_list.set_defaults(func=_cmd_skill_list)
    skl_show = skl_sub.add_parser("show", help="print one skill")
    skl_show.add_argument("name")
    skl_show.add_argument("--repo", type=Path, default=Path.cwd())
    skl_show.set_defaults(func=_cmd_skill_show)
    skl_export = skl_sub.add_parser(
        "export",
        help="write the manifest a second host reads",
        description="OPEN_QUESTIONS.md Q12 bet that a second host costs a manifest "
                    "rather than a port, because the mechanism is in the CLI and the "
                    "procedures are plain markdown. Adding a host here is adding a "
                    "table entry; if one ever needs more, the bet was wrong and the "
                    "cost is visible in one file.",
    )
    skl_export.add_argument("--host", required=True, choices=sorted(hosts.HOSTS))
    skl_export.add_argument("--repo", type=Path, default=Path.cwd())
    skl_export.set_defaults(func=_cmd_skill_export)

    boot = sub.add_parser(
        "bootstrap",
        help="give an existing repository a store it can trust",
        description="Three passes. Pass 1 derives and claims nothing; pass 2 is a "
                    "skill that proposes candidates; pass 3 is a human ratifying, "
                    "and the default is reject.",
    )
    boot_sub = boot.add_subparsers(dest="bootstrap_command", required=True)

    boot_derive = boot_sub.add_parser(
        "derive",
        help="pass 1: what a scan can see, and what it cannot",
        description="Deterministic and re-runnable. Nothing it prints is a claim.",
    )
    boot_derive.add_argument("--repo", type=Path, default=Path.cwd())
    boot_derive.add_argument("--json", action="store_true")
    boot_derive.set_defaults(func=_cmd_bootstrap_derive)

    boot_review = boot_sub.add_parser(
        "review",
        help="pass 3: write and read the candidate review sheet",
        description="Ordered highest-value kind first, batched, every verdict "
                    "prefilled `reject`. Edits already recorded are preserved.",
    )
    boot_review.add_argument("--cap", type=int, default=bootstrap.DEFAULT_CAP)
    boot_review.add_argument("--repo", type=Path, default=Path.cwd())
    boot_review.add_argument("--json", action="store_true")
    boot_review.set_defaults(func=_cmd_bootstrap_review)

    boot_seal = boot_sub.add_parser(
        "seal",
        help="write the ratified claims, the overview and the baseline ADR",
        description="Anchors are stamped at HEAD and `reviewed` set to today, "
                    "because this is the moment a human confirmed them.",
    )
    boot_seal.add_argument("--cap", type=int, default=bootstrap.DEFAULT_CAP)
    boot_seal.add_argument("--dry-run", action="store_true")
    boot_seal.add_argument("--repo", type=Path, default=Path.cwd())
    boot_seal.add_argument("--json", action="store_true")
    boot_seal.set_defaults(func=_cmd_bootstrap_seal)

    rec = sub.add_parser(
        "reconcile",
        help="what drifted while nobody was looking, and which commits did it",
        description="The recovery path the pre-commit hook needs beside it, because "
                    "the hook will be bypassed: --no-verify, a colleague's commits, a "
                    "dependency bot, or a repository adopting the harness after years "
                    "of history. Records nothing unless asked.",
    )
    rec.add_argument("--since", required=True, metavar="REV",
                     help="the commit to look back to")
    rec.add_argument("--head", default="HEAD")
    rec.add_argument("--record", action="store_true",
                     help="open a ledger entry for each drifted claim that has none")
    rec.add_argument("--repo", type=Path, default=Path.cwd())
    rec.add_argument("--json", action="store_true")
    rec.set_defaults(func=_cmd_reconcile)

    hk = sub.add_parser(
        "hooks",
        help="install the pre-commit hook, the one integration point worth taking",
        description="Catches drift at the moment it is created, while the reason "
                    "is still in somebody's head - which is what stops a busy week "
                    "from ending in a wall of findings nobody reads.",
    )
    hk.add_argument("action", nargs="?", default="status",
                    choices=("status", "install", "uninstall"))
    hk.add_argument("--repo", type=Path, default=Path.cwd())
    hk.add_argument("--command", default="forge",
                    help="how this machine invokes the kernel, if not `forge` on PATH")
    hk.add_argument("--force", action="store_true",
                    help="replace a pre-commit hook this tool did not write")
    hk.set_defaults(func=_cmd_hooks)

    doctor = sub.add_parser(
        "doctor",
        help="report the toolchain the kernel found, and whether this project's "
             "declared commands resolve",
        description="Exits 1 when a declared command cannot be run, so the first "
                    "thing a new project hears about an unresolvable `commands.test` "
                    "is this, not a verification that spent the suite's full running "
                    "time to say the same.",
    )
    doctor.add_argument("--repo", type=Path, default=Path.cwd())
    doctor.set_defaults(func=_cmd_doctor)

    return parser


def _survive_the_console() -> None:
    """Never crash for want of a character the terminal cannot draw.

    The harness prints repository content - claim titles, test names, a failing
    command's output - and repositories are written by people, in their own
    languages, with tools that emit `✓`. A Windows console at cp1252 cannot
    encode most of that, and the default `strict` handler turns it into an
    uncaught `UnicodeEncodeError`.

    Found the hard way: the fix that made `forge verify` report *what* failed
    made it crash instead, on a vitest tick, on the very next run.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            # Not a real stream - captured in a test, piped, redirected to a
            # file object without reconfigure. Printing is best-effort here and
            # a failure to harden must not become the crash it prevents.
            pass


def main(argv: list[str] | None = None) -> int:
    _survive_the_console()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
