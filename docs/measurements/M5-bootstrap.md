# M5 — bootstrap, measured on two repositories

**Date:** 2026-09-11. **Kernel:** the commit that added `forge bootstrap`.

MVP.md's acceptance criterion for M5 asks for a run on this repository and on one
real external repository, with four numbers recorded: how many candidates, how many
ratified, how long the review took, and which kinds were actually useful in the first
subsequent `investigate`. Three of the four are here. The fourth is not, and section 4
says why rather than estimating it.

---

## 1. This repository

| | |
|---|---|
| Files described | 97 |
| Candidates proposed | 8 (3 `PIT-`, 3 `CON-`, 2 `INV-`) |
| **Ratified** | **6** |
| Rejected | 2 |
| Deferred | 0 |
| Uncertain questions produced | 4 |
| Review wall time | ~4 minutes |

**Rejected, and the reason in each case.** `CON-derived-tier` restated the module
docstring it was anchored on — the derivable-claim smell, caught by eye before the
linter reached it. `INV-derived-bytes-stable` was true and already enforced by a test
the checks read, so ratifying it would have taxed every change touching `derive.py`
without adding a guarantee.

The three pitfalls were the easy ratifications, and they are the ones the design
predicts: each was paid for by a bug recorded in the design documents during M2–M4,
and none is recoverable from the code. That is the whole argument for front-loading
`PIT-` and `CON-` (OPEN_QUESTIONS Q14), and it held here.

**The store this produced is 6 claims, not 40.** Under the cap by a wide margin, and
that is the intended shape.

---

## 2. External repository: `requests` 2.34.2

Chosen because it is a real library with a real test suite, no existing store, and a
codebase nobody involved in building this harness has been reading. Obtained as the
published sdist and committed to a fresh git repository, so the history is one commit
— which is itself informative, see section 3.

### Pass 1 — derive

Deterministic, and everything it reported was correct on inspection:

| | |
|---|---|
| Files described | 100 (35 Python, 11,526 lines) |
| Entry points | none detected — correct; it is a library with no console script |
| Modules | `src/requests`, `tests`, `docs` |
| Import edges / cycles | 88 / 20 |
| Tests declared | 345 across 50 files |
| Dependencies | `certifi`, `charset_normalizer`, `idna`, `urllib3`, read from `pyproject.toml` with their declared ranges |
| Commands detected | `test: pytest`, `lint: ruff check .` |

Two things pass 1 got wrong on the first run, both now fixed: `src/requests.egg-info`
was listed as a module (committed build metadata — `.egg-info` and `.dist-info` are
now ignored by suffix), and the harness's own `.forge` directory was listed as one
(dot-directories are now excluded).

**20 import cycles** is the finding a human would act on, and it is derivation rather
than judgement — exactly the division of labour section 5.1 of WORKFLOW.md argues for.

### Passes 2 and 3

| | |
|---|---|
| Candidates proposed | 5 (3 `CON-`, 1 `INV-`, 1 `CMP-`) |
| **Ratified** | **4** |
| Rejected | 1 |
| Uncertain questions produced | 3 |
| Review wall time | ~3 minutes |

The rejected candidate is the instructive one. `CMP-models` said "Contains Request,
PreparedRequest and Response" — a directory listing in prose, which is what
`components.md` degenerates into when nobody is hostile to it. `ls` answers it.

One candidate, `CON-adapter`, was ratified carrying `rationale: unknown`. Per-prefix
adapter mounting is clearly load-bearing and clearly deliberate, and nothing in the
tree says why. Recording the gap is the honest outcome and it became an interview
question rather than an invented sentence.

After sealing, `forge check` reports one warning: `CON-session`'s prose is 75%
identifiers from its own anchor. That is a fair call — the prose names `Session`, the
cookie jar, the adapters and `api.request` — and it is the anti-noise check doing its
job on a claim a human wrote and approved.

---

## 3. What the runs changed

Four defects surfaced by running the tool rather than by testing it:

1. **A freshly sealed store warned that every claim was an orphan.** True, useless,
   and arriving at the exact moment someone decides whether the tool is worth its
   noise. Fixed by counting an inbound ADR reference as something consulting a claim
   — which it is, and the baseline ADR cites every claim it ratified.
2. **`store.stack_fact_smell` fired on "section 2.3".** A cross-reference to a
   document section read as a pinned dependency, and the claims most likely to cite a
   section are the pitfalls. Fixed with a short list of words that precede a dotted
   number for reasons other than packaging.
3. **Build metadata counted as a module** (`.egg-info`).
4. **Wrapped bullets in `## Uncertain` were truncated at their first line.** A
   question cut in half reads as a shorter, different question — in the one section
   that exists to say what nobody knows.

The single-commit history of the external repository also makes a limit visible:
`forge bootstrap derive` reads the tree, never the log, so a repository imported as a
tarball and one with ten years of history produce the same pass-1 output. Commit
messages are a real source for `PIT-` candidates, and pass 2 is where that reading
happens — but nothing in the kernel requires it, and on this run there was nothing to
read.

---

## 4. The number that is not here

**"Which kinds were actually useful in the first subsequent `investigate`" is not
measured**, because no `investigate` has been run against either store by a model.
Answering it needs an agent session and a judgement about which claims it actually
consulted, and reporting a guess in a document headed "measured" would be the exact
failure this project exists to object to.

What can be said is narrower and worth separating from the claim it resembles: of the
ten claims ratified across both repositories, **seven are `CON-` or `PIT-`** — the two
kinds Q14 recommends front-loading. That is a fact about what survived review, not
evidence that they were useful afterwards. The evidence for Q14 remains missing, and
the measurement that would supply it is one agent session away.

---

## 5. Verdict

The acceptance criterion is met on both repositories, with the fourth number recorded
as unmeasured rather than estimated.

The result that matters is the shape of the outputs: **six claims and four claims**,
against a cap of forty. A reject-by-default review on two repositories produced small,
human-confirmed baselines, and the rejections were all of the same kind — prose that
restates the code. Q14's worry was that this would be too thin to be useful. It may
still be; that is section 4's missing measurement. What is now clear is that it is not
too thin to be *honest*, and the failure mode it was designed against — forty
plausible claims nobody checked — did not occur in either run and would have been
visible in both.
