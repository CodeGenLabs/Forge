"""The traceability index, and the M2 acceptance case.

`test_the_acceptance_case` is MVP.md's M2 criterion written as a test: on a
repository with a real claim store, `forge trace INV-7` returns its claims,
tests, changes and back-references. The rest pin the individual edges and the
one property that matters more than any of them — that a reference to an ID
nobody defined is reported rather than silently indexed.
"""

from __future__ import annotations

import pytest

from forge import derive, store, trace

CLAIM_DOMAIN = """\
# Domain

### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:
  - src/pay.py#refundable
evidence:
  - test: tests/test_pay.py::test_refund_is_bounded
governs: [CMP-payments]
since: ADR-0014
reviewed: 2026-09-10
```

Partial refunds accumulate: the sum of settled refunds is what is bounded, not
each refund individually.

### CON-capture — "Capture" is the irreversible step, not the authorisation

```claim
kind: concept
status: asserted
truth-source: decision
anchors: []
reviewed: 2026-09-10
```

An authorisation can lapse; a capture cannot be undone except by a refund.
"""

CLAIM_COMPONENTS = """\
# Components

### CMP-payments — Owns money movement and the ledger

```claim
kind: component
status: asserted
truth-source: decision
anchors:
  - src/pay.py
reviewed: 2026-09-10
```

Everything that debits or credits a customer goes through here, so that the
ledger has exactly one writer.
"""

ADR = """\
# ADR-0014: Bound refunds cumulatively

Status: accepted
supersedes: ADR-0009

Refunds are bounded by the sum of prior settled refunds, not per refund.
This is what INV-7 records, and CMP-payments is where it is enforced.
"""


@pytest.fixture
def store_repo(repo):
    repo.write("src/pay.py", "def refundable(a, b):  # forge:INV-7\n    return a - b\n")
    repo.write("tests/test_pay.py", """\
# @covers INV-7
def test_refund_is_bounded():
    assert True
""")
    repo.write("docs/system/domain.md", CLAIM_DOMAIN)
    repo.write("docs/system/components.md", CLAIM_COMPONENTS)
    repo.write("docs/system/decisions/ADR-0014-cumulative-refunds.md", ADR)
    repo.write("changes/0004-refund-support/proposal.md",
               "Touches INV-7 and CMP-payments; see ADR-0014.\n")
    repo.commit("a store with one of everything")
    derive.derive_all(repo.root)
    return repo


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def test_claims_parse_out_of_markdown(store_repo):
    claims = {c.id: c for c in store.load_store(store_repo.root)}
    assert set(claims) == {"INV-7", "CON-capture", "CMP-payments"}
    inv = claims["INV-7"]
    assert inv.kind == "invariant"
    assert inv.status == "enforced"
    assert inv.truth_source == "tests"
    assert inv.anchors == ["src/pay.py#refundable"]
    assert inv.evidence == ["test:tests/test_pay.py::test_refund_is_bounded"]
    assert inv.governs == ["CMP-payments"]
    assert inv.since == "ADR-0014"
    assert "Partial refunds accumulate" in inv.prose
    assert inv.parse_error is None


def test_a_claim_without_a_block_is_recorded_not_dropped(repo):
    """A malformed claim must still appear, or the index quietly loses it."""
    claims = store.parse_claims("### INV-1 — no block here\n\nprose only\n", "docs/system/x.md")
    assert len(claims) == 1
    assert claims[0].parse_error == "no ```claim block"


def test_invalid_yaml_is_recorded_not_raised(repo):
    text = "### INV-1 — bad\n\n```claim\nkind: [unclosed\n```\n"
    claims = store.parse_claims(text, "docs/system/x.md")
    assert claims[0].parse_error and "YAML" in claims[0].parse_error


def test_evidence_accepts_both_yaml_shapes():
    mapping = store.parse_claims(
        "### INV-1 — a\n\n```claim\nevidence:\n  - test: a::b\n```\n", "x.md")[0]
    plain = store.parse_claims(
        '### INV-1 — a\n\n```claim\nevidence:\n  - "test:a::b"\n```\n', "x.md")[0]
    assert mapping.evidence == plain.evidence == ["test:a::b"]


def test_candidates_are_flagged_not_hidden(store_repo):
    store_repo.write("docs/system/candidates/refunds.md", """\
### INV-99 — proposed, not ratified

```claim
kind: invariant
status: proposed
truth-source: tests
anchors: [src/pay.py]
confidence: low
reviewed: 2026-09-10
```

Inferred from the validation code; unconfirmed.
""")
    store_repo.commit("add a candidate")
    claims = {c.id: c for c in store.load_store(store_repo.root)}
    assert claims["INV-99"].is_candidate is True
    assert claims["INV-7"].is_candidate is False


def test_adrs_are_read_with_their_supersession(store_repo):
    decisions = store.load_decisions(store_repo.root)
    assert decisions["ADR-0014"]["supersedes"] == "ADR-0009"
    assert "INV-7" in decisions["ADR-0014"]["references"]


# --------------------------------------------------------------------------
# The index
# --------------------------------------------------------------------------

def test_the_acceptance_case(store_repo):
    """MVP.md M2: one lookup returns claims, tests, changes and back-references."""
    entry = trace.lookup(store_repo.root, "INV-7")
    assert entry is not None
    assert entry["kind"] == "invariant"
    assert entry["defined_in"] == "docs/system/domain.md:3"
    assert entry["anchors"] == ["src/pay.py#refundable"]
    assert entry["anchor_paths"] == ["src/pay.py"]
    assert entry["tests"] == ["tests/test_pay.py::test_refund_is_bounded"]
    assert entry["back_references"] == ["src/pay.py:1"]
    assert entry["changes"] == ["0004-refund-support"]
    assert entry["since"] == "ADR-0014"
    assert entry["governs"] == ["CMP-payments"]
    assert entry["referenced_by_adr"] == ["ADR-0014"]


def test_reverse_edges_are_computed(store_repo):
    """Every relationship is declared once; the index supplies the other way."""
    component = trace.lookup(store_repo.root, "CMP-payments")
    assert component["governed_by"] == ["INV-7"]

    adr = trace.lookup(store_repo.root, "ADR-0014")
    assert adr["justifies"] == ["INV-7"]
    assert adr["supersedes"] == "ADR-0009"


def test_a_referenced_but_undefined_id_is_reported(store_repo):
    """ADR-0009 is superseded but has no file. Silently indexing it would make
    the index look complete while pointing at nothing."""
    index = trace.build_trace(store_repo.root)
    assert "ADR-0009" in index["summary"]["dangling_references"]
    assert index["ids"]["ADR-0009"]["defined_in"] is None


def test_an_invariant_with_no_test_is_reported(store_repo):
    store_repo.write("docs/system/domain2.md", """\
### INV-8 — nothing proves this one

```claim
kind: invariant
status: asserted
truth-source: tests
anchors: [src/pay.py]
reviewed: 2026-09-10
```

Believed true, discharged by nothing.
""")
    store_repo.commit("an undischarged invariant")
    derive.derive_all(store_repo.root)
    index = trace.build_trace(store_repo.root)
    assert index["summary"]["invariants_without_tests"] == ["INV-8"]


def test_summary_counts_separate_claims_from_candidates(store_repo):
    index = trace.build_trace(store_repo.root)
    assert index["summary"]["claims"] == 3
    assert index["summary"]["candidates"] == 0
    assert index["summary"]["decisions"] == 1


def test_anchor_path_extraction_survives_a_malformed_anchor():
    """The index records what the claim says; validating it is M0's job, and an
    index that refuses to build on a store with a mistake in it is useless."""
    assert trace._anchor_path("src/a.ts#Sym@a1b2c3d") == "src/a.ts"
    assert trace._anchor_path("packages/@acme/core/src/a.ts#Sym") == "packages/@acme/core/src/a.ts"
    assert trace._anchor_path("  src/a.ts  ") == "src/a.ts"
    assert trace._anchor_path("../nonsense#X") == "../nonsense"


def test_index_is_part_of_the_derived_tier_and_stays_deterministic(store_repo):
    assert not any(derive.derive_all(store_repo.root).values())
    payload = derive.read_json(store_repo.root / derive.DERIVED_DIR / trace.TRACE_FILE)
    assert payload["$schema"] == derive.SCHEMA
    assert payload["generated_from_commit"] == store_repo.head


# --------------------------------------------------------------------------
# The ID grammar
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("identifier", "valid"),
    [
        ("INV-7", True),            # numeric, as SYSTEM_KNOWLEDGE.md section 7.1 first specified
        ("CMP-payments", True),     # slug, as every example in the same document used
        ("CON-capture", True),
        ("API-post-refunds", True),
        ("PIT-vendor-globs", True),
        ("INV-Bad", False),         # uppercase in the token
        ("CMP-", False),            # no token
        ("XX-1", False),            # not a known kind
        ("INV_7", False),           # wrong separator
    ],
)
def test_id_grammar_accepts_numbers_and_slugs(identifier, valid):
    """Implementing the parser forced a choice the design had left contradictory.

    Slugs win because `grep -r CMP-payments` explains itself. What is enforced
    is stability, not numerality: the token is permanent, so a component
    renamed to billing keeps `CMP-payments` and changes only its title.
    """
    import re
    assert (re.fullmatch(store.ID_PATTERN, identifier) is not None) is valid


def test_a_slug_id_indexes_like_any_other(store_repo):
    entry = trace.lookup(store_repo.root, "CMP-payments")
    assert entry["defined_in"] == "docs/system/components.md:3"
    assert entry["governed_by"] == ["INV-7"]
