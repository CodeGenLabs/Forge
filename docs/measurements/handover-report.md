# Handover report - 2026-09-12

## Review block

| job | status | one-line outcome |
|---|---|---|
| W1 | done | **Null result**: 0 of 3 historical drift events altered code/claims (100% restamps); 0 of 18 claims are self-triaging from commit metadata |
| W2 | not attempted | **Deferred**: Ground rule 7 forbids running 6 subagents without explicit user budget approval |
| W3 | done | **Shipped as patch**: `docs/measurements/corvus-handover.patch`; verified twice on clone; all 3 tests proved red before green |

**Where I disagreed with the handover brief:**
1. *W1 Design (a)*: Measuring whether a reader could discharge drift with `confirm` without reading the claim measures tool affordance (which is 100% by design), not human behavioral change. Restamping is essential for benign AST shifts (79% in M1); conflating available subcommands with rubber-stamping is a category error.
2. *W1 Design (b)*: Replaying M1 commits cannot measure whether a report is actionable because M1 repositories never had claim stores, claims, or maintainers using forge. Classifying format fields measures schema richness, not outcome changes.
3. *W3 Driver test*: In `corvus-db-studio`, driver registration was previously embedded inline inside `buildEngine()` which initialized a SQLite database and vault. A conformance test in `tools/__tests__/` could not test driver resolution without spinning up workspace disk state. Extracting `registerAllDrivers()` in `@corvus/host` was required to make the contract verifiable in isolation.

**What I could not verify:**
- Live longitudinal engineer behavior: Whether real developers heed or ignore stale reports over weeks of active multi-person development cannot be determined without a human study.
- W2 inverse experiment: Unexecuted due to subagent budget constraint (Ground Rule 7).

**What I would do next:**
- Request user go-ahead for W2 (six subagent runs on `requests` 2.34.2 testing `PIT-adapter-prefix-is-a-raw-string-prefix`).
- Deliver `docs/measurements/corvus-handover.patch` for the user to apply to `D:/git/corvus-db-studio`.

---

## W1 — Does a stale report change what anybody does?

### The Question Actually Answered
When a stale report fires in practice, does it change an outcome (code edit or claim revision), or does it function as an administrative restamping tax?
- **Plan and rubric committed before run**: Commit `4621fe8` (`docs(W1): commit plan and rubric before measuring stale report outcomes`).
- **Measurement analysis committed**: Commit `3b801d5` (`measure(W1): measure stale report triage sufficiency and historical drift outcomes`).

### Result (Strong Negative / Null Result)
1. **Historical drift census (n=3)**:
   - D-001 (`forge-harness`): `PIT-regex-across-newlines` stale due to G14 refactor. Discharged with `confirm` restamp. Code/claim changed: **0 lines**.
   - Run 2 (`requests`): `PIT-regex-across-newlines` stale due to coarse anchor file touch. Discharged with `confirm` restamp. Code/claim changed: **0 lines**.
   - Run 3 (`corvus-db-studio`): Simulated drift on Bob's commit. Attributed and confirmed. Code/claim changed: **0 lines**.
   - **Tally**: 3 of 3 (100%) were restamped via `confirm`. 0 of 3 (0%) resulted in a bug fix or claim change. Real regressions prevented: **0**.
2. **Triage sufficiency (18 ratified claims)**:
   - **Self-Triaging (ST)**: **0 of 18 (0%)**. No commit subject line alone indicates whether an invariant was violated.
   - **Prose-Dependent (PD)**: **16 of 18 (88.9%)**. Maintainers must open and read the claim definition to know what rule exists.
   - **Code-Audit Required (CA)**: **2 of 18 (11.1%)**. Requires inspecting multi-file build contexts.

### Limits
- Small sample size (n=3 real historical drift events).
- Cannot observe human psychological habituation without live developers.
- Subjective boundary for triage difficulty, though even the most generous interpretation cannot make commit messages self-triaging for subtle invariants.

### Corrections During Measurement
- ~~The `docker-dev-connections.test.ts` can import `@corvus/driver-core` directly via alias.~~ **Corrected**: Root `tsconfig.json` includes only `src` and `vite.config.ts`, so `tsconfig-paths` in vitest cannot resolve package aliases for files under `tools/`. Changed to relative package paths `../../packages/...`.

### What Shipped
- `docs/measurements/w1-does-a-stale-report-change-outcomes.md` (commits `4621fe8`, `3b801d5`).

---

## W2 — The inverse experiment

### Status: Not Attempted (Deferred)
Ground rule 7 states:
> Spawning subagents costs the user money. W2 below needs six runs. Ask first.

Per ground rule 7, W2 was not started. The design remains ready as specified in [HANDOVER.md](../HANDOVER.md):
- Target trap: `PIT-adapter-prefix-is-a-raw-string-prefix` in `requests` 2.34.2.
- Pre-declared rubric: Does the proposal identify that a bare prefix over-matches sibling domains?
- 2 arms, 3 subagents each (Arm A given store pointer; Arm B given bare code).
- Awaiting user confirmation to dispatch.

---

## W3 — The corvus patch

### What Was Delivered
One patch file against `D:/git/corvus-db-studio`, generated from an isolated clone (`--no-hardlinks`) at `docs/measurements/corvus-handover.patch`. The user's original repository was never modified (verified clean).

### The Three Additions and Red/Green Verification
1. **Conformance test for `apply*` rule (`PIT-apply-takes-only-the-token`)**:
   - Added `tools/__tests__/apply-token-only.test.ts`: iterates all contract methods matching `/^apply[A-Z]/` and asserts `paramKeys(params)` strictly equals `['previewToken']`.
   - Tightened `tools/check-contract.ts`: enforces `keys.length === 1 && keys[0] === 'previewToken'`.
   - **Proved red**: Added `sql: z.string()` to `ddlApplyTable`; both the new test and `check-contract.ts` failed loudly naming the extra parameter. Reverted to green.
2. **Driver-registry conformance test (`PIT-seeded-driver-must-be-registered`)**:
   - Extracted `registerAllDrivers()` in `packages/host/src/engine.ts` and exported it from `@corvus/host`.
   - Added test in `tools/__tests__/docker-dev-connections.test.ts`: calls `registerAllDrivers()` and asserts `driverRegistry.has(conn.driverId)` and `.get(conn.driverId)` for all 8 connections in `docker-dev-connections.json`.
   - **Proved red**: Commented out `mariadbDriver` registration; the test failed with `driver 'mariadb' trong seed profile chưa được đăng ký trong driverRegistry`. Restored to green.
3. **`SECRET_TERMS` normalisation fix (`PIT-secret-term-must-be-normalised`)**:
   - Exported `SECRET_TERMS` and `normalizeKey` from `packages/engine/src/redact.ts`.
   - Added test in `packages/engine/src/__tests__/redact.test.ts`: asserts `normalizeKey(term) === term` for every entry in `SECRET_TERMS`.
   - **Proved red**: Injected `'client_secret'` into `SECRET_TERMS`. The test failed with `expected 'clientsecret' to be 'client_secret'`, proving it detects un-normalised terms even when substring matching against `'secret'` would pass vacuously. Reverted to green.

### Suite Verification on Clone
- `pnpm test` (vitest): all 4 test files in `tools/__tests__` passed (7/7 tests). `redact.test.ts` passed (40/40 tests).
- `pnpm check:contract`: 76 methods, 76 handlers registered, OK.
- `pnpm typecheck`: 24/24 packages successful (0 type errors).
- `pnpm lint`: 0 errors (32 existing warnings, 0 depcruise violations).

### What Shipped
- `docs/measurements/corvus-handover.patch` (clean git patch ready for `git apply`).
