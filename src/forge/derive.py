"""The derived tier: facts regenerated from the repository, never authored.

The store's rule is "store judgements, derive facts" (CONSTITUTION.md IV). This
module is the deriving half. Everything it writes is reproducible from the
repository at a commit, carries the commit it was produced from, and is
committed so its diffs are visible in review.

**No timestamp.** SYSTEM_KNOWLEDGE.md section 2.3 sketched the envelope with a
``generated_at`` field, which cannot coexist with the requirement two paragraphs
later that regeneration be a no-op and that ``forge check`` fail on a dirty
derived file: a timestamp makes every regeneration differ, so the dirty check
could never pass. The commit id is the provenance that matters - it is what the
staleness signal compares - and the wall clock adds nothing a git log does not
already have. The design document has been corrected to match.

Determinism is a hard requirement, not an aspiration: every mapping is written
with sorted keys, every list is sorted, and no value is derived from the
environment (no paths outside the repo, no locale, no clock).
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import gitio
from .config import Config, load_config
from .fingerprint import language_for_path

__all__ = [
    "SCHEMA",
    "DERIVED_DIR",
    "envelope",
    "write_json",
    "render_json",
    "read_json",
    "build_inventory",
    "build_tests",
    "build_backrefs",
    "build_deps",
    "label_for_path",
    "derive_all",
    "stale_artifacts",
]

SCHEMA = "forge/derived/v1"
DERIVED_DIR = "docs/system/derived"

# Directories whose contents say nothing about the code a human maintains.
_IGNORED_SEGMENTS = frozenset({
    "node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__",
    "third_party", ".git", "site-packages", "coverage", ".next", "target",
})

# Build metadata that some projects commit. Matched by suffix rather than by
# exact name because the directory carries the distribution's name.
_IGNORED_SUFFIXES = (".egg-info", ".dist-info")

_TEST_PATTERNS = (
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"[^/]+_test\.(py|go)$"),
    re.compile(r"[^/]+\.(test|spec)\.[jt]sx?$"),
)

# `@covers ID [ID ...]` in a test name or an adjacent comment. The single
# convention that makes requirement-to-test traceability a grep instead of an
# inference (SYSTEM_KNOWLEDGE.md section 8.2).
_COVERS_RE = re.compile(r"@covers\s+((?:[A-Z]{2,4}-[A-Za-z0-9_-]+[ \t,]*)+)")
_ID_RE = re.compile(r"[A-Z]{2,4}-[A-Za-z0-9_-]+")

# `forge:<ID>` back-references, in code comments and in conformance rule files.
_BACKREF_RE = re.compile(r"forge:([A-Z]{2,4}-[A-Za-z0-9_-]+)")

# Test declarations, per language. Deliberately regex rather than a parse: a
# test name is a string or an identifier, and the shapes are few.
_TEST_DECL_RES = {
    "python": [re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]*)\s*\(", re.M)],
    "go": [re.compile(r"^\s*func\s+((?:Test|Benchmark|Fuzz|Example)[A-Za-z0-9_]*)\s*\(", re.M)],
    "typescript": [
        re.compile(r"""^\s*(?:it|test)\s*(?:\.\w+)?\s*\(\s*['"`](.+?)['"`]""", re.M),
    ],
}
_TEST_DECL_RES["tsx"] = _TEST_DECL_RES["typescript"]

# Labels for files the grammars do not cover, so the inventory reads as a
# description of the repository rather than a pile of "other". These are
# labels, not claims of parseability - only `language_for_path` decides whether
# an anchor gets an AST fingerprint.
_NON_CODE_LABELS = {
    ".md": "markdown", ".markdown": "markdown", ".json": "json",
    ".toml": "toml", ".yaml": "yaml", ".yml": "yaml", ".txt": "text",
    ".sh": "shell", ".bash": "shell", ".ps1": "powershell", ".sql": "sql",
    ".css": "css", ".html": "html", ".rs": "rust", ".java": "java",
    ".rb": "ruby", ".c": "c", ".h": "c", ".cpp": "cpp", ".cs": "csharp",
    ".lock": "lockfile", ".cfg": "config", ".ini": "config",
}


def label_for_path(path: str) -> str:
    """A grammar name where we have one, else a readable file-type label."""
    language = language_for_path(path)
    if language:
        return language
    lowered = path.lower()
    for extension, label in _NON_CODE_LABELS.items():
        if lowered.endswith(extension):
            return label
    if "/" not in lowered and "." not in lowered:
        return "script"
    return "other"


def is_generated(path: str) -> bool:
    """Files the harness itself writes.

    Kept apart from `is_ignored` because it is excluded from *both* halves of
    the census - the raw tracked count as well as the described set. A file the
    harness produces moves whichever number counts it, so committing it makes
    the tier stale, which rewrites it, which is another commit. The derived
    tier has been excluded on this ground since M2; `verification.json` was
    found the long way, when `derived_fresh` failed inside the very report that
    had just written the file.
    """
    return (path.startswith(f"{DERIVED_DIR}/")
            or (path.startswith("changes/") and path.endswith("/verification.json")))


def is_ignored(path: str, config: Config | None = None) -> bool:
    """Paths the derived tier does not describe.

    Four reasons a path is skipped: it is vendored or built, it belongs to the
    tier itself, the harness generated it, or the project excluded it.

    The tier excludes *itself* because counting its own JSON is circular - the
    inventory would describe the describer. The project exclusions exist for
    repositories whose files contain IDs that are data rather than declarations;
    this repository is the extreme case, since its test fixtures are made of
    exactly the strings the scanner looks for.

    `verification.json` is here for the same circularity, found the long way.
    `forge verify` writes it; it is tracked JSON, so its line count moved the
    census; so committing it made the inventory stale; so `derived_fresh`
    failed - **in the report that had just written the file**. Reaching a
    passing verdict took verify, sync, commit, verify again, and nothing said
    so. A census that counts what the harness produces is not stable under the
    harness running, which is `PIT-derived-self-reference` wearing a different
    hat. The change's authored artifacts - proposal, spec, impact, design,
    tasks - are somebody's writing and still count.
    """
    if is_generated(path):
        return True
    segments = path.split("/")
    if any(segment in _IGNORED_SEGMENTS for segment in segments):
        return True
    if any(segment.endswith(_IGNORED_SUFFIXES) for segment in segments[:-1]):
        return True
    return bool(config and config.excludes(path))


def is_test_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in _TEST_PATTERNS)


def envelope(repo: Path, generator: str, tool: str, data: object) -> dict:
    """Wrap derived data with its provenance.

    ``generated_from_commit`` is the whole staleness story for this tier: the
    artifact is stale exactly when it differs from HEAD, reported as
    ``commits_behind``. Never a time threshold - GSD used 24 hours for its
    intel store and replaced it with commit-based staleness later, which reads
    as an admission that the clock was the wrong clock.
    """
    return {
        "$schema": SCHEMA,
        "generated_from_commit": gitio.rev_parse(repo, "HEAD"),
        "generator": generator,
        "tool": tool,
        "data": data,
    }


def render_json(payload: dict) -> bytes:
    """Serialise deterministically.

    ``sort_keys`` plus a trailing newline plus explicit LF: the same inputs must
    produce the same bytes on every platform, or the dirty check is noise rather
    than a signal. Written in binary mode for the same reason - Python's text
    mode would translate newlines on Windows.
    """
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def write_json(path: Path, payload: dict, *, dry_run: bool = False) -> bool:
    """Write *payload* if its **data** differs from what is on disk.

    ``dry_run`` answers "would this change anything?" without touching the
    working tree, which is what `forge check` needs: a check that has to write
    in order to report the tree clean is not a check.

    Only ``data`` is compared, never the envelope, and that is what breaks the
    treadmill. The envelope stamps HEAD; committing the file moves HEAD; so a
    whole-payload comparison would report the file dirty immediately after it
    was written, forever, and no amount of regenerating could settle it. A file
    cannot carry the id of the commit that contains it.

    So the split is: **content is the truth, the stamp is provenance.** When the
    content still describes the repository the file is left alone, keeping the
    id of the commit it was genuinely derived from - which is more honest than
    restamping it with a commit whose contents it was never shown.
    """
    encoded = render_json(payload)
    if path.exists():
        existing = read_json(path)
        if existing is not None and existing.get("data") == payload.get("data"):
            return False
        if path.read_bytes() == encoded:
            return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(encoded)
    return True


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------
# inventory.json
# --------------------------------------------------------------------------

def _read_stack(repo: Path, tracked: list[str]) -> dict:
    """Declared dependencies, from the manifests we can read without guessing.

    Resolved versions come from a lockfile where one is both present and cheap
    to parse; otherwise the declared range is recorded and labelled as such.
    Overstating this would be the exact failure the derived tier exists to
    avoid - a stored fact that is not quite true.
    """
    stack: dict[str, dict] = {}

    if "package.json" in tracked:
        manifest = read_json(repo / "package.json") or {}
        declared = {}
        for section in ("dependencies", "devDependencies"):
            declared.update(manifest.get(section) or {})
        resolved = {}
        lock = read_json(repo / "package-lock.json")
        if lock:
            for name, entry in (lock.get("packages") or {}).items():
                short = name.rsplit("node_modules/", 1)[-1]
                if short and isinstance(entry, dict) and entry.get("version"):
                    resolved[short] = entry["version"]
        if declared:
            stack["npm"] = {
                "manifest": "package.json",
                "lockfile": "package-lock.json" if lock else None,
                "packages": {
                    name: {
                        "declared": spec,
                        "resolved": resolved.get(name),
                    }
                    for name, spec in sorted(declared.items())
                },
            }

    if "pyproject.toml" in tracked:
        try:
            data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        declared = list((data.get("project") or {}).get("dependencies") or [])
        if declared:
            stack["python"] = {
                "manifest": "pyproject.toml",
                "lockfile": None,
                "requires_python": (data.get("project") or {}).get("requires-python"),
                "packages": {
                    # A requirement string is name + constraint; split on the
                    # first constraint character rather than parsing PEP 508,
                    # which would be a dependency for very little gain.
                    re.split(r"[<>=!~\[; ]", spec, maxsplit=1)[0]: {
                        "declared": spec, "resolved": None,
                    }
                    for spec in sorted(declared)
                },
            }

    if "go.mod" in tracked:
        text = (repo / "go.mod").read_text(encoding="utf-8", errors="replace")
        module = re.search(r"^module\s+(\S+)", text, re.M)
        requires = dict(re.findall(r"^\s*([\w./~-]+\.[\w./~-]+)\s+(v\S+)", text, re.M))
        stack["go"] = {
            "manifest": "go.mod",
            "lockfile": "go.sum" if "go.sum" in tracked else None,
            "module": module.group(1) if module else None,
            "packages": {
                name: {"declared": version, "resolved": version}
                for name, version in sorted(requires.items())
            },
        }

    return stack


def _entry_points(repo: Path, tracked: list[str]) -> list[str]:
    """Entry points a manifest actually names. Never inferred."""
    found: set[str] = set()

    if "package.json" in tracked:
        manifest = read_json(repo / "package.json") or {}
        for key in ("main", "module", "types"):
            value = manifest.get(key)
            if isinstance(value, str):
                found.add(value.lstrip("./"))
        bin_field = manifest.get("bin")
        if isinstance(bin_field, str):
            found.add(bin_field.lstrip("./"))
        elif isinstance(bin_field, dict):
            found.update(str(v).lstrip("./") for v in bin_field.values())

    if "pyproject.toml" in tracked:
        try:
            data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        for target in ((data.get("project") or {}).get("scripts") or {}).values():
            # A console script names `module.path:function`, not a file. Resolve
            # it to the file so every entry point in this list is a path, which
            # is what a consumer of the inventory can act on.
            module = str(target).split(":", 1)[0].replace(".", "/")
            for candidate in (f"src/{module}.py", f"{module}.py",
                              f"src/{module}/__init__.py", f"{module}/__init__.py"):
                if candidate in tracked:
                    found.add(candidate)
                    break
            else:
                found.add(str(target))

    for path in tracked:
        if path.endswith("main.go") and not is_ignored(path):
            found.add(path)

    return sorted(found)


def build_inventory(repo: Path) -> dict:
    """Languages, line counts, tests, entry points and declared stack.

    ``files_tracked`` counts what git tracks *minus the derived tier itself*,
    for the same reason `is_ignored` skips that directory: a census that counts
    its own output is not stable under its own commit. Committing four freshly
    written JSON files would move the count, which would make the inventory
    stale, which would rewrite it, which would be another commit. The pair to
    read is "we can see N files and we describe M of them" - neither number is
    about the describer.
    """
    config = load_config(repo)
    tracked = [p for p in gitio.list_files_at(repo, "HEAD") if not is_generated(p)]
    interesting = [p for p in tracked if not is_ignored(p, config)]

    by_language: dict[str, dict] = {}
    tests: list[str] = []
    for path in interesting:
        language = label_for_path(path)
        blob = gitio.blob_at(repo, "HEAD", path)
        lines = blob.count(b"\n") + (1 if blob and not blob.endswith(b"\n") else 0) if blob else 0
        bucket = by_language.setdefault(language, {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += lines
        if is_test_path(path):
            tests.append(path)

    return {
        "files_tracked": len(tracked),
        "files_considered": len(interesting),
        "by_language": {k: by_language[k] for k in sorted(by_language)},
        "entry_points": _entry_points(repo, tracked),
        "test_files": sorted(tests),
        "stack": _read_stack(repo, tracked),
    }


# --------------------------------------------------------------------------
# tests.json
# --------------------------------------------------------------------------

def _covers_in(text: str) -> list[str]:
    ids: set[str] = set()
    for match in _COVERS_RE.finditer(text):
        ids.update(_ID_RE.findall(match.group(1)))
    return sorted(ids)


def build_tests(repo: Path) -> dict:
    """Test files, the tests they declare, and the IDs each one covers.

    A test is bound to a requirement or an invariant by an ``@covers`` tag in
    its name or on an adjacent line. Association is by proximity - the nearest
    preceding or same-line tag - which is a convention, not a parse, and is
    reported per file so a miss is visible rather than silent.
    """
    config = load_config(repo)
    files: dict[str, dict] = {}
    by_id: dict[str, list[str]] = {}

    for path in gitio.list_files_at(repo, "HEAD"):
        if is_ignored(path, config) or not is_test_path(path):
            continue
        # Excluded files are still counted and their tests still listed; only
        # the `@covers` harvest is skipped. Dropping them entirely would cost a
        # project its own test statistics in order to silence a few fixtures.
        harvest_ids = not config.excludes_id_scan(path)
        language = language_for_path(path)
        if language is None:
            continue
        blob = gitio.blob_at(repo, "HEAD", path)
        if blob is None:
            continue
        text = blob.decode("utf-8", "replace")
        lines = text.split("\n")

        # Tag positions first, so each declaration can look backwards for the
        # nearest one that is not already claimed by a closer declaration.
        tags: dict[int, list[str]] = {}
        if harvest_ids:
            for index, line in enumerate(lines):
                covered = _covers_in(line)
                if covered:
                    tags[index] = covered

        declarations: list[dict] = []
        for pattern in _TEST_DECL_RES.get(language, []):
            for match in pattern.finditer(text):
                line_index = text.count("\n", 0, match.start())
                declarations.append({"name": match.group(1), "line": line_index + 1})
        declarations.sort(key=lambda d: d["line"])

        for position, declaration in enumerate(declarations):
            index = declaration["line"] - 1
            previous_line = declarations[position - 1]["line"] - 1 if position else -1
            covered: list[str] = list(tags.get(index, []))
            # Walk backwards to the previous declaration, no further.
            cursor = index - 1
            while cursor > previous_line and not covered:
                covered = list(tags.get(cursor, []))
                cursor -= 1
            declaration["covers"] = sorted(covered)
            for identifier in declaration["covers"]:
                by_id.setdefault(identifier, []).append(f"{path}::{declaration['name']}")

        if declarations:
            files[path] = {
                "language": language,
                "tests": declarations,
                "untagged": sum(1 for d in declarations if not d["covers"]),
            }

    return {
        "files": {k: files[k] for k in sorted(files)},
        "total_tests": sum(len(f["tests"]) for f in files.values()),
        "tagged_tests": sum(
            1 for f in files.values() for t in f["tests"] if t["covers"]
        ),
        "covers_index": {k: sorted(set(by_id[k])) for k in sorted(by_id)},
    }


# --------------------------------------------------------------------------
# Back-references from code
# --------------------------------------------------------------------------

# Back-references bind an *enforcement artifact* to a claim, so prose is
# excluded from the scan. Without this, a design document that demonstrates the
# convention - a tag written inside an example rule, or a literal grep command
# showing how to find one - creates index entries for claims that were never
# meant to exist, and they surface as dangling references. Citing an ID in prose
# is normal; only code and rule files declare that they enforce one.
#
# The same trap catches this comment: naming a real-looking ID here would make
# the module a back-reference to a claim it does not enforce. Hence the
# placeholders.
_PROSE_LABELS = frozenset({"markdown", "text", "other"})


def build_backrefs(repo: Path) -> dict:
    """`forge:<ID>` mentions in code and rule files, grouped by ID.

    This is the reverse half of traceability: a claim says which rule enforces
    it, and the rule says which claim it serves. Both directions are checked,
    so a rule tagged for a claim that does not exist is an error rather than a
    stale comment nobody notices.
    """
    config = load_config(repo)
    by_id: dict[str, list[str]] = {}
    for path in gitio.list_files_at(repo, "HEAD"):
        if is_ignored(path, config) or config.excludes_id_scan(path):
            continue
        if label_for_path(path) in _PROSE_LABELS:
            continue
        blob = gitio.blob_at(repo, "HEAD", path)
        if blob is None or b"forge:" not in blob:
            continue
        text = blob.decode("utf-8", "replace")
        for index, line in enumerate(text.split("\n")):
            for identifier in _BACKREF_RE.findall(line):
                by_id.setdefault(identifier, []).append(f"{path}:{index + 1}")
    return {"by_id": {k: sorted(set(by_id[k])) for k in sorted(by_id)}}


# --------------------------------------------------------------------------
# deps.json - the module graph
# --------------------------------------------------------------------------

# Imports are a line-shaped construct in all three MVP languages, so this is a
# regex scan rather than a parse, for the same reason the test-declaration
# scan is (see `_TEST_DECL_RES`): the shapes are few and the cost of a parse
# tree per file is not repaid.
#
# **Deviation from MVP.md M2**, which specified "by shelling out to the
# project's configured dep tool". Rejected: it makes the blast radius - and
# therefore the claim-touch set, and therefore the harness's central
# enforcement - depend on whether `depcruise` happens to be installed. A check
# that silently weakens when a tool is missing is worse than a narrower check
# that always runs. `derive.dep_tool` stays in the config shape for a project
# whose graph this scan cannot see; when it is used, the tier records which
# produced the file.
_PYTHON_FROM_RE = re.compile(r"^[ \t]*from\s+([.\w]+)\s+import\s+(?P<names>[^\n#]+)", re.M)
_PYTHON_IMPORT_RE = re.compile(r"^[ \t]*import\s+([.\w]+)", re.M)
_PYTHON_NAME_RE = re.compile(r"\b([A-Za-z_]\w*)")

_IMPORT_RES = {
    "typescript": [
        re.compile(r"""^\s*import\s[^'"]*['"]([^'"]+)['"]""", re.M),
        re.compile(r"""^\s*export\s[^'"]*from\s*['"]([^'"]+)['"]""", re.M),
        re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)"""),
    ],
    "go": [re.compile(r"""^\s*(?:[\w.]+\s+)?"([^"]+)"\s*$""", re.M)],
}
_IMPORT_RES["tsx"] = _IMPORT_RES["typescript"]

_TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _python_targets(module: str, source: str, index: set[str]) -> str | None:
    """Resolve a Python import to a tracked file, or None if it leaves the repo.

    A relative import (`from .store import Claim`) resolves against the
    importing file's package; an absolute one against every source root we can
    see, because `src/` layouts are normal and the repository is not on
    `sys.path`.
    """
    parts = module.lstrip(".")
    dots = len(module) - len(parts)
    if dots:
        base = source.rsplit("/", 1)[0] if "/" in source else ""
        for _ in range(dots - 1):
            base = base.rsplit("/", 1)[0] if "/" in base else ""
        stem = "/".join(p for p in (base, parts.replace(".", "/")) if p)
        candidates = [stem]
    else:
        stem = parts.replace(".", "/")
        candidates = [stem]
        root = source.split("/", 1)[0]
        if root and root != stem.split("/", 1)[0]:
            candidates.append(f"{root}/{stem}")

    for candidate in candidates:
        for suffix in (".py", "/__init__.py"):
            if (target := f"{candidate}{suffix}") in index:
                return target
    return None


def _python_edges(text: str, source: str, index: set[str]) -> set[str]:
    """Every in-repository file this module imports.

    `from . import gitio, store` is the case worth spelling out: resolving only
    the `.` would make the edge point at `__init__.py` and lose both real
    dependencies. Since a name in a `from X import a, b` list may be either a
    submodule or an attribute, each is tried as a submodule and kept only if a
    file answers - an attribute simply does not resolve, so nothing is invented.
    """
    targets: set[str] = set()
    for match in _PYTHON_FROM_RE.finditer(text):
        module = match.group(1)
        if (direct := _python_targets(module, source, index)):
            targets.add(direct)
        for name in _PYTHON_NAME_RE.findall(match.group("names")):
            if name in ("import", "as"):
                continue
            separator = "" if module.endswith(".") else "."
            submodule = _python_targets(f"{module}{separator}{name}", source, index)
            if submodule:
                targets.add(submodule)
    for match in _PYTHON_IMPORT_RE.finditer(text):
        if (direct := _python_targets(match.group(1), source, index)):
            targets.add(direct)
    return targets


def _relative_targets(specifier: str, source: str, index: set[str]) -> str | None:
    """Resolve a TypeScript/JavaScript specifier. Package imports are skipped:
    the graph is about *this* repository's coupling, and `react` is a fact of
    the lockfile that `inventory.json` already reports."""
    if not specifier.startswith("."):
        return None
    base = source.rsplit("/", 1)[0] if "/" in source else ""
    stem = f"{base}/{specifier}" if base else specifier
    parts: list[str] = []
    for part in stem.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    stem = "/".join(parts)
    for candidate in (stem, *(f"{stem}{ext}" for ext in _TS_EXTENSIONS),
                      *(f"{stem}/index{ext}" for ext in _TS_EXTENSIONS)):
        if candidate in index:
            return candidate
    return None


def _go_targets(specifier: str, module_path: str | None, index: set[str]) -> str | None:
    if module_path and specifier.startswith(module_path):
        directory = specifier[len(module_path):].strip("/")
    elif "/" not in specifier and specifier in {p.split("/", 1)[0] for p in index}:
        directory = specifier
    else:
        return None
    return directory or None


def _go_module_path(repo: Path, tracked: list[str]) -> str | None:
    if "go.mod" not in tracked:
        return None
    blob = gitio.blob_at(repo, "HEAD", "go.mod")
    if blob is None:
        return None
    match = re.search(r"^\s*module\s+(\S+)", blob.decode("utf-8", "replace"), re.M)
    return match.group(1) if match else None


def build_deps(repo: Path) -> dict:
    """File-to-file import edges within the repository, and the cycles in them.

    Edges are between *files*, not modules: the claim-touch rule asks "which
    files does this diff reach", and a module-level graph would have to be
    mapped back to files to answer it. Imports that leave the repository are
    dropped - the graph is about this repository's own coupling.
    """
    config = load_config(repo)
    tracked = gitio.list_files_at(repo, "HEAD")
    index = {p for p in tracked if not is_ignored(p, config)}
    go_module = _go_module_path(repo, tracked)
    go_dirs = {p.rsplit("/", 1)[0] if "/" in p else "" for p in index if p.endswith(".go")}

    edges: dict[str, set[str]] = {}
    unresolved = 0
    for path in sorted(index):
        language = language_for_path(path)
        if language not in ("python", "go", "typescript", "tsx"):
            continue
        blob = gitio.blob_at(repo, "HEAD", path)
        if blob is None:
            continue
        text = blob.decode("utf-8", "replace")
        found: set[str] = set()

        if language == "python":
            found |= _python_edges(text, path, index)
        elif language == "go":
            for pattern in _IMPORT_RES["go"]:
                for specifier in pattern.findall(text):
                    directory = _go_targets(specifier, go_module, index)
                    if directory is None or directory not in go_dirs:
                        continue
                    # A Go import names a package directory; the edge goes to
                    # every file in it, since the importer cannot say which
                    # one it meant.
                    found |= {c for c in index if c.endswith(".go")
                              and c.rsplit("/", 1)[0] == directory}
        else:
            for pattern in _IMPORT_RES["typescript"]:
                for specifier in pattern.findall(text):
                    target = _relative_targets(specifier, path, index)
                    if target:
                        found.add(target)
                    elif specifier.startswith("."):
                        unresolved += 1

        found.discard(path)
        if found:
            edges.setdefault(path, set()).update(found)

    reverse: dict[str, set[str]] = {}
    for source, targets in edges.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)

    return {
        "tool": "forge",
        "edges": {k: sorted(edges[k]) for k in sorted(edges)},
        "reverse": {k: sorted(reverse[k]) for k in sorted(reverse)},
        "cycles": _import_cycles(edges),
        "files_with_imports": len(edges),
        "unresolved_relative_imports": unresolved,
    }


def _import_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    """Every import cycle, each reported once, rotated to a stable start.

    Rotation matters more than it sounds: without it the same cycle is written
    starting from whichever file the walk happened to reach first, and the
    derived file stops being byte-identical between runs on different
    filesystems.
    """
    colour: dict[str, int] = {}
    path: list[str] = []
    on_path: set[str] = set()
    found: dict[frozenset[str], list[str]] = {}

    def walk(node: str) -> None:
        colour[node] = 1
        path.append(node)
        on_path.add(node)
        for target in sorted(edges.get(node, ())):
            if target in on_path:
                cycle = path[path.index(target):]
                start = cycle.index(min(cycle))
                found.setdefault(frozenset(cycle), cycle[start:] + cycle[:start])
            elif not colour.get(target):
                walk(target)
        path.pop()
        on_path.discard(node)
        colour[node] = 2

    import sys as _sys
    limit = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(limit, 10000))
    try:
        for node in sorted(edges):
            if not colour.get(node):
                walk(node)
    finally:
        _sys.setrecursionlimit(limit)
    return [found[key] for key in sorted(found, key=lambda k: sorted(k))]


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

@dataclass
class DerivedArtifact:
    name: str
    generator: str
    tool: str
    build: object  # Callable[[Path], object]


def _build_trace(repo: Path) -> object:
    # Imported late: trace reads the artifacts this module writes, so a
    # module-level import would be a cycle.
    from .trace import build_trace

    return build_trace(repo)


# Order matters: trace.json is computed from tests.json and backrefs.json as
# they exist on disk, so it is regenerated after them.
ARTIFACTS = [
    DerivedArtifact("inventory.json", "forge sync derived", "forge", build_inventory),
    DerivedArtifact("deps.json", "forge sync derived", "forge", build_deps),
    DerivedArtifact("tests.json", "forge sync derived", "forge", build_tests),
    DerivedArtifact("backrefs.json", "forge sync derived", "forge", build_backrefs),
    DerivedArtifact("trace.json", "forge sync derived", "forge", _build_trace),
]


def derive_all(
    repo: Path, *, only: list[str] | None = None, dry_run: bool = False
) -> dict[str, bool]:
    """Regenerate the derived tier. Returns name -> would-change."""
    directory = repo / DERIVED_DIR
    changed: dict[str, bool] = {}
    for artifact in ARTIFACTS:
        if only and artifact.name not in only:
            continue
        payload = envelope(
            repo, artifact.generator, artifact.tool, artifact.build(repo)
        )
        changed[artifact.name] = write_json(
            directory / artifact.name, payload, dry_run=dry_run
        )
    return changed


def stale_artifacts(repo: Path) -> dict[str, int | None]:
    """How many *relevant* commits behind HEAD each derived artifact is.

    None means the artifact is absent or unreadable. Commit-based, never
    time-based: a file written a minute ago against an old commit is stale, and
    one written last month against HEAD is not.

    **Commits that touched only the derived tier do not count.** A file cannot
    contain the id of the commit that contains it, so committing a freshly
    derived artifact necessarily leaves it stamped with its parent. Counting
    that as staleness would make the steady state permanently one commit behind,
    and regenerating to fix it would produce another such commit - a treadmill.
    The honest reading is that a commit which only rewrites derived data does
    not make derived data stale, and the pathspec below says exactly that.
    """
    head = gitio.rev_parse(repo, "HEAD")
    out: dict[str, int | None] = {}
    for artifact in ARTIFACTS:
        payload = read_json(repo / DERIVED_DIR / artifact.name)
        if not payload or "generated_from_commit" not in payload:
            out[artifact.name] = None
            continue
        origin = payload["generated_from_commit"]
        if origin == head:
            out[artifact.name] = 0
            continue
        try:
            count = gitio.git(
                repo, "rev-list", "--count",
                f"{gitio.validate_rev(origin)}..{head}",
                "--", ".", f":(exclude){DERIVED_DIR}",
            ).strip()
            out[artifact.name] = int(count)
        except (gitio.GitError, gitio.InvalidRevision, ValueError):
            out[artifact.name] = None
    return out
