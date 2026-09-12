"""The pre-commit hook, and the two things that had to be true before it.

OPEN_QUESTIONS.md Q10 recommends this hook as the one integration point worth
taking. It could not be built until run 3, for two reasons this file pins:
`forge sync derived` took 93 seconds on a 620-file repository, and
`forge drift --changed` compared HEAD against an anchor's sha and so returned
the same verdict whether or not anything was staged.
"""

from __future__ import annotations

from datetime import date

import pytest

from forge import anchor, change, gitio, hooks, ledger
from forge.cli import main

TODAY = date(2026, 9, 12)

CODE = "def greet():\n    return 'hi'\n"


def claim_text(sha: str) -> str:
    return (
        "# Domain\n\n### CON-greet - the greeting's shape\n\n"
        "```claim\n"
        "kind:     concept\n"
        "status:   asserted\n"
        "truth-source: code\n"
        f'anchors:  ["src/app.py#greet@{sha}"]\n'
        "reviewed: 2026-09-01\n"
        "```\n\n"
        "Prose about the greeting, long enough to read like a real claim.\n"
    )


@pytest.fixture
def anchored(repo):
    """One claim, anchored to a symbol, fresh at HEAD."""
    repo.write("src/app.py", CODE)
    base = repo.commit("the code")
    main(["init", "--repo", str(repo.root)])
    repo.write("docs/system/domain.md", claim_text(base))
    repo.commit("a claim")
    return repo


def stage(repo, text: str) -> None:
    (repo.root / "src/app.py").write_text(text, encoding="utf-8", newline="\n")
    repo._git("add", "src/app.py")


# ---------------------------------------------------------------------------
# The index is what a pre-commit hook is about
# ---------------------------------------------------------------------------

def test_a_staged_signature_change_is_seen(anchored):
    """The reason `--staged` exists. `--changed` selected by the working diff
    and still classified against HEAD, so it answered the same either way."""
    stage(anchored, "def greet(name):\n    return name\n")

    (drift,) = anchor.classify_store(anchored.root, head=gitio.INDEX)
    assert drift.status is anchor.Status.STALE


def test_a_clean_index_is_fresh(anchored):
    (drift,) = anchor.classify_store(anchored.root, head=gitio.INDEX)
    assert drift.status is anchor.Status.FRESH


def test_an_unstaged_edit_is_not_seen(anchored):
    """The working tree holds edits nobody is committing yet. A hook that
    blocked on those would block on work in progress."""
    (anchored.root / "src/app.py").write_text(
        "def greet(name):\n    return name\n", encoding="utf-8", newline="\n")

    (drift,) = anchor.classify_store(anchored.root, head=gitio.INDEX)
    assert drift.status is anchor.Status.FRESH


def test_the_index_can_be_read_like_a_revision(repo):
    repo.write("a.txt", "committed\n")
    repo.commit("one")
    (repo.root / "a.txt").write_text("staged\n", encoding="utf-8", newline="\n")
    repo._git("add", "a.txt")

    assert gitio.blob_at(repo.root, "HEAD", "a.txt") == b"committed\n"
    assert gitio.blob_at(repo.root, gitio.INDEX, "a.txt") == b"staged\n"
    assert gitio.blobs_at(repo.root, gitio.INDEX, ["a.txt"]) == {"a.txt": b"staged\n"}


def test_staged_files_reports_only_what_is_staged(repo):
    repo.write("a.txt", "one\n")
    repo.commit("one")
    (repo.root / "a.txt").write_text("staged\n", encoding="utf-8", newline="\n")
    (repo.root / "b.txt").write_text("not staged\n", encoding="utf-8", newline="\n")
    repo._git("add", "a.txt")

    assert gitio.staged_files(repo.root) == ["a.txt"]


# ---------------------------------------------------------------------------
# What the hook can honestly demand
# ---------------------------------------------------------------------------

def test_recorded_drift_no_longer_blocks(anchored, capsys):
    """A verdict points at a commit, and at pre-commit time that commit does
    not exist - so `confirm` can never clear the block. What the hook can ask
    is that the signal is not lost."""
    stage(anchored, "def greet(name):\n    return name\n")
    assert main(["drift", "--staged", "--unrecorded",
                 "--repo", str(anchored.root)]) == 1

    ledger.record(anchored.root,
                  anchor.classify_store(anchored.root, head=gitio.INDEX),
                  today=TODAY)
    assert main(["drift", "--staged", "--unrecorded",
                 "--repo", str(anchored.root)]) == 0


def test_the_drift_itself_is_still_reported(anchored):
    """`--unrecorded` narrows what *blocks*, never what is shown."""
    stage(anchored, "def greet(name):\n    return name\n")
    ledger.record(anchored.root,
                  anchor.classify_store(anchored.root, head=gitio.INDEX),
                  today=TODAY)

    assert main(["drift", "--staged", "--repo", str(anchored.root)]) == 1


def test_a_resolved_entry_does_not_keep_the_claim_quiet(anchored):
    """An entry that has been ruled on is closed, so the same claim drifting
    again is unrecorded again."""
    stage(anchored, "def greet(name):\n    return name\n")
    ledger.record(anchored.root,
                  anchor.classify_store(anchored.root, head=gitio.INDEX),
                  today=TODAY)
    ledger.resolve(anchored.root, "D-001", "V1", today=TODAY)

    assert main(["drift", "--staged", "--unrecorded",
                 "--repo", str(anchored.root)]) == 1


# ---------------------------------------------------------------------------
# Installing
# ---------------------------------------------------------------------------

def test_install_writes_an_executable_hook(anchored):
    outcome, target = hooks.install(anchored.root)
    assert outcome == "installed"
    assert target.is_file()
    body = target.read_text(encoding="utf-8")
    assert hooks.MARKER in body
    assert "--staged" in body and "--unrecorded" in body


def test_install_is_idempotent(anchored):
    hooks.install(anchored.root)
    assert hooks.install(anchored.root)[0] == "unchanged"


def test_install_refuses_somebody_elses_hook(anchored):
    """Silently replacing a project's own pre-commit script is how a tool gets
    removed rather than reported."""
    target = hooks.hooks_dir(anchored.root) / hooks.HOOK_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\nnpm run lint\n", encoding="utf-8", newline="\n")

    assert hooks.install(anchored.root)[0] == "refused"
    assert "npm run lint" in target.read_text(encoding="utf-8")
    assert hooks.install(anchored.root, force=True)[0] == "replaced"


def test_uninstall_only_removes_our_own(anchored):
    target = hooks.hooks_dir(anchored.root) / hooks.HOOK_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\nnpm run lint\n", encoding="utf-8", newline="\n")
    assert hooks.uninstall(anchored.root)[0] == "refused"

    hooks.install(anchored.root, force=True)
    assert hooks.uninstall(anchored.root)[0] == "removed"
    assert not target.exists()


def test_the_command_is_configurable(anchored):
    """A machine where the kernel is not `forge` on PATH - a virtualenv, a
    vendored checkout - still gets a hook that runs."""
    _, target = hooks.install(anchored.root, command="/opt/forge/bin/forge")
    assert "/opt/forge/bin/forge drift --staged" in target.read_text(encoding="utf-8")


def test_a_moved_hooks_directory_is_honoured(anchored):
    """Many projects set `core.hooksPath` to keep hooks in the tree. Writing to
    `.git/hooks` there produces a file git never reads and a report saying the
    hook is installed."""
    (anchored.root / ".githooks").mkdir()
    anchored._git("config", "core.hooksPath", ".githooks")

    _, target = hooks.install(anchored.root)
    assert target == anchored.root / ".githooks" / hooks.HOOK_NAME
    assert target.is_file()


def test_status_distinguishes_the_three_cases(anchored):
    assert hooks.installed_state(anchored.root)[0] == "absent"
    hooks.install(anchored.root)
    assert hooks.installed_state(anchored.root)[0] == "ours"
    hooks.hooks_dir(anchored.root).joinpath(hooks.HOOK_NAME).write_text(
        "#!/bin/sh\n", encoding="utf-8", newline="\n")
    assert hooks.installed_state(anchored.root)[0] == "theirs"
