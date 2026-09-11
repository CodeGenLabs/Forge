"""The claim-touch rule, and the blast radius it is computed from.

This is the harness's central enforcement: if these tests are wrong, "which
documentation must change?" goes back to being a judgement call.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from forge import change, derive, impact
from forge.cli import main
from forge.validate import Issue

TODAY = date(2026, 9, 11)

PAY = '''\
# forge:CMP-payments
def capture(amount_minor):
    return {"captured": amount_minor}


def refundable(captured_minor, settled_minor):  # forge:INV-refund-cap
    return captured_minor - settled_minor
'''

API = '''\
from .pay import refundable


def handle(request):
    return refundable(request["captured"], request["settled"])
'''

TESTS = '''\
# @covers INV-refund-cap
def test_refund_never_exceeds_capture():
    assert True
'''

INVARIANT = """\

### INV-refund-cap - A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors: ["src/pay.py#refundable"]
evidence:
  - test: "tests/test_pay.py::test_refund_never_exceeds_capture"
reviewed: 2026-09-01
```

Partial refunds accumulate: what is bounded is the sum of settled refunds, not
each refund on its own. An attempt over the balance must be rejected.
"""

COMPONENT = """\

### CMP-payments - Capture, refund and their money arithmetic

```claim
kind: component
status: asserted
truth-source: decision
anchors: ["src/pay.py"]
governs: [INV-refund-cap]
reviewed: 2026-09-01
```

Owns every decision about how much money may move and when. It must reject an
overdraw at its boundary rather than clamping, because a clamp silently
under-refunds a customer.
"""

ACCOUNT = """\
# Impact

## Blast radius
- src/pay.py

## Claims touched

### Unaffected
- CMP-payments - the new behaviour lands inside the existing boundary

### Updated
- INV-refund-cap - the bound now clamps instead of rejecting
"""


@pytest.fixture
def worked(repo):
    """The refund fixture from SYSTEM_KNOWLEDGE.md section 11, in miniature."""
    repo.write("src/pay.py", PAY)
    repo.write("src/api.py", API)
    repo.write("tests/test_pay.py", TESTS)
    main(["init", "--repo", str(repo.root)])
    append(repo, "docs/system/domain.md", INVARIANT)
    append(repo, "docs/system/components.md", COMPONENT)
    repo.commit("a project with two claims")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    change.new_change(repo.root, "clamp refunds", today=TODAY)
    repo.commit("open a change")
    return repo


def append(repo, path: str, text: str) -> None:
    target = repo.root / path
    target.write_text(target.read_text(encoding="utf-8") + text, encoding="utf-8")


def computed(repo) -> impact.Impact:
    item = change.find_change(repo.root, "1")
    return impact.compute_impact(repo.root, item)


def issues(repo) -> list[Issue]:
    item = change.find_change(repo.root, "1")
    return impact.check_claim_touch(repo.root, item, impact.compute_impact(repo.root, item),
                                    Issue)


def codes(found: list[Issue]) -> list[str]:
    return [i.code for i in found]


# ---------------------------------------------------------------------------
# The blast radius
# ---------------------------------------------------------------------------

def test_an_untouched_change_reaches_nothing(worked):
    result = computed(worked)
    assert result.changed_files == []
    assert result.touched == {}


def test_the_working_tree_counts_before_anything_is_committed(worked):
    """`forge impact` runs *while* the change is being written. A diff that
    only saw commits would report the blast radius of the last commit rather
    than of the work in hand."""
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    assert computed(worked).changed_files == ["src/pay.py"]


def test_untracked_files_count(worked):
    worked.write("src/ledger.py", "def settle():\n    return None\n")
    assert "src/ledger.py" in computed(worked).changed_files


def test_reverse_dependencies_widen_the_radius(worked):
    """`src/api.py` imports `src/pay.py`, so editing pay reaches api."""
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    result = computed(worked)
    assert result.changed_files == ["src/pay.py"]
    assert result.reverse_deps == ["src/api.py"]
    assert result.blast_radius == ["src/api.py", "src/pay.py"]


def test_the_changes_own_artifacts_are_not_blast_radius(worked):
    """Otherwise every change touches every claim defined in a file it happens
    to store under `changes/`, and `impact.md` names itself."""
    item = change.find_change(worked.root, "1")
    (item.root / "impact.md").write_text(ACCOUNT, encoding="utf-8")
    assert computed(worked).changed_files == []


# ---------------------------------------------------------------------------
# The touch set
# ---------------------------------------------------------------------------

def test_an_anchor_in_the_diff_touches_its_claim(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    result = computed(worked)
    assert sorted(result.touched) == ["CMP-payments", "INV-refund-cap"]
    # The reason names the symbol, not just the file: the anchor is
    # `src/pay.py#refundable` and the diff edited that function's body.
    assert "anchor src/pay.py#refundable" in result.touched["INV-refund-cap"].reasons


def test_a_component_anchor_is_read_as_a_glob(worked):
    worked.write("docs/system/components.md",
                 (worked.root / "docs/system/components.md").read_text(encoding="utf-8")
                 .replace('anchors: ["src/pay.py"]', 'anchors: ["src/*.py"]'))
    worked.commit("widen the component boundary")
    worked.write("src/api.py", API + "\n\ndef other():\n    return 1\n")
    result = computed(worked)
    assert "CMP-payments" in result.touched
    assert "component boundary" in result.touched["CMP-payments"].reasons[0]


def test_only_component_anchors_are_globbed(worked):
    """A careless `src/*` on an invariant would pull the whole tree into every
    change's touch set, and a rule that always fires gets dismissed."""
    worked.write("src/api.py", API + "\n\ndef other():\n    return 1\n")
    result = computed(worked)
    assert "INV-refund-cap" not in result.touched


def test_an_evidence_artifact_in_the_diff_touches_its_claim(worked):
    worked.write("tests/test_pay.py", TESTS + "\n\ndef test_more():\n    assert True\n")
    result = computed(worked)
    assert "INV-refund-cap" in result.touched
    assert any("evidence test" in r for r in result.touched["INV-refund-cap"].reasons)


def test_editing_a_claim_file_touches_the_claims_in_it(worked):
    worked.write("docs/system/domain.md",
                 (worked.root / "docs/system/domain.md").read_text(encoding="utf-8")
                 .replace("must be rejected", "is clamped to the balance"))
    result = computed(worked)
    assert any("its own definition" in r
               for r in result.touched["INV-refund-cap"].reasons)


def test_candidates_and_retired_claims_are_not_taxed(worked):
    """A candidate is not yet knowledge and a retired claim is history. Taxing
    a change for either makes both expensive to keep, which is the opposite of
    what the tiers are for."""
    worked.write("docs/system/candidates/guesses.md",
                 '### CON-authorisation - Reserving funds\n\n```claim\nkind: concept\n'
                 'status: proposed\ntruth-source: decision\nanchors: ["src/pay.py"]\n'
                 'confidence: low\nreviewed: 2026-09-01\n```\n\nBody one.\nBody two.\n')
    worked.commit("a candidate")
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    assert "CON-authorisation" not in computed(worked).touched


# ---------------------------------------------------------------------------
# Accounting - R5
# ---------------------------------------------------------------------------

def test_no_impact_file_with_a_non_empty_touch_set_blocks(worked):
    # Edits `refundable` itself, so the invariant anchored to that symbol is
    # touched alongside the component whose glob covers the file.
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    found = issues(worked)
    assert codes(found) == ["trace.claim_touch_complete"]
    assert "CMP-payments, INV-refund-cap" in found[0].message


def test_appending_an_unrelated_function_does_not_touch_the_symbol_claim(worked):
    """`INV-refund-cap` anchors `src/pay.py#refundable`. Adding a new function
    beside it edits the file and not the thing the claim describes, so the
    component is touched and the invariant is only nearby."""
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    result = computed(worked)
    assert set(result.touched) == {"CMP-payments"}
    assert set(result.nearby) == {"INV-refund-cap"}


def test_no_impact_file_with_an_empty_touch_set_is_fine(worked):
    assert issues(worked) == []


def test_a_complete_account_passes(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        ACCOUNT, encoding="utf-8")
    assert issues(worked) == []


def test_an_unaccounted_member_blocks_and_names_why_it_is_in_the_set(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        ACCOUNT.replace("- CMP-payments - the new behaviour lands inside the "
                        "existing boundary\n", ""), encoding="utf-8")
    found = [i for i in issues(worked) if i.claim == "CMP-payments"]
    assert found and "component boundary" in found[0].message


def test_an_entry_with_no_reason_is_not_an_account(worked):
    """`Unaffected` is cheap but not free: one honest sentence per claim. An
    entry with an ID and nothing after it turns the heading into a place to
    dump the whole set."""
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        ACCOUNT.replace("- CMP-payments - the new behaviour lands inside the "
                        "existing boundary", "- CMP-payments"), encoding="utf-8")
    found = [i for i in issues(worked) if "no reason" in i.message]
    assert found and found[0].claim == "CMP-payments"


def test_the_reason_never_swallows_the_next_line(worked):
    """`\\s*` between the ID and its reason crosses the newline and reads the
    following heading as the reason, which turns 'you gave no reason' into a
    silent pass."""
    account = impact.parse_account(
        "## Claims touched\n\n### Unaffected\n- CMP-payments\n\n### Updated\n"
        "- INV-refund-cap - clamps now\n")
    assert account.reasons["CMP-payments"] == ""
    assert account.by_id["INV-refund-cap"] == ["Updated"]


def test_a_claim_under_two_headings_blocks(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        ACCOUNT + "\n### At risk\n- CMP-payments - also this\n", encoding="utf-8")
    found = [i for i in issues(worked) if "exactly one must be true" in i.message]
    assert found


def test_editing_a_claim_and_filing_it_unaffected_blocks(worked):
    """The exact move the rule exists to stop."""
    worked.write("docs/system/domain.md",
                 (worked.root / "docs/system/domain.md").read_text(encoding="utf-8")
                 .replace("must be rejected", "is clamped to the balance"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "## Claims touched\n\n### Unaffected\n- INV-refund-cap - nothing really\n",
        encoding="utf-8")
    found = [i for i in issues(worked) if "own definition was edited" in i.message]
    assert found and found[0].claim == "INV-refund-cap"


def test_a_missing_section_blocks(worked):
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "# Impact\n\nSome prose and no account.\n", encoding="utf-8")
    found = issues(worked)
    assert "no `## Claims touched` section" in found[0].message


def test_an_invented_heading_blocks(worked):
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "## Claims touched\n\n### Probably fine\n- CMP-payments - eh\n"
        "- INV-refund-cap - eh\n", encoding="utf-8")
    found = [i for i in issues(worked) if "not one of the accounted headings" in i.message]
    assert found


def test_over_accounting_is_a_warning_not_an_error(worked):
    """Being too careful must not block, but it is a signal that the anchors
    may be pointing at the wrong files."""
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        ACCOUNT + "\n### At risk\n- PIT-nothing - just in case\n", encoding="utf-8")
    found = [i for i in issues(worked) if i.code == "trace.claim_touch_extra"]
    assert found and found[0].level == "WARNING"


# ---------------------------------------------------------------------------
# Superseding - R6
# ---------------------------------------------------------------------------

def test_superseded_without_an_adr_blocks(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "## Claims touched\n\n### Unaffected\n- CMP-payments - unchanged boundary\n\n"
        "### Superseded\n- INV-refund-cap - replaced by a clamping rule\n",
        encoding="utf-8")
    found = [i for i in issues(worked) if i.code == "trace.superseded_has_adr"]
    assert found and "without naming an ADR" in found[0].message


def test_superseded_naming_a_missing_adr_blocks(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "## Claims touched\n\n### Unaffected\n- CMP-payments - unchanged boundary\n\n"
        "### Superseded\n- INV-refund-cap -> ADR-0042 - replaced by a clamping rule\n",
        encoding="utf-8")
    found = [i for i in issues(worked) if i.code == "trace.superseded_has_adr"]
    assert found and "ADR-0042" in found[0].message


def test_superseded_naming_an_existing_adr_passes(worked):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    worked.write("docs/system/decisions/ADR-0002-clamp-refunds.md",
                 "# ADR-0002 - Clamp refunds\n\n## Status\nAccepted\n")
    (worked.root / "changes/0001-clamp-refunds/impact.md").write_text(
        "## Claims touched\n\n### Unaffected\n- CMP-payments - unchanged boundary\n\n"
        "### Superseded\n- INV-refund-cap -> ADR-0002 - replaced by a clamping rule\n",
        encoding="utf-8")
    assert [i for i in issues(worked) if i.level == "ERROR"] == []


# ---------------------------------------------------------------------------
# The command surface
# ---------------------------------------------------------------------------

def test_impact_command_prints_the_set_and_why(worked, capsys):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    assert main(["impact", "--change", "1", "--repo", str(worked.root)]) == 0
    out = capsys.readouterr().out
    assert "changed   src/pay.py" in out
    assert "imports   src/api.py" in out
    assert "INV-refund-cap" in out and "anchor src/pay.py" in out


def test_impact_json_carries_the_ids_the_design_phase_reads(worked, capsys):
    worked.write("src/pay.py", PAY.replace("captured_minor - settled_minor",
                                           "max(0, captured_minor - settled_minor)"))
    assert main(["impact", "--change", "1", "--repo", str(worked.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["claims_touched"] == ["CMP-payments", "INV-refund-cap"]
    assert payload["blast_radius"] == ["src/api.py", "src/pay.py"]


def test_check_scope_change_runs_the_rule(worked, capsys):
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    assert main(["check", "--scope", "change", "--repo", str(worked.root)]) == 1
    assert "trace.claim_touch_complete" in capsys.readouterr().out


def test_check_scope_change_can_be_limited_to_one_change(worked, capsys):
    change.new_change(worked.root, "unrelated", today=TODAY)
    worked.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    capsys.readouterr()
    main(["check", "--scope", "change", "--change", "1", "--repo", str(worked.root)])
    out = capsys.readouterr().out
    assert "0001-clamp-refunds" in out
    assert "0002-unrelated" not in out


def test_an_unknown_change_is_reported_not_ignored(worked, capsys):
    assert main(["check", "--scope", "change", "--change", "99",
                 "--repo", str(worked.root)]) == 1
    assert "change.unknown" in capsys.readouterr().out
