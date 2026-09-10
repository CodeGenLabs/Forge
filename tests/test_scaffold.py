"""`forge init`, `forge claim new`, `forge claim show`, and the templates."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from forge import derive, scaffold, store, validate
from forge.cli import main

TODAY = dt.date(2026, 9, 11)


@pytest.fixture
def fresh(repo):
    repo.write("README.md", "# A project\n")
    repo.commit("a repository with no store")
    return repo


# ---------------------------------------------------------------------------
# forge init
# ---------------------------------------------------------------------------

def test_init_then_sync_gives_a_clean_check(fresh, capsys):
    """The first thing anyone does. If this is not clean, nobody gets to the
    second thing."""
    assert main(["init", "--repo", str(fresh.root)]) == 0
    fresh.commit("forge init")
    assert main(["sync", "derived", "--repo", str(fresh.root)]) == 0
    fresh.commit("chore: sync derived tier")
    capsys.readouterr()
    assert main(["check", "--repo", str(fresh.root)]) == 0
    assert "ok - no issues" in capsys.readouterr().out


def test_init_writes_the_mandatory_files(fresh):
    main(["init", "--repo", str(fresh.root)])
    for relative in scaffold.init_files():
        assert (fresh.root / relative).is_file(), relative
    # The mandatory baseline from SYSTEM_KNOWLEDGE.md section 2.2.
    for name in ("architecture.md", "components.md", "domain.md", "pitfalls.md"):
        assert (fresh.root / store.STORE_DIR / name).is_file()
    assert (fresh.root / store.DECISIONS_DIR / "ADR-0001-adopt-forge.md").is_file()


def test_init_scaffolds_no_claims(fresh):
    """Plausible starter claims for a codebase nobody has read are precisely
    what the candidates tier exists to prevent."""
    main(["init", "--repo", str(fresh.root)])
    fresh.commit("forge init")
    assert store.load_store(fresh.root) == []


def test_init_never_overwrites(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    target = fresh.root / store.STORE_DIR / "domain.md"
    target.write_text("# Mine\n\nHand-written.\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["init", "--repo", str(fresh.root)]) == 0
    out = capsys.readouterr().out
    assert "kept" in out and "Nothing to create" in out
    assert target.read_text(encoding="utf-8") == "# Mine\n\nHand-written.\n"


def test_init_refuses_outside_a_git_repository(tmp_path, capsys):
    (tmp_path / "loose").mkdir()
    assert main(["init", "--repo", str(tmp_path / "loose")]) == 2
    assert "not a git repository" in capsys.readouterr().err


def test_the_scaffold_is_written_with_lf_endings(fresh):
    """The derived tier is byte-identical LF; the authored tier beside it has
    no reason to differ, and a CRLF store file makes every diff on a
    cross-platform checkout unreadable."""
    main(["init", "--repo", str(fresh.root)])
    for relative in scaffold.init_files():
        assert b"\r\n" not in (fresh.root / relative).read_bytes(), relative


def test_the_adoption_adr_records_what_was_rejected(fresh):
    main(["init", "--repo", str(fresh.root)])
    text = (fresh.root / store.DECISIONS_DIR / "ADR-0001-adopt-forge.md").read_text(
        encoding="utf-8")
    # An ADR with no rejected alternative records a preference, not a decision.
    assert "Alternatives considered" in text
    assert "Rejected" in text


# ---------------------------------------------------------------------------
# The templates
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", sorted(scaffold.KIND_FILE))
def test_every_mvp_kind_has_a_template(kind):
    text = scaffold.claim_template(kind, today=TODAY)
    assert "```claim" in text
    assert f"kind:     {kind}" in text
    assert "reviewed: 2026-09-11" in text


@pytest.mark.parametrize("kind", sorted(scaffold.KIND_FILE))
def test_a_template_parses_as_a_claim(kind):
    """A template the parser cannot read is not a template.

    The trap is real: an unquoted `{path}` opens a YAML flow mapping, so the
    obvious spelling of every placeholder breaks the whole fence."""
    claims = store.parse_claims(
        scaffold.claim_template(kind, "CMP-example", "A title", today=TODAY),
        "docs/system/scratch.md",
    )
    assert len(claims) == 1
    assert claims[0].parse_error is None
    assert claims[0].kind == kind


@pytest.mark.parametrize("kind", sorted(scaffold.KIND_FILE))
def test_a_template_fails_the_placeholder_check_on_purpose(repo, kind):
    """The placeholders are the checklist. A template that passed `forge check`
    would let a store fill up with headings nobody finished."""
    repo.write(f"docs/system/{scaffold.KIND_FILE[kind]}",
               scaffold.claim_template(kind, today=TODAY))
    repo.commit("an unfinished claim")
    codes = [i.code for i in validate.check_store(repo.root, today=TODAY)]
    assert "store.placeholder" in codes


def test_a_template_with_an_id_and_title_keeps_them():
    text = scaffold.claim_template("invariant", "INV-refund-cap", "A refund is bounded",
                                   today=TODAY)
    assert text.startswith("### INV-refund-cap - A refund is bounded\n")


def test_generated_text_is_ascii(fresh):
    """The target console is cp1252. The heading grammar accepts an ASCII
    hyphen as well as an em dash, so the generated form is the one that
    survives the terminal."""
    for kind in scaffold.KIND_FILE:
        assert scaffold.claim_template(kind, today=TODAY).isascii()
    assert scaffold.adr_template(2, today=TODAY).isascii()
    for content in scaffold.init_files(TODAY).values():
        assert content.isascii()


def test_an_unknown_kind_is_a_usage_error():
    with pytest.raises(ValueError, match="not an MVP claim kind"):
        scaffold.claim_template("interface")


def test_the_postponed_kinds_are_not_offered(fresh):
    """The MVP ships five kinds. The parser recognises ten so an ID from a
    later milestone is not silently skipped, but nothing generates the other
    five yet."""
    with pytest.raises(SystemExit) as exit_info:
        main(["claim", "new", "interface", "--repo", str(fresh.root)])
    assert exit_info.value.code == 2


# ---------------------------------------------------------------------------
# forge claim new
# ---------------------------------------------------------------------------

def test_claim_new_prints_rather_than_writing(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    before = (fresh.root / "docs/system/domain.md").read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(["claim", "new", "invariant", "--repo", str(fresh.root)]) == 0
    assert "```claim" in capsys.readouterr().out
    assert (fresh.root / "docs/system/domain.md").read_text(encoding="utf-8") == before


def test_claim_new_append_puts_each_kind_in_its_own_file(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    for kind, name in scaffold.KIND_FILE.items():
        assert main(["claim", "new", kind, "--append", "--repo", str(fresh.root)]) == 0
        text = (fresh.root / "docs/system" / name).read_text(encoding="utf-8")
        assert f"kind:     {kind}" in text
    capsys.readouterr()


def test_claim_new_append_says_the_check_will_fail(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    capsys.readouterr()
    main(["claim", "new", "pitfall", "--append", "--repo", str(fresh.root)])
    out = capsys.readouterr().out
    assert "fail `forge check`" in out
    assert "not a defect" in out


def test_claim_new_append_needs_the_scaffold(fresh, capsys):
    assert main(["claim", "new", "pitfall", "--append", "--repo", str(fresh.root)]) == 2
    assert "forge init" in capsys.readouterr().err


def test_claim_new_append_leaves_the_existing_claims_parseable(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    main(["claim", "new", "concept", "--id", "CON-capture", "--title", "Taking money",
          "--append", "--repo", str(fresh.root)])
    main(["claim", "new", "invariant", "--id", "INV-refund-cap", "--title", "Bounded",
          "--append", "--repo", str(fresh.root)])
    fresh.commit("two claims")
    capsys.readouterr()
    ids = [c.id for c in store.load_store(fresh.root)]
    assert ids == ["CON-capture", "INV-refund-cap"]


# ---------------------------------------------------------------------------
# forge claim show
# ---------------------------------------------------------------------------

def test_claim_show_prints_the_claim_as_written(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    main(["claim", "new", "concept", "--id", "CON-capture", "--title", "Taking money",
          "--append", "--repo", str(fresh.root)])
    fresh.commit("one claim")
    capsys.readouterr()
    assert main(["claim", "show", "CON-capture", "--repo", str(fresh.root)]) == 0
    out = capsys.readouterr().out
    assert "docs/system/domain.md:" in out
    assert "### CON-capture - Taking money" in out
    assert "kind:     concept" in out


def test_claim_show_of_an_unknown_id_exits_one(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    fresh.commit("scaffold")
    capsys.readouterr()
    assert main(["claim", "show", "INV-404", "--repo", str(fresh.root)]) == 1
    assert "no claim defines INV-404" in capsys.readouterr().err


def test_claim_show_reports_a_duplicated_id(fresh, capsys):
    """The reader has to know which of the two they are looking at before they
    act on either."""
    main(["init", "--repo", str(fresh.root)])
    for _ in range(2):
        main(["claim", "new", "pitfall", "--id", "PIT-twice", "--title", "Twice",
              "--append", "--repo", str(fresh.root)])
    fresh.commit("a duplicate")
    capsys.readouterr()
    assert main(["claim", "show", "PIT-twice", "--repo", str(fresh.root)]) == 1
    captured = capsys.readouterr()
    assert captured.out.count("### PIT-twice") == 2
    assert "defined 2 times" in captured.err


def test_claim_show_json(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    main(["claim", "new", "concept", "--id", "CON-capture", "--title", "Taking money",
          "--append", "--repo", str(fresh.root)])
    fresh.commit("one claim")
    capsys.readouterr()
    assert main(["claim", "show", "CON-capture", "--repo", str(fresh.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["id"] == "CON-capture"
    assert payload[0]["kind"] == "concept"


# ---------------------------------------------------------------------------
# --json on every command
# ---------------------------------------------------------------------------

def test_status_json(fresh, capsys):
    main(["init", "--repo", str(fresh.root)])
    fresh.commit("scaffold")
    derive.derive_all(fresh.root)
    fresh.commit("chore: sync derived tier")
    capsys.readouterr()
    assert main(["status", "--repo", str(fresh.root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["derived"] == {"not_built": [], "stale": [], "commits_behind": 0}
    assert payload["summary"]["claims"] == 0


def test_an_unbuilt_tier_is_reported_once_not_five_times(fresh, capsys):
    """Four identical errors carrying the same fix read as breakage rather than
    as a next step."""
    main(["init", "--repo", str(fresh.root)])
    fresh.commit("scaffold, no sync")
    capsys.readouterr()
    assert main(["check", "--repo", str(fresh.root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert [i["code"] for i in payload["issues"]] == ["derived.not_built"]
