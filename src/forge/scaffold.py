"""Templates, and the scaffold `forge init` writes.

Two rules the templates follow, both learned from the corpus:

**A generated claim is deliberately invalid.** Every template carries
`{placeholder}` tokens, and S9 rejects those. So a claim created and not
written fails `forge check` with a line number and a fix - which is the
behaviour you want, because the alternative is a store that fills up with
headings nobody finished. The placeholders are the checklist.

**The scaffold contains no claims.** `forge init` writes empty, titled files
and one ADR recording the adoption. Generating plausible starter claims for a
codebase nobody has read is precisely the failure the candidates tier exists to
prevent (SYSTEM_KNOWLEDGE.md section 2.4); that job belongs to `forge
bootstrap`, which routes its guesses through review.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from . import change, schema, skills, store
from .config import CONFIG_PATH

__all__ = ["claim_template", "adr_template", "init_files", "scaffold", "KIND_FILE"]

#: Which store file each kind belongs in. `forge claim new --append` uses it,
#: and so does the reader who wants to know where to look.
KIND_FILE = {
    "architecture": "architecture.md",
    "component": "components.md",
    "concept": "domain.md",
    "invariant": "domain.md",
    "pitfall": "pitfalls.md",
}

_PREFIX_FOR_KIND = {kind: prefix for prefix, kind in store.KIND_PREFIXES.items()}

# Per kind: the fields beyond the mandatory five, and the prompt that says what
# the prose has to earn. The prompts are the actual product here - a template
# whose body says "describe the component" produces the directory listing S14
# exists to catch.
#
# Placeholders are quoted. An unquoted `{path}` opens a YAML flow mapping and
# the whole fence stops parsing - a template the parser cannot read is not a
# template, which is what the round-trip test exists to catch.
_EXTRA_FIELDS = {
    "architecture": 'governs:  ["{governed-id}"]\nsince:    "ADR-{nnnn}"\n',
    "component": 'governs:  ["{governed-id}"]\n',
    "concept": "",
    "invariant": 'evidence:\n  - test: "{path}::{test name}"\n',
    "pitfall": "",
}

_PROSE_PROMPT = {
    "architecture": (
        "What must be respected, and in which direction. Then the consequence of\n"
        "inverting it - not that it would be 'bad practice', but what specifically\n"
        "stops working. An architecture claim with no consequence is a preference."
    ),
    "component": (
        "What this component is responsible for deciding, and where its boundary\n"
        "runs. Not which files it contains: `ls` answers that, and a claim that\n"
        "only answers it is flagged (S14)."
    ),
    "concept": (
        "What the word means here, and - the half that does the work - what it is\n"
        "*not*. Name the neighbouring concept it is most often confused with, and\n"
        "what goes wrong when the two are treated as one."
    ),
    "invariant": (
        "The property, stated so a test could fail it. Then what the property is\n"
        "quantified over (each item, or the sum?), and what happens at the\n"
        "boundary - rejected, clamped, or queued. That last detail is the one that\n"
        "gets implemented wrong."
    ),
    "pitfall": (
        "What was got wrong, and what it cost. A pitfall is knowledge that was\n"
        "paid for by a failure; write the failure down, because that is the part\n"
        "no static analysis can recover and the part that makes anyone believe it."
    ),
}

_ANCHORS = {
    "concept": "anchors:  []              # vocabulary has no single home; [] is legal here",
}
_DEFAULT_ANCHORS = 'anchors:  ["{path}#{Symbol}"]'

_TRUTH_SOURCE = {
    "architecture": "decision",
    "component": "decision",
    "concept": "decision",
    "invariant": "tests",
    "pitfall": "decision",
}


def claim_template(kind: str, identifier: str | None = None, title: str | None = None,
                   *, today: _dt.date | None = None) -> str:
    """One claim skeleton, ready to be filled in and not before."""
    if kind not in KIND_FILE:
        raise ValueError(
            f"{kind!r} is not an MVP claim kind; use one of {', '.join(sorted(KIND_FILE))}"
        )
    today = today or _dt.date.today()
    prefix = _PREFIX_FOR_KIND[kind]
    identifier = identifier or f"{prefix}-{{slug}}"
    return (
        # An ASCII hyphen, not the em dash the design documents use: this
        # template is *printed*, and the target console is cp1252, where an em
        # dash renders as a question mark. The heading grammar accepts either,
        # so the generated form is the one that survives the terminal.
        f"### {identifier} - {title or '{one line, stating the claim itself}'}\n"
        f"\n"
        f"```claim\n"
        f"kind:     {kind}\n"
        f"status:   asserted        # enforced only once `evidence` names a failing check\n"
        f"truth-source: {_TRUTH_SOURCE[kind]}\n"
        f"{_ANCHORS.get(kind, _DEFAULT_ANCHORS)}\n"
        f"{_EXTRA_FIELDS[kind]}"
        f"reviewed: {today.isoformat()}\n"
        f"```\n"
        f"\n"
        f"{_PROSE_PROMPT[kind]}\n"
    )


def adr_template(number: int, title: str | None = None,
                 *, today: _dt.date | None = None) -> str:
    """One ADR. Never edited once accepted - superseded instead (section 3.1)."""
    today = today or _dt.date.today()
    return (
        f"# ADR-{number:04d} - {title or '{the decision, as a sentence}'}\n"
        f"\n"
        f"- Date: {today.isoformat()}\n"
        f"- Status: Proposed\n"
        f"\n"
        f"## Context\n"
        f"\n"
        f"What was true that forced a decision. Constraints and the deadline, if one\n"
        f"applied - a decision read later without its pressure always looks wrong.\n"
        f"\n"
        f"## Decision\n"
        f"\n"
        f"What was decided, in the imperative.\n"
        f"\n"
        f"## Alternatives considered\n"
        f"\n"
        f"Each with the reason it lost. An ADR with no rejected alternative records\n"
        f"a preference rather than a decision.\n"
        f"\n"
        f"## Consequences\n"
        f"\n"
        f"What this makes easy, what it makes hard, and which claims it creates or\n"
        f"changes. Cite them by ID.\n"
    )


_OVERVIEW = """\
# System overview

One screen. What this system is for, who uses it, and the two or three facts a
newcomer needs before any other document makes sense.

This file is loaded into every agent context, so it is under a hard line budget
together with the claim files beside it (S16). When it grows, something moves
out - the budget is never raised.
"""

_STORE_FILES = {
    "architecture.md": (
        "# Architecture\n\n"
        "`ARC-` claims: what structure must be respected. Dependency direction,\n"
        "layering, what may not talk to what. Each needs an ADR (S7).\n"
    ),
    "components.md": (
        "# Components\n\n"
        "`CMP-` claims: the named parts and what each is responsible for deciding.\n"
        "Not a directory listing - that is what S14 is hostile to.\n"
    ),
    "domain.md": (
        "# Domain\n\n"
        "`CON-` claims: what the domain words mean here, and what they are not.\n"
        "`INV-` claims: properties that must always hold, each discharged by a\n"
        "named test.\n"
    ),
    "pitfalls.md": (
        "# Pitfalls\n\n"
        "`PIT-` claims: what people and agents keep getting wrong here, and what it\n"
        "cost. The highest value per line in the store, because it is the only kind\n"
        "no analysis can recover from the code.\n"
    ),
}

_CONFIG = """\
# forge configuration. Every key has a default; delete the file to use them all.
version: 1

# Pinned kernel version so this repository can detect version skew (Q11).
kernel_version: "0.0.1"

derive:
  # Paths the derived tier does not describe, on top of the built-in vendor and
  # build exclusions. Use for code this project does not own.
  exclude: []
  # Paths whose ID-looking strings are data rather than declarations - test
  # fixtures, mostly. These still count in the inventory; only the `@covers`
  # and `forge:<ID>` harvest skips them.
  # Note: Excluding a test directory means @covers tags in those tests will
  # not be harvested, so requirement and invariant coverage cannot be satisfied.
  exclude_id_scan: []

budgets:
  # The always-loaded set: OVERVIEW.md plus the mandatory claim files. Lower it
  # if you like; raising it is not a fix for being over it.
  always_loaded_lines: 400

thresholds:
  # How many recent changes the orphan check looks back over.
  orphan_change_window: 20
"""

_ADOPTION_ADR = """\
# ADR-0001 - Adopt an anchored claim store

- Date: {date}
- Status: Accepted

## Context

Knowledge about this system was spread across prose documents that nothing
checked. Prose cannot be verified, so it drifts silently and is then either
trusted when it is wrong or ignored when it is right.

## Decision

System knowledge lives in anchored claims under `docs/system/`, each pointing
at the code it describes, each checked by `forge check`. Staleness is detected
deterministically against those anchors; no model decides whether a claim is
still true.

## Alternatives considered

- **Keep free prose and review it periodically.** Rejected: review debt is
  invisible, so the review never happens on the documents that need it.
- **Let a model check the documentation against the code.** Rejected on
  measurement: models detect documentation faults well when the prose changed
  and badly when only the implementation did, which is the case that matters.

## Consequences

Every change must account for the claims its diff touches, which is new work at
the point of change and is the entire point. Nothing here is enforced until the
first claims exist - run `forge bootstrap`, or write them as you learn them.
"""


def init_files(today: _dt.date | None = None) -> dict[str, str]:
    """Relative path -> content for a fresh scaffold. Pure; writes nothing."""
    today = today or _dt.date.today()
    files = {
        CONFIG_PATH: _CONFIG,
        # Written out rather than left implicit: the kernel would happily use
        # its built-in copy forever, but a workflow you cannot see is a
        # workflow you cannot edit, and editing it is the whole point of
        # workflows being data.
        f"{schema.SCHEMA_DIR}/feature.yaml": schema.builtin_schema_text("feature"),
        f"{schema.SCHEMA_DIR}/bugfix.yaml": schema.builtin_schema_text("bugfix"),
        f"{store.STORE_DIR}/OVERVIEW.md": _OVERVIEW,
        f"{store.DECISIONS_DIR}/ADR-0001-adopt-forge.md":
            _ADOPTION_ADR.format(date=today.isoformat()),
    }
    for name, body in _STORE_FILES.items():
        files[f"{store.STORE_DIR}/{name}"] = body
    # The skills are copied out rather than left packaged, for the same reason
    # the workflow schema is: a procedure you cannot see is one you cannot
    # adapt, and the whole point of skills being markdown is that a project
    # edits them. A project that deletes the copy falls back to the shipped
    # set, so this is an opt-in fork rather than a commitment.
    for path in sorted(skills.PACKAGED_SKILLS.glob("*/SKILL.md")):
        files[f"{skills.SKILLS_DIR}/{path.parent.name}/SKILL.md"] = \
            path.read_text(encoding="utf-8")
    return files


def scaffold(repo: Path, *, today: _dt.date | None = None) -> tuple[list[str], list[str]]:
    """Write the scaffold. Returns (created, skipped).

    Never overwrites. `forge init` on a repository that already has a store is
    a normal thing to run - after a version bump, or to add a file the project
    did not need before - and a scaffolder that clobbers is one nobody runs
    twice.
    """
    created: list[str] = []
    skipped: list[str] = []
    for relative, content in sorted(init_files(today).items()):
        target = repo / relative
        if target.exists():
            skipped.append(relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        created.append(relative)
    return created, skipped


# ---------------------------------------------------------------------------
# Change artifact templates
# ---------------------------------------------------------------------------
#
# The workflow schema has declared `template:` for five artifacts since M3.
# Nothing read it, and no template existed, so every artifact was written from
# an empty file with only the schema's one-paragraph `instruction` for guidance.
# A field that is parsed, validated and never read is a promise the loader
# keeps and the tool breaks.
#
# Each template opens with `TEMPLATE_MARKER`. Deleting that line is what turns
# the file from a scaffold into an artifact - see `Change.state`.

_T_REPRODUCE = """\
{marker}
# Reproduction - {title}

## Failing test

The test that proves the bug exists before any fix is attempted.

- Test: `tests/...`
- Command: `pytest -q ...`

```
(paste failing assertion or stack trace here)
```

## Expected vs Actual

- Expected:
- Actual:

## Associated Claim

- Claim: `PIT-...` (or `INV-...`)
"""

_T_PROPOSAL = """\
{marker}
# Proposal - {title}

## Why

One or two sentences. What is wrong, or missing, today.

## What changes

- Each bullet a visible change. Mark a breaking one **BREAKING**.

## Capabilities

- Added / Modified / Removed, each by exact existing path.

## Not in this change

What a reader might reasonably expect here and will not find, and why.
"""

_T_SPEC = """\
{marker}
# {title}

## Purpose

What this capability is for, in a sentence a reader outside the change can use.

## ADDED Requirements

### Requirement: REQ-{slug}-1 - one line saying what must be true

The system SHALL ... . Behaviour only - never how it is implemented.

#### Scenario: the ordinary case

- Given ...
- When ...
- Then ...

#### Scenario: the case that makes it worth writing down

- Given ...
- When ...
- Then ...

## MODIFIED Requirements

Delete this section if nothing is modified. A MODIFIED block carries the
requirement's whole new text, never a diff fragment.

## REMOVED Requirements

Delete this section if nothing is removed. Each entry carries Reason and
Migration.
"""

_T_IMPACT = """\
{marker}
# Impact - {title}

## Blast radius

Run `forge impact --change <n>` and read the result here: what changed, and
what the import graph reaches from it.

## Claims touched

Every claim `forge impact` computes must appear below exactly once.

### Unaffected

- ID - one honest sentence saying why this change does not disturb it.

### Updated

### New

### Superseded

### At risk
"""

_T_DESIGN = """\
{marker}
# Design - {title}

## Approach

How, in enough detail that the task list falls out of it.

## Alternatives rejected

- **The obvious other way.** Why not.

## What this change does not decide

The questions a reader will have that this change deliberately leaves open.

## ADR

The decision this change records, or `None.` and why no ADR is needed.
"""

_T_TASKS = """\
{marker}
# Tasks - {title}

Each task on one physical line, naming the `REQ-` id it discharges, or marked
a chore. Work naming no requirement is work nobody agreed to.

- [ ] REQ-...: the first thing to do.
- [ ] Chore: something real that discharges no requirement.
"""

CHANGE_TEMPLATES = {
    "reproduce": _T_REPRODUCE,
    "proposal": _T_PROPOSAL,
    "spec": _T_SPEC,
    "impact": _T_IMPACT,
    "design": _T_DESIGN,
    "tasks": _T_TASKS,
}


def change_template(artifact: str, title: str, *, stem: str = "") -> str | None:
    """The starting text for one change artifact, or None if it has no template.

    `verification.json` deliberately has none: it is generated by `forge
    verify`, and a template for it would be a place to write a result by hand.
    """
    body = CHANGE_TEMPLATES.get(artifact)
    if body is None:
        return None
    return body.format(marker=change.TEMPLATE_MARKER, title=title,
                       slug=stem or change.slugify(title) or "capability")
