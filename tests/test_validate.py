"""S1-S18, the claim-store checks.

The M0 acceptance criterion has two halves and both are here: a hand-written
store of ten claims across the five MVP kinds passes `forge check` clean, and
every check has a fixture that fails it with the right code.

The clean store is the load-bearing half. A validator nobody can satisfy is a
validator that gets bypassed, and eighteen checks written without one is
exactly how that happens - each is defensible alone, and together they forbid
every real claim anyone would write.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from forge import derive, validate
from forge.cli import main

TODAY = dt.date(2026, 9, 11)

SOURCE = '''\
# The payments domain. Enforcement back-references live here, in code, because
# a claim nothing points at is an orphan (S17).
# forge:ARC-layers
# forge:ARC-no-cycles
# forge:PIT-float-money
# forge:PIT-retry-storm


def capture(amount_minor):
    """Reserve funds against an authorisation."""
    return {"captured": amount_minor}


def refundable(captured_minor, settled_minor):  # forge:INV-refund-cap
    """How much of a capture is still refundable."""
    return captured_minor - settled_minor
'''

TESTS = '''\
# @covers INV-refund-cap
def test_refund_never_exceeds_capture():
    assert True


# @covers INV-idempotent-capture
def test_capture_is_idempotent():
    assert True
'''

ARCHITECTURE = """\
# Architecture

### ARC-layers — The domain layer must not import transport or persistence

```claim
kind: architecture
status: asserted
truth-source: decision
anchors: [src/pay.py]
governs: [CMP-payments]
since: ADR-0001
reviewed: 2026-09-01
```

Handlers may call the domain; the domain must never call back. Inverting this
is what turns a refund rule into something you can only test by standing up a
web server, and it is the single change that makes the domain untestable.

### ARC-no-cycles — Module dependencies must form a directed acyclic graph

```claim
kind: architecture
status: asserted
truth-source: decision
anchors: [src/pay.py]
governs: [CMP-ledger]
since: ADR-0001
reviewed: 2026-09-01
```

A cycle between modules must be broken at the point it is introduced. Left in,
it removes the possibility of loading either half alone, which is what every
later attempt to extract a service runs into.
"""

COMPONENTS = """\
# Components

### CMP-payments — Capture, refund and their money arithmetic

```claim
kind: component
status: asserted
truth-source: decision
anchors: [src/pay.py]
governs: [CON-capture, INV-refund-cap]
reviewed: 2026-09-01
```

Owns every decision about how much money may move and when. It must reject an
overdraw at its boundary rather than clamping, because a clamp silently
under-refunds a customer and leaves no trace that it happened.

### CMP-ledger — The append-only record of settled movements

```claim
kind: component
status: asserted
truth-source: decision
anchors: [src/pay.py]
governs: [CON-settlement, INV-idempotent-capture]
reviewed: 2026-09-01
```

Records what actually moved, and may never be edited in place. A correction is
always a new entry, because an editable ledger cannot answer what was believed
at the time a dispute was raised.
"""

DOMAIN = """\
# Domain

### CON-capture — Taking money that was previously authorised

```claim
kind: concept
status: asserted
truth-source: decision
anchors: []
reviewed: 2026-09-01
```

A capture is distinct from an authorisation: the authorisation reserves, the
capture takes. Treating them as one word is what produces code that refunds
against a reservation that never moved any money.

### CON-settlement — Money that has left the acquirer and cannot be recalled

```claim
kind: concept
status: asserted
truth-source: decision
anchors: []
reviewed: 2026-09-01
```

Settlement is the point of no return, and it is not the same as a successful
response. A payment may succeed and never settle, so no rule may treat the two
as interchangeable.

### INV-refund-cap — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors: [src/pay.py#refundable]
evidence:
  - test: tests/test_pay.py::test_refund_never_exceeds_capture
reviewed: 2026-09-01
```

Partial refunds accumulate: what is bounded is the sum of settled refunds, not
each refund on its own. An attempt over the remaining balance must be rejected
at the domain boundary rather than clamped.

### INV-idempotent-capture — Capturing twice with one key moves money once

```claim
kind: invariant
status: enforced
truth-source: tests
anchors: [src/pay.py#capture]
evidence:
  - test: tests/test_pay.py::test_capture_is_idempotent
reviewed: 2026-09-01
```

A retry must be indistinguishable from the first attempt. Networks retry
without asking, so any rule that assumes one delivery per request is a rule
that will double-charge somebody.
"""

PITFALLS = """\
# Pitfalls

### PIT-float-money — Money is never a floating-point number here

```claim
kind: pitfall
status: asserted
truth-source: decision
anchors: [src/pay.py]
reviewed: 2026-09-01
```

Every amount is an integer count of minor units. This was paid for: a rounding
difference of a fraction of a unit accumulated across a settlement batch and
had to be reconciled by hand.

### PIT-retry-storm — A failed capture must not be retried in a tight loop

```claim
kind: pitfall
status: asserted
truth-source: decision
anchors: [src/pay.py]
reviewed: 2026-09-01
```

The acquirer rate-limits, and a tight retry loop converts one failure into an
outage for every other payment in flight. Back off, and never retry inside a
request handler.
"""

ADR = """\
# ADR-0001 — Adopt an anchored claim store

## Status
Accepted

## Decision
Knowledge about this system lives in anchored claims, checked by a
deterministic tool, rather than in free prose nobody can verify.
"""


@pytest.fixture
def store_repo(repo):
    """A store that passes every check. The other tests break it on purpose."""
    repo.write("src/pay.py", SOURCE)
    repo.write("tests/test_pay.py", TESTS)
    repo.write("docs/system/architecture.md", ARCHITECTURE)
    repo.write("docs/system/components.md", COMPONENTS)
    repo.write("docs/system/domain.md", DOMAIN)
    repo.write("docs/system/pitfalls.md", PITFALLS)
    repo.write("docs/system/decisions/ADR-0001-adopt-forge.md", ADR)
    repo.commit("a hand-written store")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    return repo


def check(repo, **kwargs) -> list[validate.Issue]:
    return validate.check_store(repo.root, today=TODAY, **kwargs)


def codes(issues: list[validate.Issue]) -> list[str]:
    return [issue.code for issue in issues]


def edit(repo, path: str, old: str, new: str) -> None:
    """Rewrite one fragment of a store file and re-commit."""
    target = repo.root / path
    text = target.read_text(encoding="utf-8")
    assert old in text, f"fixture drifted: {old!r} is no longer in {path}"
    repo.write(path, text.replace(old, new, 1))
    repo.commit(f"break {path}")


# ---------------------------------------------------------------------------
# The acceptance case
# ---------------------------------------------------------------------------

def test_a_hand_written_store_passes_every_check(store_repo):
    """The M0 acceptance criterion, and the check on the checks.

    Eighteen rules are easy to write and hard to satisfy together. If this ever
    fails, the validator has become stricter than the format it validates, and
    that is a bug in the validator until proven otherwise."""
    issues = check(store_repo)
    assert issues == [], "\n".join(
        f"{i.level} {i.code} {i.path}:{i.line} {i.message}" for i in issues
    )


def test_the_store_really_does_cover_the_five_mvp_kinds(store_repo):
    from forge import store as store_mod

    claims = store_mod.load_store(store_repo.root)
    assert len(claims) == 10
    assert {c.kind for c in claims} == {
        "architecture", "component", "concept", "invariant", "pitfall",
    }


def test_every_issue_carries_a_fix(store_repo):
    """An error without a next action trains people to ignore errors."""
    edit(store_repo, "docs/system/domain.md", "### CON-capture", "### con_capture")
    edit(store_repo, "docs/system/pitfalls.md", "reviewed: 2026-09-01", "reviewed: never")
    issues = check(store_repo)
    assert issues
    for issue in issues:
        assert issue.fix.strip(), f"{issue.code} has no fix"
        assert issue.path
        assert issue.level in ("ERROR", "WARNING")


# ---------------------------------------------------------------------------
# S1, S2 - identity
# ---------------------------------------------------------------------------

def test_s1_a_malformed_id_is_reported_rather_than_skipped(store_repo):
    """The failure mode this check exists for.

    The parser's heading pattern only matches well-formed IDs, so a typo makes
    the claim *invisible* rather than invalid - it silently stops being part of
    the store. Checking only what parsed would give this file a clean bill of
    health."""
    edit(store_repo, "docs/system/pitfalls.md", "### PIT-float-money", "### PIT_float_money")
    issues = check(store_repo)
    assert "store.id_format" in codes(issues)
    hit = next(i for i in issues if i.code == "store.id_format")
    assert hit.line == 3
    assert "PIT-float-money" in hit.fix


def test_s1_accepts_both_slugs_and_numbers(repo):
    repo.write("docs/system/domain.md",
               "### INV-7 — Numbered\n\n### INV-refund-cap — Slugged\n")
    repo.commit("both forms")
    assert "store.id_format" not in codes(check(repo))


def test_s2_a_duplicate_id_is_an_error(store_repo):
    edit(store_repo, "docs/system/pitfalls.md",
         "### PIT-retry-storm", "### PIT-float-money")
    issues = [i for i in check(store_repo) if i.code == "store.id_unique"]
    assert issues and "already defined" in issues[0].message


def test_s2_numeric_ids_must_ascend_within_a_file(repo):
    repo.write("docs/system/domain.md", "### INV-9 — Nine\n\nBody line one.\nBody line two.\n"
                                        "\n### INV-2 — Two\n\nBody line one.\nBody line two.\n")
    repo.commit("out of order")
    issues = [i for i in check(repo) if i.code == "store.id_unique"]
    assert issues and "does not ascend" in issues[0].message


def test_s2_slugs_have_no_ordering(repo):
    repo.write("docs/system/domain.md", "### INV-zebra — Z\n\nBody line one.\nBody line two.\n"
                                        "\n### INV-apple — A\n\nBody line one.\nBody line two.\n")
    repo.commit("slugs in any order")
    assert "store.id_unique" not in codes(check(repo))


def test_s2_a_retired_id_is_never_reused(store_repo):
    edit(store_repo, "docs/system/pitfalls.md",
         "kind: pitfall\nstatus: asserted\ntruth-source: decision\nanchors: [src/pay.py]\n"
         "reviewed: 2026-09-01\n```\n\nThe acquirer",
         "kind: pitfall\nstatus: retired\nretired-ground: 2\n"
         "retired-evidence: the linter now fails a retry inside a handler\n"
         "truth-source: decision\nanchors: [src/pay.py]\n"
         "reviewed: 2026-09-01\n```\n\nThe acquirer")
    store_repo.write("docs/system/extra.md",
                     "### PIT-retry-storm — Reused\n\n```claim\nkind: pitfall\nstatus: asserted\n"
                     "truth-source: decision\nanchors: [src/pay.py]\nreviewed: 2026-09-01\n```\n\n"
                     "Body line one, long enough to be prose.\nBody line two, likewise.\n")
    store_repo.commit("reuse a retired name")
    messages = [i.message for i in check(store_repo) if i.code == "store.id_unique"]
    assert any("never reused" in m for m in messages)


# ---------------------------------------------------------------------------
# S3, S4 - the claim block
# ---------------------------------------------------------------------------

def test_s3_a_broken_fence_is_reported(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\n  status: asserted\n : :")
    issues = [i for i in check(store_repo) if i.code == "store.claim_fence"]
    assert issues and "YAML" in issues[0].message


def test_s3_a_missing_fence_is_reported(repo):
    repo.write("docs/system/domain.md", "### CON-capture — No block\n\nProse one.\nProse two.\n")
    repo.commit("no fence")
    assert "store.claim_fence" in codes(check(repo))


@pytest.mark.parametrize("field", ["kind", "status", "truth-source", "anchors", "reviewed"])
def test_s4_each_required_field_is_required(store_repo, field):
    text = (store_repo.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    line = next(l for l in text.split("\n") if l.startswith(f"{field}:"))
    edit(store_repo, "docs/system/pitfalls.md", line + "\n", "")
    issues = [i for i in check(store_repo) if i.code == "store.required_fields"]
    assert any(field in i.message for i in issues)


def test_s4_an_empty_anchors_list_is_present_not_missing(store_repo):
    """`anchors: []` is legal for a concept; no `anchors` key never is.

    After normalisation the two are indistinguishable, which is why the parser
    records the keys the fence declared."""
    assert "store.required_fields" not in codes(check(store_repo))


@pytest.mark.parametrize("bad,good", [
    ("status: asserted", "status: probably"),
    ("truth-source: decision", "truth-source: vibes"),
])
def test_s4_values_are_checked_against_the_allowed_set(store_repo, bad, good):
    edit(store_repo, "docs/system/pitfalls.md", bad, good)
    assert "store.required_fields" in codes(check(store_repo))


def test_s4_kind_must_agree_with_the_prefix(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall", "kind: invariant")
    issues = [i for i in check(store_repo) if i.code == "store.required_fields"]
    assert any("contradicts the PIT- prefix" in i.message for i in issues)


def test_s4_a_future_review_date_is_an_error(store_repo):
    """`reviewed` feeds review-debt reporting; a date that has not happened
    makes the claim permanently the freshest thing in the store."""
    edit(store_repo, "docs/system/pitfalls.md", "reviewed: 2026-09-01", "reviewed: 2027-01-01")
    issues = [i for i in check(store_repo) if i.code == "store.required_fields"]
    assert any("in the future" in i.message for i in issues)
    assert any(TODAY.isoformat() in i.fix for i in issues)


def test_s4_a_quoted_impossible_date_is_an_error(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "reviewed: 2026-09-01", 'reviewed: "2026-02-30"')
    issues = [i for i in check(store_repo) if i.code == "store.required_fields"]
    assert any("not a real date" in i.message for i in issues)


def test_s4_an_unquoted_impossible_date_is_caught_by_the_fence(store_repo):
    """PyYAML resolves an unquoted `2026-02-30` to a timestamp and then lets
    `datetime.date` raise a ValueError, not a YAMLError. Uncaught, a typo in
    one review date takes down every command that reads the store - including
    the one whose job is to report it."""
    edit(store_repo, "docs/system/pitfalls.md", "reviewed: 2026-09-01", "reviewed: 2026-02-30")
    issues = [i for i in check(store_repo) if i.code == "store.claim_fence"]
    assert issues and "day is out of range" in issues[0].message


# ---------------------------------------------------------------------------
# S5, S6, S7
# ---------------------------------------------------------------------------

def test_s5_an_invariant_must_be_anchored(store_repo):
    edit(store_repo, "docs/system/domain.md", "anchors: [src/pay.py#refundable]", "anchors: []")
    issues = [i for i in check(store_repo) if i.code == "store.anchor_required"]
    assert issues and "rot silently" in issues[0].message


def test_s5_a_concept_may_have_no_anchors(store_repo):
    assert "store.anchor_required" not in codes(check(store_repo))


def test_s6_enforced_without_evidence_is_an_error(store_repo):
    edit(store_repo, "docs/system/domain.md",
         "evidence:\n  - test: tests/test_pay.py::test_refund_never_exceeds_capture\n", "")
    issues = [i for i in check(store_repo) if i.code == "store.evidence_required"]
    assert issues and "name the tool" in issues[0].message
    assert "status: asserted" in issues[0].fix


def test_s6_evidence_must_name_a_test_that_exists(store_repo):
    edit(store_repo, "docs/system/domain.md",
         "test: tests/test_pay.py::test_refund_never_exceeds_capture",
         "test: tests/test_pay.py::test_that_was_deleted")
    issues = [i for i in check(store_repo) if i.code == "store.evidence_required"]
    assert issues and "tests.json" in issues[0].message
    # The fix names the test that *does* cover the claim, so the reader can see
    # at once whether this is a typo or a missing test.
    assert "test_refund_never_exceeds_capture" in issues[0].fix


def test_s6_an_unrecognised_evidence_kind_is_an_error(store_repo):
    edit(store_repo, "docs/system/domain.md",
         "- test: tests/test_pay.py::test_refund_never_exceeds_capture",
         "- someone said so")
    assert "store.evidence_required" in codes(check(store_repo))


def test_s7_an_architecture_claim_needs_an_adr(store_repo):
    edit(store_repo, "docs/system/architecture.md", "since: ADR-0001\n", "")
    issues = [i for i in check(store_repo) if i.code == "store.adr_required"]
    assert issues and "must name the decision" in issues[0].message


def test_s7_the_adr_file_must_exist(store_repo):
    edit(store_repo, "docs/system/architecture.md", "since: ADR-0001", "since: ADR-0099")
    issues = [i for i in check(store_repo) if i.code == "store.adr_required"]
    assert issues and "ADR-0099" in issues[0].message


# ---------------------------------------------------------------------------
# S8 - the governs graph
# ---------------------------------------------------------------------------

def test_s8_governs_must_name_an_existing_claim(store_repo):
    edit(store_repo, "docs/system/components.md", "governs: [CON-capture, INV-refund-cap]",
         "governs: [CON-nowhere]")
    issues = [i for i in check(store_repo) if i.code == "store.governs_dag"]
    assert issues and "no claim defines" in issues[0].message


def test_s8_self_reference_is_an_error(store_repo):
    edit(store_repo, "docs/system/components.md", "governs: [CON-capture, INV-refund-cap]",
         "governs: [CMP-payments]")
    issues = [i for i in check(store_repo) if i.code == "store.governs_dag"]
    assert issues and "governs itself" in issues[0].message


def test_s8_a_cycle_is_reported_once_with_its_path(store_repo):
    edit(store_repo, "docs/system/domain.md", """kind: concept
status: asserted
truth-source: decision
anchors: []
reviewed: 2026-09-01
```

A capture is distinct""", """kind: concept
status: asserted
truth-source: decision
anchors: []
governs: [CMP-payments]
reviewed: 2026-09-01
```

A capture is distinct""")
    issues = [i for i in check(store_repo) if i.code == "store.governs_dag"]
    cycles = [i for i in issues if "cyclic" in i.message]
    assert len(cycles) == 1
    assert "CMP-payments" in cycles[0].message and "CON-capture" in cycles[0].message


def test_s8_a_deep_cycle_does_not_blow_the_stack(repo):
    """The walk is iterative. A cycle is exactly the input that makes a
    recursive one recurse forever, and this check exists to run on stores that
    have one."""
    depth = 2500  # comfortably past CPython's default recursion limit
    parts = []
    for index in range(depth):
        target = f"CMP-n{(index + 1) % depth}"
        parts.append(
            f"### CMP-n{index} — Node\n\n```claim\nkind: component\nstatus: asserted\n"
            f"truth-source: decision\nanchors: []\ngoverns: [{target}]\n"
            f"reviewed: 2026-09-01\n```\n\nBody line one.\nBody line two.\n"
        )
    repo.write("docs/system/components.md", "\n".join(parts))
    repo.commit("a very long cycle")
    issues = [i for i in check(repo) if "cyclic" in i.message]
    assert len(issues) == 1


def test_s8_supersedes_must_point_at_a_retired_claim(store_repo):
    edit(store_repo, "docs/system/pitfalls.md",
         "kind: pitfall\nstatus: asserted\ntruth-source: decision\nanchors: [src/pay.py]\nreviewed: 2026-09-01\n```\n\nEvery amount",
         "kind: pitfall\nstatus: asserted\ntruth-source: decision\nanchors: [src/pay.py]\nsupersedes: PIT-retry-storm\nreviewed: 2026-09-01\n```\n\nEvery amount")
    issues = [i for i in check(store_repo) if i.code == "store.governs_dag"]
    assert issues and "status: asserted" in issues[0].message


# ---------------------------------------------------------------------------
# S9, S11 - the prose
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("placeholder", ["TBD", "TODO", "FIXME", "XXX",
                                         "[NEEDS CLARIFICATION: whose?",
                                         "{component-name}",
                                         "similar to INV-refund-cap"])
def test_s9_placeholders_are_errors(store_repo, placeholder):
    edit(store_repo, "docs/system/pitfalls.md", "The acquirer rate-limits",
         f"{placeholder}. The acquirer rate-limits")
    assert "store.placeholder" in codes(check(store_repo))


def test_s9_a_placeholder_inside_a_code_fence_is_not_one(store_repo):
    """Fences are blanked before the scan, or every document that shows what
    the check rejects trips the check."""
    edit(store_repo, "docs/system/pitfalls.md", "Back off, and never retry",
         "Rejected, for example:\n\n```\nreviewed: TBD\n```\n\nBack off, and never retry")
    assert "store.placeholder" not in codes(check(store_repo))


def test_s9_the_reported_line_survives_fence_blanking(store_repo):
    edit(store_repo, "docs/system/pitfalls.md",
         "The acquirer rate-limits", "```\nfiller\nfiller\n```\n\nTODO. The acquirer rate-limits")
    hit = next(i for i in check(store_repo) if i.code == "store.placeholder")
    text = (store_repo.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    assert "TODO" in text.split("\n")[hit.line - 1]


def test_s11_a_claim_with_no_prose_is_a_label(store_repo):
    edit(store_repo, "docs/system/pitfalls.md",
         "The acquirer rate-limits, and a tight retry loop converts one failure into an\n"
         "outage for every other payment in flight. Back off, and never retry inside a\n"
         "request handler.\n", "One line only.\n")
    issues = [i for i in check(store_repo) if i.code == "store.prose_present"]
    assert issues and "not knowledge" in issues[0].message


# ---------------------------------------------------------------------------
# S10 - candidates
# ---------------------------------------------------------------------------

def test_s10_confidence_is_forbidden_outside_candidates(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nconfidence: high\nstatus: asserted")
    issues = [i for i in check(store_repo) if i.code == "store.candidate_isolation"]
    assert issues and "candidate field" in issues[0].message


def test_s10_a_candidate_must_be_proposed(store_repo):
    store_repo.write("docs/system/candidates/guesses.md",
                     "### CON-authorisation — Reserving funds\n\n```claim\nkind: concept\n"
                     "status: asserted\ntruth-source: decision\nanchors: []\nconfidence: low\n"
                     "reviewed: 2026-09-01\n```\n\nBody line one.\nBody line two.\n")
    store_repo.commit("a candidate that thinks it is ratified")
    issues = [i for i in check(store_repo) if i.code == "store.candidate_isolation"]
    assert any("must be status: proposed" in i.message for i in issues)


def test_s10_a_ratified_claim_may_not_govern_a_candidate(store_repo):
    store_repo.write("docs/system/candidates/guesses.md",
                     "### CON-authorisation — Reserving funds\n\n```claim\nkind: concept\n"
                     "status: proposed\ntruth-source: decision\nanchors: []\nconfidence: low\n"
                     "reviewed: 2026-09-01\n```\n\nBody line one.\nBody line two.\n")
    store_repo.write("docs/system/components.md",
                     (store_repo.root / "docs/system/components.md").read_text(encoding="utf-8")
                     .replace("governs: [CON-capture, INV-refund-cap]",
                              "governs: [CON-capture, INV-refund-cap, CON-authorisation]"))
    store_repo.commit("lean on a guess")
    issues = [i for i in check(store_repo) if i.code == "store.candidate_isolation"]
    assert any("only a candidate" in i.message for i in issues)


# ---------------------------------------------------------------------------
# S12 - anchors resolve at HEAD
# ---------------------------------------------------------------------------

def test_s12_a_deleted_path_is_reported(store_repo):
    edit(store_repo, "docs/system/domain.md", "anchors: [src/pay.py#refundable]",
         "anchors: [src/gone.py#refundable]")
    issues = [i for i in check(store_repo) if i.code == "store.anchor_missing"]
    assert issues and "does not exist at HEAD" in issues[0].message
    assert "forge reanchor INV-refund-cap" in issues[0].fix


def test_s12_a_deleted_symbol_is_reported(store_repo):
    edit(store_repo, "docs/system/domain.md", "anchors: [src/pay.py#refundable]",
         "anchors: [src/pay.py#computeRefundable]")
    issues = [i for i in check(store_repo) if i.code == "store.anchor_missing"]
    assert issues and "computeRefundable" in issues[0].message


def test_s12_a_malformed_anchor_is_reported(store_repo):
    edit(store_repo, "docs/system/domain.md", "anchors: [src/pay.py#refundable]",
         "anchors: ['/etc/passwd']")
    issues = [i for i in check(store_repo) if i.code == "store.anchor_missing"]
    assert issues and "malformed" in issues[0].message


def test_s12_a_directory_anchor_is_allowed(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "anchors: [src/pay.py]\nreviewed: 2026-09-01\n```\n\nEvery amount",
         "anchors: [src]\nreviewed: 2026-09-01\n```\n\nEvery amount")
    assert "store.anchor_missing" not in codes(check(store_repo))


def test_s12_does_not_fire_when_the_grammar_cannot_place_a_visible_name(repo):
    """A check that cries wolf on valid anchors gets switched off.

    The three MVP grammars do not model every declaration shape, so a symbol
    the parser cannot locate but which is plainly in the file is left alone."""
    repo.write("src/config.yaml", "refundable:\n  cap: enforced\n")
    repo.write("docs/system/domain.md",
               "### INV-cap — Bounded\n\n```claim\nkind: invariant\nstatus: asserted\n"
               "truth-source: config\nanchors: [src/config.yaml#refundable]\n"
               "reviewed: 2026-09-01\n```\n\nBody line one.\nBody line two.\n")
    repo.commit("an anchor into a file with no grammar")
    assert "store.anchor_missing" not in codes(check(repo))


# ---------------------------------------------------------------------------
# S13, S14, S15 - the anti-noise heuristics
# ---------------------------------------------------------------------------

def test_s13_prose_that_only_restates_the_code_is_flagged(repo):
    repo.write("src/pay.py", "def computeRefundable(capturedMinor, settledMinor):\n"
                             "    totalSettled = settledMinor\n"
                             "    return capturedMinor - totalSettled\n")
    repo.write("docs/system/domain.md",
               "### CMP-pay — Refunds\n\n```claim\nkind: component\nstatus: asserted\n"
               "truth-source: code\nanchors: [src/pay.py#computeRefundable]\n"
               "reviewed: 2026-09-01\n```\n\n"
               "The computeRefundable function takes capturedMinor and settledMinor.\n"
               "It sets totalSettled and subtracts it from capturedMinor.\n")
    repo.commit("english transcription of a function")
    issues = [i for i in check(repo) if i.code == "store.derivable_smell"]
    assert issues and issues[0].level == "WARNING"


def test_s13_a_rule_is_never_derivable(store_repo):
    """A claim that states a rule is doing the job no reader can do from the
    code, however many of its words are identifiers."""
    assert "store.derivable_smell" not in codes(check(store_repo))


def test_s13_can_be_acknowledged(repo):
    repo.write("src/pay.py", "def computeRefundable(capturedMinor, settledMinor):\n"
                             "    totalSettled = settledMinor\n"
                             "    return capturedMinor - totalSettled\n")
    repo.write("docs/system/domain.md",
               "### CMP-pay — Refunds\n\n```claim\nkind: component\nstatus: asserted\n"
               "truth-source: code\nanchors: [src/pay.py#computeRefundable]\n"
               "reviewed: 2026-09-01\n```\n\n"
               "The computeRefundable function takes capturedMinor and settledMinor.\n"
               "It sets totalSettled and subtracts it from capturedMinor.\n"
               "forge:not-derivable the naming is the interface contract here\n")
    repo.commit("acknowledged")
    assert "store.derivable_smell" not in codes(check(repo))


def test_s14_a_component_claim_that_is_a_directory_listing_is_flagged(repo):
    repo.write("src/pay.py", "x = 1\n")
    repo.write("docs/system/components.md",
               "### CMP-pay — Payments\n\n```claim\nkind: component\nstatus: asserted\n"
               "truth-source: decision\nanchors: [src/pay.py]\nreviewed: 2026-09-01\n```\n\n"
               "Lives in `src/pay/*`.\nSee the directory.\n")
    repo.commit("ls, in markdown")
    issues = [i for i in check(repo) if i.code == "store.listing_smell"]
    assert issues and "responsible for" in issues[0].fix


def test_s15_a_version_in_prose_is_flagged(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "The acquirer rate-limits",
         "We pin requests 2.31 for this. The acquirer rate-limits")
    issues = [i for i in check(store_repo) if i.code == "store.stack_fact_smell"]
    assert issues and "lockfiles" in issues[0].message


def test_the_smells_are_warnings_and_never_fail_the_gate(repo, capsys):
    repo.write("src/pay.py", "x = 1\n")
    repo.write("docs/system/components.md",
               "### CMP-pay — Payments\n\n```claim\nkind: component\nstatus: asserted\n"
               "truth-source: decision\nanchors: [src/pay.py]\nreviewed: 2026-09-01\n```\n\n"
               "Lives in `src/pay/*`.\nSee the directory.\n")
    repo.commit("a warning and nothing else")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    assert main(["check", "--repo", str(repo.root)]) == 0
    assert "WARNING" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# S16 - the always-loaded budget
# ---------------------------------------------------------------------------

def test_s16_the_always_loaded_set_has_a_budget(store_repo):
    store_repo.write("docs/system/OVERVIEW.md", "# Overview\n" + "filler\n" * 500)
    store_repo.commit("blow the budget")
    issues = [i for i in check(store_repo) if i.code == "store.budget"]
    assert issues
    assert "400" in issues[0].message
    # The budget is the point of the budget.
    assert "not a fix" in issues[0].fix


def test_s16_the_budget_can_be_lowered_by_config(store_repo):
    store_repo.write(".forge/config.yaml", "budgets:\n  always_loaded_lines: 10\n")
    store_repo.commit("a tighter budget")
    assert "store.budget" in codes(check(store_repo))


def test_s16_a_garbage_budget_falls_back_to_the_default(store_repo):
    """A typo in an optional setting must not change what is enforced."""
    store_repo.write(".forge/config.yaml", "budgets:\n  always_loaded_lines: soon\n")
    store_repo.commit("a budget that is not a number")
    assert "store.budget" not in codes(check(store_repo))


# ---------------------------------------------------------------------------
# S17 - orphans
# ---------------------------------------------------------------------------

def test_s17_a_claim_nothing_references_is_flagged(store_repo):
    store_repo.write("docs/system/pitfalls.md",
                     (store_repo.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
                     + "\n### PIT-lonely — Nobody consults this\n\n```claim\nkind: pitfall\n"
                       "status: asserted\ntruth-source: decision\nanchors: [src/pay.py]\n"
                       "reviewed: 2026-09-01\n```\n\n"
                       "This must never happen, and nothing points at the claim saying so.\n"
                       "Two lines of prose, so it is not a label.\n")
    store_repo.commit("an orphan")
    derive.derive_all(store_repo.root)
    store_repo.commit("chore: sync derived tier")
    issues = [i for i in check(store_repo) if i.code == "store.orphan"]
    assert issues and issues[0].claim == "PIT-lonely"
    assert issues[0].level == "WARNING", "an orphan is never grounds for deletion"


def test_s17_a_back_reference_is_enough(store_repo):
    assert "store.orphan" not in codes(check(store_repo))


def test_s17_a_citation_in_a_recent_change_is_enough(store_repo):
    store_repo.write("docs/system/pitfalls.md",
                     (store_repo.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
                     + "\n### PIT-lonely — Nobody consults this\n\n```claim\nkind: pitfall\n"
                       "status: asserted\ntruth-source: decision\nanchors: [src/pay.py]\n"
                       "reviewed: 2026-09-01\n```\n\n"
                       "This must never happen, and nothing points at the claim saying so.\n"
                       "Two lines of prose, so it is not a label.\n")
    store_repo.write("changes/0001-something/impact.md", "Unaffected: PIT-lonely\n")
    store_repo.commit("a change that argued about it")
    derive.derive_all(store_repo.root)
    store_repo.commit("chore: sync derived tier")
    assert "store.orphan" not in codes(check(store_repo))


# ---------------------------------------------------------------------------
# S18 - retirement grounds
# ---------------------------------------------------------------------------

def test_s18_retirement_needs_a_ground(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nstatus: retired")
    issues = [i for i in check(store_repo) if i.code == "store.retire_ground"]
    assert issues and "four grounds" in issues[0].message
    assert "forge retire" in issues[0].fix


def test_s18_a_ground_without_evidence_is_an_assertion(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nstatus: retired\nretired-ground: 2")
    issues = [i for i in check(store_repo) if i.code == "store.retire_ground"]
    assert any("not a ground" in i.message for i in issues)


def test_s18_a_ground_outside_one_to_four_is_an_error(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nstatus: retired\nretired-ground: 9\nretired-evidence: because")
    issues = [i for i in check(store_repo) if i.code == "store.retire_ground"]
    assert issues and "not one of 1-4" in issues[0].message


def test_s18_a_properly_retired_claim_passes_and_leaves_the_other_checks(store_repo):
    """Retired claims stay in the file, excluded from checks and budgets, so
    the history of what we used to believe is not lost."""
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nstatus: retired\nretired-ground: 2\n"
         "retired-evidence: the linter now fails a retry inside a handler")
    assert codes(check(store_repo)) == []


def test_a_retirement_ground_on_a_live_claim_is_an_error(store_repo):
    edit(store_repo, "docs/system/pitfalls.md", "kind: pitfall\nstatus: asserted",
         "kind: pitfall\nstatus: asserted\nretired-ground: 2\nretired-evidence: x")
    issues = [i for i in check(store_repo) if i.code == "store.retire_ground"]
    assert issues and "not retired" in issues[0].message


# ---------------------------------------------------------------------------
# The command surface
# ---------------------------------------------------------------------------

def test_check_scope_limits_what_runs(store_repo, capsys):
    edit(store_repo, "docs/system/pitfalls.md", "reviewed: 2026-09-01", "reviewed: never")
    assert main(["check", "--repo", str(store_repo.root), "--scope", "store"]) == 1
    assert "store.required_fields" in capsys.readouterr().out
    assert main(["check", "--repo", str(store_repo.root), "--scope", "trace"]) == 0


def test_check_json_carries_the_documented_issue_shape(store_repo, capsys):
    edit(store_repo, "docs/system/domain.md", "anchors: [src/pay.py#refundable]",
         "anchors: [src/gone.py#refundable]")
    assert main(["check", "--repo", str(store_repo.root), "--scope", "store", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["summary"]["errors"] >= 1
    issue = next(i for i in payload["issues"] if i["code"] == "store.anchor_missing")
    assert set(issue) >= {"level", "code", "path", "line", "claim", "message", "fix"}
    assert issue["claim"] == "INV-refund-cap"


def test_every_store_code_is_reachable():
    """A code in the table with no check behind it is a promise the tool does
    not keep."""
    source = Path(validate.__file__).read_text(encoding="utf-8")
    for code in validate.STORE_CODES:
        assert f'"{code}"' in source, f"{code} is documented but never emitted"
