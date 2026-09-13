# CONSTITUTION.md — 16 Engineering Principles

The non-negotiable principles governing Forge:

1. **Zero Core LLM Calls:** The kernel is strictly deterministic; zero non-deterministic API dependencies.
2. **Exit Code Governance:** All gates block via system exit codes (0 = proceed, non-zero = halt).
3. **Git is the Single Truth:** No external database, service, or cache.
4. **Data-Driven Artifacts:** Workflow stages are nodes in a deterministic DAG.
5. **AST Anchors:** Knowledge is bound to syntax trees, not brittle line numbers.
6. **Mechanical Drift Detection:** Staleness is computed mathematically from diffs and digests.
7. **Pre-Implementation Specification:** Behavioral delta specs must be written before code.
8. **Strict TDD:** Implementation proceeds task by task under Red-Green-Refactor.
9. **Claim-Touch Accounting:** Diff $\cap$ Anchors must be 100% accounted for.
10. **One-Way Ratchet:** Complexity can escalate tracks, never downgrade.
11. **Evidence Before Claims:** No completion claims without fresh verification command execution.
12. **Host Neutrality:** Skills contain zero proprietary vendor prompts; mechanism lives in CLI.
13. **Deterministic Derived Tier:** Derived files are formatted with LF and sorted keys.
14. **Controlled Retirement:** Claims can only be retired on 4 legitimate grounds.
15. **Pre-Commit Enforcement:** Drift prevention hooks guard the repository boundary.
16. **Version Skew Pinning:** Repositories detect and warn against kernel version discrepancies.
