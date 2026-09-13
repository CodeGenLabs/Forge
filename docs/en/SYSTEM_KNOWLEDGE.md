# SYSTEM_KNOWLEDGE.md — Anchored System Knowledge

How Forge maintains verifiable, machine-anchored system knowledge without document rot.

---

## 1. The Anchored Claim Model

A claim represents a verified fact, invariant, or architectural boundary:

```claim
kind: invariant | concept | architecture | domain | api
status: candidate | ratified | superseded | retired
truth-source: tests | code | adr | config
anchors:
  - path/to/file.py#symbol_name@commit_sha
evidence:
  - test: tests/test_file.py::test_case
governs: [CMP-component-id]
since: ADR-0001
reviewed: YYYY-MM-DD
```

### Claim Kinds:
- **`invariant`**: Non-negotiable system rules (e.g. balances cannot be negative).
- **`architecture`**: Component boundaries and dependency constraints.
- **`domain`**: Core business concepts and workflows.
- **`api`**: Public contracts and protocols.
- **`concept`**: Shared mental models and definitions.

---

## 2. AST Fingerprinting

Rather than matching fragile line numbers, Forge uses Tree-Sitter grammars:
1. Locates the named symbol AST node.
2. Normalizes whitespace, docstrings, and formatting differences.
3. Generates a cryptographic digest of structural tokens.
4. If code formatting changes, fingerprint remains identical.
5. If syntax/behavior structure changes, fingerprint changes ➔ flags STALE immediately.

---

## 3. The Claim-Touch Set

When a change diff is submitted:
$$\text{Diff Files & Symbols} \cap \text{Claim Anchors} = \text{Touch Set}$$

- **Zero guess work:** The system knows precisely which claims the author modified.
- **Mandatory accounting:** `impact.md` must declare `unaffected`, `updated`, or `superseded` for every touched claim.
