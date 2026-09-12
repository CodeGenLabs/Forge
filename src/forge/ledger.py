"""The drift ledger: detected, classified as far as evidence allows, human-resolved.

SYSTEM_KNOWLEDGE.md section 6. `docs/system/DRIFT.md` is machine-appended and
human-resolved, and the split is the whole point: the kernel says *what moved*,
which it can compute, and never *what that means*, which it cannot.

The rule this file exists to hold: **there is no command that rewrites a claim
to match the code.** Auto-reconciliation would make the store a lagging copy of
the implementation, which is exactly the thing the harness is supposed to
notice. So a resolution records a verdict and the human edits the claim, and the
kernel's contribution is to refuse the resolutions that are not honest - a V3
naming an ADR that does not exist, a V2 with no evidence note.

An entry looks like a claim on purpose. Same heading-plus-fence shape, parsed by
the same idiom, so there is one thing to learn and one grammar to get wrong.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import gitio, store

__all__ = [
    "DRIFT_FILE", "Entry", "LedgerError", "VERDICTS",
    "load_ledger", "next_id", "record", "resolve", "waive", "confirm",
    "open_entries",
]

DRIFT_FILE = "docs/system/DRIFT.md"

#: The four verdicts, and what each one asserts. The set is closed: a drift that
#: does not fit one of these is a sign the claim was never checkable, which is
#: itself V2.
VERDICTS = {
    "V1": "the code is wrong",
    "V2": "the claim was never true",
    "V3": "the decision changed",
    "V4": "the claim is under-specified",
}

_HEADING_RE = re.compile(
    r"^##\s+(?P<id>D-\d{3,})\s*(?:[-–—:]\s*(?P<title>[^\n]*))?$", re.M)
_FENCE_RE = re.compile(r"^```drift\s*$(?P<body>.*?)^```\s*$", re.M | re.S)

_HEADER = """\
# Drift ledger

> Machine-appended, human-resolved. `forge drift record` writes an entry when a
> claim's anchors stop matching what a human confirmed; `forge drift resolve`
> records what that means. The kernel never edits a claim to match the code -
> see SYSTEM_KNOWLEDGE.md section 6.
>
> Verdicts: **V1** the code is wrong. **V2** the claim was never true. **V3** the
> decision changed, and an ADR records it. **V4** the claim is under-specified.
"""


class LedgerError(ValueError):
    """A resolution the kernel refuses, or a ledger it cannot read."""


@dataclass
class Entry:
    id: str
    claim: str = ""
    title: str = ""
    line: int = 0
    detected: str = ""
    detected_by: str = "forge drift"
    signal: str = ""
    anchors_changed: list[str] = field(default_factory=list)
    proposed_verdict: str | None = None
    proposed_reasoning: str = ""
    status: str = "open"            # open | resolved | waived
    verdict: str | None = None
    resolved: str | None = None
    evidence: str | None = None
    adr: str | None = None
    waived_until: str | None = None
    waiver_reason: str | None = None
    #: `<sha> <author> - <subject>` for the commits that reached this
    #: claim's anchors. The report had this and the record did not, which
    #: left the one thing `forge reconcile` adds over a plain scan out of
    #: the artifact that survives the terminal being closed.
    caused_by: list[str] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def expired(self, today: _dt.date, head: str = "") -> bool:
        """Whether a waiver has run out.

        A waiver with no expiry is not a waiver, so one that cannot be read as
        either a date or this repository's HEAD is treated as expired rather
        than as permanent. The failure mode of the other choice is a gate that
        is silently off forever.
        """
        if self.status != "waived":
            return False
        if not self.waived_until:
            return True
        try:
            return _dt.date.fromisoformat(self.waived_until) < today
        except ValueError:
            return bool(head) and self.waived_until.lower() not in head.lower()

    def to_dict(self) -> dict:
        return {
            "id": self.id, "claim": self.claim, "status": self.status,
            "signal": self.signal, "detected": self.detected,
            "verdict": self.verdict, "adr": self.adr,
            "waived_until": self.waived_until,
            "anchors_changed": self.anchors_changed,
        }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def parse_ledger(text: str) -> list[Entry]:
    """Every entry in the ledger document, in file order."""
    entries: list[Entry] = []
    headings = list(_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        entry = Entry(
            id=heading.group("id"),
            title=(heading.group("title") or "").strip(),
            line=text.count("\n", 0, heading.start()) + 1,
        )
        fence = _FENCE_RE.search(text[start:end])
        if fence is None:
            entry.parse_error = "no ```drift block"
            entries.append(entry)
            continue
        try:
            block = yaml.safe_load(fence.group("body")) or {}
        # ValueError alongside YAMLError for the same reason store.py catches
        # both: PyYAML resolves an impossible date and lets `datetime` raise.
        except (yaml.YAMLError, ValueError) as exc:
            entry.parse_error = f"drift block is not valid YAML: {exc}"
            block = {}
        if not isinstance(block, dict):
            entry.parse_error = "drift block is not a mapping"
            block = {}
        block = {str(k).replace("_", "-"): v for k, v in block.items()}

        entry.claim = str(block.get("claim") or "").strip()
        entry.detected = _text(block.get("detected"))
        entry.detected_by = str(block.get("detected-by") or "forge drift").strip()
        entry.signal = str(block.get("signal") or "").strip()
        entry.anchors_changed = [str(a) for a in (block.get("anchors-changed") or [])]
        entry.proposed_verdict = _opt(block.get("proposed-verdict"))
        entry.proposed_reasoning = str(block.get("proposed-reasoning") or "").strip()
        entry.status = str(block.get("status") or "open").strip() or "open"
        entry.verdict = _opt(block.get("verdict"))
        entry.resolved = _opt(block.get("resolved"))
        entry.evidence = _opt(block.get("evidence"))
        entry.adr = _opt(block.get("adr"))
        entry.waived_until = _opt(block.get("waived-until"))
        entry.waiver_reason = _opt(block.get("waiver-reason"))
        entry.caused_by = [str(c) for c in (block.get("caused-by") or [])]
        entries.append(entry)
    return entries


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _opt(value: object) -> str | None:
    text = _text(value)
    return text or None


def load_ledger(repo: Path) -> list[Entry]:
    target = repo / DRIFT_FILE
    if not target.is_file():
        return []
    return parse_ledger(target.read_text(encoding="utf-8", errors="replace"))


def open_entries(repo: Path, *, today: _dt.date | None = None) -> list[Entry]:
    """Entries that still owe somebody a decision.

    An expired waiver is open again, which is the only thing that makes a
    waiver different from deleting the entry.
    """
    today = today or _dt.date.today()
    head = gitio.rev_parse(repo, "HEAD") if gitio.is_repo(repo) else ""
    return [e for e in load_ledger(repo)
            if e.is_open or e.expired(today, head)]


def next_id(entries: list[Entry]) -> str:
    """Monotonic across resolved entries: an id is never reused."""
    highest = 0
    for entry in entries:
        try:
            highest = max(highest, int(entry.id.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"D-{highest + 1:03d}"


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _render(entry: Entry) -> str:
    block: dict[str, object] = {
        "claim": entry.claim,
        "detected": entry.detected,
        "detected_by": entry.detected_by,
        "signal": entry.signal,
        "anchors_changed": entry.anchors_changed,
    }
    if entry.caused_by:
        block["caused_by"] = entry.caused_by
    if entry.proposed_verdict:
        block["proposed_verdict"] = entry.proposed_verdict
    if entry.proposed_reasoning:
        block["proposed_reasoning"] = entry.proposed_reasoning
    block["status"] = entry.status
    for key, value in (("verdict", entry.verdict), ("resolved", entry.resolved),
                       ("evidence", entry.evidence), ("adr", entry.adr),
                       ("waived_until", entry.waived_until),
                       ("waiver_reason", entry.waiver_reason)):
        if value:
            block[key] = value
    body = yaml.safe_dump(block, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=88)
    return f"## {entry.id} - {entry.title}\n\n```drift\n{body}```\n"


def write_ledger(repo: Path, entries: list[Entry]) -> Path:
    target = repo / DRIFT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(_render(e) for e in entries)
    target.write_text(_HEADER + ("\n" + body if body else ""),
                      encoding="utf-8", newline="\n")
    return target


def record(repo: Path, drifts, *, today: _dt.date | None = None,
           causes: dict[str, list[str]] | None = None) -> list[Entry]:
    """Append an open entry for each obligating claim that is not fresh.

    Idempotent by claim: a claim with an entry already open gets no second one.
    Re-running after a week of drift must not produce a week of duplicates -
    that is how a ledger becomes a thing people stop opening.
    """
    today = today or _dt.date.today()
    entries = load_ledger(repo)
    already = {e.claim for e in entries if e.is_open}
    added: list[Entry] = []

    for drift in drifts:
        if not drift.obligating or not drift.changed or drift.claim_id in already:
            continue
        entry = Entry(
            id=next_id(entries + added),
            claim=drift.claim_id,
            title=f"{drift.claim_id} {drift.status.value if drift.status else 'unclassified'}",
            detected=today.isoformat(),
            signal=drift.status.value if drift.status else "unclassified",
            anchors_changed=[f"{r.anchor} ({r.status.value})" for r in drift.culprits]
                            + [f"{a} (unclassifiable: {m})" for a, m in drift.errors],
            proposed_verdict=_propose(drift),
            proposed_reasoning=_reasoning(drift),
            caused_by=list((causes or {}).get(drift.claim_id, [])),
        )
        added.append(entry)

    if added:
        write_ledger(repo, entries + added)
    return added


def _propose(drift) -> str | None:
    """A proposal, never a decision.

    Only the one case the evidence actually supports is proposed. A signature
    change means the thing the claim points at is not there in the shape it was
    confirmed in, which is at least a re-anchoring question. Everything else -
    a changed body, a vanished symbol - is exactly the judgement the ledger
    exists to route to a human, and a machine guess there would be read as an
    answer.
    """
    from .anchor import Status

    return "V1" if drift.status is Status.STALE and not drift.errors else None


def _reasoning(drift) -> str:
    from .anchor import Status

    if drift.errors:
        return ("An anchor could not be classified at all, so nothing is known about "
                "whether the claim still holds. Fix the anchor before deciding.")
    if drift.status is Status.MISSING:
        return ("What the claim points at is gone. Either it moved and the anchor "
                "needs restamping, or the thing the claim describes no longer "
                "exists - which is a different verdict.")
    if drift.status is Status.SHIFTED:
        return ("The body changed and the signature did not. Often harmless; the "
                "question is whether the property the claim asserts survived.")
    return ("The signature changed, so the code this claim describes is not in the "
            "shape a human confirmed. Proposed V1 because that is the only reading "
            "the fingerprint supports on its own; the other three are judgements.")


# ---------------------------------------------------------------------------
# Resolving
# ---------------------------------------------------------------------------

def _find(entries: list[Entry], entry_id: str) -> Entry:
    for entry in entries:
        if entry.id == entry_id:
            return entry
    raise LedgerError(f"{entry_id} is not in {DRIFT_FILE}")


def resolve(repo: Path, entry_id: str, verdict: str, *,
            evidence: str | None = None, adr: str | None = None,
            accept_asserted: bool = False,
            today: _dt.date | None = None) -> Entry:
    """Record a human's verdict, refusing the ones that are not honest.

    The kernel's whole contribution here is the refusals. It cannot tell whether
    V3 is the right reading, but it can tell that the ADR named does not exist -
    and an ADR that does not exist is how "the decision changed" becomes a
    sentence nobody has to stand behind.
    """
    today = today or _dt.date.today()
    verdict = verdict.strip().upper()
    if verdict not in VERDICTS:
        raise LedgerError(
            f"{verdict!r} is not a verdict; use one of "
            + ", ".join(f"{k} ({v})" for k, v in VERDICTS.items()))

    entries = load_ledger(repo)
    entry = _find(entries, entry_id)
    if entry.status == "resolved":
        raise LedgerError(
            f"{entry_id} was already resolved as {entry.verdict}. A verdict that "
            f"turned out wrong is a new detection, not an overwrite")

    if verdict == "V2" and not (evidence or "").strip():
        raise LedgerError(
            "V2 says the claim was never true, so it needs --evidence saying how "
            "that is known. Without it the store loses a claim and keeps no record "
            "of why")
    if verdict == "V3":
        if not (adr or "").strip():
            raise LedgerError(
                "V3 says a decision changed, so it needs --adr naming the decision "
                "that records it")
        known = store.load_decisions(repo)
        identifier = _adr_id(adr)
        if identifier not in known:
            raise LedgerError(
                f"{identifier} is not in {store.DECISIONS_DIR}. Write the ADR first: "
                f"a decision nobody recorded is not a decision that changed")
        adr = identifier
    if verdict == "V4" and not accept_asserted and not (evidence or "").strip():
        raise LedgerError(
            "V4 says the claim was too vague, so the sharper claim needs new "
            "evidence - pass --evidence naming it, or --accept-asserted to record "
            "on purpose that the sharper claim is still only asserted")

    entry.status = "resolved"
    entry.verdict = verdict
    entry.resolved = today.isoformat()
    entry.evidence = (evidence or "").strip() or None
    entry.adr = adr
    if verdict == "V4" and accept_asserted and not entry.evidence:
        entry.evidence = "accepted as asserted, with no new evidence"
    write_ledger(repo, entries)
    return entry


def confirm(repo: Path, entry_id: str, *, head: str = "HEAD",
            today: _dt.date | None = None) -> tuple[Entry, list[str]]:
    """Record that a human read the drift and the claim still holds, and restamp.

    Not a fifth verdict. The four are a closed grammar about *what the drift
    means*, and all four say something is wrong somewhere; this says nothing is.

    It is needed because the commonest signal by far is a file-level anchor
    going stale on an edit that never touched what the claim describes - the
    first entry this ledger ever opened was exactly that, on a claim whose
    regex was untouched by the change that flagged it. With only the four
    verdicts available, the honest options were to file a false V1 or to leave
    an entry open forever, and both end with the ledger being ignored.

    The restamp is the kernel writing down what the human just asserted: that
    the claim was confirmed at this commit. That is what `@sha` means, and it
    is the opposite of the auto-reconciliation this design refuses - no prose
    is touched, nothing is made to agree with the code, and it happens only
    when somebody names an entry and asks for it.
    """
    today = today or _dt.date.today()
    entries = load_ledger(repo)
    entry = _find(entries, entry_id)
    if entry.status == "resolved":
        raise LedgerError(f"{entry_id} is already resolved as {entry.verdict}")
    if not entry.claim:
        raise LedgerError(f"{entry_id} names no claim, so there is nothing to restamp")

    sha = gitio.rev_parse(repo, head)
    restamped = _restamp(repo, entry.claim, sha, today)
    if not restamped:
        raise LedgerError(
            f"no anchor of {entry.claim} could be restamped; the claim may have "
            f"moved or its anchors may be malformed - `forge check --scope store`")

    entry.status = "resolved"
    entry.verdict = "confirmed"
    entry.resolved = today.isoformat()
    entry.evidence = f"re-confirmed at {sha[:10]}; anchors restamped, prose unchanged"
    write_ledger(repo, entries)
    return entry, restamped


def _restamp(repo: Path, claim_id: str, sha: str, today: _dt.date) -> list[str]:
    """Rewrite one claim's `@sha` values and its `reviewed:` date, in place."""
    short = sha[:10]
    changed: list[str] = []
    for claim in store.load_store(repo):
        if claim.id != claim_id or claim.is_candidate:
            continue
        target = repo / claim.file
        lines = target.read_text(encoding="utf-8").split("\n")
        for index in range(claim.line - 1, min(claim.end_line, len(lines))):
            line = lines[index]
            if line.lstrip().startswith("anchors:"):
                new = re.sub(r"@[0-9a-fA-F]{4,40}", f"@{short}", line)
                if "@" not in line:
                    # An unstamped anchor is the case `forge check` reports as
                    # a defect, not one to quietly invent a baseline for.
                    continue
                if new != line:
                    lines[index] = new
                    changed.append(f"{claim.file}:{index + 1}")
            elif line.lstrip().startswith("reviewed:"):
                lines[index] = re.sub(r"reviewed:\s*\S+",
                                      f"reviewed: {today.isoformat()}", line)
        if changed:
            target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return changed


def _adr_id(value: str) -> str:
    """`21`, `0021` and `ADR-0021` all name the same decision."""
    text = value.strip()
    if text.upper().startswith("ADR-"):
        text = text[4:]
    try:
        return f"ADR-{int(text):04d}"
    except ValueError:
        return value.strip()


def waive(repo: Path, entry_id: str, *, until: str, reason: str,
          today: _dt.date | None = None) -> Entry:
    """Silence one entry, with an expiry and a reason, both recorded.

    This exists because the alternative is a permanently red gate, and a
    permanently red gate gets turned off entirely. OpenSpec's named-bypass
    pattern: make it explicit, named and committed.
    """
    if not reason.strip():
        raise LedgerError("a waiver needs a reason; an unexplained one is a deletion")
    if not until.strip():
        raise LedgerError(
            "a waiver needs --until, a date or a commit. One that never expires is "
            "the disabled gate this mechanism exists to avoid")

    entries = load_ledger(repo)
    entry = _find(entries, entry_id)
    if entry.status == "resolved":
        raise LedgerError(f"{entry_id} is already resolved as {entry.verdict}")
    entry.status = "waived"
    entry.waived_until = until.strip()
    entry.waiver_reason = reason.strip()
    write_ledger(repo, entries)
    return entry
