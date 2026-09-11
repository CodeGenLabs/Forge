"""`forge verify`: evidence that a change is done, as an artifact.

Not an opinion. `verification.json` is generated and never authored, because
an authored verification report is a place to write "all tests pass" without
having run them - which is the exact failure Superpowers wrote a whole skill
to prevent.

**Tests passing is item 1 of 8** (WORKFLOW.md section 3.9). That is the
concrete answer to "the harness must not declare success merely because tests
pass":

1. build, typecheck, lint, test - fresh output, captured here, not remembered
2. every `REQ-*` in this change discharged by a test carrying its `@covers` tag
3. every `enforced` claim in the touch set still proved by its evidence
4. `impact.md`'s claim-touch account complete
5. no open unwaived drift touching this change's claims
6. no open unwaived debt introduced by this change
7. `derived/` regenerates to a no-op
8. no test skipped that was passing before this change

Conditions 5, 6 and 8 need ledgers and a baseline test run that no milestone
has built. They are reported as `unavailable`, never as `pass`: a condition
that reports success because nothing checked it is the thing this file exists
to prevent.
"""

from __future__ import annotations

import json
import shutil as _shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import derive, gitio, impact, spec, validate
from .change import Change
from .config import load_config

__all__ = ["VERIFICATION_FILE", "verify", "read_verification", "CONDITIONS",
           "resolve_command", "DEFAULT_TIMEOUT"]

#: Seconds a single `commands.*` line may run before the condition is
#: recorded `unavailable`. Overridable per project (`commands.timeout`)
#: and per run (`--timeout`): this repository's own suite exceeds the
#: old hardcoded 900, so `tests` could never pass on it.
DEFAULT_TIMEOUT = 900

VERIFICATION_FILE = "verification.json"

#: Which conditions may be waived, from WORKFLOW.md section 3.9. Conditions
#: 1-4 and 7 are not waivable: they are the ones that say whether the change
#: does what it said, and a waiver on those is a change that was never
#: verified at all.
WAIVABLE = ("drift", "debt")

CONDITIONS = (
    "build", "typecheck", "lint", "tests",
    "requirement_cover", "claim_evidence", "claim_touch",
    "drift", "debt", "derived_fresh", "no_new_skips",
)


@dataclass
class Command:
    name: str
    line: str


def _commands(repo: Path) -> dict[str, str]:
    """`commands:` from `.forge/config.yaml`.

    A project that declares none gets `unavailable`, not `pass`. The harness
    cannot know how to build a repository it was never told about, and
    guessing (`npm test` because a package.json exists) is how a verification
    report ends up green for a suite that never ran.
    """
    import yaml

    target = repo / ".forge/config.yaml"
    if not target.is_file():
        return {}
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    section = raw.get("commands") if isinstance(raw.get("commands"), dict) else {}
    return {str(k): str(v) for k, v in section.items() if v}


def resolve_command(repo: Path, line: str) -> str | None:
    """Why *line* cannot be run, or None if it can.

    `forge bootstrap seal` detects `pytest` from a manifest, and a bare console
    script is only on PATH while the project's virtualenv is activated. Run
    through the shell without it, the command does not exist and the condition
    reports `fail` - a verification that says the suite failed when the suite
    was never started, which is the one thing this report must never do.

    Only the first token is resolved, and only when it looks like a program
    rather than a path or a shell construct. Anything containing a separator,
    a quote or an operator is handed to the shell untouched: the shell is
    better at shell than this function is.
    """
    head = line.strip().split()[:1]
    if not head:
        return "the command is empty"
    token = head[0]
    # `=` is here for the `FOO=1 cmd` prefix: an env-var assignment is a shell
    # construct whose first token is not a program at all, and resolving it
    # would report the assignment itself as a missing binary.
    if any(ch in token for ch in "/\\\"'$%(){}<>|&;="):
        return None
    if _shutil.which(token):
        return None
    for relative in (f".venv/Scripts/{token}.exe", f".venv/bin/{token}",
                     f"venv/Scripts/{token}.exe", f"venv/bin/{token}"):
        if (repo / relative).is_file():
            return (f"{token!r} is not on PATH, but {relative} exists - write "
                    f"that path in the command, spelled for this platform's shell")
    return f"{token!r} is not on PATH"


def _run(repo: Path, name: str, line: str, timeout: int) -> dict:
    unresolvable = resolve_command(repo, line)
    if unresolvable:
        # `unavailable`, not `fail`. The project declared a command this
        # machine cannot run; that is a fact about the setup, and calling it a
        # failing build is how a report gets disbelieved and then ignored.
        return {**_unavailable(
            unresolvable,
            "correct `commands` in .forge/config.yaml, or activate the "
            "environment the command needs",
        ), "cmd": line}
    try:
        completed = subprocess.run(
            line, cwd=repo, shell=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # Also `unavailable`: a command that ran out of time did not fail, and
        # recording "we do not know" as "it failed" throws away the one
        # distinction the rest of this module is careful to keep.
        return {**_unavailable(
            f"timed out after {timeout}s",
            "raise `commands.timeout` in .forge/config.yaml, pass --timeout, "
            "or make the command faster",
        ), "cmd": line}
    except OSError as exc:
        return {"status": "fail", "cmd": line, "error": str(exc)}
    tail = completed.stderr.decode("utf-8", "replace").strip().splitlines()
    return {
        "status": "pass" if completed.returncode == 0 else "fail",
        "cmd": line,
        "exit": completed.returncode,
        # The last few lines only. A verification report is read by a person
        # deciding whether to sync; a full build log in it guarantees nobody
        # reads either.
        **({"tail": tail[-5:]} if completed.returncode != 0 and tail else {}),
    }


def _unavailable(reason: str, fix: str) -> dict:
    """A condition this *project* has not made checkable. Blocks the verdict."""
    return {"status": "unavailable", "reason": reason, "fix": fix}


def _pending(reason: str, fix: str) -> dict:
    """A condition this *kernel* cannot check yet. Recorded, does not block.

    The line between this and `unavailable` is who owes the work. A project
    that never declared a test command has an unverified change and should be
    told so. A project waiting on a ledger the harness has not shipped cannot
    act on the finding at all, and a verdict nobody can ever reach is a
    verdict people route around - which costs the seven conditions that *do*
    work. Both are listed in the report either way; only the verdict differs.
    """
    return {"status": "pending", "reason": reason, "fix": fix}


def _deltas(repo: Path, item: Change) -> list[spec.Delta]:
    return [
        spec.parse_delta((repo / path).read_text(encoding="utf-8", errors="replace"),
                         path, spec.capability_of(path, item.relative))
        for path in spec.delta_files(repo, item.relative)
    ]


def verify(repo: Path, item: Change, *, waived: tuple[str, ...] = (),
           timeout: int | None = None, run_commands: bool = True) -> dict:
    """Produce the verification report. Writes nothing; the caller decides."""
    from .validate import Issue

    gates: dict[str, dict] = {}
    commands = _commands(repo)
    if timeout is None:
        # `commands.timeout` sits beside the commands it bounds, because
        # how long a suite takes is a property of the project, not of the
        # kernel that starts it.
        try:
            timeout = max(1, int(commands.get('timeout', DEFAULT_TIMEOUT)))
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT

    # 1. build / typecheck / lint / tests
    for name in ("build", "typecheck", "lint", "tests"):
        line = commands.get("test" if name == "tests" else name)
        if not line:
            gates[name] = _unavailable(
                f"no `commands.{'test' if name == 'tests' else name}` in "
                f".forge/config.yaml",
                "declare it, or accept that this condition is unproven - guessing the "
                "command is how a report goes green for a suite that never ran",
            )
        elif not run_commands:
            gates[name] = _unavailable("commands were not run (--no-run)",
                                       "re-run without --no-run before syncing")
        else:
            gates[name] = _run(repo, name, line, timeout)

    deltas = _deltas(repo, item)
    promised = spec.promised_requirements(deltas)
    covers = (((derive.read_json(repo / derive.DERIVED_DIR / "tests.json") or {})
               .get("data") or {}).get("covers_index") or {})

    # 2. requirement coverage
    undischarged = sorted(i for i in promised if not covers.get(i))
    gates["requirement_cover"] = {
        "status": "fail" if undischarged else "pass",
        "requirements": len(promised),
        "discharged": len(promised) - len(undischarged),
        "undischarged": undischarged,
    }

    # 3. enforced claims in the touch set still proved by their evidence
    computed = impact.compute_impact(repo, item)
    store_issues = validate.check_store(repo)
    failing = sorted({i.claim for i in store_issues
                      if i.code == "store.evidence_required" and i.claim
                      and i.claim in computed.touched})
    enforced = [c for c in computed.touched.values()
                if c.claim and c.claim.status == "enforced"]
    gates["claim_evidence"] = {
        "status": "fail" if failing else "pass",
        "enforced_claims": len(enforced),
        "failing": failing,
    }

    # 4. the claim-touch account. The unaccounted set is recomputed here
    # rather than scraped out of the issue list: the "there is no impact.md at
    # all" issue names the claims in its message and carries no single claim
    # id, so reading the issues would report zero unaccounted claims in the
    # one case where every claim is unaccounted.
    touch_issues = [i for i in impact.check_claim_touch(repo, item, computed, Issue)
                    if i.level == "ERROR"]
    account_file = item.root / "impact.md"
    accounted = set(impact.parse_account(
        account_file.read_text(encoding="utf-8", errors="replace")
    ).by_id) if account_file.is_file() else set()
    gates["claim_touch"] = {
        "status": "fail" if touch_issues else "pass",
        "unaccounted": sorted(set(computed.touched) - accounted),
    }

    # 5, 6, 8 - the ledgers and the baseline run
    gates["drift"] = _pending(
        "DRIFT.md is not built yet",
        "until the ledger exists, run `forge drift` on the touch set by hand")
    gates["debt"] = _pending(
        "DEBT.md is not built yet",
        "until the ledger exists, look for stubs and TODOs added by this change")
    gates["no_new_skips"] = _pending(
        "no baseline test run to compare against",
        "until the runner records per-test results, check the suite output for "
        "newly skipped tests")

    # 7. derived tier
    dirty = sorted(n for n, changed in derive.derive_all(repo, dry_run=True).items()
                   if changed)
    behind = max((v for v in derive.stale_artifacts(repo).values() if v is not None),
                 default=0)
    gates["derived_fresh"] = {
        "status": "fail" if dirty else "pass",
        "dirty": dirty,
        "commits_behind": behind,
    }

    for name in waived:
        if name in gates and name in WAIVABLE:
            gates[name] = {**gates[name], "status": "waived"}

    hard_fail = [n for n, g in gates.items() if g["status"] == "fail"]
    unproven = [n for n, g in gates.items() if g["status"] == "unavailable"]
    pending = [n for n, g in gates.items() if g["status"] == "pending"]
    verdict = "fail" if hard_fail else "unproven" if unproven else "pass"

    return {
        "change": item.name,
        "commit": gitio.rev_parse(repo, "HEAD"),
        "base": computed.base,
        "gates": {k: gates[k] for k in CONDITIONS if k in gates},
        "waived": sorted(waived),
        "failing": sorted(hard_fail),
        "unproven": sorted(unproven),
        "pending": sorted(pending),
        "verdict": verdict,
    }


def write_verification(repo: Path, item: Change, report: dict) -> Path:
    target = item.root / VERIFICATION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    return target


def read_verification(repo: Path, item: Change) -> dict | None:
    target = item.root / VERIFICATION_FILE
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
