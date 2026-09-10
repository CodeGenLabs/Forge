"""M1 measurement, part two: controlled perturbations on real code.

Replaying history (``measure_anchors.py``) tells us the *volume* of drift a
ledger would carry, but it cannot measure the false-positive rate we actually
fear: across 600 replayed commits in three real repositories there were almost
no pure renames and almost no formatting-only commits, because these projects
run formatters continuously. An empty population yields no rate, and reporting
"0 false positives" from an empty population would be dishonest.

So this harness borrows the method from arXiv:2604.03447 (the TRACE paper, which
we cite in RESEARCH.md for the opposite finding): take real code, inject
perturbations whose ground truth is known by construction, and measure.

Two families, and the interesting property is different for each:

* **neutral** - provably behaviour-preserving. Every verdict must be ``fresh``;
  any other verdict is a **false positive**, and false positives are what make a
  drift ledger noise.
* **substantive** - provably behaviour-changing. Every verdict must be non-fresh;
  a ``fresh`` verdict is a **false negative**, and false negatives are what make
  a drift ledger a lie.

Perturbations are applied through tree-sitter rather than by regex, so "rewrite
every comment" edits exactly the comment nodes and nothing else. That is what
makes the ground-truth label defensible.

Usage::

    python tools/perturb_anchors.py --repo ../some-repo --samples 40
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forge import gitio  # noqa: E402
from forge.anchor import Anchor, Status, classify  # noqa: E402
from forge.fingerprint import (  # noqa: E402
    _iter_declarations,
    grammar_for_path,
    language_for_path,
)

NEUTRAL = "neutral"
SUBSTANTIVE = "substantive"

_SKIP_SEGMENTS = {
    "node_modules", "vendor", "dist", "build", ".venv", "venv",
    "__pycache__", "third_party", "testdata", "generated",
}


def _interesting(path: str) -> bool:
    if language_for_path(path) is None:
        return False
    return not any(seg in _SKIP_SEGMENTS for seg in path.split("/"))


def _parse(source: bytes, path: str):
    grammar = grammar_for_path(path)
    if grammar is None:
        return None
    from tree_sitter import Parser

    return Parser(grammar.language).parse(source)


def _nodes(root, predicate):
    out = []
    stack = [root]
    while stack:
        node = stack.pop()
        if predicate(node):
            out.append(node)
        for i in range(node.child_count - 1, -1, -1):
            stack.append(node.child(i))
    return out


def _splice(source: bytes, edits: list[tuple[int, int, bytes]]) -> bytes:
    """Apply (start, end, replacement) byte edits, last-first so offsets hold."""
    out = source
    for start, end, replacement in sorted(edits, key=lambda e: -e[0]):
        out = out[:start] + replacement + out[end:]
    return out


# --------------------------------------------------------------------------
# Neutral perturbations - ground truth: behaviour unchanged
# --------------------------------------------------------------------------
#
# A correction the first run forced. "Add trailing whitespace to every line" is
# *not* behaviour-preserving when a line falls inside a multi-line string: a
# template literal, a docstring or a Go raw string carries its own whitespace as
# content, so touching it is a real change and the anchor is right to say so.
# The first run scored 17/171 "false positives" that were all this mistake in
# the ground truth, not a defect in the detector.
#
# So the line-based perturbations are literal-aware: they skip any line that
# intersects a multi-line literal. This keeps the "neutral" label true, which is
# the only thing that makes the rate mean anything.

_LITERAL_HINTS = ("string", "template", "heredoc")


def _protected_ranges(source: bytes, path: str) -> list[tuple[int, int]]:
    """Byte ranges of multi-line literals, whose whitespace is content."""
    tree = _parse(source, path)
    if tree is None:
        return []
    nodes = _nodes(
        tree.root_node,
        lambda n: any(hint in n.type for hint in _LITERAL_HINTS)
        and source.count(b"\n", n.start_byte, n.end_byte) > 0,
    )
    return [(n.start_byte, n.end_byte) for n in nodes]


def _line_spans(source: bytes) -> list[tuple[int, int, bytes]]:
    """(start, end, text) for each line, without its newline."""
    spans = []
    offset = 0
    for line in source.split(b"\n"):
        spans.append((offset, offset + len(line), line))
        offset += len(line) + 1
    return spans


def _intersects(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < r_end and r_start < end for r_start, r_end in ranges)


def _still_parses(source: bytes, path: str) -> bool:
    """Does this source still parse?

    The general guard against the bug class that produced every false positive
    in the first two runs: a "neutral" perturbation that actually produced
    invalid code, whose changed fingerprint was then scored against the
    detector. Any neutral case that fails this is discarded rather than counted,
    so a future perturbation bug shows up as a shrinking population instead of a
    fabricated defect.

    Tree-sitter is error-tolerant by design, so it is necessary but not
    sufficient: it happily parsed a Python file that CPython rejected with
    "expected an indented block". Where a real parser is available for the
    language, it is used as well.
    """
    tree = _parse(source, path)
    if tree is None or tree.root_node.has_error:
        return False
    if language_for_path(path) == "python":
        import ast

        try:
            ast.parse(source)
        except (SyntaxError, ValueError):
            return False
    return True


def p_rewrite_comments(source: bytes, path: str) -> bytes | None:
    """Replace the text of every comment node, preserving its delimiters.

    Applied through the parse tree, so it provably touches only comments.
    """
    tree = _parse(source, path)
    if tree is None:
        return None
    comments = _nodes(tree.root_node, lambda n: "comment" in n.type)
    if not comments:
        return None
    edits = []
    for node in comments:
        text = source[node.start_byte:node.end_byte]
        if text.startswith(b"//"):
            edits.append((node.start_byte, node.end_byte, b"// rewritten"))
        elif text.startswith(b"#"):
            edits.append((node.start_byte, node.end_byte, b"# rewritten"))
        elif text.startswith(b"/*"):
            edits.append((node.start_byte, node.end_byte, b"/* rewritten */"))
    return _splice(source, edits) if edits else None


def p_double_indent(source: bytes, path: str) -> bytes | None:
    """Double every line's leading whitespace.

    Uniform reindentation preserves semantics in all three languages, Python
    included: only the relative depth of a block matters.

    Skipped entirely on a file containing a multi-line literal. Doubling the
    code around a protected literal breaks the indentation relationship between
    them - CPython rejected a real sample with "expected an indented block after
    function definition", because the `def` line doubled while its docstring was
    held back. Tree-sitter is error-tolerant and parsed it anyway, so the only
    honest options are "skip the file" or "produce broken code and call it
    neutral". Skipping loses population; the alternative loses the label.
    """
    if _protected_ranges(source, path):
        return None
    out: list[bytes] = []
    changed = False
    for _start, _end, line in _line_spans(source):
        stripped = line.lstrip(b" \t")
        indent = line[: len(line) - len(stripped)]
        if indent and stripped:
            out.append(indent + indent + stripped)
            changed = True
        else:
            out.append(line)
    return b"\n".join(out) if changed else None


def p_blank_lines(source: bytes, path: str) -> bytes | None:
    """Insert a blank line after each top-level line, outside multi-line literals."""
    protected = _protected_ranges(source, path)
    out: list[bytes] = []
    changed = False
    for start, end, line in _line_spans(source):
        out.append(line)
        if line and not line[:1].isspace() and not _intersects(start, end, protected):
            out.append(b"")
            changed = True
    return b"\n".join(out) if changed else None


def p_trailing_whitespace(source: bytes, path: str) -> bytes | None:
    protected = _protected_ranges(source, path)
    out: list[bytes] = []
    changed = False
    for start, end, line in _line_spans(source):
        if line.strip() and not _intersects(start, end, protected):
            out.append(line + b"   ")
            changed = True
        else:
            out.append(line)
    return b"\n".join(out) if changed else None


def p_crlf(source: bytes, path: str) -> bytes | None:
    """Convert to CRLF line endings, outside multi-line literals.

    The classic cross-platform false positive - and the reason the exclusion
    matters: converting the newlines *inside* a template literal or a docstring
    genuinely changes the string, so an anchor is right to flag it.
    """
    if b"\r\n" in source:
        return None
    protected = _protected_ranges(source, path)
    pieces: list[bytes] = []
    cursor = 0
    changed = False
    while True:
        index = source.find(b"\n", cursor)
        if index == -1:
            pieces.append(source[cursor:])
            break
        pieces.append(source[cursor:index])
        if _intersects(index, index + 1, protected):
            pieces.append(b"\n")
        else:
            pieces.append(b"\r\n")
            changed = True
        cursor = index + 1
    return b"".join(pieces) if changed else None


def p_swap_quotes(source: bytes, path: str) -> bytes | None:
    """Swap double for single quotes on simple string literals (TS/Python).

    Triple-quoted strings are excluded. Slicing `text[1:-1]` off `\"\"\"Doc.\"\"\"`
    yields `'\"\"Doc.\"\"'` - a different string, not a requoted one - which is a
    real change that the detector was right to flag. That mistake accounted for
    13 of 25 "false positives" on Python in an earlier run.
    """
    lang = language_for_path(path)
    if lang not in ("typescript", "tsx", "python"):
        return None
    tree = _parse(source, path)
    if tree is None:
        return None
    strings = _nodes(tree.root_node, lambda n: n.type == "string")
    edits = []
    for node in strings:
        text = source[node.start_byte:node.end_byte]
        if len(text) < 2 or b"\\" in text or b"\n" in text:
            continue
        if text.startswith((b'"""', b"'''")) or text.endswith((b'"""', b"'''")):
            continue
        # A prefixed literal (f"", rb"") keeps its prefix outside the quotes,
        # so only bare `"..."` is safe to requote by slicing.
        if text.startswith(b'"') and text.endswith(b'"') and b"'" not in text:
            edits.append((node.start_byte, node.end_byte, b"'" + text[1:-1] + b"'"))
    return _splice(source, edits) if edits else None


# --------------------------------------------------------------------------
# Substantive perturbations - ground truth: behaviour changed
# --------------------------------------------------------------------------

def s_flip_operator(source: bytes, path: str, symbol_node) -> bytes | None:
    """Flip one arithmetic or comparison operator inside the target symbol."""
    swaps = {b"+": b"-", b"-": b"+", b"*": b"/", b"<": b">", b">": b"<",
             b"==": b"!=", b"!=": b"==", b"&&": b"||", b"||": b"&&",
             b"and": b"or", b"or": b"and"}
    ops = _nodes(
        symbol_node,
        lambda n: n.child_count == 0 and source[n.start_byte:n.end_byte] in swaps,
    )
    if not ops:
        return None
    node = ops[0]
    text = source[node.start_byte:node.end_byte]
    return _splice(source, [(node.start_byte, node.end_byte, swaps[text])])


def s_delete_body_statement(source: bytes, path: str, symbol_node) -> bytes | None:
    """Delete the last statement of the target symbol's body."""
    body = symbol_node.child_by_field_name("body")
    if body is None:
        return None
    statements = [
        body.child(i) for i in range(body.child_count)
        if body.child(i).is_named and "comment" not in body.child(i).type
    ]
    if len(statements) < 2:
        return None
    victim = statements[-1]
    return _splice(source, [(victim.start_byte, victim.end_byte, b"pass" if
                             language_for_path(path) == "python" else b";")])


def s_rename_symbol(source: bytes, path: str, symbol_node) -> bytes | None:
    """Rename the declaration itself - the anchor should report missing."""
    name = symbol_node.child_by_field_name("name")
    if name is None:
        return None
    return _splice(source, [(name.start_byte, name.end_byte,
                             source[name.start_byte:name.end_byte] + b"Renamed")])


NEUTRAL_PERTURBATIONS = {
    "rewrite_comments": p_rewrite_comments,
    "double_indent": p_double_indent,
    "blank_lines": p_blank_lines,
    "trailing_whitespace": p_trailing_whitespace,
    "crlf": p_crlf,
    "swap_quotes": p_swap_quotes,
}

SUBSTANTIVE_PERTURBATIONS = {
    "flip_operator": s_flip_operator,
    "delete_statement": s_delete_body_statement,
    "rename_declaration": s_rename_symbol,
}


@dataclass
class Sample:
    path: str
    symbol: str
    language: str
    source: bytes


def collect_samples(repo: Path, *, count: int, rng: random.Random) -> list[Sample]:
    out = gitio.git(repo, "ls-tree", "-r", "--name-only", "HEAD")
    paths = [p.strip() for p in out.splitlines() if p.strip() and _interesting(p.strip())]
    rng.shuffle(paths)

    samples: list[Sample] = []
    for path in paths:
        if len(samples) >= count:
            break
        blob = gitio.blob_at(repo, "HEAD", path)
        if blob is None or len(blob) > 200_000 or not blob.strip():
            continue
        tree = _parse(blob, path)
        lang = language_for_path(path)
        if tree is None or lang is None:
            continue
        candidates = [
            (name, node) for name, node in _iter_declarations(tree.root_node, lang)
            if node.child_by_field_name("body") is not None
            and node.end_byte - node.start_byte > 120
        ]
        if not candidates:
            continue
        name, _node = candidates[rng.randrange(len(candidates))]
        samples.append(Sample(path=path, symbol=name, language=lang, source=blob))
    return samples


def run_case(
    workdir: Path,
    sample: Sample,
    *,
    new_source: bytes,
    move_to: str | None = None,
) -> Status:
    """Commit a perturbation in a scratch clone and classify the anchor."""
    baseline = gitio.git(workdir, "rev-parse", "HEAD").strip()
    target = workdir / sample.path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(new_source)

    if move_to:
        destination = workdir / move_to
        destination.parent.mkdir(parents=True, exist_ok=True)
        gitio.git(workdir, "add", "-A")
        gitio.git(workdir, "mv", "-f", sample.path, move_to)

    gitio.git(workdir, "add", "-A")
    gitio.git(workdir, "-c", "user.name=forge", "-c", "user.email=f@invalid",
              "commit", "-q", "-m", "perturbation", "--allow-empty")

    anchor = Anchor(path=sample.path, symbol=sample.symbol, sha=None,
                    raw=f"{sample.path}#{sample.symbol}")
    result = classify(workdir, anchor, baseline=baseline, head="HEAD")

    # Roll the scratch clone back so each case is independent.
    gitio.git(workdir, "reset", "-q", "--hard", baseline)
    gitio.git(workdir, "clean", "-qfd")
    return result.status


def measure(repo: Path, *, samples: int, seed: int) -> dict:
    rng = random.Random(seed)
    started = time.time()
    picked = collect_samples(repo, count=samples, rng=rng)
    if not picked:
        raise SystemExit(f"{repo}: no anchorable declarations found at HEAD")

    scratch = Path(tempfile.mkdtemp(prefix="forge-perturb-"))
    workdir = scratch / "work"
    try:
        gitio.git(repo, "worktree", "list")  # fail fast if not a repo
        subprocess.run(
            ["git", "clone", "-q", "--no-hardlinks", "--depth", "2",
             str(repo), str(workdir)],
            check=True, capture_output=True,
        )
        gitio.git(workdir, "config", "core.autocrlf", "false")

        outcomes: dict[str, Counter] = defaultdict(Counter)
        examples: dict[str, list[dict]] = defaultdict(list)
        applied = Counter()
        discarded = Counter()

        for sample in picked:
            tree = _parse(sample.source, sample.path)
            if tree is None:
                continue
            lang = sample.language
            node = None
            for name, candidate in _iter_declarations(tree.root_node, lang):
                if name == sample.symbol:
                    node = candidate
                    break
            if node is None:
                continue

            original_parses = _still_parses(sample.source, sample.path)

            for label, fn in NEUTRAL_PERTURBATIONS.items():
                new_source = fn(sample.source, sample.path)
                if new_source is None or new_source == sample.source:
                    continue
                if original_parses and not _still_parses(new_source, sample.path):
                    # The perturbation broke the code, so it is not neutral and
                    # scoring it against the detector would be measuring our bug.
                    discarded[label] += 1
                    continue
                applied[label] += 1
                status = run_case(workdir, sample, new_source=new_source)
                outcomes[f"{NEUTRAL}:{label}"][status.value] += 1
                if status is not Status.FRESH and len(examples[label]) < 3:
                    examples[label].append(
                        {"path": sample.path, "symbol": sample.symbol,
                         "status": status.value}
                    )

            # A pure move: content byte-identical, path different.
            moved_to = "forge_moved/" + sample.path
            applied["pure_rename"] += 1
            status = run_case(workdir, sample, new_source=sample.source, move_to=moved_to)
            outcomes[f"{NEUTRAL}:pure_rename"][status.value] += 1
            if status is not Status.FRESH and len(examples["pure_rename"]) < 3:
                examples["pure_rename"].append(
                    {"path": sample.path, "symbol": sample.symbol, "status": status.value}
                )

            # A move plus a comment rewrite: still neutral.
            commented = p_rewrite_comments(sample.source, sample.path)
            if commented is not None and commented != sample.source:
                applied["rename_plus_comments"] += 1
                status = run_case(
                    workdir, sample, new_source=commented,
                    move_to="forge_moved2/" + sample.path,
                )
                outcomes[f"{NEUTRAL}:rename_plus_comments"][status.value] += 1

            for label, fn in SUBSTANTIVE_PERTURBATIONS.items():
                new_source = fn(sample.source, sample.path, node)
                if new_source is None or new_source == sample.source:
                    continue
                applied[label] += 1
                status = run_case(workdir, sample, new_source=new_source)
                outcomes[f"{SUBSTANTIVE}:{label}"][status.value] += 1
                if status is Status.FRESH and len(examples[label]) < 3:
                    examples[label].append(
                        {"path": sample.path, "symbol": sample.symbol,
                         "status": "fresh (FALSE NEGATIVE)"}
                    )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    neutral_total = neutral_fp = 0
    substantive_total = substantive_fn = 0
    for key, counter in outcomes.items():
        family, _, _label = key.partition(":")
        total = sum(counter.values())
        if family == NEUTRAL:
            neutral_total += total
            neutral_fp += total - counter.get("fresh", 0)
        else:
            substantive_total += total
            substantive_fn += counter.get("fresh", 0)

    return {
        "repo": str(repo),
        "head": gitio.rev_parse(repo, "HEAD"),
        "seed": seed,
        "elapsed_seconds": round(time.time() - started, 1),
        "samples": len(picked),
        "samples_by_language": dict(Counter(s.language for s in picked)),
        "cases_applied": dict(applied),
        "cases_discarded_as_not_neutral": dict(discarded),
        "outcomes": {k: dict(v) for k, v in sorted(outcomes.items())},
        "false_positive_examples": {k: v for k, v in examples.items() if v},
        "totals": {
            "neutral_cases": neutral_total,
            "neutral_false_positives": neutral_fp,
            "neutral_false_positive_rate": (
                round(neutral_fp / neutral_total, 4) if neutral_total else None
            ),
            "substantive_cases": substantive_total,
            "substantive_false_negatives": substantive_fn,
            "substantive_false_negative_rate": (
                round(substantive_fn / substantive_total, 4) if substantive_total else None
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not gitio.is_repo(repo):
        raise SystemExit(f"{repo} is not a git repository")

    report = measure(repo, samples=args.samples, seed=args.seed)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    totals = report["totals"]
    print(f"repo                     {report['repo']}")
    print(f"samples                  {report['samples']} {report['samples_by_language']}")
    print(f"cases applied            {report['cases_applied']}")
    if report["cases_discarded_as_not_neutral"]:
        print(f"cases discarded          {report['cases_discarded_as_not_neutral']}"
              f"  (perturbation broke the code; not scored)")
    print()
    print("neutral (must be fresh):")
    for key, counter in report["outcomes"].items():
        if key.startswith(NEUTRAL):
            print(f"  {key.split(':', 1)[1]:22} {counter}")
    print(f"  -> false positives     {totals['neutral_false_positives']}"
          f"/{totals['neutral_cases']} = {totals['neutral_false_positive_rate']}")
    print()
    print("substantive (must not be fresh):")
    for key, counter in report["outcomes"].items():
        if key.startswith(SUBSTANTIVE):
            print(f"  {key.split(':', 1)[1]:22} {counter}")
    print(f"  -> false negatives     {totals['substantive_false_negatives']}"
          f"/{totals['substantive_cases']} = {totals['substantive_false_negative_rate']}")
    print()
    print(f"elapsed                  {report['elapsed_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
