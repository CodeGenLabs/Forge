"""Declarative gates: `(point, check, blocking)` triples, run by name.

GSD's model, kept and shrunk. The number is a budget, not an accident: ten
gates at nine points, against GSD's fourteen at `plan:pre` alone. Every gate
has to be justifiable in one sentence, and gates that never fire get deleted.

Two rules the runner enforces, both about honesty:

**A check the kernel does not implement never passes silently.** It reports
`gate.unavailable` and names the milestone that will bring it. A gate that
quietly succeeds because nobody wrote its check is worse than no gate, because
it is evidence of a check that did not happen.

**`blocking` decides the exit code, not whether the check runs.** A
non-blocking gate still reports what it found. The distinction is about
whether the lifecycle stops, never about whether the reader is told.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from . import change, derive, gitio, impact, spec, validate
from .config import load_config
from .validate import Issue

__all__ = ["Gate", "GateResult", "DEFAULT_GATES", "POINTS", "load_gates", "run_gate"]

# The gate table from ARCHITECTURE.md section 3.3. Written as text for the
# same reason the workflow schema is: a project overrides it by editing YAML,
# and the default must go through the same loader as the override.
#
# *Deviation, recorded here because ARCHITECTURE.md says "twelve gates at ten
# points" and then lists ten at nine. The list is the specification; the count
# was a sentence written before it. Rather than invent two gates to reach
# twelve, the list is implemented as written.*
_DEFAULT_GATES_YAML = """\
- point: investigate:pre
  check: derived.freshness
  blocking: false
  onError: skip
- point: spec:post
  check: store.spec_grammar
  blocking: true
- point: impact:post
  check: trace.claim_touch_complete
  blocking: true
- point: analyze:post
  check: trace.requirement_task_coverage
  blocking: true
- point: implement:pre
  check: derived.freshness
  blocking: true
- point: implement:task:post
  check: task.scope_and_covers
  blocking: true
- point: verify:post
  check: verify.definition_of_done
  blocking: true
- point: verify:post
  check: drift.rules_conformance
  blocking: true
- point: sync:pre
  check: store.valid
  blocking: true
- point: converge:post
  check: repo.clean
  blocking: true
"""


@dataclass(frozen=True)
class Gate:
    point: str
    check: str
    blocking: bool = True
    on_error: str = "fail"      # "fail" | "skip"

    def to_dict(self) -> dict:
        return {"point": self.point, "check": self.check,
                "blocking": self.blocking, "onError": self.on_error}


@dataclass
class GateResult:
    gate: Gate
    issues: list[Issue]
    available: bool = True

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def blocks(self) -> bool:
        """Whether this result should stop the lifecycle.

        `onError: skip` is the escape hatch for a gate whose inputs may
        legitimately not exist yet - `derived.freshness` at `investigate:pre`
        on a repository that has never run `forge sync derived`.
        """
        if self.passed or not self.gate.blocking:
            return False
        return self.gate.on_error != "skip"

    def to_dict(self) -> dict:
        return {
            **self.gate.to_dict(),
            "available": self.available,
            "passed": self.passed,
            "blocks": self.blocks,
            "issues": [i.to_dict() for i in self.issues],
        }


def load_gates(repo: Path) -> list[Gate]:
    """The project's `gates:` list if it has one, else the kernel's."""
    target = repo / ".forge/config.yaml"
    raw = None
    if target.is_file():
        try:
            loaded = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict) and isinstance(loaded.get("gates"), list):
                raw = loaded["gates"]
        except (OSError, yaml.YAMLError):
            raw = None
    if raw is None:
        raw = yaml.safe_load(_DEFAULT_GATES_YAML)

    gates: list[Gate] = []
    for entry in raw:
        if not isinstance(entry, dict) or not entry.get("point") or not entry.get("check"):
            continue
        gates.append(Gate(
            point=str(entry["point"]),
            check=str(entry["check"]),
            blocking=bool(entry.get("blocking", True)),
            on_error=str(entry.get("onError") or entry.get("on_error") or "fail"),
        ))
    return gates


def points(repo: Path) -> list[str]:
    """The points this repository actually declares, in table order."""
    seen: list[str] = []
    for gate in load_gates(repo):
        if gate.point not in seen:
            seen.append(gate.point)
    return seen


#: The default points, for `--help` and for argument completion. A project
#: that overrides `gates:` may add its own; `points()` is the live answer and
#: this is only the advertised one.
POINTS = (
    "investigate:pre", "spec:post", "impact:post", "analyze:post",
    "implement:pre", "implement:task:post", "verify:post", "sync:pre",
    "converge:post",
)


# ---------------------------------------------------------------------------
# The checks, by name
# ---------------------------------------------------------------------------

def _deltas(repo: Path, item: change.Change) -> list[spec.Delta]:
    out = []
    for path in spec.delta_files(repo, item.relative):
        out.append(spec.parse_delta(
            (repo / path).read_text(encoding="utf-8", errors="replace"),
            path, spec.capability_of(path, item.relative),
        ))
    return out


def _check_derived_freshness(repo: Path, item: change.Change | None) -> list[Issue]:
    issues = []
    if not any((repo / derive.DERIVED_DIR / a.name).exists() for a in derive.ARTIFACTS):
        return [Issue(
            "ERROR", "derived.not_built", derive.DERIVED_DIR,
            "the derived tier has never been built, so nothing that reads it can be "
            "trusted at this point",
            "forge sync derived",
        )]
    for name, changed in derive.derive_all(repo, dry_run=True).items():
        if changed:
            issues.append(Issue(
                "ERROR", "derived.dirty", f"{derive.DERIVED_DIR}/{name}",
                "regenerating produces different bytes; it was hand-edited or is stale",
                "forge sync derived",
            ))
    behind = max((v for v in derive.stale_artifacts(repo).values() if v is not None),
                 default=0)
    threshold = load_config(repo).derived_stale_commits
    if not issues and behind > threshold:
        issues.append(Issue(
            "WARNING", "derived.freshness", derive.DERIVED_DIR,
            f"the derived tier was produced {behind} commits ago, over the "
            f"threshold of {threshold}",
            "forge sync derived - the content still matches, but nothing has "
            "re-checked it in a while",
        ))
    return issues


def _check_spec_grammar(repo: Path, item: change.Change | None) -> list[Issue]:
    if item is None:
        return [_needs_change("store.spec_grammar")]
    deltas = _deltas(repo, item)
    issues = [i for delta in deltas for i in spec.check_delta(repo, delta, Issue)]
    issues.extend(spec.check_nonempty(item, deltas, Issue))
    return issues


def _check_claim_touch(repo: Path, item: change.Change | None) -> list[Issue]:
    if item is None:
        return [_needs_change("trace.claim_touch_complete")]
    return impact.check_claim_touch(repo, item, impact.compute_impact(repo, item), Issue)


def _check_task_coverage(repo: Path, item: change.Change | None) -> list[Issue]:
    if item is None:
        return [_needs_change("trace.requirement_task_coverage")]
    return spec.check_task_coverage(item, _deltas(repo, item), Issue)


def _check_store_valid(repo: Path, item: change.Change | None) -> list[Issue]:
    return validate.check_store(repo)


def _check_repo_clean(repo: Path, item: change.Change | None) -> list[Issue]:
    dirty = gitio.git(repo, "status", "--porcelain", check=False).strip()
    if not dirty:
        return []
    files = [line[3:] for line in dirty.splitlines()][:8]
    return [Issue(
        "ERROR", "repo.clean", ".",
        f"the working tree has uncommitted changes: {', '.join(files)}"
        + (" ..." if len(dirty.splitlines()) > 8 else ""),
        "commit or stash them; converge archives the change, and an archive taken "
        "over a dirty tree records a state that never existed",
    )]


def _check_definition_of_done(repo: Path, item: change.Change | None) -> list[Issue]:
    if item is None:
        return [_needs_change("verify.definition_of_done")]
    from .verify import read_verification

    report = read_verification(repo, item)
    if report is None:
        return [Issue(
            "ERROR", "verify.definition_of_done", f"{item.relative}/verification.json",
            "no verification report; nothing has been verified at this point",
            f"forge verify --change {item.number}",
        )]
    if report.get("verdict") == "pass":
        return []
    failing = [name for name, gate in (report.get("gates") or {}).items()
               if gate.get("status") not in ("pass", "waived", "skipped")]
    return [Issue(
        "ERROR", "verify.definition_of_done", f"{item.relative}/verification.json",
        f"verification verdict is {report.get('verdict')!r}; failing: "
        f"{', '.join(failing) or 'unknown'}",
        f"fix what failed and re-run `forge verify --change {item.number}`. Tests "
        f"passing is one of eight conditions, not the condition",
    )]


def _needs_change(check: str) -> Issue:
    return Issue(
        "ERROR", "gate.needs_change", ".",
        f"{check} is about one change and none was named",
        "pass --change N",
    )


def _unavailable(check: str, milestone: str) -> list[Issue]:
    """A check the kernel does not implement yet.

    Reported, never passed. A gate that succeeds because nobody wrote its
    check is worse than no gate: it is evidence of a check that did not happen.
    """
    return [Issue(
        "WARNING", "gate.unavailable", ".",
        f"{check} is not implemented yet, so this gate proves nothing. Owed by: "
        f"{milestone}",
        "check it by hand at this point, and do not read the gate's silence as a pass",
    )]


CHECKS = {
    "derived.freshness": _check_derived_freshness,
    "store.spec_grammar": _check_spec_grammar,
    "trace.claim_touch_complete": _check_claim_touch,
    "trace.requirement_task_coverage": _check_task_coverage,
    "store.valid": _check_store_valid,
    "repo.clean": _check_repo_clean,
    "verify.definition_of_done": _check_definition_of_done,
}

#: Checks the gate table names that no milestone has built. Listed rather than
#: omitted, so `forge gate` can say *which* milestone owes each one instead of
#: reporting an unknown name.
PENDING = {
    "task.scope_and_covers": "M4, which brings per-task execution records",
    "drift.rules_conformance": "the rule tier: .forge/rules/ and its back-references",
}


def run_gate(repo: Path, point: str, item: change.Change | None) -> list[GateResult]:
    """Every gate declared at *point*. An unknown point returns []."""
    results: list[GateResult] = []
    for gate in load_gates(repo):
        if gate.point != point:
            continue
        runner = CHECKS.get(gate.check)
        if runner is None:
            milestone = PENDING.get(gate.check, "no milestone: this check has no owner")
            results.append(GateResult(gate, _unavailable(gate.check, milestone),
                                      available=False))
            continue
        results.append(GateResult(gate, runner(repo, item)))
    return results
