# ARCHITECTURE.md — System Architecture of Forge

## 1. System Classification

Forge is a **personal software engineering harness** that operates directly inside git repositories.

### Key Characteristics:
- **Zero background services:** Operates strictly via ephemeral CLI invocations.
- **Git is the database:** All state, claims, schemas, and reports are plain-text files committed to Git.
- **Zero Core LLM calls:** The kernel is 100% deterministic; intelligence resides in the Host Agent.
- **Language Agnostic:** Supports Python, TypeScript, Go, C# (.NET), and degrades gracefully to coarse hashing for unsupported languages.

### Three Inviolable Rules
1. **The Kernel never calls an AI model:** All calculations are pure functions of repository state.
2. **Skills cannot self-enforce:** All blocking originates from kernel CLI exit codes.
3. **All state is plain text in Git:** No hidden databases or external sync servers.

---

## 2. Core Components

### 2.1 Kernel Modules
The Python kernel consists of 6 focused modules:
1. `fingerprint`: Tree-Sitter AST hashing, symbol lookup, and coarse line normalizers.
2. `derive`: Deterministic code scanning (`inventory`, `deps`, `tests`, `trace`, `backrefs`).
3. `store`: Claim store parser, validator, and 18 structural integrity checks (S1–S18).
4. `lifecycle`: Artifact DAG resolution, change tracking, and spec delta folding.
5. `gates`: Pre/post point-in-time checks blocking invalid lifecycle transitions.
6. `verify`: Eleven objective verification conditions including automated test runs.

### 2.2 Command Surface
```bash
# Administration, Distribution & Status
forge init                              # Scaffold .forge/ and docs/system/
forge doctor                            # Check toolchain (python, git, grammars, test runner)
forge status                            # 1-screen system overview
forge check [--scope store|change|all]  # Run deterministic integrity checks
forge install --host <name>             # Export skills to agent host (claude, antigravity, codex)
forge hooks [install|uninstall|status]  # Manage pre-commit drift protection hook

# Gates, Sync & Reconciliation
forge gate <point> [--change N]         # Execute lifecycle gate
forge sync derived                      # Rebuild derived tier
forge verify --change <N>               # Run full verification suite
forge reconcile --since <ref>           # Reconcile unmanaged git commits

# Baseline Bootstrap (3-Pass)
forge bootstrap derive                  # Pass 1: Mechanical code scan
forge bootstrap review                  # Pass 3: Interactive review sheet
forge bootstrap seal                    # Seal ratified claims & create Baseline ADR

# Drift Management
forge drift [--store|--changed] [--json]# Check AST anchor freshness
forge drift record                      # Open ledger entries in DRIFT.md
forge drift resolve <D-id> --verdict V  # Record drift resolution verdict
forge drift waive <D-id> --reason TEXT  # Record waiver with justification

# Claim Store Management
forge claim new <kind> [--append]       # Scaffold new claim template
forge claim show <ID>                   # Inspect claim details
forge ratify <ID>                       # Ratify candidate claim
forge retire <ID> --ground <1-4>        # Retire claim with valid grounds
forge trace <ID> [--json]               # 2-way traceability lookup

# Change Lifecycle
forge change new <slug> --track A|B|C   # Open new change
forge change show <N>                   # Inspect change DAG status
forge change track <N> --to C --reason  # Escalate track (one-way ratchet)
forge instructions <artifact> --change N# Fetch phase context contract
forge impact --change <N>               # Compute blast radius & claim touch set
forge archive --change <N>              # Fold spec deltas & archive change
```

### 2.3 Core AI Skills (Reasoning Tier)
Seven markdown-based procedural skills guide the AI agent through each lifecycle phase:
- `forge` (understand router): Classifies request into Track A/B/C and opens change.
- `investigate`: Explores existing code, records findings, and proposes candidate claims.
- `specify`: Authors delta requirements and testable scenarios.
- `plan-tasks`: Decomposes spec into ordered, checkable TDD tasks.
- `implement`: Executes tasks under strict Red-Green-Refactor discipline.
- `curate-knowledge`: Updates ratified claims and balances the drift ledger.
- `bootstrap`: Guides the human partner through 3-pass codebase adoption.

---

## 3. Standard Repository Layout

```
.
├── .forge/
│   ├── config.yaml            # Project configuration & command bindings
│   ├── schema/                # Artifact DAG schemas (feature.yaml, bugfix.yaml)
│   └── skills/                # Packaged skill procedures
├── docs/system/               # Permanent System Knowledge Store
│   ├── OVERVIEW.md            # Always-loaded high-level architectural map
│   ├── DRIFT.md               # Drift ledger
│   ├── domain.md              # Domain rules and business invariants
│   ├── decisions/             # Architectural Decision Records (ADRs)
│   └── derived/               # Machine-generated facts (LF, sorted keys)
│       ├── trace.json         # Bidirectional trace index
│       ├── deps.json          # Dependency graph
│       └── inventory.json     # Symbol & endpoint inventory
└── changes/                   # Active in-flight changes
    └── 0001-<slug>/
        ├── .forge.yaml        # Change metadata and track selection
        ├── proposal.md        # Change intent and problem statement
        ├── spec.md            # Delta requirements
        ├── impact.md          # Claim-touch accounting
        ├── tasks.md           # Ordered TDD task checklist
        └── verification.json  # Recorded verification results
```
