"""The hardening layer.

Anchors are read out of markdown files, so every SHA and every path in them is
untrusted as far as argv is concerned. GSD validates its stored commit id as
4-40 hex characters for exactly this reason; these tests hold that line.
"""

from __future__ import annotations

import pytest

from forge import gitio


@pytest.mark.parametrize("rev", ["HEAD", "a1b2c3d", "A1B2" , "0" * 40])
def test_accepted_revisions(rev):
    assert gitio.validate_rev(rev)


@pytest.mark.parametrize(
    "rev",
    [
        "",
        "HEAD~3",            # the full revision grammar is deliberately not accepted
        "main@{2}",
        ":/some message",
        "--upload-pack=evil",
        "a1b2c3d; rm -rf /",
        "abc",               # too short
        "z" * 8,             # not hex
        "0" * 41,            # too long
    ],
)
def test_rejected_revisions(rev):
    with pytest.raises(gitio.InvalidRevision):
        gitio.validate_rev(rev)


def test_rejected_revision_is_not_a_dashed_option():
    """The concrete attack: a stored value that git would read as an option."""
    with pytest.raises(gitio.InvalidRevision):
        gitio.validate_rev("--output=/tmp/pwned")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("src/a.ts", "src/a.ts"),
        (r"src\a.ts", "src/a.ts"),
        ("./src/a.ts", "src/a.ts"),
        ("src//a.ts", "src/a.ts"),
        ("src/domain/", "src/domain/"),
    ],
)
def test_path_normalisation(given, expected):
    assert gitio.validate_repo_path(given) == expected


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "/etc/passwd", "C:/Windows", r"C:\Windows", "../x", "a/../../x", "a\0b", "."],
)
def test_rejected_paths(bad):
    with pytest.raises(gitio.InvalidPath):
        gitio.validate_repo_path(bad)


def test_blob_and_existence(repo):
    repo.write("a.txt", "one\n")
    first = repo.commit("first")
    repo.write("a.txt", "two\n")
    repo.commit("second")

    assert gitio.blob_at(repo.root, first, "a.txt") == b"one\n"
    assert gitio.blob_at(repo.root, "HEAD", "a.txt") == b"two\n"
    assert gitio.blob_at(repo.root, first, "missing.txt") is None
    assert gitio.exists_at(repo.root, first, "a.txt")
    assert not gitio.exists_at(repo.root, first, "missing.txt")


def test_rename_map_both_directions(repo):
    repo.write("old/name.ts", "export const x = 1;\n")
    first = repo.commit("first")
    repo.move("old/name.ts", "new/name.ts")
    second = repo.commit("moved")

    forward, backward = gitio.rename_map(repo.root, first, second)
    assert forward == {"old/name.ts": "new/name.ts"}
    assert backward == {"new/name.ts": "old/name.ts"}


def test_resolve_path_forwards_through_a_rename(repo):
    """An anchor holds the old name; the file has since moved."""
    repo.write("old/name.ts", "export const x = 1;\n")
    first = repo.commit("first")
    repo.move("old/name.ts", "new/name.ts")
    second = repo.commit("moved")

    at_head, other = gitio.resolve_path_at(
        repo.root, "old/name.ts", target_rev=second, other_rev=first
    )
    assert at_head == "new/name.ts"
    assert other == "old/name.ts"


def test_resolve_path_backwards_through_a_rename(repo):
    repo.write("old/name.ts", "export const x = 1;\n")
    first = repo.commit("first")
    repo.move("old/name.ts", "new/name.ts")
    second = repo.commit("moved")

    at_base, other = gitio.resolve_path_at(
        repo.root, "new/name.ts", target_rev=first, other_rev=second
    )
    assert at_base == "old/name.ts"
    assert other == "new/name.ts"


def test_resolve_path_returns_none_when_genuinely_absent(repo):
    repo.write("a.ts", "export const x = 1;\n")
    first = repo.commit("first")
    repo.write("b.ts", "export const y = 2;\n")
    second = repo.commit("added b")

    assert gitio.resolve_path_at(
        repo.root, "b.ts", target_rev=first, other_rev=second
    ) == (None, None)


def test_whitespace_only_diff_is_recognised(repo):
    repo.write("a.ts", "export function f() {\n  return 1;\n}\n")
    first = repo.commit("first")
    repo.write("a.ts", "export function f() {\n\n      return 1;\n}\n   \n")
    second = repo.commit("reindent")
    assert gitio.diff_is_whitespace_only(repo.root, first, second, "a.ts")


def test_substantive_diff_is_not_whitespace_only(repo):
    repo.write("a.ts", "export function f() {\n  return 1;\n}\n")
    first = repo.commit("first")
    repo.write("a.ts", "export function f() {\n  return 2;\n}\n")
    second = repo.commit("change")
    assert not gitio.diff_is_whitespace_only(repo.root, first, second, "a.ts")


def test_unchanged_file_is_not_reported_as_whitespace_only(repo):
    """No diff at all is not a whitespace-only diff; the ground truth for the
    M1 measurement depends on that distinction."""
    repo.write("a.ts", "export const x = 1;\n")
    first = repo.commit("first")
    repo.write("b.ts", "export const y = 2;\n")
    second = repo.commit("touch another file")
    assert not gitio.diff_is_whitespace_only(repo.root, first, second, "a.ts")


def test_rev_list_is_oldest_first(repo):
    a = repo.commit("a")
    b = repo.commit("b")
    c = repo.commit("c")
    assert gitio.rev_list(repo.root, count=3) == [a, b, c]


def test_tree_hash_changes_when_anything_beneath_changes(repo):
    repo.write("pkg/a.ts", "export const x = 1;\n")
    first = repo.commit("first")
    before = gitio.tree_hash_at(repo.root, first, "pkg")

    repo.write("pkg/b.ts", "export const y = 2;\n")
    second = repo.commit("add sibling")
    after = gitio.tree_hash_at(repo.root, second, "pkg")

    assert before and after and before != after
    assert gitio.tree_hash_at(repo.root, first, "nope") is None
