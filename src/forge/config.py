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
    #: Line budget for the always-loaded set (`budgets.always_loaded_lines`).
    #: Configurable so a project can set it *lower*; CONSTITUTION.md says it is
    #: never raised, and the check's `fix` string says so rather than the
    #: loader refusing to read a larger number - a check that argues is more
    #: useful than a loader that lies about what the file says.
    always_loaded_lines: int = 400
    #: How many recent changes the orphan check looks back over
    #: (`thresholds.orphan_change_window`).
    orphan_change_window: int = 20
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

    derive_section = _section(raw, "derive")
    budgets = _section(raw, "budgets")
    thresholds = _section(raw, "thresholds")
    defaults = Config()
    return Config(
        exclude=_string_list(derive_section.get("exclude")),
        exclude_id_scan=_string_list(derive_section.get("exclude_id_scan")),
        always_loaded_lines=_positive_int(
            budgets.get("always_loaded_lines"), defaults.always_loaded_lines
        ),
        orphan_change_window=_positive_int(
            thresholds.get("orphan_change_window"), defaults.orphan_change_window
        ),
        source=CONFIG_PATH,
    )


def _section(raw: dict, name: str) -> dict:
    value = raw.get(name)
    return value if isinstance(value, dict) else {}


def _positive_int(value: object, default: int) -> int:
    """A number, or the default. A garbage value never disables a check.

    Silently falling back to the default is deliberate: the alternative is
    `int(None)` blowing up, or a `0` budget that makes the check fire on every
    store. A typo in an optional setting must not change what is enforced.
    """
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


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
