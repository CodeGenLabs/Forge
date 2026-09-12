"""Evidence test execution for forge claims.

Evaluates test evidence declared on claims against the current repository state
to determine whether an invariant or pitfall still holds when code moves.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .store import Claim

__all__ = [
    "EvidenceResult",
    "parse_test_target",
    "build_test_command",
    "get_test_command",
    "run_evidence_test",
    "evaluate_evidence",
    "evaluate_claim_evidence",
]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_INTERESTING_RE = re.compile(
    r"(?i)\b(fail(ed|ure|s)?|error|assert\w*|expected|not ok|panic|"
    r"traceback|exception)\b|[✕×✗]|^\s*(FAIL|ERR)"
)
_NOISE_RE = re.compile(r"\(\d+ tests?\)\s*\d+m?s\s*$|^\s*[✓√?]\s|^\s*\d+\s*passed")


@dataclass
class EvidenceResult:
    """The result of executing one evidence test."""
    target: str
    status: str  # "pass" | "fail" | "unavailable" | "error"
    exit_code: int | None = None
    duration_s: float = 0.0
    cmd: str = ""
    failures: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_s": round(self.duration_s, 3),
            "cmd": self.cmd,
            "failures": self.failures,
            "reason": self.reason,
        }


def parse_test_target(entry: str) -> str | None:
    """Extract a test target from an evidence string.

    Accepts 'test: path::name', 'test:path::name', and quoted variations.
    Returns None if entry is not a test reference.
    """
    cleaned = entry.strip()
    if not cleaned.lower().startswith("test:"):
        return None
    raw = cleaned[5:].strip().strip('"').strip("'")
    return raw if raw else None


def get_test_command(repo: Path) -> str | None:
    """Read `commands.test` from .forge/config.yaml."""
    target = repo / ".forge/config.yaml"
    if not target.is_file():
        return None
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    section = raw.get("commands") if isinstance(raw.get("commands"), dict) else {}
    cmd = section.get("test")
    if not cmd or str(cmd).strip().lower() in ("none", "n/a", "not applicable", "-"):
        return None
    return str(cmd).strip()


def build_test_command(base_cmd: str, target: str) -> str:
    """Construct a shell command that runs specifically *target*.

    Handles pytest, vitest, jest, and generic runners.
    """
    lower = base_cmd.lower()
    if "vitest" in lower or "jest" in lower:
        if "::" in target:
            file_part, test_part = target.split("::", 1)
            return f'{base_cmd} {file_part} -t "{test_part}"'
        return f"{base_cmd} {target}"
    # Default (pytest, go test, etc.): append target directly
    return f"{base_cmd} {target}"


def _extract_failures(stdout: bytes | None, stderr: bytes | None) -> list[str]:
    text = "\n".join(
        _ANSI_RE.sub("", stream.decode("utf-8", "replace"))
        for stream in (stdout, stderr) if stream
    )
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    named = [ln for ln in lines if _INTERESTING_RE.search(ln) and not _NOISE_RE.search(ln)]
    return named[:10] if named else lines[-5:]


def run_evidence_test(
    repo: Path,
    target: str,
    base_cmd: str | None = None,
    timeout: int = 30,
) -> EvidenceResult:
    """Execute a single test target and return structured EvidenceResult."""
    cmd_base = base_cmd if base_cmd is not None else get_test_command(repo)
    if not cmd_base:
        return EvidenceResult(
            target=target,
            status="unavailable",
            reason="no test command configured in .forge/config.yaml",
        )

    cmd = build_test_command(cmd_base, target)
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd, cwd=repo, shell=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - start
        return EvidenceResult(
            target=target,
            status="unavailable",
            cmd=cmd,
            duration_s=duration,
            reason=f"timed out after {timeout}s",
        )
    except OSError as exc:
        duration = time.perf_counter() - start
        return EvidenceResult(
            target=target,
            status="error",
            cmd=cmd,
            duration_s=duration,
            reason=str(exc),
        )

    duration = time.perf_counter() - start
    if completed.returncode == 0:
        return EvidenceResult(
            target=target,
            status="pass",
            exit_code=0,
            duration_s=duration,
            cmd=cmd,
        )

    failures = _extract_failures(completed.stdout, completed.stderr)
    return EvidenceResult(
        target=target,
        status="fail",
        exit_code=completed.returncode,
        duration_s=duration,
        cmd=cmd,
        failures=failures,
    )


def evaluate_evidence(
    repo: Path,
    evidence_entries: list[str],
    base_cmd: str | None = None,
    timeout: int = 30,
) -> list[EvidenceResult]:
    """Find and run all test targets in an evidence string list."""
    results: list[EvidenceResult] = []
    for entry in evidence_entries:
        target = parse_test_target(entry)
        if target:
            results.append(run_evidence_test(repo, target, base_cmd=base_cmd, timeout=timeout))
    return results


def evaluate_claim_evidence(
    repo: Path,
    claim: Claim,
    base_cmd: str | None = None,
    timeout: int = 30,
) -> list[EvidenceResult]:
    """Find and run all test evidence entries declared on a claim."""
    return evaluate_evidence(repo, claim.evidence, base_cmd=base_cmd, timeout=timeout)
