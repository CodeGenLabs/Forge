"""Bootstrap: giving an existing repository a store it can trust.

This is where honesty matters most. A model reading an unfamiliar codebase
produces confident, plausible, partly wrong claims, and plausible-but-wrong
knowledge is worse than none - so the whole design of this module is about
making "we do not know" a first-class outcome rather than a gap something
fills in.

Three passes, and they are split by *who can be trusted with what*:

1. **derive** - no model, no claims. The stack, the modules, the entry points,
   the tests. All of it is derivation, none of it is knowledge, and none of it
   needs review. This is most of what a bootstrap is usually sold as.
2. **propose** - a skill, not kernel code. Parallel subagents write candidates
   with anchors, confidence, and the evidence they inferred from. The kernel's
   only job here is to check them (`forge check --scope candidates`).
3. **review** - a human ratifies, and **the default is reject**. The kernel
   writes the review sheet: ordered highest-value-kind first, batched, every
   verdict prefilled `reject`, with the agents' `## Uncertain` questions
   interleaved. The conversation is a skill; the ordering, the batching and
   the applying are here.

**The default is reject, and the cap is 40.** Baseline completeness is not the
goal - baseline trustworthiness is. Twelve ratified claims plus a complete
derived tier is a good outcome; forty half-checked claims is a liability that
surfaces six months later when one of them is wrong.

Per OPEN_QUESTIONS Q14, the review front-loads `PIT-` and `CON-`: a pitfall is
knowledge paid for by a failure and a concept fixes a word, both are
un-derivable, both are cheap to confirm, and both make the first
`investigate` noticeably better. Inferred component descriptions do not.
"""

from __future__ import annotations

import datetime as _dt
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import derive, gitio, store
from .anchor import AnchorError, parse_anchor
from .config import CONFIG_PATH

__all__ = [
    "REVIEW_FILE",
    "DEFAULT_CAP",
    "KIND_ORDER",
    "BATCH_SIZE",
    "Summary",
    "Verdict",
    "summarise",
    "detect_commands",
    "build_review",
    "read_review",
    "check_candidates",
    "seal",
]

REVIEW_FILE = "docs/system/candidates/REVIEW.md"

#: The claim cap in force at seal time. Not a limit on what a repository may
#: eventually hold - a limit on what one unattended scan may add to it.
DEFAULT_CAP = 40

#: Batches of at most eight, BMAD's rule. Past that a review becomes a list
#: someone scrolls rather than a set of decisions someone makes.
BATCH_SIZE = 8

#: Review order, highest value per line first (SYSTEM_KNOWLEDGE.md 2.2).
KIND_ORDER = ("pitfall", "concept", "invariant", "component", "architecture")

VERDICTS = ("ratify", "edit", "reject", "defer")

_UNCERTAIN_RE = re.compile(r"^##\s+Uncertain\s*$", re.M)
_ANY_H2_RE = re.compile(r"^##\s+", re.M)
_QUESTION_RE = re.compile(r"^\s*[-*]\s*(?P<text>\S.*?)\s*$", re.M)
# Anything at all inside the brackets, so a verdict nobody can read is
# *reported* rather than invisible. A stricter pattern would skip the line,
# the candidate would silently default to reject, and the person who wrote
# "yes please" would never learn that it did nothing.
_VERDICT_RE = re.compile(
    r"^[ \t]*[-*][ \t]*\[(?P<verdict>[^\]\n]*)\][ \t]*(?P<id>" + store.ID_PATTERN
    + r")\b(?P<rest>[^\n]*)$", re.M)
_RATIONALE_UNKNOWN_RE = re.compile(r"rationale:\s*unknown", re.I)
_BECAUSE_RE = re.compile(r"\b(because|in order to|the reason is|so that)\b", re.I)
_EVIDENCE_RE = re.compile(r"^\s*evidence[- ]from:\s*(?P<text>\S.*)$", re.M | re.I)


# ---------------------------------------------------------------------------
# Pass 1 - derive
# ---------------------------------------------------------------------------

@dataclass
class Summary:
    """What a scan can say, and nothing more."""
    head: str
    files_tracked: int
    files_considered: int
    by_language: dict
    entry_points: list[str]
    test_files: int
    tests_declared: int
    stack: dict
    modules: list[str]
    import_edges: int
    import_cycles: list[list[str]]
    commands: dict[str, str]
    not_derivable: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "head": self.head,
            "files_tracked": self.files_tracked,
            "files_considered": self.files_considered,
            "by_language": self.by_language,
            "entry_points": self.entry_points,
            "test_files": self.test_files,
            "tests_declared": self.tests_declared,
            "stack": self.stack,
            "modules": self.modules,
            "import_edges": self.import_edges,
            "import_cycles": self.import_cycles,
            "commands": self.commands,
            "not_derivable": self.not_derivable,
        }


#: Stated in the output of every derive run, because the most useful thing a
#: bootstrap can tell you is what it did *not* learn. WORKFLOW.md section 5.1
#: puts numbers on it: architecture ~40%, invariants ~25%, rationale ~5%,
#: pitfalls 0%. A bootstrap that emits confident claims about those four is
#: producing exactly the noise the harness exists to prevent.
NOT_DERIVABLE = [
    "component boundaries and what each part is responsible for - the "
    "directories suggest a shape, the responsibility is a judgement",
    "which properties are *required* rather than merely currently true",
    "why any of it is like this; rationale is not in the code",
    "the traps people keep falling into, which are earned from failures and "
    "not from a scan",
]


#: Labels that do not make a directory a module. Prose and configuration are
#: part of a repository and are not part of its architecture: a monorepo was
#: reporting `docs`, `docker`, `specs`, `scripts` and `tools` alongside `apps`
#: and `packages`, which is the repository's furniture listed as its shape.
_NOT_CODE_LABELS = frozenset({
    "markdown", "text", "other", "json", "yaml", "toml", "config",
    "lockfile", "sql", "css", "html",
})


def _module_roots(paths: list[str]) -> list[str]:
    """Top-level source directories, which is as far as a scan can honestly
    go towards "what are the modules".

    Dot-directories are excluded: `.forge`, `.github` and their kin are
    configuration, and listing them as modules would put the harness's own
    directory in a summary of the system it describes.

    A directory that holds only other directories is a *container*, and its
    modules are one level down. That was hardcoded as `src`, `lib`, `pkg` and
    `internal`; it is now structural, which is the same answer for those four
    and the right answer for a monorepo's `packages/` and `apps/`.
    """
    code = [p for p in paths
            if not p.split("/")[0].startswith(".")
            and derive.label_for_path(p) not in _NOT_CODE_LABELS]

    direct: set[str] = set()      # roots holding code files of their own
    nested: dict[str, set[str]] = {}
    for path in code:
        parts = path.split("/")
        if len(parts) < 2:
            continue
        if len(parts) == 2:
            direct.add(parts[0])
        else:
            nested.setdefault(parts[0], set()).add("/".join(parts[:2]))

    roots: set[str] = set()
    for root, children in nested.items():
        if root in direct:
            # It has code of its own, so the directory itself is the module.
            roots.add(root)
        else:
            roots.update(children)
    roots.update(direct - set(nested))
    return sorted(roots)


def summarise(repo: Path) -> Summary:
    inventory = derive.build_inventory(repo)
    deps = derive.build_deps(repo)
    tests = derive.build_tests(repo)
    interesting = [p for p in gitio.list_files_at(repo, "HEAD")
                   if not derive.is_ignored(p)]
    return Summary(
        head=gitio.rev_parse(repo, "HEAD"),
        files_tracked=inventory["files_tracked"],
        files_considered=inventory["files_considered"],
        by_language=inventory["by_language"],
        entry_points=inventory["entry_points"],
        test_files=len(inventory["test_files"]),
        tests_declared=tests["total_tests"],
        stack=inventory["stack"],
        modules=_module_roots(interesting),
        import_edges=sum(len(v) for v in deps["edges"].values()),
        import_cycles=deps["cycles"],
        commands=detect_commands(repo),
        not_derivable=list(NOT_DERIVABLE),
    )


def detect_commands(repo: Path) -> dict[str, str]:
    """Build, test, lint and typecheck, read off the project's own manifests.

    Only what a manifest states. Nothing is guessed from the presence of a
    file - `npm test` because a package.json exists is how a verification
    report goes green for a suite that never ran, and `forge verify` would
    rather report a condition unproven than proven by a command nobody chose.
    """
    found: dict[str, str] = {}

    package = repo / "package.json"
    if package.is_file():
        try:
            import json
            scripts = (json.loads(package.read_text(encoding="utf-8"))
                       .get("scripts") or {})
        except (OSError, ValueError):
            scripts = {}
        runner = "pnpm" if (repo / "pnpm-lock.yaml").is_file() else \
                 "yarn" if (repo / "yarn.lock").is_file() else "npm run"
        for key in ("build", "test", "lint", "typecheck"):
            if key in scripts:
                found[key] = f"{runner} {key}"

    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        tools = data.get("tool") or {}
        if "pytest" in tools and "test" not in found:
            found["test"] = "pytest"
        if "ruff" in tools and "lint" not in found:
            found["lint"] = "ruff check ."
        if "mypy" in tools and "typecheck" not in found:
            found["typecheck"] = "mypy ."

    if (repo / "go.mod").is_file():
        found.setdefault("build", "go build ./...")
        found.setdefault("test", "go test ./...")
        found.setdefault("lint", "go vet ./...")

    makefile = repo / "Makefile"
    if makefile.is_file():
        text = makefile.read_text(encoding="utf-8", errors="replace")
        for key in ("build", "test", "lint", "typecheck"):
            if re.search(rf"^{key}:", text, re.M):
                found.setdefault(key, f"make {key}")

    return {k: found[k] for k in sorted(found)}


# ---------------------------------------------------------------------------
# Candidate validation
# ---------------------------------------------------------------------------

def check_candidates(repo: Path, issue) -> list:
    """The four rules from WORKFLOW.md section 5.2.

    These run against candidates only. The ratified store has its own
    eighteen checks; these are the ones that decide whether a *guess* is even
    admissible, and each exists because of a specific way generated claims go
    wrong.
    """
    issues = []
    for claim in store.load_store(repo):
        if not claim.is_candidate:
            continue

        def error(message: str, fix: str, code: str = "candidate.invalid") -> None:
            issues.append(issue("ERROR", code, claim.file, message, fix,
                                line=claim.line, claim=claim.id))

        # 1. Anchors required, for every kind - including the ones the
        # ratified store exempts. A concept may be un-anchorable once a human
        # has agreed it is real; a *guessed* concept with nothing to point at
        # is a sentence, and there is no way to check it later.
        if not claim.anchors:
            error("a candidate with no anchor cannot be checked and cannot be "
                  "confirmed",
                  "anchor it on the code it was inferred from, or drop it - "
                  "`concept` is exempt once ratified, never while proposed",
                  code="candidate.no_anchor")
        else:
            for raw in claim.anchors:
                try:
                    parse_anchor(raw)
                except AnchorError as exc:
                    error(f"anchor {raw!r} is malformed: {exc}",
                          "an anchor is path[#Symbol], repository-relative",
                          code="candidate.no_anchor")

        # 2. Confidence, always. The tier exists so that "plausible" is a
        # state rather than something laundered into truth.
        if not claim.confidence:
            error("no `confidence`",
                  "high = the code says so plainly; medium = inferred from "
                  "behaviour; low = a pattern noticed twice",
                  code="candidate.no_confidence")

        # 3. No invented rationale.
        prose = _blank_fences(claim.prose)
        if _BECAUSE_RE.search(prose) and not _RATIONALE_UNKNOWN_RE.search(prose) \
                and not _EVIDENCE_RE.search(claim.prose):
            error("states a reason with no evidence line behind it",
                  "add `evidence-from: <what you read>`, or write "
                  "`rationale: unknown` - a guessed reason reads exactly like a "
                  "remembered one six months later",
                  code="candidate.invented_rationale")

        # 4. An invariant must name what enforces or proves it.
        if claim.kind == "invariant" and not claim.evidence:
            error("an invariant candidate names neither enforcing code nor a "
                  "proving test",
                  "name the test or the guard, or downgrade it to a question in "
                  "the `## Uncertain` section - whether a property is required "
                  "or merely currently true is not in the code",
                  code="candidate.unproven_invariant")
    return issues


def _blank_fences(text: str) -> str:
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Pass 3 - the review sheet
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    id: str
    verdict: str
    note: str = ""
    line: int = 0


def _uncertain_questions(repo: Path) -> dict[str, list[str]]:
    """The `## Uncertain` sections of the candidate files, by file.

    The most valuable part of a generation pass, and the part most easily
    lost: it is the only place the scan says what it could not determine.
    """
    out: dict[str, list[str]] = {}
    root = repo / store.CANDIDATES_DIR
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.md")):
        if path.name == Path(REVIEW_FILE).name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match = _UNCERTAIN_RE.search(text)
        if not match:
            continue
        rest = text[match.end():]
        following = _ANY_H2_RE.search(rest)
        section = rest[:following.start()] if following else rest
        questions = _bullets(section)
        if questions:
            out[path.relative_to(repo).as_posix()] = questions
    return out


def _bullets(section: str) -> list[str]:
    """Bullet items, with wrapped continuation lines joined back on.

    Matching per line would truncate every question at its first line, and a
    question cut in half reads as a shorter, different question - which is
    the opposite of useful in the one section that exists to say what nobody
    knows.
    """
    items: list[str] = []
    for line in section.split("\n"):
        stripped = line.strip()
        match = _QUESTION_RE.match(line)
        if match:
            items.append(match.group("text"))
        elif items and stripped and line[:1] in " \t":
            items[-1] = f"{items[-1]} {stripped}"
    return items


_PROSE_SUFFIXES = (".md", ".rst", ".txt", ".adoc")
_DOC_PATH_RE = re.compile(r"""[\w./\-]+\.(?:md|rst|txt|adoc)""", re.I)


def restates(claim: store.Claim) -> list[str]:
    """Prose documents this candidate's evidence points at.

    Not a defect and not a check - a fact the scan already knows, handed to
    the reviewer because Q1 showed it is the fact that decides the verdict.

    A claim derived from a rules document competes with that document for the
    same reader, and the reader usually finds the document. Measured in
    docs/measurements/q1-does-the-store-help.md: three agents pointed at the
    store and three pointed only at the code avoided the same trap at the same
    rate, and every agent in the second arm located the rules file unaided and
    cited the very section the claim had been derived from.

    A check cannot carry this. Firing on any doc-backed evidence would flag
    good claims - the claim under test named a conformance test as well, and
    was redundant anyway - so the rule is a judgement, and judgement belongs
    in pass 3 with a human in front of it.
    """
    seen: list[str] = []
    sources = list(claim.evidence)
    for match in _EVIDENCE_RE.finditer(claim.prose):
        sources.append(match.group("text"))
    for source in sources:
        for hit in _DOC_PATH_RE.findall(source):
            path = hit.lstrip("./")
            if path.lower().endswith(_PROSE_SUFFIXES) and path not in seen:
                seen.append(path)
    return seen


def _ordered_candidates(repo: Path) -> list[store.Claim]:
    def key(claim: store.Claim) -> tuple:
        rank = KIND_ORDER.index(claim.kind) if claim.kind in KIND_ORDER \
            else len(KIND_ORDER)
        return (rank, claim.file, claim.line)
    return sorted((c for c in store.load_store(repo) if c.is_candidate), key=key)


def build_review(repo: Path, *, cap: int = DEFAULT_CAP,
                 existing: str | None = None) -> str:
    """Render the review sheet. Verdicts already recorded are preserved."""
    kept = {v.id: v for v in read_review(existing)} if existing else {}
    candidates = _ordered_candidates(repo)
    questions = _uncertain_questions(repo)

    lines = [
        "# Candidate review",
        "",
        "Every verdict below starts at `reject`, and that is the posture, not a",
        "placeholder. Baseline completeness is not the goal; baseline",
        "trustworthiness is. Twelve ratified claims plus a complete derived tier",
        "is a good outcome, and forty half-checked ones is a liability that",
        "surfaces six months later when one of them is wrong.",
        "",
        f"Verdicts: {', '.join(f'`{v}`' for v in VERDICTS)}. `edit` means ratify",
        "after you change the prose; make the edit in the candidate file itself.",
        "",
        f"Cap in force: {cap} ratified claims from this bootstrap.",
        "",
        "A `restates:` line means the candidate was derived from a document",
        "already in this repository. That is not a defect - it is usually where",
        "the best candidates come from - but it is the fact most worth weighing:",
        "an agent that finds the document gets the knowledge without the claim,",
        "and then the claim is a second copy to keep in step with the first. Ask",
        "what the claim adds that its source does not. An anchor that goes stale",
        "when the code moves is a real answer; a shorter restatement is not.",
        "",
    ]

    if not candidates:
        lines += ["No candidates. Run the `bootstrap` skill's generation pass, or",
                  "seal an empty baseline - which is a legitimate outcome.", ""]

    for index in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[index:index + BATCH_SIZE]
        lines.append(f"## Batch {index // BATCH_SIZE + 1}")
        lines.append("")
        for claim in batch:
            previous = kept.get(claim.id)
            verdict = previous.verdict if previous else "reject"
            note = f"  {previous.note}" if previous and previous.note else ""
            lines.append(f"- [{verdict}] {claim.id} ({claim.kind}, "
                         f"confidence {claim.confidence or 'unset'}) - "
                         f"{claim.title or 'untitled'}{note}")
            lines.append(f"      anchors: {', '.join(claim.anchors) or 'none'}")
            lines.append(f"      defined: {claim.file}:{claim.line}")
            restated = restates(claim)
            if restated:
                lines.append(f"      restates: {', '.join(restated)} - would a "
                             "reader find that anyway?")
        lines.append("")

    if questions:
        # Interleaved with the batches in spirit and placed after them in
        # fact: they are read alongside, and a question that turns out to
        # settle a candidate is worth more than the candidate.
        lines += ["## Questions the scan could not answer", "",
                  "These are worth more than most of the candidates above. A scan",
                  "that says what it could not determine is telling you where to",
                  "look; one that quietly fills the gap is not.", ""]
        for path, items in sorted(questions.items()):
            lines.append(f"From `{path}`:")
            lines.extend(f"- {item}" for item in items)
            lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def read_review(text: str | None) -> list[Verdict]:
    if not text:
        return []
    out = []
    for match in _VERDICT_RE.finditer(text):
        out.append(Verdict(
            id=match.group("id"),
            verdict=(match.group("verdict") or "").strip().lower(),
            note=match.group("rest").strip(),
            line=text.count("\n", 0, match.start()) + 1,
        ))
    return out


# ---------------------------------------------------------------------------
# Seal
# ---------------------------------------------------------------------------

_BASELINE_HEADING = "## Baseline recorded by `forge bootstrap seal`"


@dataclass
class SealPlan:
    ratified: list[store.Claim] = field(default_factory=list)
    rejected: list[store.Claim] = field(default_factory=list)
    deferred: list[store.Claim] = field(default_factory=list)
    unknown_verdicts: list[Verdict] = field(default_factory=list)
    over_cap: list[store.Claim] = field(default_factory=list)
    writes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ratified": [c.id for c in self.ratified],
            "rejected": [c.id for c in self.rejected],
            "deferred": [c.id for c in self.deferred],
            "over_cap": [c.id for c in self.over_cap],
            "unknown_verdicts": [f"{v.id}:{v.verdict}" for v in self.unknown_verdicts],
            "writes": sorted(self.writes),
        }


def _ratified_text(claim: store.Claim, sha: str, today: _dt.date) -> str:
    """The claim as it will appear in its kind's file.

    Anchors stamped at HEAD and `reviewed` set to today, because this is the
    moment a human confirmed it - which is the only event that may ever set
    either field.
    """
    lines = [f"### {claim.id} - {claim.title}".rstrip(), "", "```claim",
             f"kind:     {claim.kind}",
             "status:   asserted",
             f"truth-source: {claim.truth_source or 'decision'}"]
    anchors = [f'"{a.split("@", 1)[0]}@{sha[:10]}"' for a in claim.anchors]
    lines.append(f"anchors:  [{', '.join(anchors)}]" if anchors else "anchors:  []")
    if claim.evidence:
        lines.append("evidence:")
        for entry in claim.evidence:
            kind, _, value = entry.partition(":")
            lines.append(f'  - {kind.strip()}: "{value.strip()}"')
    if claim.governs:
        lines.append(f"governs:  [{', '.join(claim.governs)}]")
    lines += [f"reviewed: {today.isoformat()}", "```", "", claim.prose.strip(), ""]
    return "\n".join(lines)


_KIND_FILE = {
    "architecture": "architecture.md", "component": "components.md",
    "concept": "domain.md", "invariant": "domain.md", "pitfall": "pitfalls.md",
}


def plan_seal(repo: Path, *, cap: int = DEFAULT_CAP,
              today: _dt.date | None = None) -> SealPlan:
    today = today or _dt.date.today()
    plan = SealPlan()
    sheet = repo / REVIEW_FILE
    verdicts = {v.id: v for v in read_review(
        sheet.read_text(encoding="utf-8", errors="replace") if sheet.is_file() else None)}

    by_kind: dict[str, list[str]] = {}
    for claim in _ordered_candidates(repo):
        verdict = verdicts.get(claim.id)
        decision = verdict.verdict if verdict else "reject"
        if decision not in VERDICTS:
            plan.unknown_verdicts.append(verdict)
            decision = "reject"
        if decision == "defer":
            plan.deferred.append(claim)
        elif decision in ("ratify", "edit"):
            if len(plan.ratified) >= cap:
                plan.over_cap.append(claim)
                continue
            plan.ratified.append(claim)
            by_kind.setdefault(_KIND_FILE.get(claim.kind, "domain.md"), []).append(
                _ratified_text(claim, gitio.rev_parse(repo, "HEAD"), today))
        else:
            plan.rejected.append(claim)

    for name, blocks in sorted(by_kind.items()):
        relative = f"{store.STORE_DIR}/{name}"
        target = repo / relative
        head = target.read_text(encoding="utf-8") if target.is_file() \
            else f"# {name.removesuffix('.md').title()}\n"
        plan.writes[relative] = head.rstrip("\n") + "\n\n" + "\n".join(blocks)

    plan.writes[f"{store.DECISIONS_DIR}/ADR-0001-adopt-forge.md"] = _adr(
        repo, plan, cap, today)
    overview = repo / store.STORE_DIR / "OVERVIEW.md"
    if not overview.is_file():
        plan.writes[f"{store.STORE_DIR}/OVERVIEW.md"] = _overview(repo)
    config = _config_with_commands(repo)
    if config is not None:
        plan.writes[CONFIG_PATH] = config
    return plan


def _adr(repo: Path, plan: SealPlan, cap: int, today: _dt.date) -> str:
    """ADR-0001, extended with what the baseline did *not* ratify.

    That half is the point. A store with no record of its own gaps is
    ambiguous between "nothing to say here" and "nobody looked", and those
    call for opposite responses from the next person.
    """
    target = repo / store.DECISIONS_DIR / "ADR-0001-adopt-forge.md"
    existing = target.read_text(encoding="utf-8") if target.is_file() else \
        "# ADR-0001 - Adopt an anchored claim store\n\n- Status: Accepted\n"
    existing = existing.split(_BASELINE_HEADING)[0].rstrip("\n")

    def listing(claims: list[store.Claim]) -> list[str]:
        return [f"- {c.id} ({c.kind}, confidence {c.confidence or 'unset'}) - "
                f"{c.title or 'untitled'}" for c in claims] or ["- none"]

    lines = [existing, "", _BASELINE_HEADING, "",
             f"- Date: {today.isoformat()}",
             f"- Commit: {gitio.rev_parse(repo, 'HEAD')}",
             f"- Cap in force: {cap} ratified claims from this bootstrap", "",
             "### Ratified", ""]
    lines += listing(plan.ratified)
    lines += ["", "### Proposed and not ratified", "",
              "Recorded because the absence of a claim should be explicit. A store",
              "with no record of its own gaps is ambiguous between \"nothing to say",
              "here\" and \"nobody looked\", and those call for opposite responses.",
              ""]
    lines += listing(plan.rejected + plan.deferred)
    lines += ["", "### Deliberately not attempted", ""]
    lines += [f"- {item}" for item in NOT_DERIVABLE]
    lines += ["",
              "The first change that touches an area will produce better knowledge",
              "about it than any scan, because the change has a reason, a test, and",
              "a human who cared. Bootstrap's job was to make that change possible,",
              "not to front-load a documentation project.", ""]
    return "\n".join(lines)


def _overview(repo: Path) -> str:
    summary = summarise(repo)
    languages = ", ".join(
        f"{name} ({data['files']} files)"
        for name, data in sorted(summary.by_language.items(),
                                 key=lambda kv: -kv[1]["lines"])[:3]) or "unknown"
    return (
        "# System overview\n"
        "\n"
        "> Written by `forge bootstrap seal` from what a scan can see. The facts\n"
        "> below are derived and true; the *purpose* is not something a scan can\n"
        "> know, and the first paragraph is the one a human has to replace.\n"
        "\n"
        "## What this system is for\n"
        "\n"
        "Unwritten. One paragraph: who uses this, and what would break for them\n"
        "if it stopped.\n"
        "\n"
        "## Shape\n"
        "\n"
        f"- {summary.files_considered} files the harness describes, mostly {languages}\n"
        f"- Entry points: {', '.join(summary.entry_points) or 'none detected'}\n"
        f"- {summary.tests_declared} declared tests across "
        f"{summary.test_files} files\n"
        "\n"
        "This file is loaded into every agent context, so it shares a hard line\n"
        "budget with the claim files beside it. When it grows, something moves\n"
        "out - the budget is never raised.\n"
    )


def _config_with_commands(repo: Path) -> str | None:
    """Add detected commands to the config, or None if it already has them.

    Never overwrites: a project that declared `commands.test` has chosen it,
    and a scan's guess losing to a human's choice is the correct direction.
    """
    commands = detect_commands(repo)
    if not commands:
        return None
    target = repo / CONFIG_PATH
    raw: dict = {}
    text = ""
    if target.is_file():
        text = target.read_text(encoding="utf-8")
        try:
            raw = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            return None
        if not isinstance(raw, dict):
            return None
    if isinstance(raw.get("commands"), dict) and raw["commands"]:
        return None
    block = ["", "# Detected by `forge bootstrap seal` from this project's manifests.",
             "# Nothing here was guessed from a file merely existing: an unproven",
             "# verification condition is better than one proven by a command",
             "# nobody chose.", "commands:"]
    block += [f"  {key}: {value}" for key, value in commands.items()]
    return (text.rstrip("\n") + "\n" if text else "version: 1\n") + "\n".join(block) + "\n"


def seal(repo: Path, *, cap: int = DEFAULT_CAP, today: _dt.date | None = None,
         dry_run: bool = False) -> SealPlan:
    plan = plan_seal(repo, cap=cap, today=today)
    if dry_run:
        return plan
    for relative, content in sorted(plan.writes.items()):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    # Ratified candidates are removed from the candidates tier, because a
    # claim that exists in both places is two claims with one ID - and the
    # store check would say so. Everything else stays: readable, not citable.
    _remove_ratified(repo, plan.ratified)
    return plan


def _remove_ratified(repo: Path, ratified: list[store.Claim]) -> None:
    by_file: dict[str, list[store.Claim]] = {}
    for claim in ratified:
        by_file.setdefault(claim.file, []).append(claim)
    for relative, claims in by_file.items():
        target = repo / relative
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8")
        for claim in sorted(claims, key=lambda c: -c.line):
            lines = text.split("\n")
            del lines[claim.line - 1:claim.end_line]
            text = "\n".join(lines)
        target.write_text(re.sub(r"\n{3,}", "\n\n", text).rstrip("\n") + "\n",
                          encoding="utf-8", newline="\n")
