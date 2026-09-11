"""The drift ledger: what the kernel computes, and what it refuses.

The division this file is about: the kernel can tell that code moved, and it
cannot tell what that means. So every test here is either about a detection
being recorded faithfully, or about a resolution being refused for a reason
that is checkable - a V3 naming an ADR that does not exist, a V2 with no
evidence. The kernel never picks a verdict and never edits a claim's prose.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from forge import anchor, ledger, store
from forge.cli import main

TODAY = _dt.date(2026, 9, 11)

CODE = "def greet():\n    return 'hi'\n"


def claim_text(sha: str, ident: str = "INV-greeting") -> str:
    return (
        f"# Domain\n\n### {ident} - the greeting never changes shape\n\n"
        "```claim\n"
        "kind:     invariant\n"
        "status:   asserted\n"
        "truth-source: code\n"
        f'anchors:  ["src/app.py#greet@{sha}"]\n'
        "reviewed: 2026-09-01\n"
        "```\n\n"
        "Prose about the greeting, long enough to read like a claim and to say\n"
        "something a reader could not get from the symbol name.\n"
    )


@pytest.fixture
def drifted(repo):
    """A store with one claim whose code has since moved."""
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    repo.commit("a claim")
    repo.write("src/app.py", "def greet(name):\n    return f'hi {name}'\n")
    repo.commit("the signature changed")
    return repo


def record(repo):
    return ledger.record(repo.root, anchor.classify_store(repo.root), today=TODAY)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_a_stale_claim_opens_an_entry(drifted):
    (entry,) = record(drifted)
    assert entry.id == "D-001"
    assert entry.claim == "INV-greeting"
    assert entry.signal == "stale"
    assert entry.status == "open"
    assert entry.anchors_changed


def test_the_proposal_is_a_proposal_and_only_for_the_case_evidence_supports(drifted):
    """V1 is proposed for a signature change because that is the only reading
    a fingerprint supports alone. Everything else is a judgement, and a machine
    guess in that slot is read as an answer."""
    (entry,) = record(drifted)
    assert entry.proposed_verdict == "V1"
    assert entry.verdict is None


def test_a_body_only_change_proposes_nothing(repo):
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    repo.commit("a claim")
    repo.write("src/app.py", "def greet():\n    return 'hello'\n")
    repo.commit("the body changed, the signature did not")

    (entry,) = record(repo)
    assert entry.signal == "shifted"
    assert entry.proposed_verdict is None


def test_recording_twice_does_not_duplicate(drifted):
    """A week of unresolved drift must not produce a week of entries; that is
    how a ledger becomes a file people stop opening."""
    assert len(record(drifted)) == 1
    assert record(drifted) == []
    assert len(ledger.load_ledger(drifted.root)) == 1


def test_a_fresh_store_records_nothing(repo):
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    repo.commit("a claim")

    assert record(repo) == []


def test_ids_are_never_reused(drifted):
    record(drifted)
    ledger.resolve(drifted.root, "D-001", "V1", today=TODAY)
    drifted.write("src/app.py", "def greet(a, b):\n    return 0\n")
    drifted.commit("it moved again")

    (second,) = record(drifted)
    assert second.id == "D-002"


# ---------------------------------------------------------------------------
# The refusals - the kernel's whole contribution to a resolution
# ---------------------------------------------------------------------------

def test_v2_needs_evidence(drifted):
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="evidence"):
        ledger.resolve(drifted.root, "D-001", "V2", today=TODAY)


def test_v3_needs_an_adr(drifted):
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="--adr"):
        ledger.resolve(drifted.root, "D-001", "V3", today=TODAY)


def test_v3_refuses_an_adr_that_does_not_exist(drifted):
    """A decision nobody recorded is not a decision that changed."""
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="ADR-0099"):
        ledger.resolve(drifted.root, "D-001", "V3", adr="99", today=TODAY)


def test_v3_accepts_the_adr_forge_init_wrote(drifted):
    record(drifted)
    entry = ledger.resolve(drifted.root, "D-001", "V3", adr="1", today=TODAY)
    assert entry.verdict == "V3"
    assert entry.adr == "ADR-0001"


def test_an_adr_may_be_named_three_ways(drifted):
    record(drifted)
    assert ledger._adr_id("1") == ledger._adr_id("0001") == ledger._adr_id("ADR-0001")


def test_v4_needs_evidence_or_an_explicit_acceptance(drifted):
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="accept-asserted"):
        ledger.resolve(drifted.root, "D-001", "V4", today=TODAY)
    entry = ledger.resolve(drifted.root, "D-001", "V4",
                           accept_asserted=True, today=TODAY)
    assert entry.evidence and "asserted" in entry.evidence


def test_an_unknown_verdict_is_refused(drifted):
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="not a verdict"):
        ledger.resolve(drifted.root, "D-001", "V9", today=TODAY)


def test_a_resolved_entry_is_not_overwritten(drifted):
    """A verdict that turned out wrong is a new detection, not an edit of the
    record that says what somebody believed at the time."""
    record(drifted)
    ledger.resolve(drifted.root, "D-001", "V1", today=TODAY)
    with pytest.raises(ledger.LedgerError, match="already resolved"):
        ledger.resolve(drifted.root, "D-001", "V2", evidence="x", today=TODAY)


# ---------------------------------------------------------------------------
# `confirm` - not a fifth verdict
# ---------------------------------------------------------------------------

def test_confirm_restamps_and_leaves_the_prose_alone(drifted):
    record(drifted)
    before = next(c for c in store.load_store(drifted.root)).prose

    entry, restamped = ledger.confirm(drifted.root, "D-001", today=TODAY)
    assert entry.verdict == "confirmed"
    assert restamped

    after = next(c for c in store.load_store(drifted.root))
    assert after.prose == before
    assert after.reviewed == "2026-09-11"


def test_a_confirmed_claim_is_fresh_again(drifted):
    """The end-to-end point: the signal clears because a human confirmed it,
    and the next scan is quiet."""
    record(drifted)
    ledger.confirm(drifted.root, "D-001", today=TODAY)
    drifted.commit("restamped")

    (drift,) = anchor.classify_store(drifted.root)
    assert drift.changed is False


def test_confirm_refuses_an_already_resolved_entry(drifted):
    record(drifted)
    ledger.resolve(drifted.root, "D-001", "V1", today=TODAY)
    with pytest.raises(ledger.LedgerError, match="already resolved"):
        ledger.confirm(drifted.root, "D-001", today=TODAY)


# ---------------------------------------------------------------------------
# Waivers
# ---------------------------------------------------------------------------

def test_a_waiver_needs_a_reason_and_an_expiry(drifted):
    record(drifted)
    with pytest.raises(ledger.LedgerError, match="reason"):
        ledger.waive(drifted.root, "D-001", until="2026-12-01", reason="  ")
    with pytest.raises(ledger.LedgerError, match="--until"):
        ledger.waive(drifted.root, "D-001", until="", reason="shipping Friday")


def test_a_live_waiver_closes_the_entry(drifted):
    record(drifted)
    ledger.waive(drifted.root, "D-001", until="2099-01-01", reason="shipping Friday")
    assert ledger.open_entries(drifted.root, today=TODAY) == []


def test_an_expired_waiver_opens_it_again(drifted):
    """This is the only thing that makes a waiver different from deleting the
    entry."""
    record(drifted)
    ledger.waive(drifted.root, "D-001", until="2026-01-01", reason="shipping Friday")
    assert [e.id for e in ledger.open_entries(drifted.root, today=TODAY)] == ["D-001"]


def test_a_waiver_with_an_unreadable_expiry_is_expired(drifted):
    """A waiver that never expires is the disabled gate this exists to avoid,
    so an unreadable expiry fails open rather than closed."""
    record(drifted)
    ledger.waive(drifted.root, "D-001", until="soon", reason="shipping Friday")
    assert [e.id for e in ledger.open_entries(drifted.root, today=TODAY)] == ["D-001"]


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_the_ledger_survives_a_write_and_a_read(drifted):
    record(drifted)
    ledger.resolve(drifted.root, "D-001", "V2",
                   evidence="the property was never enforced anywhere", today=TODAY)
    (entry,) = ledger.load_ledger(drifted.root)
    assert entry.status == "resolved"
    assert entry.verdict == "V2"
    assert entry.resolved == "2026-09-11"
    assert "never enforced" in entry.evidence
    assert entry.parse_error is None
