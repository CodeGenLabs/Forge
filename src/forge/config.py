"""Project configuration: one file, defaults when it is absent.

`.forge/config.yaml` is the seam where a project adapts the harness without
forking anything (ARCHITECTURE.md section 3.3). The kernel must work with no
config at all, so every value has a default and a malformed file degrades to
those defaults with a warning rather than refusing to run - a tool that cannot
start because its optional configuration has a typo is worse than one that
starts with defaults and says so.

Only the keys the current milestones use are read. The rest of the shape in
ARCHITECTURE.md arrives with the milestone that needs it.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml

__all__ = ["Config", "load_config", "CONFIG_PATH"]

CONFIG_PATH = ".forge/config.yaml"


@dataclass
class Config:
    #: Globs excluded from everything, on top of the built-in vendor and build
    #: exclusions. Use for code the project does not own.
    exclude: list[str] = field(default_factory=list)
    #: Globs whose ID-looking strings are data rather than declarations. These
    #: files still count in the inventory; only `@covers` and `forge:<ID>`
    #: harvesting skips them. Two keys rather than one because conflating them
    #: costs a repository its own test statistics to silence a few fixtures.
    exclude_id_scan: list[str] = field(default_factory=list)
    #: Where the file came from, or None when defaults are in use.
    source: str | None = None
    #: Populated when the file exists but could not be read.
    error: str | None = None

    def excludes(self, path: str) -> bool:
        return _matches(path, self.exclude)

    def excludes_id_scan(self, path: str) -> bool:
        """True when this path's IDs are fixture data, not declarations."""
        return self.excludes(path) or _matches(path, self.exclude_id_scan)


def load_config(repo: Path) -> Config:
    target = repo / CONFIG_PATH
    if not target.is_file():
        return Config()
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return Config(source=CONFIG_PATH, error=f"could not read {CONFIG_PATH}: {exc}")
    if not isinstance(raw, dict):
        return Config(source=CONFIG_PATH, error=f"{CONFIG_PATH} is not a mapping")

    derive_section = raw.get("derive") if isinstance(raw.get("derive"), dict) else {}
    return Config(
        exclude=_string_list(derive_section.get("exclude")),
        exclude_id_scan=_string_list(derive_section.get("exclude_id_scan")),
        source=CONFIG_PATH,
    )


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _matches(path: str, patterns: list[str]) -> bool:
    """Glob match that treats a directory pattern as covering its subtree.

    `tests/*` is the shape a person writes for "the tests"; fnmatch alone would
    not match `tests/unit/test_x.py` because `*` does not cross a separator.
    Matching the pattern's directory prefix as well is what makes the config
    behave the way it reads.
    """
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        prefix = pattern.rstrip("*").rstrip("/")
        if prefix and (path == prefix or path.startswith(prefix + "/")):
            return True
    return False
