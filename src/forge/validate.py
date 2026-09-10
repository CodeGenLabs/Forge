"""The store checks: S1-S18 from [MVP.md](../../MVP.md) section 3.

Every check here is a script. None calls a model, none reads the network, and
each one is a pure function of the repository at a commit - which is the whole
reason a gate built on them can be trusted (CONSTITUTION.md).

Two rules shape the module:

**Every ERROR carries a `fix` naming the command or the edit that resolves it.**
An error message without a next action trains people to ignore errors, and a
store people ignore is worse than no store.

**Anti-noise checks are warnings, never errors.** S13-S15 and S17 are
heuristics about *writing quality*, and a heuristic that blocks a commit gets
disabled within a week. Each has an explicit acknowledgement comment that
silences it, so disagreeing with the heuristic is a recorded decision rather
than a deleted check.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

from . import derive, gitio, store
from .anchor import AnchorError, parse_anchor
from .config import Config, load_config
from .fingerprint import find_symbol, language_for_path, symbol_appears_textually

__all__ = ["Issue", "check_store", "ALWAYS_LOADED", "STORE_CODES"]

# ---------------------------------------------------------------------------
# Vocabulary the checks enforce. Every value here is from SYSTEM_KNOWLEDGE.md
# section 1.2; changing one is a design change, not a tuning knob.
# ---------------------------------------------------------------------------

STATUSES = ("enforced", "asserted", "proposed", "retired")
TRUTH_SOURCES = ("code", "tests", "config", "spec", "decision", "derived")
CONFIDENCES = ("high", "medium", "low")
EVIDENCE_KINDS = ("test", "rule", "contract", "check")

#: Kinds whose `anchors` may legitimately be empty: a constraint originates
#: outside the repository and a concept is vocabulary with no single home.
#: Every other kind must anchor, because an unanchored claim can never be
#: checked and will silently rot (SYSTEM_KNOWLEDGE.md section 1.2, note 1).
UNANCHORED_KINDS = ("concept", "constraint")

#: The set loaded into every agent context, and therefore the set with a hard
#: line budget (SYSTEM_KNOWLEDGE.md section 7.2 check 18).
ALWAYS_LOADED = (
    "docs/system/OVERVIEW.md",
    "docs/system/architecture.md",
    "docs/system/components.md",
    "docs/system/domain.md",
    "docs/system/pitfalls.md",
)

STORE_CODES = (
    "store.id_format", "store.id_unique", "store.claim_fence",
    "store.required_fields", "store.anchor_required", "store.evidence_required",
    "store.adr_required", "store.governs_dag", "store.placeholder",
    "store.candidate_isolation", "store.prose_present", "store.anchor_missing",
    "store.derivable_smell", "store.listing_smell", "store.stack_fact_smell",
    "store.budget", "store.orphan", "store.retire_ground",
)

_MVP_PREFIXES = ("ARC", "CMP", "CON", "INV", "PIT")

# A heading that is *trying* to be a claim. Deliberately laxer than
# `store._HEADING_RE`: the strict pattern silently skips a malformed ID, which
# is the failure mode S1 exists to catch. A claim nobody can see is worse than
# a claim that fails a check.
_LOOSE_HEADING_RE = re.compile(
    r"^###\s+(?P<id>[A-Za-z]{2,6}[-_][A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:[—-]\s*(?P<title>.*))?$",
    re.M,
)
_STRICT_ID_RE = re.compile(r"\A(?:" + "|".join(store.KIND_PREFIXES) + r")-(?:\d+|[a-z0-9][a-z0-9-]*)\Z")
_NUMERIC_ID_RE = re.compile(r"\A(?P<prefix>[A-Z]{2,4})-(?P<number>\d+)\Z")
_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_ADR_RE = re.compile(r"\AADR-\d{4}\Z")

_PLACEHOLDERS = (
    (re.compile(r"\bTBD\b"), "TBD"),
    (re.compile(r"\bTODO\b"), "TODO"),
    (re.compile(r"\bFIXME\b"), "FIXME"),
    (re.compile(r"\bXXX\b"), "XXX"),
    (re.compile(r"\[NEEDS CLARIFICATION"), "[NEEDS CLARIFICATION"),
    (re.compile(r"\{[a-z][a-z0-9_-]*\}"), "a {template-token}"),
    (re.compile(r"\bsimilar to\s+" + store.ANY_ID_PATTERN), "'similar to <ID>'"),
)

_MODALS = re.compile(
    r"\b(must not|may not|must|never|always|shall|cannot|is forbidden|is required)\b",
    re.I,
)
_IDENTIFIER_RE = re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]*\b|\b[a-z][a-z0-9]*_[a-z0-9_]+\b")
_BACKTICKED_RE = re.compile(r"`([^`\n]+)`")
_GLOB_RE = re.compile(r"[\w./*-]*[*][\w./*-]*|`[^`\n]*/[^`\n]*`")
_VERSION_NEAR_PACKAGE_RE = re.compile(
    r"\b([A-Za-z][\w.@/-]{1,40})\b[\s@:v=><~^]{0,4}\bv?\d+\.\d+(?:\.\d+)?\b"
)

# The acknowledgement comments that silence each anti-noise warning. They live
# in the claim's prose, so disagreeing with a heuristic is a line in the store
# with a reason attached rather than a flag in a config file nobody reads.
_ACK = {
    "store.derivable_smell": "forge:not-derivable",
    "store.listing_smell": "forge:not-a-listing",
    "store.stack_fact_smell": "forge:version-is-load-bearing",
    "store.orphan": "forge:intentionally-unreferenced",
}


@dataclass
class Issue:
    """One finding, in the shape every forge command emits.

    ARCHITECTURE.md section 4: `{level, code, path, line, claim, message, fix}`.
    Skills parse this and never the human-formatted rendering, so the keys are
    part of the interface.
    """

    level: str
    code: str
    path: str
    message: str
    fix: str
    line: int | None = None
    claim: str | None = None

    def to_dict(self) -> dict:
        out = {"level": self.level, "code": self.code, "path": self.path}
        if self.line is not None:
            out["line"] = self.line
        if self.claim is not None:
            out["claim"] = self.claim
        out["message"] = self.message
        out["fix"] = self.fix
        return out

    @property
    def sort_key(self) -> tuple:
        return (self.path, self.line or 0, self.code, self.claim or "")


def _error(code: str, claim: store.Claim, message: str, fix: str, *, line: int | None = None) -> Issue:
    return Issue("ERROR", code, claim.file, message, fix,
                 line=line if line is not None else claim.line, claim=claim.id)


def _warning(code: str, claim: store.Claim, message: str, fix: str) -> Issue:
    return Issue("WARNING", code, claim.file, message, fix, line=claim.line, claim=claim.id)


# ---------------------------------------------------------------------------
# Fence blanking (BMAD's `lint_spine.py` technique)
# ---------------------------------------------------------------------------

def blank_fences(text: str) -> str:
    """Replace fenced-code content with blank lines, preserving line numbers.

    Without this, every check that scans prose fires on the examples that
    document the check. This file's own design documents are the extreme case:
    SYSTEM_KNOWLEDGE.md contains a worked claim with `TBD` in it to show what
    is rejected. Blanking keeps the line count identical so a reported line
    number still points at the right line.
    """
    out: list[str] = []
    inside = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# S1, S2 - identity
# ---------------------------------------------------------------------------

def _check_ids(repo: Path, claims: list[store.Claim], texts: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []

    # S1. Scanned from the raw text rather than from parsed claims, because the
    # parser's strict heading pattern *skips* a malformed ID rather than
    # reporting it - so checking only what parsed would give a clean bill of
    # health to the exact file this check exists for.
    for path, text in texts.items():
        for match in _LOOSE_HEADING_RE.finditer(blank_fences(text)):
            identifier = match.group("id")
            if _STRICT_ID_RE.match(identifier):
                continue
            line = text.count("\n", 0, match.start()) + 1
            issues.append(Issue(
                "ERROR", "store.id_format", path,
                f"{identifier!r} is not a claim ID: expected "
                f"<PREFIX>-<digits|kebab-slug> with PREFIX one of "
                f"{', '.join(sorted(store.KIND_PREFIXES))}",
                f"rename the heading to a valid ID, e.g. "
                f"{_suggest_id(identifier)}",
                line=line, claim=identifier,
            ))

    # S2a. Uniqueness store-wide. An ID is a permanent name and the entire
    # traceability substrate; two claims sharing one makes `grep -r INV-7` an
    # ambiguous answer, and the index silently keeps whichever it saw last.
    seen: dict[str, store.Claim] = {}
    for claim in claims:
        first = seen.get(claim.id)
        if first is None:
            seen[claim.id] = claim
            continue
        issues.append(_error(
            "store.id_unique", claim,
            f"{claim.id} is already defined at {first.file}:{first.line}",
            "give one of them a new ID; an ID is a permanent name and is never reused",
        ))

    # S2b. Numeric IDs ascend within a file. Slugs have no ordering, so the
    # check applies only to the numeric form (SYSTEM_KNOWLEDGE.md section 7.1,
    # as revised).
    by_file: dict[str, list[store.Claim]] = {}
    for claim in claims:
        by_file.setdefault(claim.file, []).append(claim)
    for path, in_file in by_file.items():
        highest: dict[str, tuple[int, store.Claim]] = {}
        for claim in in_file:
            match = _NUMERIC_ID_RE.match(claim.id)
            if not match:
                continue
            prefix, number = match.group("prefix"), int(match.group("number"))
            previous = highest.get(prefix)
            if previous and number <= previous[0]:
                issues.append(_error(
                    "store.id_unique", claim,
                    f"{claim.id} does not ascend: {previous[1].id} appears above it "
                    f"at line {previous[1].line}",
                    f"move {claim.id} below {previous[1].id}, or give it the next free number",
                ))
            else:
                highest[prefix] = (number, claim)

    # S2c. Never reused. A retired claim keeps its ID forever, so an ID that
    # names a retired claim may not also name a live one.
    retired = {c.id for c in claims if c.status == "retired"}
    for claim in claims:
        if claim.status != "retired" and claim.id in retired:
            issues.append(_error(
                "store.id_unique", claim,
                f"{claim.id} is also the ID of a retired claim; retired IDs are never reused",
                f"give this claim a new ID - {claim.id} is the permanent name of what was retired",
            ))
    return issues


def _suggest_id(identifier: str) -> str:
    prefix, _, rest = identifier.replace("_", "-").partition("-")
    prefix = prefix.upper()
    if prefix not in store.KIND_PREFIXES:
        prefix = "CMP"
    slug = re.sub(r"[^a-z0-9-]+", "-", rest.lower()).strip("-") or "name"
    return f"{prefix}-{slug}"


# ---------------------------------------------------------------------------
# S3, S4, S5, S6, S7, S10, S18 - the claim block
# ---------------------------------------------------------------------------

def _check_block(
    claim: store.Claim,
    decisions: dict[str, dict],
    covers_index: dict[str, list[str]],
    today: _dt.date,
) -> list[Issue]:
    issues: list[Issue] = []

    # S3
    if claim.parse_error:
        return [_error(
            "store.claim_fence", claim,
            claim.parse_error,
            "the claim fence is ```claim followed by a YAML mapping and a closing ```",
        )]

    # S4 - presence, then range. Presence is checked against the keys the fence
    # declared, not against the parsed values: `anchors: []` is legal for a
    # concept and no `anchors` key at all never is, and after normalisation the
    # two are indistinguishable.
    for required in ("kind", "status", "truth-source", "anchors", "reviewed"):
        if required not in claim.fields:
            issues.append(_error(
                "store.required_fields", claim,
                f"required field {required!r} is missing",
                f"add {required}: to the claim fence",
            ))

    if claim.kind and claim.kind not in store.KIND_PREFIXES.values():
        issues.append(_error(
            "store.required_fields", claim,
            f"kind {claim.kind!r} is not a claim kind",
            f"use one of {', '.join(sorted(set(store.KIND_PREFIXES.values())))}",
        ))
    elif claim.kind and claim.kind != store.KIND_PREFIXES.get(claim.prefix):
        issues.append(_error(
            "store.required_fields", claim,
            f"kind {claim.kind!r} contradicts the {claim.prefix}- prefix, which means "
            f"{store.KIND_PREFIXES.get(claim.prefix)!r}",
            f"set kind: {store.KIND_PREFIXES.get(claim.prefix)}, or renumber under the right prefix",
        ))

    if claim.status and claim.status not in STATUSES:
        issues.append(_error(
            "store.required_fields", claim,
            f"status {claim.status!r} is not one of {', '.join(STATUSES)}",
            "set a status the checks understand; `asserted` is the honest default",
        ))
    if claim.truth_source and claim.truth_source not in TRUTH_SOURCES:
        issues.append(_error(
            "store.required_fields", claim,
            f"truth-source {claim.truth_source!r} is not one of {', '.join(TRUTH_SOURCES)}",
            "name the artifact that decides this claim; see SYSTEM_KNOWLEDGE.md section 3.1",
        ))
    if claim.confidence and claim.confidence not in CONFIDENCES:
        issues.append(_error(
            "store.required_fields", claim,
            f"confidence {claim.confidence!r} is not one of {', '.join(CONFIDENCES)}",
            f"use one of {', '.join(CONFIDENCES)}",
        ))
    if claim.reviewed is not None:
        issues.extend(_check_reviewed(claim, today))
    if claim.since is not None and not _ADR_RE.match(claim.since):
        issues.append(_error(
            "store.required_fields", claim,
            f"since {claim.since!r} is not an ADR id",
            "since: ADR-0014 - four digits, matching a file in docs/system/decisions/",
        ))

    # S5
    if not claim.anchors and claim.kind not in UNANCHORED_KINDS:
        issues.append(_error(
            "store.anchor_required", claim,
            f"a {claim.kind or 'claim'} with no anchors can never be checked and will "
            f"rot silently",
            "add anchors: [path#Symbol], or change the kind to concept if it is vocabulary",
        ))

    # S6
    if claim.status == "enforced":
        if not claim.evidence:
            issues.append(_error(
                "store.evidence_required", claim,
                "status: enforced means a tool fails when this is violated - name the tool",
                "add evidence: [test: path::name] or [rule: file#id], "
                "or downgrade to status: asserted",
            ))
        issues.extend(_check_evidence(claim, covers_index))

    # S7
    if claim.kind == "architecture":
        if not claim.since:
            issues.append(_error(
                "store.adr_required", claim,
                "an architecture claim must name the decision that created it",
                "add since: ADR-nnnn, and write the ADR if it does not exist",
            ))
        elif claim.since not in decisions:
            issues.append(_error(
                "store.adr_required", claim,
                f"{claim.since} has no file in {store.DECISIONS_DIR}/",
                f"create {store.DECISIONS_DIR}/{claim.since}-<slug>.md, or correct the reference",
            ))

    # S10
    if claim.confidence and not claim.is_candidate:
        issues.append(_error(
            "store.candidate_isolation", claim,
            "confidence is a candidate field; a ratified claim is either true or not here",
            "remove the confidence field, or move the claim to "
            f"{store.CANDIDATES_DIR}/",
        ))
    if claim.is_candidate and claim.status and claim.status != "proposed":
        issues.append(_error(
            "store.candidate_isolation", claim,
            f"a candidate must be status: proposed, not {claim.status!r}",
            f"set status: proposed, or ratify it out of {store.CANDIDATES_DIR}/",
        ))

    # S18
    if claim.status == "retired":
        issues.extend(_check_retirement(claim))
    elif claim.retired_ground or claim.retired_evidence:
        issues.append(_error(
            "store.retire_ground", claim,
            "a retirement ground is recorded on a claim that is not retired",
            "set status: retired, or remove retired-ground/retired-evidence",
        ))

    return issues


def _check_reviewed(claim: store.Claim, today: _dt.date) -> list[Issue]:
    if not _DATE_RE.match(claim.reviewed or ""):
        return [_error(
            "store.required_fields", claim,
            f"reviewed {claim.reviewed!r} is not a YYYY-MM-DD date",
            "reviewed: 2026-09-11 - the day a human last read the prose and agreed with it",
        )]
    try:
        reviewed = _dt.date.fromisoformat(claim.reviewed)
    except ValueError:
        return [_error(
            "store.required_fields", claim,
            f"reviewed {claim.reviewed!r} is not a real date",
            "reviewed: YYYY-MM-DD",
        )]
    if reviewed > today:
        # A future review date is not pedantry: `reviewed` is the input to
        # review-debt reporting, and a date that has not happened yet makes the
        # claim permanently the freshest thing in the store.
        return [_error(
            "store.required_fields", claim,
            f"reviewed {claim.reviewed} is in the future; a review that has not "
            f"happened cannot be recorded",
            f"set reviewed: {today.isoformat()} if you are reviewing it now",
        )]
    return []


def _check_evidence(claim: store.Claim, covers_index: dict[str, list[str]]) -> list[Issue]:
    """Every evidence entry names something that resolves.

    `test:` entries are resolved against `derived/tests.json`, which is the
    point of having the derived tier: evidence that names a test nobody can
    find is the failure mode `status: enforced` is supposed to prevent.
    """
    issues: list[Issue] = []
    known = {entry for entries in covers_index.values() for entry in entries}
    for entry in claim.evidence:
        kind, _, value = entry.partition(":")
        kind, value = kind.strip(), value.strip()
        if kind not in EVIDENCE_KINDS or not value:
            issues.append(_error(
                "store.evidence_required", claim,
                f"evidence entry {entry!r} does not name a kind and a target",
                f"write one of {', '.join(k + ':' for k in EVIDENCE_KINDS)} followed by the target",
            ))
            continue
        if kind != "test":
            # `rule:` and `contract:` resolution reads a rule file and a
            # contract artifact; both arrive with M3 (MVP.md R3).
            continue
        if value in known:
            continue
        covering = covers_index.get(claim.id) or []
        issues.append(_error(
            "store.evidence_required", claim,
            f"evidence names test {value!r}, which is not in "
            f"{derive.DERIVED_DIR}/tests.json",
            f"tag the test with `@covers {claim.id}` and run `forge sync derived`"
            + (f"; {claim.id} is currently covered by {covering[0]}" if covering else ""),
        ))
    return issues


def _check_retirement(claim: store.Claim) -> list[Issue]:
    """Retirement needs a ground and evidence, per SYSTEM_KNOWLEDGE.md 10.2.

    The four grounds are the whole anti-over-pruning policy. Without this
    check, `status: retired` is a one-word delete button, and the corpus shows
    exactly where that leads: files emptied because "the agent could derive it".
    """
    grounds = {
        "1": "stale or incorrect - the referent is gone, or it was never true",
        "2": "mechanically enforced - a check now fails the violation it names",
        "3": "harmful or contradictory",
        "4": "the human approved this specific deletion",
    }
    issues: list[Issue] = []
    if not claim.retired_ground:
        issues.append(_error(
            "store.retire_ground", claim,
            "a retired claim must record which of the four grounds retired it",
            f"forge retire {claim.id} --ground <1-4> --evidence <text>",
        ))
    elif claim.retired_ground not in grounds:
        issues.append(_error(
            "store.retire_ground", claim,
            f"retired-ground {claim.retired_ground!r} is not one of 1-4 "
            f"(SYSTEM_KNOWLEDGE.md section 10.2)",
            "; ".join(f"{k} = {v}" for k, v in grounds.items()),
        ))
    if not claim.retired_evidence:
        issues.append(_error(
            "store.retire_ground", claim,
            "a retirement ground without evidence is an assertion, not a ground",
            f"forge retire {claim.id} --ground {claim.retired_ground or '<1-4>'} "
            f"--evidence <what makes it true>",
        ))
    return issues


# ---------------------------------------------------------------------------
# S8 - the governs graph
# ---------------------------------------------------------------------------

def _check_governs(claims: list[store.Claim]) -> list[Issue]:
    issues: list[Issue] = []
    by_id = {c.id: c for c in claims}
    edges: dict[str, list[str]] = {}

    for claim in claims:
        targets: list[str] = []
        for target in claim.governs:
            if target == claim.id:
                issues.append(_error(
                    "store.governs_dag", claim,
                    f"{claim.id} governs itself",
                    "remove the self-reference; governs points at the claims this one constrains",
                ))
                continue
            if target not in by_id:
                issues.append(_error(
                    "store.governs_dag", claim,
                    f"governs {target}, which no claim defines",
                    f"define {target} in the store, or drop it from governs",
                ))
                continue
            if not claim.is_candidate and by_id[target].is_candidate:
                # Also SYSTEM_KNOWLEDGE.md 2.4: a ratified claim may not lean
                # on something nobody has ratified.
                issues.append(_error(
                    "store.candidate_isolation", claim,
                    f"{claim.id} governs {target}, which is only a candidate",
                    f"forge ratify {target}, or drop the reference",
                ))
            targets.append(target)
        edges[claim.id] = targets

    for cycle in _find_cycles(edges):
        head = by_id[cycle[0]]
        issues.append(_error(
            "store.governs_dag", head,
            "governs is cyclic: " + " -> ".join([*cycle, cycle[0]]),
            f"break the cycle - governs is a hierarchy, so one of these edges is "
            f"the wrong direction",
        ))

    # supersedes: SYSTEM_KNOWLEDGE.md 7.1 check 8.
    for claim in claims:
        if not claim.supersedes:
            continue
        target = by_id.get(claim.supersedes)
        if target is None:
            issues.append(_error(
                "store.governs_dag", claim,
                f"supersedes {claim.supersedes}, which no claim defines",
                "a superseded claim stays in the file as status: retired; restore it "
                "or drop the reference",
            ))
        elif target.status != "retired":
            issues.append(_error(
                "store.governs_dag", claim,
                f"supersedes {claim.supersedes}, which is status: {target.status or 'unset'}",
                f"forge retire {claim.supersedes} --ground 3 --evidence "
                f"'superseded by {claim.id}'",
            ))
    return issues


def _find_cycles(edges: dict[str, list[str]]) -> list[list[str]]:
    """Every cycle reachable in the governs graph, each reported once.

    Iterative depth-first search with an explicit stack: a claim store is not
    deep, but a cycle is exactly the input that makes a recursive walk blow
    the stack, and this check exists to be run on stores that have one.
    """
    colour: dict[str, int] = {}  # 0 = open, 1 = closed
    found: list[list[str]] = []
    reported: set[frozenset[str]] = set()

    for root in sorted(edges):
        if colour.get(root):
            continue
        path: list[str] = []
        on_path: set[str] = set()
        stack: list[tuple[str, int]] = [(root, 0)]
        while stack:
            node, index = stack.pop()
            if index == 0:
                if colour.get(node):
                    continue
                path.append(node)
                on_path.add(node)
            targets = edges.get(node, [])
            if index < len(targets):
                stack.append((node, index + 1))
                target = targets[index]
                if target in on_path:
                    cycle = path[path.index(target):]
                    key = frozenset(cycle)
                    if key not in reported:
                        reported.add(key)
                        found.append(cycle)
                elif not colour.get(target):
                    stack.append((target, 0))
            else:
                colour[node] = 1
                on_path.discard(node)
                path.pop()
    return found


# ---------------------------------------------------------------------------
# S9, S11 - the prose
# ---------------------------------------------------------------------------

def _check_prose(claims: list[store.Claim], texts: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []

    # S9. Scanned over the whole file with fences blanked, then attributed to
    # whichever claim's section the line falls in - a placeholder in the claim
    # fence is as much a placeholder as one in the prose.
    for path, text in texts.items():
        in_file = sorted((c for c in claims if c.file == path), key=lambda c: c.line)
        blanked = blank_fences(text).split("\n")
        owners = _owners_by_line(in_file, len(blanked))
        for index, line in enumerate(blanked):
            number = index + 1
            for pattern, label in _PLACEHOLDERS:
                match = pattern.search(line)
                if not match:
                    continue
                owner = owners[index]
                issues.append(Issue(
                    "ERROR", "store.placeholder", path,
                    f"{label} at line {number}: a placeholder is a claim that has not "
                    f"been made",
                    "write what it should say, or delete the claim until you know",
                    line=number, claim=owner.id if owner else None,
                ))

    # S11
    for claim in claims:
        if claim.parse_error:
            continue
        body = [line for line in claim.prose.split("\n") if line.strip()]
        if len(body) >= 2:
            continue
        issues.append(_error(
            "store.prose_present", claim,
            f"the prose body is {len(body)} non-blank line(s); a heading with no "
            f"explanation is a label, not knowledge",
            "say what the reader cannot get from the code: why it is this way, and "
            "what breaks if it is not",
        ))
    return issues


def _owners_by_line(in_file: list[store.Claim], lines: int) -> list[store.Claim | None]:
    """Which claim's section each line belongs to, built once per file.

    Asking per line would be quadratic, and the input that makes that hurt -
    a file with thousands of claims - is a real one: a generated candidates
    file from bootstrap looks exactly like that.
    """
    owners: list[store.Claim | None] = [None] * lines
    for claim in in_file:
        for index in range(claim.line - 1, min(claim.end_line, lines)):
            owners[index] = claim
    return owners


# ---------------------------------------------------------------------------
# S12 - anchors resolve at HEAD
# ---------------------------------------------------------------------------

def _check_anchors(repo: Path, claims: list[store.Claim]) -> list[Issue]:
    """Every anchor names a path, and a symbol in it, that exists at HEAD.

    This is the cheap half of drift detection and it runs on every check: an
    anchor pointing at a deleted file is not a judgement call. The expensive
    half - has the code *changed* since the anchor was stamped - is
    `forge drift`, which needs a baseline and a fingerprint.
    """
    issues: list[Issue] = []
    try:
        tracked = set(gitio.list_files_at(repo, "HEAD"))
    except (gitio.GitError, gitio.InvalidRevision):
        return []  # an empty repository has nothing to anchor into
    directories = {parent for path in tracked for parent in _parents(path)}
    sources: dict[str, bytes | None] = {}

    for claim in claims:
        for raw in claim.anchors:
            try:
                anchor = parse_anchor(raw)
            except AnchorError as exc:
                issues.append(_error(
                    "store.anchor_missing", claim,
                    f"anchor {raw!r} is malformed: {exc}",
                    "an anchor is path[#Symbol][@sha], repository-relative",
                ))
                continue

            if anchor.path in directories and anchor.path not in tracked:
                if anchor.symbol:
                    issues.append(_error(
                        "store.anchor_missing", claim,
                        f"anchor {raw!r} names a symbol inside a directory",
                        f"anchor a file: {anchor.path}/<file>#{anchor.symbol}",
                    ))
                continue
            if anchor.path not in tracked:
                issues.append(_error(
                    "store.anchor_missing", claim,
                    f"anchor path {anchor.path!r} does not exist at HEAD",
                    f"forge reanchor {claim.id}, or forge retire {claim.id} --ground 1 "
                    f"--evidence 'the referent is gone'",
                ))
                continue
            if not anchor.symbol:
                continue

            if anchor.path not in sources:
                sources[anchor.path] = gitio.blob_at(repo, "HEAD", anchor.path)
            blob = sources[anchor.path]
            if blob is None:
                continue
            if find_symbol(blob, anchor.path, anchor.symbol) is not None:
                continue
            if symbol_appears_textually(blob, anchor.symbol):
                # The grammar could not place it but the name is in the file.
                # Reporting this as missing would be a false positive on every
                # declaration shape the three MVP grammars do not model, and a
                # check that cries wolf on valid anchors gets switched off.
                continue
            known = "" if language_for_path(anchor.path) else \
                " (no grammar for this file type, so the search was textual)"
            issues.append(_error(
                "store.anchor_missing", claim,
                f"symbol {anchor.symbol!r} is not in {anchor.path} at HEAD{known}",
                f"forge reanchor {claim.id} if it was renamed, or forge retire "
                f"{claim.id} --ground 1 --evidence 'the symbol is gone'",
            ))
    return issues


def _parents(path: str) -> list[str]:
    parts = path.split("/")[:-1]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


# ---------------------------------------------------------------------------
# S13, S14, S15 - the anti-noise heuristics
# ---------------------------------------------------------------------------

def _check_smells(repo: Path, claims: list[store.Claim]) -> list[Issue]:
    issues: list[Issue] = []
    for claim in claims:
        prose = blank_fences(claim.prose)
        if not prose.strip():
            continue  # S11 already said so
        found = [
            *_derivable_smell(repo, claim, prose),
            *_listing_smell(claim, prose),
            *_stack_fact_smell(claim, prose),
        ]
        # The acknowledgement is read from the raw prose, not the blanked copy:
        # a reader may well put the reason next to the code it is about.
        issues.extend(i for i in found if _ACK[i.code] not in claim.prose)
    return issues


def _derivable_smell(repo: Path, claim: store.Claim, prose: str) -> list[Issue]:
    """Prose that is mostly identifiers from its own anchors, with no modal.

    The failure this catches is the one AI-generated documentation always
    commits: restating the code in English. A claim earns its line count by
    saying something the reader cannot get by opening the file - a rule
    (`must`, `never`), a reason, or a consequence.
    """
    if _MODALS.search(prose):
        return []
    identifiers = set(_IDENTIFIER_RE.findall(prose))
    identifiers.update(
        token for match in _BACKTICKED_RE.findall(prose)
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", match)
    )
    if len(identifiers) < 4:
        # Below this there is no ratio worth computing, and firing on a
        # two-word claim would make the check noise.
        return []

    corpus = ""
    for raw in claim.anchors:
        try:
            anchor = parse_anchor(raw)
        except AnchorError:
            continue
        blob = gitio.blob_at(repo, "HEAD", anchor.path)
        if blob:
            corpus += blob.decode("utf-8", "replace")
        corpus += " " + raw
    if not corpus:
        return []

    present = {name for name in identifiers if name in corpus}
    ratio = len(present) / len(identifiers)
    if ratio <= 0.6:
        return []
    return [_warning(
        "store.derivable_smell", claim,
        f"{round(ratio * 100)}% of the identifiers in this prose appear in its own "
        f"anchors, and it states no rule - it may just restate the code",
        f"say why it is this way and what breaks otherwise, or acknowledge with "
        f"`{_ACK['store.derivable_smell']} <reason>` in the prose",
    )]


def _listing_smell(claim: store.Claim, prose: str) -> list[Issue]:
    if claim.kind != "component":
        return []
    if not _GLOB_RE.search(prose):
        return []
    words = len(re.findall(r"[A-Za-z][A-Za-z'-]+", prose))
    if words >= 15:
        return []
    return [_warning(
        "store.listing_smell", claim,
        f"a component claim with a path glob and {words} words of explanation is a "
        f"directory listing; `ls` already does that",
        f"say what the component is responsible for and where its boundary is, or "
        f"acknowledge with `{_ACK['store.listing_smell']} <reason>` in the prose",
    )]


def _stack_fact_smell(claim: store.Claim, prose: str) -> list[Issue]:
    match = _VERSION_NEAR_PACKAGE_RE.search(prose)
    if not match:
        return []
    return [_warning(
        "store.stack_fact_smell", claim,
        f"{match.group(0)!r} pins a version in prose; versions live in lockfiles and "
        f"are reported by {derive.DERIVED_DIR}/inventory.json",
        f"drop the version, or acknowledge with "
        f"`{_ACK['store.stack_fact_smell']} <reason>` if the exact version is the claim",
    )]


# ---------------------------------------------------------------------------
# S16 - the always-loaded budget
# ---------------------------------------------------------------------------

def _check_budget(repo: Path, config: Config) -> list[Issue]:
    budget = config.always_loaded_lines
    present: list[tuple[str, int]] = []
    for relative in ALWAYS_LOADED:
        path = repo / relative
        if not path.is_file():
            continue
        present.append((relative, path.read_text(encoding="utf-8", errors="replace").count("\n") + 1))
    total = sum(lines for _, lines in present)
    if total <= budget:
        return []
    worst = max(present, key=lambda item: item[1])
    breakdown = ", ".join(f"{name.rsplit('/', 1)[-1]} {n}" for name, n in present)
    return [Issue(
        "ERROR", "store.budget", worst[0],
        f"the always-loaded set is {total} lines against a budget of {budget} "
        f"({breakdown})",
        # The budget is never raised, which is the point of it: a context
        # budget that yields to its contents is a suggestion (CONSTITUTION.md).
        f"cut or relocate - {worst[0]} is the largest at {worst[1]} lines. Raising "
        f"budgets.always_loaded_lines is not a fix",
    )]


# ---------------------------------------------------------------------------
# S17 - orphans
# ---------------------------------------------------------------------------

def _check_orphans(repo: Path, claims: list[store.Claim], config: Config) -> list[Issue]:
    """A claim nothing ever consults: no inbound `governs`, no back-reference,
    never cited by a recent change.

    A warning, never an error, and explicitly **not** grounds for deletion
    (SYSTEM_KNOWLEDGE.md section 10.2). What it means is that the claim is
    either badly placed or genuinely dead, and both deserve a look.
    """
    backrefs = ((derive.read_json(repo / derive.DERIVED_DIR / "backrefs.json") or {})
                .get("data") or {}).get("by_id") or {}
    governed: set[str] = set()
    for claim in claims:
        governed.update(claim.governs)

    from .trace import recent_change_citations  # local: trace imports nothing here

    cited = recent_change_citations(repo, config.orphan_change_window)

    issues: list[Issue] = []
    for claim in claims:
        if claim.is_candidate or claim.status in ("retired", "proposed"):
            continue
        if claim.id in governed or claim.id in backrefs or claim.id in cited:
            continue
        if _ACK["store.orphan"] in claim.prose:
            continue
        issues.append(_warning(
            "store.orphan", claim,
            f"nothing references {claim.id}: no claim governs it, no `forge:{claim.id}` "
            f"in the code, and no change in the last {config.orphan_change_window} cited it",
            f"point a rule or a test at it with `forge:{claim.id}`, move it somewhere it "
            f"will be read, or acknowledge with `{_ACK['store.orphan']} <reason>`",
        ))
    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def check_store(repo: Path, *, today: _dt.date | None = None) -> list[Issue]:
    """Run S1-S18 over the claim store. Deterministic; no model, no network."""
    today = today or _dt.date.today()
    config = load_config(repo)
    claims = store.load_store(repo)
    decisions = store.load_decisions(repo)
    texts = {
        path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8", errors="replace")
        for path in store.store_files(repo)
    }
    covers_index = (((derive.read_json(repo / derive.DERIVED_DIR / "tests.json") or {})
                     .get("data") or {}).get("covers_index") or {})

    issues: list[Issue] = []
    if config.error:
        issues.append(Issue(
            "WARNING", "store.config", config.source or ".forge/config.yaml",
            config.error, "fix the YAML, or delete the file to use defaults",
        ))
    issues.extend(_check_ids(repo, claims, texts))
    for claim in claims:
        issues.extend(_check_block(claim, decisions, covers_index, today))
    issues.extend(_check_governs(claims))
    issues.extend(_check_prose(claims, texts))
    issues.extend(_check_anchors(repo, claims))
    issues.extend(_check_smells(repo, claims))
    issues.extend(_check_budget(repo, config))
    issues.extend(_check_orphans(repo, claims, config))
    return sorted(issues, key=lambda issue: issue.sort_key)
