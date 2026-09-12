"""Tests for forge.evidence: parsing test targets, formatting commands, running tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from forge.evidence import (
    EvidenceResult,
    build_test_command,
    evaluate_claim_evidence,
    get_test_command,
    parse_test_target,
    run_evidence_test,
)
from forge.store import Claim


def test_parse_test_target():
    assert parse_test_target("test: tests/foo.py::test_bar") == "tests/foo.py::test_bar"
    assert parse_test_target("test:tests/foo.py::test_bar") == "tests/foo.py::test_bar"
    assert parse_test_target('test: "tests/foo.py::test_bar"') == "tests/foo.py::test_bar"
    assert parse_test_target("test: 'tests/foo.py::test_bar'") == "tests/foo.py::test_bar"
    assert parse_test_target("adr: ADR-0001") is None
    assert parse_test_target("rfc: 1234") is None
    assert parse_test_target("test:") is None
    assert parse_test_target("   ") is None


def test_build_test_command():
    # Pytest runner
    pytest_cmd = f"{sys.executable} -m pytest -q"
    target = "tests/test_spec.py::test_bullets"
    assert build_test_command(pytest_cmd, target) == f"{pytest_cmd} {target}"

    # Vitest runner with :: syntax
    vitest_cmd = "pnpm exec vitest run"
    v_target = "tools/__tests__/foo.test.ts::should work"
    assert build_test_command(vitest_cmd, v_target) == 'pnpm exec vitest run tools/__tests__/foo.test.ts -t "should work"'

    # Generic runner
    generic = "cargo test --"
    assert build_test_command(generic, "my_test") == "cargo test -- my_test"


def test_get_test_command(repo):
    # No config
    assert get_test_command(repo.root) is None

    # Config with test command
    repo.write(".forge/config.yaml", "commands:\n  test: pytest -q\n")
    assert get_test_command(repo.root) == "pytest -q"

    # Config with none
    repo.write(".forge/config.yaml", "commands:\n  test: none\n")
    assert get_test_command(repo.root) is None


def test_run_evidence_test_pass(repo):
    repo.write(
        "test_sample.py",
        "def test_ok():\n    assert 1 + 1 == 2\n",
    )
    cmd = f"{sys.executable} -m pytest -q"
    result = run_evidence_test(repo.root, "test_sample.py::test_ok", base_cmd=cmd)
    assert result.status == "pass"
    assert result.exit_code == 0
    assert result.duration_s >= 0.0
    assert not result.failures


def test_run_evidence_test_fail(repo):
    repo.write(
        "test_sample.py",
        "def test_broken():\n    assert 1 == 2, 'math broke'\n",
    )
    cmd = f"{sys.executable} -m pytest -q"
    result = run_evidence_test(repo.root, "test_sample.py::test_broken", base_cmd=cmd)
    assert result.status == "fail"
    assert result.exit_code != 0
    assert any("math broke" in line for line in result.failures)


def test_run_evidence_unavailable_when_no_runner(repo):
    result = run_evidence_test(repo.root, "tests/foo.py::test_bar", base_cmd=None)
    assert result.status == "unavailable"
    assert "no test command" in result.reason


def test_evaluate_claim_evidence(repo):
    repo.write(
        "test_sample.py",
        "def test_one():\n    pass\n",
    )
    cmd = f"{sys.executable} -m pytest -q"
    claim = Claim(
        id="PIT-example",
        kind="pitfall",
        file="docs/system/pitfalls.md",
        line=10,
        evidence=[
            "test: test_sample.py::test_one",
            "adr: ADR-0001",
        ],
    )
    results = evaluate_claim_evidence(repo.root, claim, base_cmd=cmd)
    assert len(results) == 1
    assert results[0].target == "test_sample.py::test_one"
    assert results[0].status == "pass"
