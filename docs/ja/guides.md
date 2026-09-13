[ [English](../en/guides.md) | [Tiếng Việt](../vi/guides.md) | 🌐 **日本語** ]
---

# ガイドとCI/CD

実務環境へのForgeの導入方法について解説します。

---

## 1. AIエージェントとの協調
Forge は `src/forge/_skills/` に標準スキルを備えており、Claude、Gemini、ChatGPT などのモデルが正確にタスクを実行できるようガイドします。

---

## 2. GitHub Actions CI連携
`.github/workflows/forge.yml`:
```yaml
name: Forge Verification

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  forge-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install git+https://github.com/CodeGenLabs/forge-harness.git
      - run: forge check
```
