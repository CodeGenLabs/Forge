[ [English](../en/guides.md) | 🌐 **Tiếng Việt** | [日本語](../ja/guides.md) ]
---

# Hướng dẫn & Tích hợp

Hướng dẫn tích hợp Forge vào quy trình phát triển thực tế, CI/CD và AI Agent.

---

## 1. Tích hợp AI Coding Agent

Forge tích hợp sẵn bộ kỹ năng Agent Skill tại `src/forge/_skills/`:
* `forge`: Điều phối toàn bộ quy trình thay đổi.
* `specify`: Định nghĩa yêu cầu chính xác, không mập mờ ranh giới.
* `plan-tasks`: Lập kế hoạch công việc theo từng bước kiểm thử được.
* `implement`: Triển khai code theo TDD và đúng phạm vi quy định.
* `curate-knowledge`: Khám phá các cạm bẫy mới và bảo trì tri thức.

---

## 2. Cấu hình CI/CD trên GitHub Actions

Tạo file `.github/workflows/forge.yml`:
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
        run: pip install git+https://github.com/CodeGenLabs/forge-harness.git

      - name: Doctor Check
        run: forge doctor

      - name: Run Forge Check
        run: forge check
```
