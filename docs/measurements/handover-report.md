# Handover report - 2026-09-12

## Review block

| job | status | one-line outcome |
|---|---|---|
| W1 | done | **Null result**: 0 of 3 historical drift events altered code/claims (100% restamps); 0 of 18 claims are self-triaging from commit metadata |
| W2 | done | **Definitive null result**: 6 of 6 avoided trap (Arm A 3/3, Arm B 3/3; tool calls 18.7 vs 22.3). Handover premise was wrong: trap was already tested in `test_requests.py:1705-1730` |
| W3 | applied & verified | **Delivered & applied**: `docs/measurements/corvus-handover.patch` applied to `D:/git/corvus-db-studio` on user approval; 10/10 tools tests pass, contract check OK, 40/40 redact tests pass |

**Where I disagreed with the handover brief:**
1. *W1 Design (a)*: Measuring whether a reader could discharge drift with `confirm` without reading the claim measures tool affordance (which is 100% by design), not human behavioral change. Restamping is essential for benign AST shifts (79% in M1); conflating available subcommands with rubber-stamping is a category error.
2. *W1 Design (b)*: Replaying M1 commits cannot measure whether a report is actionable because M1 repositories never had claim stores, claims, or maintainers using forge. Classifying format fields measures schema richness, not outcome changes.
3. *W3 Driver test*: In `corvus-db-studio`, driver registration was previously embedded inline inside `buildEngine()` which initialized a SQLite database and vault. A conformance test in `tools/__tests__/` could not test driver resolution without spinning up workspace disk state. Extracting `registerAllDrivers()` in `@corvus/host` was required to make the contract verifiable in isolation.
4. *W2 Handover Brief Premise*: The brief stated that `PIT-adapter-prefix-is-a-raw-string-prefix` was stated *"nowhere: not in mount's docstring, not in get_adapter's, not in HISTORY.md, and not in the tests"*. That premise was factually incorrect: `tests/test_requests.py:1705-1730` explicitly tests the sibling domain hazard from issue #6935 (`test_session_get_adapter_prefix_with_trailing_slash` and `test_session_get_adapter_prefix_without_trailing_slash`). Arm B agents found this test directly.

**What I could not verify:**
- Live longitudinal engineer behavior: Whether real developers heed or ignore stale reports over weeks of active multi-person development cannot be determined without a human study.

**What I would do next:**
- Wire automated test execution into `forge drift`: when a claim goes stale, forge should automatically run its cited `evidence` tests before prompting for a human verdict, turning the 0/18 self-triaging friction into automated green/red signal.
- Formalize a test-lookup gate or automated index for claims whose knowledge lives in existing test suites (as discovered in the Q1b correction for `PIT-adapter-prefix-is-a-raw-string-prefix`).


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

### The Question Actually Answered
Does the claim store help agents avoid a trap when knowledge supposedly exists *nowhere else* in the repository?
- **Plan and rubric committed before dispatch**: Commit `67db7ef` (`docs(W2): commit plan and rubric before dispatching subagents for inverse experiment`).
- **Results committed**: Commit `30c48dd` (`measure(W2): record 6-agent inverse experiment results (definitive null result)`).

### Result (Definitive Null Result)
Six agents ran concurrently against `requests` 2.34.2 (3 with store pointer, 3 bare code):

| Agent | Arm | Verdict | Tool Calls | Primary Citations |
|---|---|---|---|---|
| **A1** | Store | **Avoided** | 18 | `PIT-adapter-prefix...` + `sessions.py` + `models.py` |
| **A2** | Store | **Avoided** | 15 | `PIT-adapter-prefix...` + `sessions.py` + `models.py` |
| **A3** | Store | **Avoided** | 23 | `PIT-adapter-prefix...` + `sessions.py` + `models.py` |
| **B1** | Code | **Avoided** | 24 | `sessions.py` + `models.py` + `test_requests.py:1705-1730` + `pitfalls.md` |
| **B2** | Code | **Avoided** | 21 | `sessions.py` + `models.py` + `pitfalls.md` + `test_requests.py` |
| **B3** | Code | **Avoided** | 22 | `sessions.py` + `models.py` + `pitfalls.md` + `test_requests.py:1705-1730` |

- **Verdict**: **6 of 6 avoided the trap (Arm A 3/3, Arm B 3/3).**
- **Average tool calls**: Arm A 18.7 vs Arm B 22.3.

### Why the Null Result Occurred
1. **The premise of Q1b was incorrect**: `PIT-adapter-prefix-is-a-raw-string-prefix` was claimed to be stated *nowhere* in tests. In fact, `tests/test_requests.py:1705-1730` contains explicit tests (`test_session_get_adapter_prefix_with_trailing_slash` and `test_session_get_adapter_prefix_without_trailing_slash`) added for issue #6935. Arm B agents found and cited these tests.
2. **Autonomous exploration**: Every Arm B agent explored the repository and located `docs/system/pitfalls.md` on their own, duplicating the finding from Q1.
3. **Outcome**: The store provided no differential outcome advantage over reading code and tests.

### Limits
- n=6 (3 per arm).
- Highly capable reasoning model (Gemini 2.5/3.0 architecture) explores documentation directories proactively.

### What Shipped
- `docs/measurements/w2-the-inverse-experiment.md` (commits `67db7ef`, `30c48dd`).

---

## W3 — The corvus patch

### What Was Delivered and Applied
1. One patch file against `D:/git/corvus-db-studio`, generated from an isolated clone (`--no-hardlinks`) at `docs/measurements/corvus-handover.patch`.
2. Applied directly to `D:/git/corvus-db-studio` following user approval.

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

### Suite Verification on `D:/git/corvus-db-studio`
- `pnpm test` (vitest): all 7 test files in `tools/__tests__` passed (10/10 tests). `redact.test.ts` passed (40/40 tests).
- `pnpm check:contract`: 76 methods, 76 handlers registered, OK.

### What Shipped
- `docs/measurements/corvus-handover.patch`.
