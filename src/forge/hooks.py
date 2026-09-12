"""The one integration point worth taking a hook for.

OPEN_QUESTIONS.md Q10 names the way every knowledge-maintenance scheme dies:
hotfixes, other people's commits and dependency bots accumulate stale anchors,
the first `forge drift` after a busy week produces a wall of findings, and
somebody declares harness bankruptcy. The answer it recommends is a pre-commit
hook - catch drift at the moment it is created, while the reason is still in
somebody's head.

Two things had to be true first, and neither was until run 3.

**It has to be fast.** `forge sync derived` took 93 seconds on a 620-file
repository before the batch reader; at that price no hook survives a week. It
is 1.4 seconds now, and the hook does less than that.

**It has to look at the index.** `forge drift --changed` selected by the
working diff and still classified against HEAD, so it returned the same verdict
whether or not anything was staged. A hook built on it would have been a
placebo that everybody trusted. `--staged` compares against the index, which is
what is about to become a commit.

What the hook deliberately does *not* do:

- **It does not run the test suite.** That is `forge verify`'s job at a point
  where somebody is waiting for an answer, not on every commit.
- **It does not sync the derived tier.** The census is of HEAD, so before a
  commit it is already correct and after the commit it is stale - a pre-commit
  hook is the one place that cannot fix it. `forge status` says when to run it.
- **It does not rewrite anything.** A hook that edits what you are committing
  is a hook people disable.
"""

from __future__ import annotations

import stat
from pathlib import Path

from . import gitio

__all__ = ["HOOK_NAME", "hook_body", "install", "installed_state", "MARKER"]

HOOK_NAME = "pre-commit"

#: How the hook identifies itself, so an upgrade can replace its own work and
#: nothing else. A hook somebody wrote by hand is theirs.
MARKER = "# installed by `forge hooks install`"

_BODY = """\
#!/bin/sh
{marker}
#
# Two cheap checks on what is staged. Both exit non-zero to stop the commit;
# `git commit --no-verify` skips them, and that is deliberate - a hook nobody
# can bypass is a hook people uninstall.
#
# What is NOT here, and why: the test suite belongs to `forge verify`, and
# `forge sync derived` cannot run usefully before a commit because the census
# it builds is of HEAD.
root=$(git rev-parse --show-toplevel)

if ! {forge} check --scope store --repo "$root"; then
    echo ""
    echo "The claim store does not validate. Fix what is reported above, or"
    echo "commit with --no-verify and fix it in the next commit."
    exit 1
fi

if ! {forge} drift --staged --unrecorded --repo "$root"; then
    echo ""
    echo "Code under a claim's anchor changed here, and nobody has written that"
    echo "down. The hook does not ask for a verdict - a verdict points at a commit"
    echo "and this one does not exist yet. It asks that the signal is not lost:"
    echo ""
    echo "    {forge} drift record --staged"
    echo ""
    echo "That opens a ledger entry and lets the commit through. Rule on it after,"
    echo "against the commit it is about:"
    echo ""
    echo "    {forge} drift confirm <id>      # still true; restamps the anchor"
    echo "    {forge} drift resolve <id> --verdict V1|V2|V3|V4"
    echo ""
    echo "Or commit with --no-verify and lose the note."
    exit 1
fi
"""


def hook_body(command: str = "forge") -> str:
    """The script, with *command* as the way this machine invokes the kernel."""
    return _BODY.format(marker=MARKER, forge=command)


def hooks_dir(repo: Path) -> Path:
    """Where git looks for hooks, honouring `core.hooksPath`.

    A project that has moved its hooks - many do, to keep them in the tree -
    would otherwise get a file written somewhere git never reads, and a report
    saying the hook is installed.
    """
    configured = gitio.git(repo, "config", "--get", "core.hooksPath",
                           check=False).strip()
    if configured:
        candidate = Path(configured)
        return candidate if candidate.is_absolute() else repo / candidate
    common = gitio.git(repo, "rev-parse", "--git-common-dir", check=False).strip()
    root = Path(common) if common else repo / ".git"
    if not root.is_absolute():
        root = repo / root
    return root / "hooks"


def installed_state(repo: Path) -> tuple[str, Path]:
    """(state, path) where state is `absent`, `ours`, or `theirs`."""
    target = hooks_dir(repo) / HOOK_NAME
    if not target.is_file():
        return "absent", target
    text = target.read_text(encoding="utf-8", errors="replace")
    return ("ours" if MARKER in text else "theirs"), target


def install(repo: Path, *, command: str = "forge", force: bool = False) -> tuple[str, Path]:
    """Write the hook. Returns (what happened, path).

    Refuses to overwrite a hook this tool did not write, unless forced. Silently
    replacing somebody's own pre-commit script is the kind of thing that gets a
    tool removed rather than reported.
    """
    state, target = installed_state(repo)
    if state == "theirs" and not force:
        return "refused", target

    body = hook_body(command)
    if state == "ours" and target.read_text(encoding="utf-8", errors="replace") == body:
        return "unchanged", target

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")
    # Git runs the hook through the shell, and on anything POSIX it has to be
    # executable. Harmless on Windows.
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return ("replaced" if state != "absent" else "installed"), target


def uninstall(repo: Path) -> tuple[str, Path]:
    """Remove the hook, but only if this tool wrote it."""
    state, target = installed_state(repo)
    if state == "absent":
        return "absent", target
    if state == "theirs":
        return "refused", target
    target.unlink()
    return "removed", target
