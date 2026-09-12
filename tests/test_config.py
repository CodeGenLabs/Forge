"""Tests for .forge/config.yaml loading, kernel version pinning, and skew detection.

OPEN_QUESTIONS.md Q11: "Pin the kernel version in .forge/config.yaml so a repo can detect skew."
ROADMAP.md R9: "pin the kernel version in .forge/config.yaml so a repository can detect skew".
"""

from __future__ import annotations

import pytest

from forge import __version__, config, validate
from forge.cli import main


@pytest.fixture
def project(repo):
    repo.write("src/app.py", "def go():\n    return 1\n")
    main(["init", "--repo", str(repo.root)])
    repo.commit("scaffold project")
    return repo


def test_load_config_defaults(tmp_path):
    cfg = config.load_config(tmp_path)
    assert cfg.kernel_version is None
    assert cfg.exclude == []
    assert cfg.always_loaded_lines == 400


def test_load_config_kernel_version(tmp_path):
    target = tmp_path / config.CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("kernel_version: '0.0.1'\n", encoding="utf-8")
    cfg = config.load_config(tmp_path)
    assert cfg.kernel_version == "0.0.1"


def test_load_config_kernel_version_nested(tmp_path):
    target = tmp_path / config.CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("kernel:\n  version: '0.0.2'\n", encoding="utf-8")
    cfg = config.load_config(tmp_path)
    assert cfg.kernel_version == "0.0.2"


def test_detect_kernel_skew_exact():
    assert config.detect_kernel_skew("0.0.1", "0.0.1") is None
    older = config.detect_kernel_skew("0.0.2", "0.0.1")
    assert older and "older than pinned 0.0.2" in older
    newer = config.detect_kernel_skew("0.0.1", "0.0.2")
    assert newer and "newer than pinned 0.0.1" in newer


def test_detect_kernel_skew_minimum():
    assert config.detect_kernel_skew(">=0.0.1", "0.0.1") is None
    assert config.detect_kernel_skew(">=0.0.1", "0.1.0") is None
    older = config.detect_kernel_skew(">=0.0.2", "0.0.1")
    assert older and "older than minimum required >=0.0.2" in older


def test_detect_kernel_skew_compatible():
    assert config.detect_kernel_skew("~=0.0.1", "0.0.2") is None
    mismatch = config.detect_kernel_skew("~=1.0.0", "0.9.0")
    assert mismatch is not None


def test_check_store_reports_kernel_skew(project):
    cfg_file = project.root / config.CONFIG_PATH
    cfg_file.write_text("kernel_version: '99.0.0'\n", encoding="utf-8")
    issues = validate.check_store(project.root)
    skew_issues = [i for i in issues if i.code == "store.kernel_skew"]
    assert len(skew_issues) == 1
    assert "kernel version skew" in skew_issues[0].message
    assert "running" in skew_issues[0].message


def test_check_store_passes_when_kernel_version_matches(project):
    cfg_file = project.root / config.CONFIG_PATH
    cfg_file.write_text(f"kernel_version: '{__version__}'\n", encoding="utf-8")
    issues = validate.check_store(project.root)
    skew_issues = [i for i in issues if i.code == "store.kernel_skew"]
    assert len(skew_issues) == 0


def test_doctor_reports_kernel_version_and_skew(project, capsys):
    cfg_file = project.root / config.CONFIG_PATH
    cfg_file.write_text("kernel_version: '99.0.0'\n", encoding="utf-8")
    main(["doctor", "--repo", str(project.root)])
    out = capsys.readouterr().out
    assert f"kernel           {__version__}" in out
    assert "kernel_pin       99.0.0 (SKEW:" in out
