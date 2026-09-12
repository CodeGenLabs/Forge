"""Safe, deterministic git access.

Two rules govern this module, and both come from the research:

1. **git is never invoked through a shell.** Every call is a list of argv
   elements passed to ``subprocess.run`` with ``shell=False``.
2. **No stored value reaches git unvalidated.** Anchors carry SHAs and paths
   that were read out of a markdown file, which is untrusted input as far as
   argv is concerned. GSD validates ``built_at_commit`` as 4-40 hex characters
   for exactly this reason ("a hostile graph.json cannot inject dashed options
   into argv"); we apply the same rule to every revision and every path.

Nothing here calls a model, and every function is a pure function of the
repository at a commit.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

__all__ = [
    "GitError",
    "InvalidRevision",
    "InvalidPath",
    "validate_rev",
    "validate_repo_path",
    "git",
    "blob_at",
    "blobs_at",
    "exists_at",
    "tree_hash_at",
    "rev_parse",
    "rev_list",
    "rename_map",
    "resolve_path_at",
    "changed_files",
    "first_commit_touching",
    "parent_of",
    "diff_is_whitespace_only",
    "is_repo",
]

# A revision we are willing to hand to git. Hex object names of 4-40 chars, or
# one of a tiny allowlist of symbolic names. Deliberately does NOT accept the
# full git revision grammar (``HEAD~3``, ``main@{2}``, ``:/message``): the
# harness only ever needs concrete commits, and a narrow accept set is the
# cheapest defence against a crafted value in a claim file.
_REV_RE = re.compile(r"\A[0-9a-fA-F]{4,40}\Z")
_SYMBOLIC_REVS = frozenset({"HEAD"})

_WINDOWS_DRIVE_RE = re.compile(r"\A[A-Za-z]:")


class GitError(RuntimeError):
    """A git invocation failed."""


class InvalidRevision(ValueError):
    """A revision string was rejected before reaching git."""


class InvalidPath(ValueError):
    """A repository-relative path was rejected before reaching git."""


def validate_rev(rev: str) -> str:
    """Return *rev* unchanged, or raise :class:`InvalidRevision`."""
    if not isinstance(rev, str) or not rev:
        raise InvalidRevision("revision must be a non-empty string")
    if rev in _SYMBOLIC_REVS:
        return rev
    if not _REV_RE.match(rev):
        raise InvalidRevision(
            f"revision {rev!r} is not 4-40 hex characters or one of {sorted(_SYMBOLIC_REVS)}"
        )
    return rev.lower()


def validate_repo_path(path: str) -> str:
    """Normalise a repository-relative path to POSIX form, or raise.

    Rejects absolute paths, Windows drive-qualified paths, ``..`` traversal and
    NUL bytes. A trailing slash is preserved because it is how a directory
    anchor is written.
    """
    if not isinstance(path, str) or not path.strip():
        raise InvalidPath("path must be a non-empty string")
    if "\0" in path:
        raise InvalidPath("path contains a NUL byte")

    trailing_slash = path.endswith(("/", "\\"))
    normalised = path.replace("\\", "/")

    if normalised.startswith("/") or _WINDOWS_DRIVE_RE.match(normalised):
        raise InvalidPath(f"path {path!r} must be relative to the repository root")

    parts = [p for p in normalised.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise InvalidPath(f"path {path!r} must not traverse outside the repository")
    if not parts:
        raise InvalidPath(f"path {path!r} resolves to nothing")

    out = "/".join(parts)
    return out + "/" if trailing_slash else out


def git(repo: Path, *args: str, check: bool = True) -> str:
    """Run git in *repo* and return stdout as text.

    ``core.quotePath=false`` keeps non-ASCII paths readable instead of
    octal-escaped, so path comparisons downstream are byte-for-byte honest.
    """
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {' '.join(args)} failed ({completed.returncode}): {stderr}")
    return completed.stdout.decode("utf-8", "replace")


def _git_bytes(repo: Path, *args: str) -> bytes | None:
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def blob_at(repo: Path, rev: str, path: str) -> bytes | None:
    """Return the bytes of *path* at *rev*, or None if it does not exist there.

    Bytes, not text: the fingerprint must be computed over what git actually
    stores, before any encoding or line-ending translation.
    """
    rev = validate_rev(rev)
    path = validate_repo_path(path)
    return _git_bytes(repo, "show", f"{rev}:{path}")


def blobs_at(repo: Path, rev: str, paths: list[str]) -> dict[str, bytes | None]:
    """Read many blobs at *rev* in one git process.

    `blob_at` spawns `git show` per file, which is fine for the handful of
    anchors a drift scan reads and ruinous for a census. Measured: `forge sync
    derived` took **93 seconds** on a 635-file repository and under a second on
    a 95-file one - process creation, not work. Three artifacts each read every
    tracked file, so that is roughly 1,900 spawns.

    `git cat-file --batch` answers all of them down one pipe. A path that does
    not exist at *rev* comes back as `<name> missing`, and is reported as None
    rather than raising - the same contract `blob_at` has, because the callers
    that count files must not stop at the first deleted one.
    """
    rev = validate_rev(rev)
    wanted = [validate_repo_path(p) for p in paths]
    if not wanted:
        return {}

    request = "".join(f"{rev}:{p}\n" for p in wanted).encode("utf-8")
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(repo),
         "cat-file", "--batch"],
        input=request, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        # One bad path must not lose the other six hundred answers.
        return {p: blob_at(repo, rev, p) for p in wanted}

    out: dict[str, bytes | None] = {}
    data = completed.stdout
    offset = 0
    for path in wanted:
        end = data.find(b"\n", offset)
        if end < 0:
            out[path] = None
            continue
        header = data[offset:end].decode("utf-8", "replace").split()
        offset = end + 1
        if len(header) < 3 or header[1] != "blob":
            # "missing", or a tree where a file was expected.
            out[path] = None
            continue
        size = int(header[2])
        out[path] = data[offset:offset + size]
        # Each blob is followed by a newline git adds itself.
        offset += size + 1
    return out


def exists_at(repo: Path, rev: str, path: str) -> bool:
    """True if *path* exists at *rev* (as a blob or a tree)."""
    rev = validate_rev(rev)
    path = validate_repo_path(path).rstrip("/")
    completed = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{rev}:{path}"],
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def tree_hash_at(repo: Path, rev: str, dirpath: str) -> str | None:
    """Return the tree object id of a directory at *rev*, or None.

    A directory anchor fingerprints the tree hash: it changes when anything
    beneath it changes, which is the correct (coarse) semantics for a claim
    anchored to a whole component.
    """
    rev = validate_rev(rev)
    dirpath = validate_repo_path(dirpath).rstrip("/")
    out = _git_bytes(repo, "rev-parse", f"{rev}:{dirpath}")
    if out is None:
        return None
    return out.decode().strip() or None


def rev_parse(repo: Path, rev: str) -> str:
    """Resolve *rev* to a full object id."""
    return git(repo, "rev-parse", validate_rev(rev)).strip()


def rev_list(repo: Path, *, head: str = "HEAD", count: int | None = None,
             reverse: bool = True, first_parent: bool = True) -> list[str]:
    """List commit ids ending at *head*, oldest first by default.

    ``first_parent`` keeps the walk on the mainline. Without it, a replay over
    a merge-heavy history revisits side-branch commits and the per-commit
    counts stop meaning "one step of the project's history".
    """
    args = ["rev-list"]
    if first_parent:
        args.append("--first-parent")
    if count is not None:
        args.append(f"-n{int(count)}")
    args.append(validate_rev(head))
    out = git(repo, *args).split()
    return list(reversed(out)) if reverse else out


def rename_map(repo: Path, base: str, head: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return (old->new, new->old) rename maps between two revisions.

    This is what makes an anchor survive a file move. ``--find-renames`` is
    git's own similarity detection, so a pure move is recognised without the
    harness having to reason about it.
    """
    base = validate_rev(base)
    head = validate_rev(head)
    out = git(
        repo, "diff", "--find-renames", "--name-status", "--diff-filter=R",
        base, head, check=False,
    )
    forward: dict[str, str] = {}
    backward: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].startswith("R"):
            continue
        _status, old, new = parts
        forward[old] = new
        backward[new] = old
    return forward, backward


def resolve_path_at(repo: Path, path: str, *, target_rev: str, other_rev: str) -> tuple[str | None, str | None]:
    """Locate *path* at *target_rev*, following renames between the two revisions.

    *path* is expressed as it exists at *other_rev*. Returns
    ``(path_at_target, path_at_other)`` where the second element is filled in
    only when a rename was followed, else None. ``(None, None)`` means the file
    genuinely is not present at *target_rev* under any followed name.
    """
    path = validate_repo_path(path).rstrip("/")
    if exists_at(repo, target_rev, path):
        return path, None

    target_full = rev_parse(repo, target_rev)
    other_full = rev_parse(repo, other_rev)

    # Direction matters: git records renames old->new walking forwards in time,
    # so pick the map that answers "what is this file called at the target".
    if _is_ancestor(repo, target_full, other_full):
        # Target is the older commit: we hold the new name and want the old one.
        _forward, backward = rename_map(repo, target_full, other_full)
        candidate = backward.get(path)
    else:
        # Target is the newer commit: we hold the old name and want the new one.
        forward, _backward = rename_map(repo, other_full, target_full)
        candidate = forward.get(path)

    if candidate and exists_at(repo, target_rev, candidate):
        return candidate, path
    return None, None


def _is_ancestor(repo: Path, maybe_ancestor: str, rev: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor",
         validate_rev(maybe_ancestor), validate_rev(rev)],
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def list_files_at(repo: Path, rev: str) -> list[str]:
    """Every tracked path at *rev*, POSIX-separated."""
    out = git(repo, "ls-tree", "-r", "--name-only", validate_rev(rev))
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_files(repo: Path, base: str, *, head: str | None = None) -> list[str]:
    """Paths that differ between *base* and the working tree (or *head*).

    The working tree is included by default, and that is the point: `forge
    impact` runs *while* a change is being written, so a diff that only saw
    commits would report the blast radius of the last commit rather than of
    the work in hand. Untracked files count too - a new module nobody has
    added yet is exactly the kind of thing a component boundary claim is
    about.
    """
    base = validate_rev(base)
    paths: set[str] = set()

    if head is not None:
        out = git(repo, "diff", "--name-only", "--find-renames",
                  base, validate_rev(head), check=False)
    else:
        out = git(repo, "diff", "--name-only", "--find-renames", base, check=False)
    paths.update(line.strip() for line in out.splitlines() if line.strip())

    if head is None:
        untracked = git(repo, "ls-files", "--others", "--exclude-standard", check=False)
        paths.update(line.strip() for line in untracked.splitlines() if line.strip())

    return sorted(paths)


def first_commit_touching(repo: Path, path: str) -> str | None:
    """The commit that introduced *path*, or None if it is not committed yet."""
    out = git(repo, "log", "--diff-filter=A", "--format=%H", "--follow",
              "--", validate_repo_path(path), check=False)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[-1] if lines else None


def parent_of(repo: Path, rev: str) -> str | None:
    out = git(repo, "rev-parse", "--verify", f"{validate_rev(rev)}^", check=False).strip()
    return out or None


def grep_files_at(repo: Path, rev: str, needle: str) -> list[str]:
    """Paths at *rev* containing *needle* as a whole word.

    Used to narrow the search when a file has moved and git's rename detection
    missed it. ``-e`` and ``--`` keep a needle that begins with a dash from
    being read as an option, and the caller has already validated it as an
    identifier - two layers, because this is the one place a stored value picks
    the files we then parse.
    """
    if not needle:
        return []
    out = git(
        repo, "grep", "--files-with-matches", "--fixed-strings", "--word-regexp",
        "-e", needle, validate_rev(rev), "--",
        check=False,
    )
    paths = []
    for line in out.splitlines():
        # `git grep <rev>` prefixes each path with "<rev>:".
        _, _, path = line.partition(":")
        if path.strip():
            paths.append(path.strip())
    return paths


def diff_is_whitespace_only(repo: Path, base: str, head: str, path: str) -> bool:
    """True if *path* differs between the revisions only by whitespace.

    Ground truth for the M1 measurement: any anchor on such a file that reports
    stale is a false positive by construction, because a reviewer would have
    nothing to look at.
    """
    base = validate_rev(base)
    head = validate_rev(head)
    path = validate_repo_path(path)

    raw = git(repo, "diff", "--numstat", base, head, "--", path, check=False).strip()
    if not raw:
        return False  # no textual difference at all; not a whitespace-only change
    ignoring = git(
        repo, "diff", "--ignore-all-space", "--ignore-blank-lines",
        "--numstat", base, head, "--", path, check=False,
    ).strip()
    return ignoring == ""


_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


def changed_line_ranges(repo: Path, base: str, path: str,
                        *, head: str | None = None) -> list[tuple[int, int]]:
    """Inclusive 1-based line ranges of *path* that differ from *base*.

    Line numbers are in the **head** file, because every caller asks the same
    question - which of the things currently written here did this change
    touch - and that question is about the file as it stands now.

    An untracked or newly added file has no baseline to diff against, so the
    whole file is reported changed: ``[(1, <line count>)]``. Returning nothing
    there would quietly answer "you changed none of it".

    A pure deletion hunk (``@@ -10,3 +9,0 @@``) records a count of zero. It is
    reported as the single line it collapsed to, so that a claim whose body was
    deleted still intersects something; dropping zero-width hunks would make
    "the diff removed this claim's definition" invisible.
    """
    base = validate_rev(base)
    path = validate_repo_path(path)

    args = ["diff", "-U0", "--no-color", "--find-renames", base]
    if head is not None:
        args.append(validate_rev(head))
    out = git(repo, *args, "--", path, check=False)

    ranges: list[tuple[int, int]] = []
    for line in out.splitlines():
        match = _HUNK_RE.match(line)
        if not match:
            continue
        start = int(match.group("start"))
        count = int(match.group("count") or 1)
        ranges.append((start, start + count - 1) if count else (start, start))

    if not ranges and not exists_at(repo, base, path):
        target = repo / path
        if target.is_file():
            total = target.read_bytes().count(b"\n") + 1
            return [(1, total)]
    return ranges


def is_repo(path: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True, check=False,
    )
    return completed.returncode == 0

