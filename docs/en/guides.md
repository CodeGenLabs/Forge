[ 🌐 **English** | [Tiếng Việt](../vi/guides.md) | [日本語](../ja/guides.md) ]
---

# Guides & Integrations

Practical guides for integrating Forge into your engineering workflows, CI/CD pipelines, and AI agent platforms.

---

## 1. Working with AI Coding Agents

Forge includes built-in agent **Skills** located in `src/forge/_skills/`. These skills give AI models like Claude, Gemini, ChatGPT, Cursor, and Antigravity precise operational instructions:

* `forge`: Orchestrates the overall change lifecycle.
* `specify`: Crafts airtight requirements without leaving boundaries ambiguous.
* `plan-tasks`: Breaks designs into atomic, testable tasks.
* `implement`: Test-driven development with scope enforcement.
* `curate-knowledge`: Discovers candidates and manages drift.

### Recommended System Prompt Addition
Add this snippet to your AI agent instructions (e.g. `CLAUDE.md`, `.cursorrules`, or custom agent prompt):
```markdown
This repository is governed by Forge Harness.
1. Before implementing non-trivial changes, run `forge change new <name>` and follow the change gates.
2. Ensure all constitutional invariants in `docs/system/pitfalls.md` are respected.
3. Before submitting changes, run `forge check` and ensure 0 errors.
```

---

## 2. GitHub Actions CI/CD Integration

Keep your repository clean automatically on every Pull Request. Create `.github/workflows/forge.yml`:

```yaml
name: Forge Verification

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  forge-check:
    name: Check Invariants & Claims
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Forge
        run: |
          pip install git+https://github.com/CodeGenLabs/forge-harness.git

      - name: Environment Health
        run: forge doctor

      - name: Verify Repository Claims
        run: forge check
```

---

## 3. Monorepo Multi-Package Setup

Forge natively supports monorepos (Python, TypeScript, Go, C#):
```yaml
# .forge/config.yaml
monorepo:
  enabled: true
  packages:
    - "packages/*"
    - "apps/*"
  exclude_id_scan:
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/build/**"
```
Anchors seamlessly target packages:
* `packages/core/src/index.ts#CoreClient`
* `apps/web/src/pages/index.tsx#HomePage`

---

## 4. Resolving Stale Drift

When code refactoring triggers drift:
1. Run `forge check` to locate stale claims.
2. Review the diff: did the architectural contract actually change, or was it just a harmless internal refactoring?
3. If contract changed: Update the description in `docs/system/pitfalls.md` or `docs/system/domain.md`.
4. If harmless refactor: Update the anchor target symbol or re-anchor.
5. Run `forge sync derived` and commit.
