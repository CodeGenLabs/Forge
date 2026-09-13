# Privacy & Telemetry Policy

**Effective Date:** September 2026  
**Repository:** [CodeGenLabs/forge-harness](https://github.com/CodeGenLabs/forge-harness)

At Forge, we believe developer tooling must respect privacy, security, and repository confidentiality. This policy explains our approach to telemetry, error reporting, and data handling.

---

## 1. Zero Background Telemetry

* **No Secret Tracking:** Forge does **not** contain background analytics, tracking pixels, telemetry daemons, or silent "phone-home" mechanisms.
* **100% Offline by Design:** All kernel operations (`forge check`, `forge drift`, `forge gate`, `forge verify`, etc.) run entirely locally on your machine.
* **Deterministic Computations:** Calculations rely only on local Git history and Tree-Sitter AST structures.

---

## 2. Voluntary Issue & Crash Reporting

When Forge encounters an unexpected internal error (crash) or when you explicitly invoke `forge report`:

1. **User Control First:**
   * Forge will **never** automatically submit data to any remote server or third-party service.
   * If an unexpected crash occurs in an interactive terminal, Forge will ask for your consent before opening a pre-filled GitHub Issue link in your default browser.
   * You can inspect, edit, or cancel the issue report before submitting it on GitHub.

2. **Data Sanitization & Privacy Scrubbing:**
   Before generating an issue report URL, Forge scrubs sensitive data:
   * **Home Directories:** Paths like `C:\Users\<username>\...` or `/home/<username>/...` are sanitized to `~/...`.
   * **No Proprietary Code:** Forge never includes your source code files, repository business logic, commit messages, or diffs in error reports.
   * **Environment Metadata Only:** Only non-sensitive diagnostic information is included (Forge version, Python version, Operating System name, and scrubbed Python exception tracebacks).

---

## 3. Disabling Prompts

* If you run Forge in CI/CD pipelines or headless scripts (where `stdin` is not an interactive terminal), Forge suppresses interactive prompts and only outputs the sanitized error message.
* You can also set `FORGE_NO_REPORT=1` or `FORGE_DEBUG=1` in your environment to completely suppress report suggestions.

---

## 4. Contact & Open Source Transparency

Forge is open-source under the MIT License. You can audit every line of our reporting logic in `src/forge/report.py`.

For questions or security concerns, open an issue on [GitHub](https://github.com/CodeGenLabs/forge-harness/issues).
