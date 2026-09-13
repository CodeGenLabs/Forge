[ 🌐 **English** | [Tiếng Việt](../vi/cli-reference.md) | [日本語](../ja/cli-reference.md) ]
---

# CLI Reference

Comprehensive documentation for all 11 subcommands available in the `forge` command-line interface.

---

## Command Summary

| Command | Purpose | Primary Options |
| :--- | :--- | :--- |
| `forge init` | Initialize Forge structure in a project | `--repo <path>`, `--dry-run` |
| `forge doctor` | Diagnose environment and tool dependencies | `--json` |
| `forge check` | Validate repository integrity, claims & gates | `--repo <path>`, `--scope <all\|claims\|trace>` |
| `forge sync` | Synchronize derived machine-truth tier | `derived`, `--repo <path>` |
| `forge anchor` | Classify and inspect AST code anchors | `classify <anchor>`, `find <file>` |
| `forge claim` | Query, list, and validate claims | `list`, `show <id>`, `stale` |
| `forge change` | Manage structured change lifecycle | `new`, `list`, `show`, `archive` |
| `forge gate` | Evaluate lifecycle checkpoint gates | `<point>`, `--change <id>` |
| `forge verify` | Execute tests and claim-touch accounting | `--change <id>`, `--fast` |
| `forge reconcile`| Attribute drift and suggest repairs | `--repo <path>`, `--auto-retire` |
| `forge host` | Run MCP server or agent host adapters | `--port <port>` |
| `forge report` | Report a bug, crash, or feature request (sanitized) | `--feature`, `--no-browser` |

---

## Detailed Command Documentation

### `forge init`
Initializes `.forge/config.yaml` and standard `docs/system/` scaffolding.
```bash
forge init [--repo <path>] [--dry-run]
```
* `--repo`: Target directory (defaults to current directory).
* `--dry-run`: Print actions without creating files.

### `forge doctor`
Checks Python runtime, Git binary, Tree-sitter parsers, and terminal console compatibility.
```bash
forge doctor
```

### `forge check`
Verifies claim freshness, AST anchor resolution, derived tier freshness, and gate integrity.
```bash
forge check [--repo <path>] [--scope <scope>]
```
**Exit Codes:**
* `0`: All claims fresh, 0 errors.
* `1`: Stale claims, broken anchors, or gate violations detected.

### `forge sync derived`
Recomputes AST dependencies, test mappings, and inventory from Git HEAD.
```bash
forge sync derived [--repo <path>]
```
> [!IMPORTANT]
> Always commit your source code changes *first*, then run `forge sync derived` and commit the updated `docs/system/derived/` files.

### `forge change`
Manages changes in `changes/XXXX-name/`:
```bash
# Create a new change workspace
forge change new "add-jwt-validation"

# List active changes
forge change list

# Show change status and open gates
forge change show 0001

# Archive a completed change
forge change archive 0001
```

### `forge gate <checkpoint>`
Evaluates whether a change satisfies prerequisites to advance to the next development phase:
```bash
forge gate proposal:pre --change 0001
forge gate proposal:post --change 0001
forge gate design:post --change 0001
forge gate impact:post --change 0001
```

### `forge verify`
Runs test commands configured in `.forge/config.yaml` and reconciles touched claims against git diff:
```bash
forge verify --change 0001
```

### `forge reconcile`
Inspects all drift events in `docs/system/DRIFT.md` and attributes blame/resolution:
```bash
forge reconcile [--repo <path>]
```

### `forge report`
Opens a pre-filled, sanitized issue template in your browser to report a bug or request a feature:
```bash
forge report [--feature] [--no-browser]
```

---

## 🔒 Privacy & Telemetry Policy

Forge is committed to **Zero Secret Telemetry**:
* 100% of core calculations run offline and locally.
* When reporting issues via `forge report` or during an unexpected crash, all local usernames and paths are scrubbed (`/home/<user>` or `C:\Users\<user>` becomes `~`).
* Nothing is ever submitted silently; you always review and submit issues yourself. For full details, see [PRIVACY.md](https://github.com/CodeGenLabs/forge-harness/blob/main/PRIVACY.md).

