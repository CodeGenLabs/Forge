"""Tests for crash handling, privacy sanitization, and issue reporting."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from forge import report
from forge.cli import main


def test_sanitize_text_home_directory():
    home = str(Path.home())
    test_input = f"Error in {home}/projects/my-secret-repo/src/main.py at line 42"
    sanitized = report.sanitize_text(test_input)
    assert home not in sanitized
    assert "~" in sanitized


def test_sanitize_text_tokens_and_credentials():
    test_input = "Failed to clone https://ghp_abcdef1234567890@github.com/secret/repo.git"
    sanitized = report.sanitize_text(test_input)
    assert "ghp_abcdef1234567890" not in sanitized
    assert "https://***@github.com/secret/repo.git" in sanitized


def test_get_environment_info():
    env = report.get_environment_info()
    assert "forge_version" in env
    assert "python_version" in env
    assert "os" in env


def test_build_issue_url():
    url = report.build_issue_url(
        title="Test Error",
        body="This is a test crash body",
        labels=["bug", "crash-report"],
    )
    assert url.startswith("https://github.com/CodeGenLabs/forge-harness/issues/new")
    assert "title=Test+Error" in url or "title=Test%20Error" in url
    assert "labels=bug%2Ccrash-report" in url or "labels=bug,crash-report" in url


def test_build_issue_url_truncation():
    # Long body should be truncated safely to stay well within browser URL limits (~4000 chars)
    giant_body = "A" * 10000
    url = report.build_issue_url(title="Test", body=giant_body)
    assert len(url) <= 5000
    assert "truncated" in url.lower()


def test_handle_crash_debug_mode(monkeypatch):
    monkeypatch.setenv("FORGE_DEBUG", "1")
    with pytest.raises(ValueError, match="intentional boom"):
        report.handle_crash(ValueError("intentional boom"), argv=["test"])


def test_handle_crash_no_report_mode(monkeypatch, capsys):
    monkeypatch.setenv("FORGE_NO_REPORT", "1")
    code = report.handle_crash(ValueError("test error"), argv=["forge", "check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "forge: internal error: ValueError: test error" in err
    assert "https://github.com" not in err


def test_handle_crash_non_interactive(monkeypatch, capsys):
    monkeypatch.delenv("FORGE_DEBUG", raising=False)
    monkeypatch.delenv("FORGE_NO_REPORT", raising=False)
    # Simulate non-interactive session
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    code = report.handle_crash(RuntimeError("AST parser blew up"), argv=["forge", "check"])
    assert code == 1
    err = capsys.readouterr().err
    assert "forge: internal error: RuntimeError: AST parser blew up" in err
    assert "https://github.com/CodeGenLabs/forge-harness/issues/new" in err


def test_cmd_report_no_browser(capsys):
    code = main(["report", "--no-browser"])
    assert code == 0
    out = capsys.readouterr().out
    assert "https://github.com/CodeGenLabs/forge-harness/issues/new" in out
