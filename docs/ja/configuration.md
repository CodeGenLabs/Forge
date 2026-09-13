[ [English](../en/configuration.md) | [Tiếng Việt](../vi/configuration.md) | 🌐 **日本語** ]
---

# 設定リファレンス

`.forge/config.yaml` の記述仕様です。

```yaml
version: 1

project:
  name: "my-project"
  stack:
    - python
    - typescript

paths:
  system_knowledge: "docs/system"
  changes: "changes"
  derived: "docs/system/derived"

commands:
  test: "pytest -q"
```
