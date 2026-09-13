# Forge Harness

<p align="center">
  <strong>Personal Software Engineering Harness with Anchored System Knowledge & Deterministic Staleness Detection</strong>
</p>

<p align="center">
  <a href="https://github.com/CodeGenLabs/forge-harness/actions/workflows/ci.yml"><img src="https://github.com/CodeGenLabs/forge-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/ast-tree--sitter-orange.svg" alt="Tree Sitter AST">
  <img src="https://img.shields.io/badge/docs-mkdocs--material-purple.svg" alt="MkDocs">
</p>

---

## 🌐 Language / Ngôn ngữ / 言語

| [🇬🇧 English Documentation](en/index.md) | [🇻🇳 Tài liệu Tiếng Việt](vi/index.md) | [🇯🇵 日本語ドキュメント](ja/index.md) |
| :--- | :--- | :--- |

---

## What is Forge?

**Forge** is a personal software engineering harness designed to govern AI coding agents and engineering teams through deterministic verification. 

Instead of relying on LLM self-reporting or loose Markdown notes that drift invisibly as code changes, Forge establishes a **3-Tier Ground Truth System**:

```mermaid
graph TD
    subgraph Human ["Tier 1: Human Intent"]
        H1["Constitutional Rules<br/>docs/system/pitfalls.md"]
        H2["Architectural Models<br/>docs/system/domain.md"]
        H3["Decisions<br/>docs/system/decisions/"]
    end

    subgraph Agent ["Tier 2: Agent Work"]
        A1["Structured Changes<br/>changes/XXXX-name/"]
        A2["Gates: Proposal → Design → Verify"]
        A3["Attributed Touches & Drifts"]
    end

    subgraph Machine ["Tier 3: Machine Truth"]
        M1["AST Anchors (Python, TS, Go, C#)"]
        M2["Cryptographic SHA Baselines"]
        M3["Derived Dependency Graph & Trace"]
    end

    Human --> Agent
    Agent --> Machine
    Machine -.->|Deterministic Check| Human
```

---

## ⚡ Quickstart (30 Seconds)

### 1. Install Globally
```bash
# Recommended using pipx or uv
uv tool install git+https://github.com/CodeGenLabs/forge-harness.git
# or
pipx install git+https://github.com/CodeGenLabs/forge-harness.git
```

### 2. Initialize in Any Project
```bash
cd /path/to/my-project
forge init
forge doctor
forge check
```

---

## 📚 Documentation Navigation

* **[Getting Started](en/getting-started.md)**: Installation options, prerequisites, environment check, and your first repository initialization.
* **[Core Concepts](en/concepts.md)**: 3-Tier model, Claim Store, AST Code Anchoring, Gate Lifecycle, and Attributed Drift.
* **[CLI Reference](en/cli-reference.md)**: Full syntax, arguments, and examples for all 11 subcommands.
* **[Guides & CI/CD](en/guides.md)**: Working with AI Agents (Claude, Gemini, ChatGPT), GitHub Actions workflow, Monorepo setups.
* **[Architecture](en/architecture.md)**: Deep dive into the kernel, AST fingerprints, and cryptographic verification.
* **[Configuration](en/configuration.md)**: Complete `.forge/config.yaml` schema and options.
* **[Troubleshooting](en/troubleshooting.md)**: FAQ, Windows console quirks, PATH troubleshooting, and common gate errors.
