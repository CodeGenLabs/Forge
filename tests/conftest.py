"""Fixtures that build throwaway git repositories.

Tests run against real git, not a mock. The behaviour under test *is* git's
rename detection and object model, so mocking it would test nothing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class Repo:
    """A tiny git repository builder for tests."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._git("init", "-b", "main")
        self._git("config", "user.name", "forge test")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "core.autocrlf", "false")

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True, check=True,
        )
        return completed.stdout.decode("utf-8", "replace")

    def write(self, path: str, content: bytes | str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        target.write_bytes(data)

    def move(self, old: str, new: str) -> None:
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        self._git("mv", old, new)

    def remove(self, path: str) -> None:
        self._git("rm", "-q", path)

    def commit(self, message: str) -> str:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message, "--allow-empty")
        return self.head

    @property
    def head(self) -> str:
        return self._git("rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(tmp_path / "repo")
