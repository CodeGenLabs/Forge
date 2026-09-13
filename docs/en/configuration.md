[ 🌐 **English** | [Tiếng Việt](../vi/configuration.md) | [日本語](../ja/configuration.md) ]
---

# Configuration Reference

Specification of `.forge/config.yaml`.

---

## Schema Overview

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
  typecheck: "mypy src"
  lint: "ruff check ."

rules:
  require_change_for_claims: true
  allow_unanchored_candidates: false
  gate_timeout_seconds: 600

exclude_id_scan:
  - ".git/**"
  - ".venv/**"
  - "node_modules/**"
  - "dist/**"
```

---

## Configuration Keys

### `project`
* `name` *(string)*: Project identifier.
* `stack` *(list)*: Primary languages (`python`, `typescript`, `go`, `csharp`).

### `commands`
* `test`: Test command executed during `forge verify`.
* `typecheck`: Optional static type analysis command.
* `lint`: Optional linter command.

### `rules`
* `require_change_for_claims`: Enforces that changes to `docs/system/` must go through a structured change workspace.
* `allow_unanchored_candidates`: Whether candidate claims are allowed without code anchors.
