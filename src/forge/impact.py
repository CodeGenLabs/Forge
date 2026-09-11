"""The claim-touch rule: the harness's central enforcement.

`claim_touch_set(D)` is the set of claims a diff `D` reaches
(SYSTEM_KNOWLEDGE.md section 9.2):

    { claim | any anchor resolves to a file in D }
  u { claim | any CMP- path glob matches a file in D }
  u { claim | any evidence artifact is in D }

`impact.md` must account for **every** member under exactly one heading, and
`forge check` blocks if any is unaccounted for. That turns "which documentation
must change?" from a judgement call into a set operation, which is the piece I
found nowhere in the corpus.

Two consequences the implementation has to preserve, because they are the
reason the rule works:

- **`Unaffected` is cheap but not free.** It costs one honest sentence per
  claim. An entry with an ID and no reason is not an account, so it is
  rejected - otherwise the heading becomes a place to dump the whole set.
- **Every claim taxes every change that touches its files.** That is the
  pressure that keeps the store small, and it is why a store of forty good
  claims is worth more than four hundred. Nothing here may quietly narrow the
  set to make the tax cheaper.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import derive, gitio, store
from .anchor import AnchorError, parse_anchor
from .fingerprint import find_symbol
from .change import Change
from .config import load_config
from .store import Claim

__all__ = [
    "Impact",
    "ClaimTouch",
    "Account",
    "HEADINGS",
    "compute_impact",
    "parse_account",
    "check_claim_touch",
]

#: The five headings a claim may be accounted under, from WORKFLOW.md 3.4.
#: A closed set, because an open one lets a claim be filed under a heading
#: nobody checks.
HEADINGS = ("Unaffected", "Updated", "New", "Superseded", "At risk")

#: Headings that count as "this claim changes". A claim whose own definition
#: the diff edited must be under one of these: editing a claim while filing it
#: as Unaffected is the exact move the rule exists to stop.
#:
#: `New` belongs here. A claim this change introduces has, trivially, had its
#: definition edited - the diff is where it came from - and without `New` the
#: rule rejects every change that records a piece of knowledge, which is the
#: single most common thing a change should do. Leaving it out made adding one
#: pitfall claim unsatisfiable by any account that was also true.
CHANGING = ("Updated", "New", "Superseded")

_SECTION_RE = re.compile(r"^##\s+Claims\s+touched\s*$", re.M | re.I)
_HEADING_RE = re.compile(r"^###\s+(?P<heading>.+?)\s*$", re.M)
# Horizontal whitespace only between the ID and its reason. `\s*` would cross
# the newline and swallow the next line as this entry's reason, which turns
# "you gave no reason" into "you gave the following heading as a reason" - the
# check silently stops firing.
_ENTRY_RE = re.compile(
    r"^[ \t]*[-*][ \t]*(?P<id>" + store.ANY_ID_PATTERN + r")[ \t]*(?P<rest>[^\n]*)$", re.M)
_ADR_IN_TEXT_RE = re.compile(r"\b(ADR-\d{4})\b")
_ANY_HEADING_RE = re.compile(r"^##\s+", re.M)


@dataclass
class ClaimTouch:
    id: str
    claim: Claim | None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.claim.kind if self.claim else "unknown",
            "status": self.claim.status if self.claim else "",
            "defined_in": self.claim.file if self.claim else None,
            "reasons": sorted(self.reasons),
        }


@dataclass
class Impact:
    change: str
    base: str
    changed_files: list[str]
    reverse_deps: list[str]
    touched: dict[str, ClaimTouch]
    #: Claims the diff only reaches through the import graph. Reported so the
    #: reading value of the blast radius survives; never owed an account.
    nearby: dict[str, ClaimTouch] = field(default_factory=dict)

    @property
    def blast_radius(self) -> list[str]:
        return sorted(set(self.changed_files) | set(self.reverse_deps))

    def to_dict(self) -> dict:
        return {
            "change": self.change,
            "base": self.base,
            "changed_files": self.changed_files,
            "reverse_deps": self.reverse_deps,
            "blast_radius": self.blast_radius,
            "claims_touched": sorted(self.touched),
            "claims": [self.touched[k].to_dict() for k in sorted(self.touched)],
            "claims_nearby": sorted(self.nearby),
            "nearby": [self.nearby[k].to_dict() for k in sorted(self.nearby)],
        }


@dataclass
class Account:
    """What `impact.md` says, parsed. `by_id` maps an ID to its headings -
    plural, because being under two is itself a fault worth naming."""
    present: bool = False
    by_id: dict[str, list[str]] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    unknown_headings: list[str] = field(default_factory=list)
    line_of: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Computing the set
# ---------------------------------------------------------------------------

def resolve_base(repo: Path, item: Change, override: str | None = None) -> str:
    """The commit the change started from.

    The change directory is created before any work happens, so the commit
    that introduced `.forge.yaml` is the boundary: everything after it is this
    change. Before that commit exists - the normal case while the first
    artifact is being written - the boundary is HEAD.
    """
    if override:
        return gitio.rev_parse(repo, override)
    marker = f"{item.relative}/.forge.yaml"
    created = gitio.first_commit_touching(repo, marker)
    if created:
        return gitio.parent_of(repo, created) or created
    return gitio.rev_parse(repo, "HEAD")


def _overlaps(ranges: list[tuple[int, int]], start: int, end: int) -> bool:
    """Whether any changed range intersects the claim's own [start, end] lines.

    A claim with no recorded ``end_line`` (an unparseable fence, say) falls
    back to its heading line alone. Falling back to "the whole file" instead
    would quietly restore the file-level behaviour this replaces, in exactly
    the case where the parser already knows something is wrong.
    """
    last = end if end >= start else start
    return any(hi >= start and lo <= last for lo, hi in ranges)


def _is_component_glob(claim: Claim, value: str) -> bool:
    """Component anchors are read as globs; other kinds are read as paths.

    Only `CMP-` gets this, per section 9.2. Widening it to every kind would
    make one careless `src/*` anchor on an invariant pull the whole tree into
    every change's touch set, and a rule that always fires teaches people to
    dismiss it.
    """
    return claim.kind == "component" or any(ch in value for ch in "*?[")


def compute_impact(repo: Path, item: Change, *, base: str | None = None) -> Impact:
    resolved_base = resolve_base(repo, item, base)
    config = load_config(repo)
    changed = [p for p in gitio.changed_files(repo, resolved_base)
               # The change's own artifacts are excluded: `impact.md` naming
               # itself as blast radius is noise, and every change would touch
               # every claim defined in a file it happens to store under
               # `changes/`. Vendored and built paths go too - `gitio` reports
               # untracked files on purpose, and a repository with no
               # `.gitignore` was reporting `__pycache__/*.pyc` as changed
               # source.
               if not p.startswith(f"{item.relative}/")
               and not derive.is_ignored(p, config)]

    deps = ((derive.read_json(repo / derive.DERIVED_DIR / "deps.json") or {})
            .get("data") or {})
    reverse_index: dict[str, list[str]] = deps.get("reverse") or {}
    reverse: set[str] = set()
    for path in changed:
        reverse.update(reverse_index.get(path, []))
    reverse -= set(changed)

    # Obligations are computed against the diff, never against the blast
    # radius. SYSTEM_KNOWLEDGE.md section 9.2 defines `claim_touch_set(D)` on
    # the diff `D`, and the two are not interchangeable: the blast radius
    # answers "what might this affect?" and is a reading aid, while the touch
    # set answers "what must you account for?" and is an obligation.
    #
    # Measured on `requests` - 35 modules, 88 import edges, 20 cycles - a
    # one-line type-annotation change to `models.py` touched 10 claims out of
    # 10, eight of them anchored to files the diff never opened. An obligation
    # that always fires is one people learn to discharge without reading, and
    # a rule that is satisfied without reading is worse than no rule, because
    # the gate still prints `pass`.
    diff = set(changed)
    claims = store.load_store(repo)
    touched: dict[str, ClaimTouch] = {}
    near: dict[str, ClaimTouch] = {}
    # Memoised per file: several claims share one claim file, and asking git
    # for the same file's hunks once per claim is the difference between one
    # subprocess and forty.
    edited_ranges: dict[str, list[tuple[int, int]]] = {}

    def note(claim: Claim, reason: str) -> None:
        entry = touched.setdefault(claim.id, ClaimTouch(claim.id, claim))
        if reason not in entry.reasons:
            entry.reasons.append(reason)

    def nearby(claim: Claim, reason: str) -> None:
        """Worth reading, never owed a sentence.

        A claim whose anchors only *import* the diff is exactly what the blast
        radius is for. Reporting it keeps the reading value that matching on
        the radius used to provide; keeping it out of `touched` is what stops
        it becoming an obligation.
        """
        entry = near.setdefault(claim.id, ClaimTouch(claim.id, claim))
        if reason not in entry.reasons:
            entry.reasons.append(reason)

    for claim in claims:
        if claim.is_candidate or claim.status == "retired":
            # A candidate is not yet knowledge and a retired claim is history.
            # Taxing a change for either would make both expensive to keep,
            # which is the opposite of what the tiers are for.
            continue

        for raw in claim.anchors:
            try:
                parsed = parse_anchor(raw)
            except AnchorError:
                continue
            path = parsed.path
            if _is_component_glob(claim, path):
                hits = [f for f in diff if _glob_matches(f, path)]
                if hits:
                    note(claim, f"component boundary {path} matches {sorted(hits)[0]}"
                                + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""))
                elif any(_glob_matches(f, path) for f in reverse):
                    nearby(claim, f"component boundary {path} is imported by the diff")
            elif path in diff:
                if path not in edited_ranges:
                    edited_ranges[path] = gitio.changed_line_ranges(
                        repo, resolved_base, path)
                reason = _symbol_hit(repo, parsed, edited_ranges[path])
                if reason and reason.startswith(_NEAR):
                    nearby(claim, reason[len(_NEAR):])
                elif reason:
                    note(claim, reason)
            elif any(f == path or f.startswith(f"{path}/") for f in diff):
                note(claim, f"anchor directory {path}")
            elif path in reverse:
                nearby(claim, f"anchor {path} imports something the diff changed")

        for entry in claim.evidence:
            kind, _, value = entry.partition(":")
            target = value.split("::", 1)[0].strip()
            if target and target in diff:
                note(claim, f"evidence {kind.strip()} {target}")

        # File-level would be wrong here, and wrong in the direction that
        # matters: appending one new claim to a shared file would mark every
        # other claim in it as having had its definition edited, and the rule
        # then demands each be re-filed as `Updated`. The only ways through
        # are to write `Updated` about a claim nobody updated, or to split
        # every claim into its own file - which is the rubber-stamping
        # OPEN_QUESTIONS.md Q3 asks about, arriving by the front door.
        if claim.file in diff:
            if claim.file not in edited_ranges:
                edited_ranges[claim.file] = gitio.changed_line_ranges(
                    repo, resolved_base, claim.file)
            if _overlaps(edited_ranges[claim.file], claim.line, claim.end_line):
                note(claim, f"its own definition in {claim.file} was edited")

    return Impact(
        change=item.name,
        base=resolved_base,
        changed_files=sorted(changed),
        reverse_deps=sorted(reverse),
        touched=touched,
        # A claim can be both: anchored to one file the diff changed and to
        # another that merely imports it. `touched` wins, because an obligation
        # outranks a suggestion.
        nearby={k: v for k, v in near.items() if k not in touched},
    )


#: Prefix marking a `_symbol_hit` result as worth reading rather than owed a
#: heading. A sentinel rather than a second return value because every caller
#: has to decide which bucket it goes in, and an ignorable flag is how a claim
#: ends up silently in the wrong one.
_NEAR = "NEARBY::"


def _symbol_hit(repo: Path, parsed, ranges: list[tuple[int, int]]) -> str | None:
    """Why this anchor counts as touched, or None if the diff missed its symbol.

    A file-level anchor is touched whenever its file is. A *symbol* anchor
    should not be: measured on `requests`, a one-method change put five claims
    in the touch set because all five anchor symbols in `models.py`, and four
    of those symbols the diff never opened.

    Every way of not knowing falls back to the file, and that direction is
    deliberate. No grammar installed, a declaration form the table does not
    cover, a symbol that has been renamed away, a file that is gone from the
    working tree - in each case the honest answer is "this might be about the
    part that changed", and over-reporting costs a sentence while
    under-reporting costs a claim nobody re-read.
    """
    if not parsed.symbol:
        return f"anchor {parsed.path}"
    if not ranges:
        # An added file has no hunks to intersect; the whole thing is new.
        return f"anchor {parsed.path}"

    target = repo / parsed.path
    try:
        source = target.read_bytes()
    except OSError:
        return f"anchor {parsed.path} (unreadable at head, compared whole file)"

    located = find_symbol(source, parsed.path, parsed.symbol)
    if located is None or not located.start_line:
        return (f"anchor {parsed.path}#{parsed.symbol} "
                f"(symbol not resolvable, compared whole file)")
    if any(start <= located.end_line and end >= located.start_line
           for start, end in ranges):
        return f"anchor {parsed.path}#{parsed.symbol}"
    # Not nothing. The diff opened the file this claim points into and changed
    # a different part of it, which is worth a reader's eye and is not worth a
    # mandatory sentence - the same line the import graph sits on.
    return _NEAR + (f"anchor {parsed.path}#{parsed.symbol} is in a file the diff "
                    f"changed elsewhere")


def _glob_matches(path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(path, pattern):
        return True
    # `src/payments` as a component anchor means the subtree, the way anyone
    # writing it would expect; fnmatch alone would not cross a separator.
    prefix = pattern.rstrip("*").rstrip("/")
    return bool(prefix) and (path == prefix or path.startswith(f"{prefix}/"))


# ---------------------------------------------------------------------------
# Reading the account
# ---------------------------------------------------------------------------

def parse_account(text: str) -> Account:
    """Read the `## Claims touched` section of an `impact.md`."""
    account = Account()
    start = _SECTION_RE.search(text)
    if start is None:
        return account
    account.present = True

    rest = text[start.end():]
    end = _ANY_HEADING_RE.search(rest)
    section = rest[:end.start()] if end else rest
    offset = text.count("\n", 0, start.end())

    positions = [(m.start(), m.group("heading").strip()) for m in _HEADING_RE.finditer(section)]
    for match in _ENTRY_RE.finditer(section):
        heading = next((name for pos, name in reversed(positions) if pos < match.start()), None)
        if heading is None:
            continue
        canonical = next((h for h in HEADINGS if h.lower() == heading.lower()), None)
        if canonical is None:
            if heading not in account.unknown_headings:
                account.unknown_headings.append(heading)
            continue
        identifier = match.group("id")
        account.by_id.setdefault(identifier, []).append(canonical)
        account.reasons[identifier] = match.group("rest").strip()
        account.line_of[identifier] = offset + section.count("\n", 0, match.start()) + 1
    return account


# ---------------------------------------------------------------------------
# R5 / R6 - the check
# ---------------------------------------------------------------------------

def check_claim_touch(repo: Path, item: Change, impact: Impact,
                      issue) -> list:
    """R5 and R6. `issue` is the `Issue` constructor, injected to keep this
    module free of a dependency on the CLI's reporting shape."""
    relative = f"{item.relative}/impact.md"
    target = repo / item.relative / "impact.md"
    issues = []

    if not target.is_file():
        if not impact.touched:
            return []
        return [issue(
            "ERROR", "trace.claim_touch_complete", relative,
            f"this change reaches {len(impact.touched)} claim(s) and there is no "
            f"impact.md accounting for them: {', '.join(sorted(impact.touched))}",
            f"forge impact --change {item.number} writes the list; account for each "
            f"under Unaffected, Updated, New, Superseded or At risk",
        )]

    text = target.read_text(encoding="utf-8", errors="replace")
    account = parse_account(text)
    if not account.present:
        return [issue(
            "ERROR", "trace.claim_touch_complete", relative,
            "impact.md has no `## Claims touched` section",
            "add `## Claims touched` with a `### Unaffected` / `### Updated` / "
            "`### Superseded` breakdown",
        )]

    for heading in account.unknown_headings:
        issues.append(issue(
            "ERROR", "trace.claim_touch_complete", relative,
            f"`### {heading}` is not one of the accounted headings",
            f"use one of {', '.join(HEADINGS)} - a claim filed under a heading "
            f"nothing checks is a claim nobody accounted for",
        ))

    decisions = store.load_decisions(repo)

    for identifier in sorted(impact.touched):
        entry = impact.touched[identifier]
        headings = account.by_id.get(identifier)
        if not headings:
            issues.append(issue(
                "ERROR", "trace.claim_touch_complete", relative,
                f"{identifier} is in this change's touch set and impact.md does not "
                f"mention it ({entry.reasons[0]})",
                f"add `- {identifier} - <one sentence>` under the heading that is true; "
                f"Unaffected is fine, and costs exactly that sentence",
                claim=identifier,
            ))
            continue
        if len(set(headings)) > 1:
            issues.append(issue(
                "ERROR", "trace.claim_touch_complete", relative,
                f"{identifier} is accounted under {' and '.join(sorted(set(headings)))}; "
                f"exactly one must be true",
                "delete the entry that is not true",
                line=account.line_of.get(identifier), claim=identifier,
            ))
        if not _reason_text(account.reasons.get(identifier, "")):
            issues.append(issue(
                "ERROR", "trace.claim_touch_complete", relative,
                f"{identifier} is listed with no reason",
                "one honest sentence. That price is the point: it is what keeps the "
                "claim count low and the account meaningful",
                line=account.line_of.get(identifier), claim=identifier,
            ))

        edited_itself = any("its own definition" in r for r in entry.reasons)
        if edited_itself and not set(headings) & set(CHANGING):
            issues.append(issue(
                "ERROR", "trace.claim_touch_complete", relative,
                f"{identifier}'s own definition was edited by this change but it is "
                f"filed as {headings[0]}",
                f"file it under Updated, or under Superseded with the ADR that "
                f"replaced it",
                line=account.line_of.get(identifier), claim=identifier,
            ))

    # R6: superseded needs an ADR that exists.
    for identifier, headings in sorted(account.by_id.items()):
        if "Superseded" not in headings:
            continue
        named = _ADR_IN_TEXT_RE.findall(account.reasons.get(identifier, ""))
        if not named:
            issues.append(issue(
                "ERROR", "trace.superseded_has_adr", relative,
                f"{identifier} is superseded without naming an ADR",
                f"`- {identifier} -> ADR-nnnn - <what changed>`; superseding a claim "
                f"is a decision, and a decision with no record is a preference",
                line=account.line_of.get(identifier), claim=identifier,
            ))
            continue
        for adr in named:
            if adr not in decisions:
                issues.append(issue(
                    "ERROR", "trace.superseded_has_adr", relative,
                    f"{identifier} names {adr}, which has no file in "
                    f"{store.DECISIONS_DIR}/",
                    f"write {store.DECISIONS_DIR}/{adr}-<slug>.md, or correct the reference",
                    line=account.line_of.get(identifier), claim=identifier,
                ))

    # Over-accounting is not a fault, but it is a signal: either the anchors
    # are wrong or the author is accounting for something the diff never
    # reached. A warning, because being too careful must not block.
    for identifier in sorted(account.by_id):
        if identifier in impact.touched or identifier.startswith(("REQ-", "ADR-")):
            continue
        issues.append(issue(
            "WARNING", "trace.claim_touch_extra", relative,
            f"{identifier} is accounted for but is not in the computed touch set",
            f"harmless, but check its anchors - if this change really reaches it, "
            f"the anchors are pointing at the wrong files",
            line=account.line_of.get(identifier), claim=identifier,
        ))
    return issues


def _reason_text(rest: str) -> str:
    """The prose after the ID, with the separators and any ADR arrow removed."""
    text = rest.strip()
    text = re.sub(r"\A(?:->|=>|→)\s*ADR-\d{4}", "", text).strip()
    text = text.lstrip("-–—:> ").strip()
    return text
