# WORKFLOW.md — Change Lifecycle & Gates

Detailed specification of the **Change Lifecycle** and **Gate Enforcement** in Forge.

---

## 1. Core Principles

1. **The Artifact DAG is Data:**  
   `.forge/schema/<type>.yaml` declares artifacts with explicit dependency relationships (`generates`, `requires`, `reads`). Completion is derived from file existence on disk, eliminating desynchronized status flags.
2. **Gates are Exit Codes:**  
   A gate runs deterministic checks. If any blocking check fails, the CLI returns a non-zero exit code, physically halting the workflow.

---

## 2. The 3-Track Scale Router

Scale classification occurs at the `understand` phase:

| Feature | Track A (Probe) | Track B (Bounded) | Track C (Structural) |
|---|---|---|---|
| **Use Case** | Feasibility checks, spikes, throwaway research. | Contained changes within existing flows; no schema or architecture changes. | New modules, API changes, schema migrations, invariant touches. |
| **Artifacts** | None (chat output). | `proposal.md`, `spec.md` (if logic changes), `tasks.md`. | `proposal.md`, `spec.md`, `impact.md`, `design.md` (ADR), `tasks.md`. |
| **Phases** | understand ➔ investigate. | understand ➔ investigate ➔ spec? ➔ tasks ➔ implement ➔ verify ➔ sync ➔ archive. | Full lifecycle DAG from start to finish. |
| **Human Review** | G1. | G1, G5. | G1, G2, G3, G5. |

### Automatic Escalation (One-Way Ratchet)
A change automatically escalates B ➔ C if:
- Blast radius touches any `ARC-`, `API-`, or `DAT-` claim.
- The diff introduces a public route, export, or migration.
- Changed file count exceeds project budget (default > 15 files).

---

## 3. Dedicated Bugfix Workflow
Bugfixes follow a specialized DAG declaring `reproduce.md` as the root mandatory artifact:
- Proves the defect with a reproducible test case before any fix is designed or attempted.
- Downstream planning (`proposal.md`, `tasks.md`) remains blocked until reproduction evidence is documented.

---

## 4. Verification Conditions (`forge verify`)
Before archiving, 11 objective conditions are checked:
1. `tests_pass`: Configured test runner exits 0.
2. `build_succeeds`: Build command exits 0.
3. `dag_complete`: All artifacts required by the active track exist.
4. `touch_accounted`: Every claim in the computed touch set is accounted for in `impact.md`.
5. `no_unwaived_drift`: No unresolved drift ledger entries remain.
6. `no_schema_violations`: All artifacts match their declared templates.
