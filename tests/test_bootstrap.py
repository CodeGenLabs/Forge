"""The three bootstrap passes, and the rules that keep a guess admissible."""

from __future__ import annotations

import json
from datetime import date

import pytest

from forge import bootstrap, derive, store
from forge.cli import main
from forge.validate import Issue

TODAY = date(2026, 9, 11)

SOURCE = '''\
def capture(amount_minor):
    """Reserve funds."""
    return {"captured": amount_minor}


def refundable(captured, settled):
    return captured - settled
'''

TESTS = '''\
def test_refund_is_bounded():
    assert True
'''

# `CMP-pay`'s prose used to be a single line and passed `store.prose_present`
# only by absorbing the `## Uncertain` section below it - the parser ran a
# claim to the next `### <ID>` and stopped nowhere else. Now that a claim ends
# at the next section too, the check sees what is really there, so the fixture
# says what a component claim is supposed to say.
CANDIDATES = """\
# Candidates

### PIT-float-money - Money is never a float here

```claim
kind: pitfall
status: proposed
truth-source: decision
anchors: ["src/pay.py#capture"]
confidence: high
reviewed: 2026-09-01
```

Every amount is an integer count of minor units, and a rounding difference
accumulated across a settlement batch once had to be reconciled by hand.

### CON-capture - Taking money that was previously authorised

```claim
kind: concept
status: proposed
truth-source: decision
anchors: ["src/pay.py#capture"]
confidence: medium
reviewed: 2026-09-01
```

An authorisation reserves; a capture takes. Treating them as one word
produces code that refunds against money that never moved.

### CMP-pay - The payments module

```claim
kind: component
status: proposed
truth-source: code
anchors: ["src/pay.py"]
confidence: low
reviewed: 2026-09-01
```

Contains capture and refundable. Owns every decision about how much money may
move and when, and rejects an overdraw at its boundary rather than clamping -
a clamp silently under-refunds a customer.

## Uncertain

- Is the minor-unit rule enforced anywhere, or only a convention that has
  held so far?
- Why is there no currency on a capture?
"""


@pytest.fixture
def project(repo):
    repo.write("src/pay.py", SOURCE)
    repo.write("tests/test_pay.py", TESTS)
    repo.write("pyproject.toml",
               '[project]\nname = "demo"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/candidates/scan.md", CANDIDATES)
    repo.commit("a project with candidates")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    return repo


def candidate_issues(repo) -> list[Issue]:
    return bootstrap.check_candidates(repo.root, Issue)


def codes(found: list[Issue]) -> list[str]:
    return [i.code for i in found]


def set_verdict(repo, identifier: str, verdict: str) -> None:
    target = repo.root / bootstrap.REVIEW_FILE
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace(f"- [reject] {identifier} ",
                                   f"- [{verdict}] {identifier} "), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pass 1 - derive
# ---------------------------------------------------------------------------

def test_derive_reports_facts_and_nothing_else(project):
    summary = bootstrap.summarise(project.root)
    assert summary.entry_points == []
    assert summary.tests_declared == 1
    # `src/pay.py` is a file. A src layout's module is the package inside it,
    # and with only two path parts there is no package.
    #
    # `docs` used to be here and is not a module: it holds markdown. A monorepo
    # reported `docs`, `docker` and `specs` beside `apps` and `packages`, which
    # is the repository's furniture listed as its architecture.
    assert summary.modules == ["src", "tests"]


def test_derive_names_what_it_could_not_learn(project, capsys):
    """The most useful thing a bootstrap can say. Architecture is about 40%
    inferable, invariants 25%, rationale 5%, pitfalls 0% - and a scan that
    emits confident claims about those four is the noise the harness exists
    to prevent."""
    assert main(["bootstrap", "derive", "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "Not derivable, and deliberately not guessed" in out
    assert "rationale is not in the code" in out
    assert "Nothing above is a claim" in out


def test_derive_is_re_runnable(project):
    first = bootstrap.summarise(project.root).to_dict()
    assert bootstrap.summarise(project.root).to_dict() == first


def test_dot_directories_are_not_modules(project):
    """Listing `.forge` as a module puts the harness's own directory in a
    summary of the system it describes."""
    assert not any(m.startswith(".") for m in bootstrap.summarise(project.root).modules)


def test_build_metadata_is_not_a_module(repo):
    repo.write("src/demo/__init__.py", "")
    repo.write("src/demo.egg-info/PKG-INFO", "Name: demo\n")
    repo.commit("committed build metadata")
    assert bootstrap.summarise(repo.root).modules == ["src/demo"]


# ---------------------------------------------------------------------------
# Command detection
# ---------------------------------------------------------------------------

def test_commands_come_from_manifests(project):
    assert bootstrap.detect_commands(project.root) == {"test": "pytest"}


def test_nothing_is_guessed_from_a_file_merely_existing(repo):
    """`npm test` because a package.json exists is how a verification report
    goes green for a suite that never ran."""
    repo.write("package.json", '{"name": "demo"}\n')
    repo.commit("a manifest with no scripts")
    assert bootstrap.detect_commands(repo.root) == {}


def test_a_node_project_uses_its_own_runner(repo):
    repo.write("package.json",
               '{"scripts": {"build": "tsc", "test": "vitest"}}\n')
    repo.write("pnpm-lock.yaml", "lockfileVersion: 9\n")
    repo.commit("a pnpm project")
    assert bootstrap.detect_commands(repo.root) == {
        "build": "pnpm build", "test": "pnpm test",
    }


def test_a_go_project(repo):
    repo.write("go.mod", "module example.com/x\n\ngo 1.22\n")
    repo.commit("a go module")
    assert bootstrap.detect_commands(repo.root)["test"] == "go test ./..."


# ---------------------------------------------------------------------------
# Candidate admissibility
# ---------------------------------------------------------------------------

def test_a_well_formed_candidate_set_passes(project):
    assert candidate_issues(project) == []


def test_an_unanchored_candidate_is_rejected_even_for_a_concept(project):
    """A ratified concept may be unanchored once a human agrees it is real.
    A guessed one with nothing to point at can never be confirmed."""
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace('anchors: ["src/pay.py#capture"]\nconfidence: medium',
                                     'anchors: []\nconfidence: medium'))
    project.commit("an unanchored guess")
    assert "candidate.no_anchor" in codes(candidate_issues(project))


def test_a_candidate_without_confidence_is_rejected(project):
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace("confidence: high\n", "", 1))
    project.commit("no confidence")
    assert "candidate.no_confidence" in codes(candidate_issues(project))


def test_an_invented_rationale_is_rejected(project):
    """A guessed reason reads exactly like a remembered one six months
    later, and it silences the question permanently."""
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace(
                      "Every amount is an integer count of minor units,",
                      "Amounts are integers because the gateway rejects decimals,"))
    project.commit("a guessed reason")
    found = [i for i in candidate_issues(project)
             if i.code == "candidate.invented_rationale"]
    assert found and "evidence-from" in found[0].fix


def test_a_rationale_with_evidence_is_accepted(project):
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace(
                      "Every amount is an integer count of minor units,",
                      "Amounts are integers because the gateway rejects decimals,\n"
                      "evidence-from: the validator in capture() and its test,"))
    project.commit("an evidenced reason")
    assert "candidate.invented_rationale" not in codes(candidate_issues(project))


def test_rationale_unknown_is_accepted(project):
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace(
                      "Every amount is an integer count of minor units,",
                      "Amounts are integers because of something upstream.\n"
                      "rationale: unknown\n"))
    project.commit("an admitted gap")
    assert "candidate.invented_rationale" not in codes(candidate_issues(project))


def test_an_invariant_with_no_evidence_is_rejected(project):
    """Whether a property is *required* or merely currently true is not in
    the code."""
    project.write("docs/system/candidates/scan.md", CANDIDATES + """
### INV-positive - Totals are always positive

```claim
kind: invariant
status: proposed
truth-source: code
anchors: ["src/pay.py#capture"]
confidence: low
reviewed: 2026-09-01
```

Nothing has produced a negative one so far.
""")
    project.commit("an observation dressed as an invariant")
    found = [i for i in candidate_issues(project)
             if i.code == "candidate.unproven_invariant"]
    assert found and "downgrade it to a question" in found[0].fix


def test_ratified_claims_are_not_subject_to_candidate_rules(project):
    """These decide whether a *guess* is admissible. The ratified store has
    its own eighteen checks."""
    target = project.root / "docs/system/domain.md"
    target.write_text(target.read_text(encoding="utf-8")
                      + "\n### CON-x - A thing\n\n```claim\nkind: concept\n"
                        "status: asserted\ntruth-source: decision\nanchors: []\n"
                        "reviewed: 2026-09-01\n```\n\nBody one.\nBody two.\n",
                      encoding="utf-8")
    project.commit("an unanchored ratified concept")
    assert candidate_issues(project) == []


# ---------------------------------------------------------------------------
# Pass 3 - the review sheet
# ---------------------------------------------------------------------------

def test_the_sheet_orders_pitfalls_and_concepts_first(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    sheet = (project.root / bootstrap.REVIEW_FILE).read_text(encoding="utf-8")
    order = [v.id for v in bootstrap.read_review(sheet)]
    assert order == ["PIT-float-money", "CON-capture", "CMP-pay"]


def test_every_verdict_starts_at_reject(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    sheet = (project.root / bootstrap.REVIEW_FILE).read_text(encoding="utf-8")
    assert {v.verdict for v in bootstrap.read_review(sheet)} == {"reject"}
    assert "that is the posture, not a" in sheet


def test_recorded_verdicts_survive_a_regeneration(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    main(["bootstrap", "review", "--repo", str(project.root)])
    sheet = (project.root / bootstrap.REVIEW_FILE).read_text(encoding="utf-8")
    verdicts = {v.id: v.verdict for v in bootstrap.read_review(sheet)}
    assert verdicts["PIT-float-money"] == "ratify"


def test_the_uncertain_questions_are_collected(project):
    """The most valuable part of a generation pass, and the part most easily
    lost."""
    main(["bootstrap", "review", "--repo", str(project.root)])
    sheet = (project.root / bootstrap.REVIEW_FILE).read_text(encoding="utf-8")
    assert "Questions the scan could not answer" in sheet
    assert "Why is there no currency on a capture?" in sheet


def test_a_wrapped_question_is_not_truncated(project):
    """A question cut in half reads as a shorter, different question."""
    main(["bootstrap", "review", "--repo", str(project.root)])
    sheet = (project.root / bootstrap.REVIEW_FILE).read_text(encoding="utf-8")
    assert "only a convention that has held so far?" in sheet


def test_batches_are_at_most_eight(repo):
    repo.write("README.md", "# x\n")
    repo.write("src/pay.py", SOURCE)
    main(["init", "--repo", str(repo.root)])
    blocks = "".join(
        f"\n### PIT-n{i} - Trap {i}\n\n```claim\nkind: pitfall\n"
        f"status: proposed\ntruth-source: decision\nanchors: [\"src/pay.py\"]\n"
        f"confidence: low\nreviewed: 2026-09-01\n```\n\nSomething that went "
        f"wrong once.\nAnd cost time.\n"
        for i in range(20))
    repo.write("docs/system/candidates/scan.md", "# Candidates\n" + blocks)
    repo.commit("twenty candidates")
    sheet = bootstrap.build_review(repo.root)
    assert sheet.count("## Batch ") == 3


# ---------------------------------------------------------------------------
# Seal
# ---------------------------------------------------------------------------

def test_seal_writes_ratified_claims_with_anchors_stamped_at_head(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    head = project.head
    bootstrap.seal(project.root, today=TODAY)
    text = (project.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    assert f"src/pay.py#capture@{head[:10]}" in text
    assert "reviewed: 2026-09-11" in text
    assert "status:   asserted" in text
    assert "confidence" not in text


def test_a_ratified_candidate_leaves_the_candidates_tier(project):
    """A claim in both places is two claims with one ID, and the store check
    would say so."""
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    bootstrap.seal(project.root, today=TODAY)
    remaining = [c.id for c in store.load_store(project.root) if c.is_candidate]
    assert "PIT-float-money" not in remaining
    assert "CON-capture" in remaining


def test_unratified_candidates_stay_readable(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    bootstrap.seal(project.root, today=TODAY)
    assert (project.root / "docs/system/candidates/scan.md").is_file()


def test_the_default_is_reject_even_with_no_sheet(project):
    """Not answering is not ratifying."""
    plan = bootstrap.seal(project.root, today=TODAY, dry_run=True)
    assert plan.ratified == []
    assert len(plan.rejected) == 3


def test_edit_counts_as_ratify(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "CON-capture", "edit")
    plan = bootstrap.seal(project.root, today=TODAY, dry_run=True)
    assert [c.id for c in plan.ratified] == ["CON-capture"]


def test_defer_is_neither(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "CON-capture", "defer")
    plan = bootstrap.seal(project.root, today=TODAY, dry_run=True)
    assert [c.id for c in plan.deferred] == ["CON-capture"]
    assert plan.ratified == []


def test_an_unreadable_verdict_is_treated_as_reject(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "CON-capture", "yes please")
    plan = bootstrap.seal(project.root, today=TODAY, dry_run=True)
    assert plan.ratified == []
    assert [v.id for v in plan.unknown_verdicts] == ["CON-capture"]


def test_the_cap_holds(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    for identifier in ("PIT-float-money", "CON-capture", "CMP-pay"):
        set_verdict(project, identifier, "ratify")
    plan = bootstrap.seal(project.root, today=TODAY, cap=2, dry_run=True)
    assert len(plan.ratified) == 2
    assert [c.id for c in plan.over_cap] == ["CMP-pay"]


def test_the_adr_records_what_was_not_ratified(project):
    """A store with no record of its own gaps is ambiguous between "nothing
    to say here" and "nobody looked"."""
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    bootstrap.seal(project.root, today=TODAY)
    adr = (project.root / "docs/system/decisions/ADR-0001-adopt-forge.md").read_text(
        encoding="utf-8")
    assert "### Ratified" in adr and "PIT-float-money" in adr
    assert "### Proposed and not ratified" in adr and "CMP-pay" in adr
    assert "### Deliberately not attempted" in adr
    assert "Cap in force: 40" in adr
    # The adoption decision it extends is still there.
    assert "Adopt an anchored claim store" in adr


def test_sealing_twice_does_not_duplicate_the_baseline(project):
    main(["bootstrap", "review", "--repo", str(project.root)])
    bootstrap.seal(project.root, today=TODAY)
    bootstrap.seal(project.root, today=TODAY)
    adr = (project.root / "docs/system/decisions/ADR-0001-adopt-forge.md").read_text(
        encoding="utf-8")
    assert adr.count("## Baseline recorded") == 1


def test_seal_writes_the_detected_commands(project):
    bootstrap.seal(project.root, today=TODAY)
    config = (project.root / ".forge/config.yaml").read_text(encoding="utf-8")
    assert "test: pytest" in config


def test_seal_never_overwrites_chosen_commands(project):
    """A scan's guess losing to a human's choice is the correct direction."""
    target = project.root / ".forge/config.yaml"
    target.write_text("version: 1\n\ncommands:\n  test: make check\n", encoding="utf-8")
    bootstrap.seal(project.root, today=TODAY)
    assert "make check" in target.read_text(encoding="utf-8")
    assert "pytest" not in target.read_text(encoding="utf-8")


def test_seal_leaves_an_existing_overview_alone(project):
    target = project.root / "docs/system/OVERVIEW.md"
    target.write_text("# Mine\n\nHand-written.\n", encoding="utf-8")
    bootstrap.seal(project.root, today=TODAY)
    assert target.read_text(encoding="utf-8") == "# Mine\n\nHand-written.\n"


def test_the_generated_overview_admits_what_it_cannot_know(repo):
    repo.write("src/pay.py", SOURCE)
    main(["init", "--repo", str(repo.root)])
    (repo.root / "docs/system/OVERVIEW.md").unlink()
    repo.commit("no overview")
    bootstrap.seal(repo.root, today=TODAY)
    text = (repo.root / "docs/system/OVERVIEW.md").read_text(encoding="utf-8")
    assert "Unwritten" in text
    assert "not something a scan can" in text


# ---------------------------------------------------------------------------
# The sealed store holds up
# ---------------------------------------------------------------------------

def test_a_sealed_baseline_passes_forge_check(project, capsys):
    """The acceptance case: bootstrap produces a store the checks accept.

    The orphan check is the one this would have failed. Every claim in a
    fresh baseline has nothing pointing at it - true, useless, and arriving
    at the moment someone decides whether the tool is worth its noise. An
    inbound ADR reference counts, and the baseline ADR cites them all."""
    main(["bootstrap", "review", "--repo", str(project.root)])
    for identifier in ("PIT-float-money", "CON-capture"):
        set_verdict(project, identifier, "ratify")
    main(["bootstrap", "seal", "--repo", str(project.root)])
    project.commit("seal the baseline")
    derive.derive_all(project.root)
    project.commit("chore: sync derived tier")
    capsys.readouterr()
    assert main(["check", "--repo", str(project.root)]) == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    assert "store.orphan" not in out


def test_an_adr_citation_rescues_a_claim_from_the_orphan_check(project):
    from forge import validate

    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    main(["bootstrap", "seal", "--repo", str(project.root)])
    project.commit("seal")
    derive.derive_all(project.root)
    project.commit("chore: sync derived tier")
    orphans = [i for i in validate.check_store(project.root, today=TODAY)
               if i.code == "store.orphan"]
    assert orphans == []


def test_a_document_section_reference_is_not_a_pinned_version(project):
    """`section 2.3` read as a dependency, and the claims most likely to cite
    a section are the pitfalls."""
    from forge import validate

    target = project.root / "docs/system/pitfalls.md"
    target.write_text(target.read_text(encoding="utf-8")
                      + "\n### PIT-x - A trap\n\n```claim\nkind: pitfall\n"
                        "status: asserted\ntruth-source: decision\n"
                        'anchors: ["src/pay.py"]\nreviewed: 2026-09-01\n```\n\n'
                        "The reason is recorded in SYSTEM_KNOWLEDGE.md section 2.3.\n"
                        "It must never be undone without reading that first.\n",
                      encoding="utf-8")
    project.commit("a claim citing a section")
    found = [i for i in validate.check_store(project.root, today=TODAY)
             if i.code == "store.stack_fact_smell"]
    assert found == []


# ---------------------------------------------------------------------------
# The command surface
# ---------------------------------------------------------------------------

def test_seal_refuses_a_ratified_candidate_that_fails_its_rules(project, capsys):
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace("confidence: high\n", "", 1))
    project.commit("no confidence")
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    capsys.readouterr()
    assert main(["bootstrap", "seal", "--repo", str(project.root)]) == 1
    assert "nothing sealed" in capsys.readouterr().err


def test_seal_ignores_rule_failures_on_candidates_nobody_ratified(project, capsys):
    """A guess left as a guess does not have to be admissible."""
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace("confidence: high\n", "", 1))
    project.commit("no confidence")
    main(["bootstrap", "review", "--repo", str(project.root)])
    capsys.readouterr()
    assert main(["bootstrap", "seal", "--repo", str(project.root)]) == 0


def test_seal_dry_run_writes_nothing(project, capsys):
    main(["bootstrap", "review", "--repo", str(project.root)])
    set_verdict(project, "PIT-float-money", "ratify")
    before = (project.root / "docs/system/pitfalls.md").read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(["bootstrap", "seal", "--dry-run", "--repo", str(project.root)]) == 0
    assert "would write" in capsys.readouterr().out
    assert (project.root / "docs/system/pitfalls.md").read_text(
        encoding="utf-8") == before


def test_derive_json(project, capsys):
    assert main(["bootstrap", "derive", "--repo", str(project.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["commands"] == {"test": "pytest"}
    assert len(payload["not_derivable"]) == 4


def test_check_scope_candidates(project, capsys):
    project.write("docs/system/candidates/scan.md",
                  CANDIDATES.replace('anchors: ["src/pay.py#capture"]', "anchors: []", 1))
    project.commit("an unanchored guess")
    assert main(["check", "--scope", "candidates", "--repo", str(project.root)]) == 1
    assert "candidate.no_anchor" in capsys.readouterr().out


def test_the_measurement_is_recorded():
    """M5's acceptance criterion is a recorded outcome, not a passing test."""
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent
            / "docs/measurements/M5-bootstrap.md").read_text(encoding="utf-8")
    assert "requests" in text
    # The fourth number is not measured, and the document has to say so
    # rather than estimate it.
    assert "unmeasured rather than estimated" in text


# ---------------------------------------------------------------------------
# What counts as a module
# ---------------------------------------------------------------------------

def test_a_prose_directory_is_not_a_module():
    """A monorepo reported `docs`, `docker`, `specs`, `scripts` and `tools`
    beside `apps` and `packages` - the repository's furniture listed as its
    architecture."""
    roots = bootstrap._module_roots([
        "src/app/main.py", "docs/guide.md", "specs/api.md",
        "config/settings.yaml", "LICENSE",
    ])
    assert roots == ["src/app"]


def test_a_container_directory_expands_one_level():
    """`packages/` holds no code of its own; its modules are one level down.
    This was hardcoded for `src`, `lib`, `pkg` and `internal`, and is now
    structural - the same answer for those four, the right one for a monorepo."""
    roots = bootstrap._module_roots([
        "packages/client/src/a.ts", "packages/contract/src/b.ts",
        "apps/web/main.tsx",
    ])
    assert roots == ["apps/web", "packages/client", "packages/contract"]


def test_a_directory_with_code_of_its_own_stays_whole():
    """`tools/` with both `tools/run.ts` and `tools/__tests__/x.ts` is one
    module, not two: it has code at its own level."""
    roots = bootstrap._module_roots(["tools/run.ts", "tools/__tests__/x.test.ts"])
    assert roots == ["tools"]


def test_a_src_layout_still_names_the_package():
    """The case the hardcoded list existed for, unchanged."""
    assert bootstrap._module_roots(
        ["src/forge/cli.py", "src/forge/derive.py", "tests/test_cli.py"]
    ) == ["src/forge", "tests"]


def test_a_flat_file_is_not_a_module():
    """`src/pay.py` is a file. With only two parts the second is not a package."""
    assert bootstrap._module_roots(["setup.py", "README.md"]) == []


def test_a_dot_directory_is_never_a_module():
    """`.forge` and `.github` are configuration, and listing them would put the
    harness's own directory in a summary of the system it describes."""
    assert bootstrap._module_roots(
        [".forge/skills/forge/SKILL.md", ".github/workflows/ci.yml",
         "src/app/main.py"]
    ) == ["src/app"]
