[ [English](../en/configuration.md) | 🌐 **Tiếng Việt** | [日本語](../ja/configuration.md) ]
---

# Cấu hình `.forge/config.yaml`

File cấu hình chính của Forge được đặt tại `.forge/config.yaml`.

```yaml
version: 1

project:
  name: "du-an-cua-toi"
  stack:
    - python
    - typescript

paths:
  system_knowledge: "docs/system"
  changes: "changes"
  derived: "docs/system/derived"

commands:
  test: "pytest -q"

rules:
  require_change_for_claims: true
```
