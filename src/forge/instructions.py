"""`forge instructions`: resolving an artifact's `reads` contract.

ARCHITECTURE.md calls this the single most important structural difference
from every prompt-first framework in the corpus, and the claim is narrow
enough to be worth restating exactly: **what a phase is entitled to read is a
property of the data model, not of the prompt.** The DAG declares it, the
kernel resolves it, and a phase that wants more has to change the schema -
where the change is visible - rather than quietly widening a paragraph.

Three selector shapes, from ARCHITECTURE.md section 4.1:

- a path, with `${change}` substituted and globs expanded;
- `derived: [deps, inventory]`, naming artifacts of the derived tier;
- `claims: metadata` for the whole store's index, or
  `claims: "${impact.claims_touched}"` for the bodies of exactly the claims
  this change reaches.

The last one is the point. `design` reads the claims the change actually
touches - not all of them, not a summary, not whatever fit - and that set is
computed, so it cannot drift from what `impact.md` had to account for.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import change, derive, impact, schema, store

__all__ = ["resolve", "InstructionError"]

_SELECTOR_RE = re.compile(r"\$\{(?P<name>[a-z][a-z0-9_.]*)\}")
_TEMPLATE_DIR = ".forge/templates"


class InstructionError(ValueError):
    """An artifact was asked for that the workflow does not declare."""


def _substitute(text: str, item: change.Change) -> str:
    # The schema writes `changes/${change}/proposal.md`, so the variable is
    # the change's *name* and not its path - substituting the path yields
    # `changes/changes/0001-x/...`, which silently resolves to nothing and
    # makes the contract look empty rather than broken.
    return text.replace("${change}", item.name)


def _expand(repo: Path, pattern: str) -> list[str]:
    if any(ch in pattern for ch in "*?["):
        matched = set(repo.glob(pattern))
        if pattern.endswith("/**"):
            matched.update(repo.glob(pattern[:-3] + "/**/*"))
            matched.update(repo.glob(pattern[:-3] + "/*"))
        return sorted(p.relative_to(repo).as_posix()
                      for p in matched if p.is_file())
    return [pattern] if (repo / pattern).is_file() else []


def _claim_metadata(claims: list[store.Claim]) -> list[dict]:
    """Enough to decide what to read next, and no prose.

    The index, not the content: a phase that needs a claim's reasoning asks
    for it by id. Handing over every body 'just in case' is how a context
    contract becomes a context dump.
    """
    return [
        {"id": c.id, "kind": c.kind, "status": c.status, "title": c.title,
         "defined_in": f"{c.file}:{c.line}", "anchors": c.anchors,
         "candidate": c.is_candidate}
        for c in sorted(claims, key=lambda c: c.id)
        if not c.is_candidate
    ]


def _claim_bodies(claims: list[store.Claim], ids: list[str]) -> list[dict]:
    wanted = set(ids)
    return [
        {"id": c.id, "kind": c.kind, "status": c.status, "title": c.title,
         "defined_in": f"{c.file}:{c.line}", "anchors": c.anchors,
         "evidence": c.evidence, "governs": c.governs, "prose": c.prose}
        for c in sorted(claims, key=lambda c: c.id)
        if c.id in wanted
    ]


def resolve(repo: Path, item: change.Change, artifact_id: str,
            loaded: schema.Schema | None = None) -> dict:
    """Everything the named artifact's phase is entitled to, resolved."""
    loaded = loaded or schema.load_schema(repo, item.workflow)
    artifact = loaded.by_id(artifact_id)
    if artifact is None:
        raise InstructionError(
            f"{artifact_id!r} is not an artifact of the {loaded.name!r} workflow; "
            f"it declares {', '.join(loaded.ids)}"
        )

    requirement = artifact.requirement_for(item.track)
    states = {s.id: s for s in item.state(loaded)}
    waiting = states[artifact_id].waiting_on if artifact_id in states else []

    files: list[str] = []
    derived: list[str] = []
    claims_out: dict = {}
    unresolved: list[str] = []
    all_claims = store.load_store(repo)

    for entry in artifact.reads:
        if isinstance(entry, str):
            files.extend(_expand(repo, _substitute(entry, item)))
            continue
        if not isinstance(entry, dict):
            unresolved.append(repr(entry))
            continue
        for key, value in entry.items():
            if key == "derived":
                for name in (value if isinstance(value, list) else [value]):
                    path = f"{derive.DERIVED_DIR}/{name}.json"
                    if (repo / path).is_file():
                        derived.append(path)
                    else:
                        unresolved.append(f"derived:{name} (run `forge sync derived`)")
            elif key == "claims":
                claims_out = _resolve_claims(repo, item, value, all_claims, unresolved)
            else:
                unresolved.append(f"{key}:{value}")

    template = None
    if artifact.template:
        candidate = f"{_TEMPLATE_DIR}/{artifact.template}"
        template = candidate if (repo / candidate).is_file() else None

    return {
        "artifact": artifact.id,
        "change": item.name,
        "track": item.track,
        "required": requirement,
        "generates": f"{item.relative}/{artifact.generates}" if artifact.generates else None,
        "template": template,
        "instruction": artifact.instruction,
        "blocked_by": waiting,
        "reads": {
            "files": sorted(set(files)),
            "derived": sorted(set(derived)),
            "claims": claims_out,
        },
        "unresolved": sorted(set(unresolved)),
    }


def _resolve_claims(repo: Path, item: change.Change, value: object,
                    all_claims: list[store.Claim], unresolved: list[str]) -> dict:
    if value == "metadata":
        return {"mode": "metadata", "entries": _claim_metadata(all_claims)}

    if isinstance(value, list):
        ids = [str(v) for v in value]
        return {"mode": "ids", "entries": _claim_bodies(all_claims, ids)}

    text = str(value)
    match = _SELECTOR_RE.fullmatch(text.strip())
    if match and match.group("name") == "impact.claims_touched":
        # Computed, not read out of impact.md: the two must agree, and the
        # computation is the half that cannot be edited to say less.
        ids = sorted(impact.compute_impact(repo, item).touched)
        return {"mode": "impact.claims_touched", "ids": ids,
                "entries": _claim_bodies(all_claims, ids)}

    if match:
        unresolved.append(f"claims:{text} (no such selector)")
        return {}
    return {"mode": "ids", "entries": _claim_bodies(all_claims, [text])}
