"""The behaviour M1 exists to establish.

Every test here is a claim about what a reviewer should be asked to look at.
The two that matter most are `test_reformatting_only_is_fresh` and
`test_pure_rename_is_fresh` - those are the two mechanical false-positive
sources that would make the drift ledger noise, and noise is worse than no
ledger because it looks like coverage.
"""

from __future__ import annotations

import pytest

from forge.anchor import AnchorError, Status, classify, parse_anchor

REFUND_V1 = """\
export function computeRefundable(captured: number, settled: number): number {
  // the bound is cumulative
  return captured - settled;
}

export const LIMIT = 100;
"""

REFUND_REFORMATTED = """\
export function computeRefundable(
  captured: number,
  settled: number,
): number {
  // reworded comment, same behaviour

  return captured-settled;
}

export const LIMIT = 100;
"""

REFUND_BODY_CHANGED = """\
export function computeRefundable(captured: number, settled: number): number {
  return Math.max(0, captured - settled);
}

export const LIMIT = 100;
"""

REFUND_SIGNATURE_CHANGED = """\
export function computeRefundable(captured: number, settled: number, fees: number): number {
  return captured - settled;
}

export const LIMIT = 100;
"""

REFUND_SYMBOL_GONE = """\
export const LIMIT = 100;
"""


@pytest.fixture
def base(repo):
    repo.write("src/payments/refund.ts", REFUND_V1)
    repo.write("README.md", "# fixture\n")
    return repo.commit("initial")


def _classify(repo, base, anchor: str, head="HEAD"):
    return classify(repo.root, parse_anchor(anchor), baseline=base, head=head)


def test_unchanged_is_fresh(repo, base):
    repo.write("README.md", "# fixture\n\nunrelated edit\n")
    repo.commit("touch something else")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.FRESH
    assert not r.changed


def test_reformatting_only_is_fresh(repo, base):
    """Reflow, blank lines and a reworded comment must not surface as drift."""
    repo.write("src/payments/refund.ts", REFUND_REFORMATTED)
    repo.commit("reformat")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.FRESH, r.detail


def test_body_change_is_shifted(repo, base):
    repo.write("src/payments/refund.ts", REFUND_BODY_CHANGED)
    repo.commit("clamp at zero")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.SHIFTED


def test_signature_change_is_stale(repo, base):
    repo.write("src/payments/refund.ts", REFUND_SIGNATURE_CHANGED)
    repo.commit("add fees parameter")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.STALE


def test_deleted_symbol_is_missing(repo, base):
    repo.write("src/payments/refund.ts", REFUND_SYMBOL_GONE)
    repo.commit("drop the function")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.MISSING
    assert "not found" in r.detail


def test_deleted_file_is_missing(repo, base):
    repo.remove("src/payments/refund.ts")
    repo.commit("delete the module")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.MISSING


def test_pure_rename_is_fresh(repo, base):
    """A file move with no content change must not invalidate the anchor.

    This is the single most important false-positive source: without rename
    following, any refactor that moves files marks every anchor in them stale.
    """
    repo.move("src/payments/refund.ts", "src/billing/refund.ts")
    repo.commit("move payments -> billing")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.FRESH, r.detail
    assert r.moved is True
    assert r.baseline_path == "src/payments/refund.ts"
    assert r.head_path == "src/billing/refund.ts"


def test_rename_plus_body_change_is_shifted(repo, base):
    repo.move("src/payments/refund.ts", "src/billing/refund.ts")
    repo.write("src/billing/refund.ts", REFUND_BODY_CHANGED)
    repo.commit("move and clamp")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.status is Status.SHIFTED, r.detail


def test_anchor_pointing_at_a_future_file_is_missing(repo, base):
    """An anchor whose target did not exist at its own baseline is an authoring bug."""
    repo.write("src/payments/fees.ts", "export function fee(): number { return 1; }\n")
    repo.commit("add fees")
    r = _classify(repo, base, "src/payments/fees.ts#fee")
    assert r.status is Status.MISSING
    assert "baseline" in r.detail


def test_const_declarator_resolves(repo, base):
    repo.write("src/payments/refund.ts", REFUND_V1.replace("LIMIT = 100", "LIMIT = 250"))
    repo.commit("raise the limit")
    r = _classify(repo, base, "src/payments/refund.ts#LIMIT")
    assert r.status is Status.STALE


def test_directory_anchor_tracks_anything_beneath_it(repo, base):
    fresh = _classify(repo, base, "src/payments/")
    assert fresh.status is Status.FRESH

    repo.write("src/payments/ledger.ts", "export const x = 1;\n")
    repo.commit("add a file under the component")
    r = _classify(repo, base, "src/payments/")
    assert r.status is Status.STALE


def test_unknown_language_falls_back_to_coarse(repo, base):
    """Coarse mode is line-based: it absorbs trailing whitespace and blank lines.

    It does *not* absorb a reflow across lines - that is the precision a grammar
    buys, and the coarse flag is how the weaker signal stays visible.
    """
    repo.write("src/thing.rs", "fn main() {}\n")
    mid = repo.commit("add rust")
    repo.write("src/thing.rs", "fn main() {}   \n\n\n")
    repo.commit("trailing whitespace and blank lines")

    r = classify(repo.root, parse_anchor("src/thing.rs"), baseline=mid)
    assert r.coarse is True
    assert r.status is Status.FRESH


def test_coarse_mode_sees_a_real_change(repo, base):
    repo.write("src/thing.rs", "fn main() {}\n")
    mid = repo.commit("add rust")
    repo.write("src/thing.rs", "fn main() { println!(\"x\"); }\n")
    repo.commit("change rust")
    r = classify(repo.root, parse_anchor("src/thing.rs"), baseline=mid)
    assert r.coarse is True and r.status is Status.STALE


def test_unresolvable_symbol_degrades_instead_of_blocking(repo, base):
    """A declaration form the table does not cover must not report `missing`.

    An object property bound to an arrow function is a `pair` node with no
    `name` field, so the declaration table cannot resolve it. Reporting
    `missing` - a blocking status - for a limit of our own table is how a ledger
    earns being ignored, so it degrades to a whole-file comparison instead.
    """
    repo.write("src/odd.ts", "export default { onRefund: (x: number) => x };\n")
    mid = repo.commit("add odd shape")
    repo.write("src/odd.ts", "export default { onRefund: (x: number) => x + 1 };\n")
    repo.commit("change it")
    r = classify(repo.root, parse_anchor("src/odd.ts#onRefund"), baseline=mid)
    assert r.status is not Status.MISSING
    assert r.symbol_unresolved is True
    assert "not resolvable" in r.detail


def test_missing_baseline_is_an_error(repo, base):
    with pytest.raises(AnchorError):
        classify(repo.root, parse_anchor("src/payments/refund.ts"))


def test_recorded_sha_is_used_when_no_baseline_is_passed(repo, base):
    repo.write("src/payments/refund.ts", REFUND_SIGNATURE_CHANGED)
    repo.commit("change signature")
    r = classify(repo.root, parse_anchor(f"src/payments/refund.ts#computeRefundable@{base}"))
    assert r.status is Status.STALE
    assert r.baseline == base


def test_move_reports_both_paths_in_the_right_order(repo, base):
    """Regression: an earlier version put the head path in `renamed_from` and
    the baseline path in `renamed_to`, so the CLI printed a message that
    contradicted itself."""
    repo.move("src/payments/refund.ts", "src/billing/refund.ts")
    repo.commit("move")
    r = _classify(repo, base, "src/payments/refund.ts")
    assert r.baseline_path == "src/payments/refund.ts"
    assert r.head_path == "src/billing/refund.ts"
    assert r.moved is True


def test_unmoved_anchor_is_not_reported_as_moved(repo, base):
    repo.write("src/payments/refund.ts", REFUND_BODY_CHANGED)
    repo.commit("edit in place")
    r = _classify(repo, base, "src/payments/refund.ts#computeRefundable")
    assert r.moved is False
    assert r.baseline_path == r.head_path == "src/payments/refund.ts"


# --------------------------------------------------------------------------
# Content-addressed relocation: when git's rename detection is not enough
# --------------------------------------------------------------------------

GO_COMMENT_HEAVY = """\
package pkg

// Render turns a name into a greeting.
// It carries several lines of doc comment, as Go style encourages, so the
// comments dominate the byte count of this file. Rewriting them while moving
// the file drops git's similarity score below its rename threshold.
// Another line, to push the ratio further.
// And another, because complete sentences are the convention here.
func Render(name string) string {
\treturn "hi " + name
}
"""

GO_COMMENTS_REWRITTEN = """\
package pkg

// rewritten
func Render(name string) string {
\treturn "hi " + name
}
"""


@pytest.fixture
def go_base(repo):
    repo.write("pkg/a.go", GO_COMMENT_HEAVY)
    return repo.commit("initial")


def test_move_below_gits_rename_threshold_is_still_followed(repo, go_base):
    """The M1 residual defect, closed.

    Rewriting the doc comments while moving the file leaves git measuring ~13%
    similarity, so it reports add + delete and the anchor cannot follow the
    move. Content-addressed relocation finds it anyway, because the *symbol*
    fingerprint is unchanged.
    """
    repo.move("pkg/a.go", "moved/pkg/a.go")
    repo.write("moved/pkg/a.go", GO_COMMENTS_REWRITTEN)
    repo.commit("move and rewrite comments")

    # Confirm the premise: git really does not see this as a rename.
    from forge import gitio
    forward, _ = gitio.rename_map(repo.root, go_base, "HEAD")
    assert forward == {}, "premise broken: git detected the rename after all"

    r = _classify(repo, go_base, "pkg/a.go#Render")
    assert r.status is Status.FRESH, r.detail
    assert r.relocated is True
    assert r.head_path == "moved/pkg/a.go"


def test_file_anchor_relocates_by_whole_file_fingerprint(repo, go_base):
    repo.move("pkg/a.go", "moved/pkg/a.go")
    repo.write("moved/pkg/a.go", GO_COMMENTS_REWRITTEN)
    repo.commit("move and rewrite comments")
    r = _classify(repo, go_base, "pkg/a.go")
    assert r.status is Status.FRESH and r.relocated is True


def test_relocation_refuses_when_ambiguous(repo, go_base):
    """Two equally good candidates is not a move; it is a question.

    Guessing one would be worse than reporting missing, because a wrong
    relocation silently re-anchors a claim to the wrong code.

    The copies carry rewritten comments so git's similarity stays under its
    threshold and declines to call either one a rename - otherwise git picks a
    winner itself and this code never runs.
    """
    repo.remove("pkg/a.go")
    repo.write("one/a.go", GO_COMMENTS_REWRITTEN)
    repo.write("two/a.go", GO_COMMENTS_REWRITTEN)
    repo.commit("delete and duplicate with rewritten comments")

    from forge import gitio
    forward, _ = gitio.rename_map(repo.root, go_base, "HEAD")
    assert forward == {}, "premise broken: git resolved it to a single rename"

    r = _classify(repo, go_base, "pkg/a.go#Render")
    assert r.status is Status.MISSING
    assert "ambiguous" in r.detail


def test_git_resolves_an_unambiguous_identical_copy_itself(repo, go_base):
    """The complementary case: identical content, so git detects the rename at
    100% and relocation never needs to run."""
    repo.move("pkg/a.go", "one/a.go")
    repo.commit("plain move")
    r = _classify(repo, go_base, "pkg/a.go#Render")
    assert r.status is Status.FRESH
    assert r.relocated is False
    assert r.head_path == "one/a.go"


def test_relocation_does_not_fire_on_a_genuine_deletion(repo, go_base):
    repo.remove("pkg/a.go")
    repo.commit("delete it")
    r = _classify(repo, go_base, "pkg/a.go#Render")
    assert r.status is Status.MISSING
    assert r.relocated is False
    assert "ambiguous" not in r.detail


def test_relocation_does_not_accept_a_different_implementation(repo, go_base):
    """A same-named symbol elsewhere is not the same code.

    Only an identical fingerprint, or an identical signature when no exact
    match exists, is accepted - never mere name equality.
    """
    repo.remove("pkg/a.go")
    repo.write(
        "other/a.go",
        "package pkg\n\nfunc Render(name string, loud bool) string {\n"
        "\treturn name + \"!\"\n}\n",
    )
    repo.commit("delete, and add an unrelated Render")
    r = _classify(repo, go_base, "pkg/a.go#Render")
    assert r.status is Status.MISSING, r.detail
