"""`forge instructions`: the `reads` contract, resolved from the schema."""

from __future__ import annotations

import json
from datetime import date

import pytest

from forge import change, derive, instructions, schema
from forge.cli import main

TODAY = date(2026, 9, 11)

PAY = '''\
# forge:CMP-payments
def refundable(captured, settled):  # forge:INV-refund-cap
    return captured - settled
'''

COMPONENT = """\

### CMP-payments - Capture, refund and their money arithmetic

```claim
kind: component
status: asserted
truth-source: decision
anchors: ["src/pay.py"]
reviewed: 2026-09-01
```

Owns every decision about how much money may move and when. It must reject an
overdraw at its boundary rather than clamping.
"""

CANDIDATE = """\
### CON-authorisation - Reserving funds

```claim
kind: concept
status: proposed
truth-source: decision
anchors: []
confidence: low
reviewed: 2026-09-01
```

A guess nobody has ratified yet.
It is here to be read, never to be cited.
"""


@pytest.fixture
def project(repo):
    repo.write("src/pay.py", PAY)
    main(["init", "--repo", str(repo.root)])
    target = repo.root / "docs/system/components.md"
    target.write_text(target.read_text(encoding="utf-8") + COMPONENT, encoding="utf-8")
    repo.write("docs/system/candidates/guesses.md", CANDIDATE)
    repo.commit("a project with one claim and one candidate")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    change.new_change(repo.root, "refund support", today=TODAY)
    repo.commit("open a change")
    return repo


def item(repo) -> change.Change:
    return change.find_change(repo.root, "1")


def resolve(repo, artifact: str) -> dict:
    return instructions.resolve(repo.root, item(repo), artifact)


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

def test_a_path_selector_resolves_to_existing_files(project):
    assert resolve(project, "proposal")["reads"]["files"] == ["docs/system/OVERVIEW.md"]


def test_a_missing_file_is_simply_absent(project):
    """`reads` says what a phase is *entitled* to, not what exists. A design
    phase blocked on a spec that has not been written reports the block; it
    does not report a missing file as an error."""
    resolved = resolve(project, "design")
    assert resolved["reads"]["files"] == []
    assert resolved["blocked_by"] == ["spec", "impact"]


def test_the_change_variable_is_substituted(project):
    (item(project).root / "impact.md").write_text("# Impact\n", encoding="utf-8")
    (item(project).root / "spec/payments").mkdir(parents=True)
    (item(project).root / "spec/payments/spec.md").write_text("x\n", encoding="utf-8")
    files = resolve(project, "design")["reads"]["files"]
    assert "changes/0001-refund-support/impact.md" in files
    assert "changes/0001-refund-support/spec/payments/spec.md" in files


def test_a_derived_selector_names_the_artifact_file(project):
    derived = resolve(project, "impact")["reads"]["derived"]
    assert derived == ["docs/system/derived/deps.json",
                       "docs/system/derived/inventory.json"]


def test_an_unbuilt_derived_artifact_is_reported_unresolved(repo):
    repo.write("src/pay.py", PAY)
    main(["init", "--repo", str(repo.root)])
    repo.commit("no sync yet")
    change.new_change(repo.root, "x", today=TODAY)
    resolved = instructions.resolve(repo.root, change.find_change(repo.root, "1"),
                                    "impact")
    assert any("derived:deps" in u for u in resolved["unresolved"])
    assert any("forge sync derived" in u for u in resolved["unresolved"])


def test_claims_metadata_is_the_index_not_the_prose(project):
    """A phase that needs a claim's reasoning asks for it by id. Handing over
    every body just in case is how a context contract becomes a context dump."""
    claims = resolve(project, "proposal")["reads"]["claims"]
    assert claims["mode"] == "metadata"
    assert [e["id"] for e in claims["entries"]] == ["CMP-payments"]
    assert "prose" not in claims["entries"][0]


def test_claims_metadata_excludes_candidates(project):
    """A candidate may be read, never cited. It does not belong in the set a
    phase is handed as established."""
    claims = resolve(project, "proposal")["reads"]["claims"]
    assert "CON-authorisation" not in [e["id"] for e in claims["entries"]]


def test_the_impact_selector_expands_to_the_computed_touch_set(project):
    """Computed, not read out of impact.md: the two must agree, and the
    computation is the half nobody can edit to say less."""
    project.write("src/pay.py", PAY + "\n\ndef void():\n    return None\n")
    claims = resolve(project, "design")["reads"]["claims"]
    assert claims["mode"] == "impact.claims_touched"
    assert claims["ids"] == ["CMP-payments"]
    assert claims["entries"][0]["prose"].startswith("Owns every decision")


def test_the_impact_selector_is_empty_when_nothing_is_touched(project):
    claims = resolve(project, "design")["reads"]["claims"]
    assert claims["ids"] == []


def test_an_unknown_selector_is_reported_not_ignored(repo):
    repo.write("README.md", "x\n")
    main(["init", "--repo", str(repo.root)])
    (repo.root / ".forge/schema/feature.yaml").write_text(
        "name: feature\nversion: 1\ntracks: [C]\nartifacts:\n"
        "  - id: proposal\n    generates: proposal.md\n    requires: []\n"
        "    tracks: [C]\n    reads:\n      - claims: \"${nope.thing}\"\n",
        encoding="utf-8")
    repo.commit("a schema with a bad selector")
    change.new_change(repo.root, "x", today=TODAY)
    resolved = instructions.resolve(repo.root, change.find_change(repo.root, "1"),
                                    "proposal")
    assert any("no such selector" in u for u in resolved["unresolved"])


def test_an_explicit_claim_id_list_resolves_to_bodies(repo):
    repo.write("src/pay.py", PAY)
    main(["init", "--repo", str(repo.root)])
    target = repo.root / "docs/system/components.md"
    target.write_text(target.read_text(encoding="utf-8") + COMPONENT, encoding="utf-8")
    (repo.root / ".forge/schema/feature.yaml").write_text(
        "name: feature\nversion: 1\ntracks: [C]\nartifacts:\n"
        "  - id: proposal\n    generates: proposal.md\n    requires: []\n"
        "    tracks: [C]\n    reads:\n      - claims: [CMP-payments]\n",
        encoding="utf-8")
    repo.commit("a schema naming a claim")
    change.new_change(repo.root, "x", today=TODAY)
    claims = instructions.resolve(repo.root, change.find_change(repo.root, "1"),
                                  "proposal")["reads"]["claims"]
    assert claims["entries"][0]["id"] == "CMP-payments"
    assert "prose" in claims["entries"][0]


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def test_instructions_prints_the_contract_and_the_instruction(project, capsys):
    assert main(["instructions", "proposal", "--change", "1",
                 "--repo", str(project.root)]) == 0
    out = capsys.readouterr().out
    assert "read      docs/system/OVERVIEW.md" in out
    assert "1 claim(s), metadata only" in out
    assert "Why, in one or two sentences" in out


def test_instructions_json(project, capsys):
    assert main(["instructions", "impact", "--change", "1",
                 "--repo", str(project.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact"] == "impact"
    assert payload["generates"] == "changes/0001-refund-support/impact.md"
    assert payload["required"] == schema.REQUIRED


def test_an_unknown_artifact_names_the_ones_that_exist(project, capsys):
    assert main(["instructions", "nope", "--change", "1",
                 "--repo", str(project.root)]) == 2
    assert "it declares proposal, spec" in capsys.readouterr().err


def test_an_artifact_absent_from_the_track_still_resolves(project):
    """`forge instructions` answers "what would this phase read", which is a
    reasonable question on a track that does not require the phase."""
    changed = item(project)
    changed.meta["track"] = "B"
    changed.write_meta()
    assert instructions.resolve(project.root, change.find_change(project.root, "1"),
                                "impact")["required"] == schema.ABSENT
