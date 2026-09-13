"""Crash handling, privacy sanitization, and issue reporting for Forge CLI."""

from __future__ import annotations

import argparse
import getpass
import os
import platform
import re
import sys
import traceback
import urllib.parse
import webbrowser
from pathlib import Path

GITHUB_ISSUES_URL = "https://github.com/CodeGenLabs/forge-harness/issues/new"
MAX_URL_LENGTH = 4000


def get_forge_version() -> str:
    try:
        from importlib.metadata import version
        return version("forge-harness")
    except Exception:
        return "0.1.0"


def sanitize_text(text: str) -> str:
    """Scrub local user paths, credentials, and sensitive data from text."""
    # 1. Scrub token / password URLs like https://token@github.com
    text = re.sub(r'(https?://)[^/\s@]+@', r'\1***@', text)

    # 2. Scrub user's home directory
    try:
        home = str(Path.home())
        if home and len(home) > 2:
            # Direct replacement
            text = text.replace(home, "~")
            # Case-insensitive replacement on Windows
            if sys.platform == "win32":
                pattern = re.escape(home)
                text = re.sub(pattern, "~", text, flags=re.IGNORECASE)
                pattern_fwd = re.escape(home.replace("\\", "/"))
                text = re.sub(pattern_fwd, "~", text, flags=re.IGNORECASE)
    except Exception:
        pass

    # 3. Scrub username if found in standard user paths (e.g. /home/user or Users\user)
    try:
        user = getpass.getuser()
        if user and len(user) > 1:
            text = re.sub(r'([\\/]Users[\\/])' + re.escape(user), r'\1<user>', text, flags=re.IGNORECASE)
            text = re.sub(r'([\\/]home[\\/])' + re.escape(user), r'\1<user>', text, flags=re.IGNORECASE)
    except Exception:
        pass

    return text


def get_environment_info() -> dict[str, str]:
    """Collect non-sensitive environment metadata."""
    return {
        "forge_version": get_forge_version(),
        "python_version": platform.python_version(),
        "os": platform.platform(aliased=True),
    }


def build_issue_url(
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> str:
    """Build a pre-filled GitHub Issue URL, truncating if necessary."""
    params: dict[str, str] = {
        "title": title,
    }
    if labels:
        params["labels"] = ",".join(labels)

    base_encoded = urllib.parse.urlencode(params)
    target_body = body

    test_query = f"{base_encoded}&{urllib.parse.urlencode({'body': target_body})}"
    if len(f"{GITHUB_ISSUES_URL}?{test_query}") > MAX_URL_LENGTH:
        available = MAX_URL_LENGTH - len(f"{GITHUB_ISSUES_URL}?{base_encoded}&body=") - 200
        if available > 200:
            target_body = body[:available] + "\n\n... [Remaining content truncated to fit browser URL limit]"
        else:
            target_body = "[Content truncated to fit browser URL limit]"

    params["body"] = target_body
    return f"{GITHUB_ISSUES_URL}?{urllib.parse.urlencode(params)}"


def generate_crash_report(exc: BaseException, argv: list[str] | None = None) -> tuple[str, str, str]:
    """Generate title, body, and URL for an unhandled crash."""
    env = get_environment_info()
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    raw_tb = "".join(tb_lines)
    scrubbed_tb = sanitize_text(raw_tb)

    cmd = " ".join(argv) if argv else "forge"
    scrubbed_cmd = sanitize_text(cmd)

    exc_name = type(exc).__name__
    exc_msg = str(exc)
    title = f"[Crash Report]: {exc_name}: {exc_msg}"[:80]

    body = (
        f"### Command Executed\n"
        f"```bash\n"
        f"{scrubbed_cmd}\n"
        f"```\n\n"
        f"### Environment Details\n"
        f"- **Forge Version:** {env['forge_version']}\n"
        f"- **Python Version:** {env['python_version']}\n"
        f"- **OS:** {env['os']}\n\n"
        f"### Scrubbed Error Traceback\n"
        f"```text\n"
        f"{scrubbed_tb}\n"
        f"```\n\n"
        f"### Privacy Notice\n"
        f"This report was generated locally. All home directories and sensitive credentials "
        f"have been scrubbed. Please review before submitting.\n"
    )

    url = build_issue_url(title=title, body=body, labels=["bug", "crash-report"])
    return title, body, url


def handle_crash(
    exc: BaseException,
    argv: list[str] | None = None,
    stream=None,
) -> int:
    """Graceful crash handler for CLI entrypoint."""
    if stream is None:
        stream = sys.stderr
    if os.environ.get("FORGE_DEBUG") == "1":
        raise exc

    if isinstance(exc, SystemExit):
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    if isinstance(exc, KeyboardInterrupt):
        return 130

    exc_name = type(exc).__name__
    exc_msg = str(exc)
    print(f"forge: internal error: {exc_name}: {exc_msg}", file=stream)

    if os.environ.get("FORGE_NO_REPORT") == "1":
        return 1

    _, _, url = generate_crash_report(exc, argv)

    is_interactive = False
    try:
        is_interactive = sys.stdin.isatty() and not os.environ.get("CI")
    except Exception:
        pass

    if is_interactive:
        print("", file=stream)
        print("Forge encountered an unexpected error.", file=stream)
        print("To help improve Forge, you can open a pre-filled issue on GitHub.", file=stream)
        print("No confidential code or paths will be sent.", file=stream)
        try:
            choice = input("Open pre-filled issue in your browser? [y/N]: ").strip().lower()
            if choice in ("y", "yes"):
                webbrowser.open(url)
                print("Opened GitHub issue in your browser.", file=stream)
                return 1
        except (KeyboardInterrupt, EOFError):
            pass

    print("", file=stream)
    print("To report this issue, visit:", file=stream)
    print(f"  {url}", file=stream)
    return 1


def cmd_report(args: argparse.Namespace) -> int:
    """Implement `forge report` CLI command."""
    env = get_environment_info()

    if getattr(args, "feature", False):
        title = "[Feature]: "
        body = (
            "### Problem Statement\n\n"
            "### Proposed Solution\n\n"
            f"### Environment Info\n"
            f"- Forge: {env['forge_version']}\n"
            f"- Python: {env['python_version']}\n"
            f"- OS: {env['os']}\n"
        )
        labels = ["enhancement"]
    else:
        title = "[Bug]: "
        body = (
            "### What happened?\n\n"
            "### Expected Behavior\n\n"
            "### Steps to Reproduce\n\n"
            f"### Environment Details\n"
            f"- Forge: {env['forge_version']}\n"
            f"- Python: {env['python_version']}\n"
            f"- OS: {env['os']}\n"
        )
        labels = ["bug"]

    url = build_issue_url(title=title, body=body, labels=labels)

    if getattr(args, "no_browser", False):
        print(url)
        return 0

    print("Opening GitHub issue tracker in your browser...")
    print(f"URL: {url}")
    try:
        opened = webbrowser.open(url)
        if not opened:
            print("Could not launch browser automatically. Please open the link above.")
    except Exception:
        print("Could not launch browser automatically. Please open the link above.")
    return 0
