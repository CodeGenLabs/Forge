"""Normalised-AST fingerprints, and locating a named declaration.

The mechanism is adopted from Fiberplane's `drift` documentation linter: parse
the source with tree-sitter and hash a normalised fingerprint of the syntax
tree - node kinds plus token text, with whitespace, comments and positions
dropped. The point is a comparison that is insensitive to reformatting and to
comment edits but sensitive to anything that changes what the code does.

Two deliberate properties:

* **A missing grammar is not a failure.** Without a grammar the source is
  reduced to a whitespace-normalised content hash and the result carries
  ``coarse=True``. The harness works with zero grammars installed, just less
  precisely, and the weaker signal is visible rather than silent.
* **Signature and body are fingerprinted separately.** A change confined to a
  function body is a weaker signal than a change to its name, parameters or
  return type. That distinction is what lets the drift ledger stay quiet about
  ordinary edits (``shifted``) and speak up about contract changes (``stale``)
  - see OPEN_QUESTIONS.md Q2.
"""

from __future__ import annotations

import hashlib
import re
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

__all__ = [
    "Grammar",
    "grammar_for_path",
    "language_for_path",
    "fingerprint_source",
    "coarse_fingerprint",
    "find_symbol",
    "SymbolNode",
    "available_languages",
]

_DIGEST_SIZE = 16
_SEP = "\x1f"

# An anonymous leaf containing a word character is a keyword, not punctuation.
_WORD_RE = re.compile(r"\w")

# Python's grammar exposes string delimiters as *named* nodes (`string_start`,
# `string_end`), where TypeScript leaves them anonymous. Without normalisation
# the same reformatting - a formatter switching quote style - would be absorbed
# in TypeScript and reported as drift in Python. Quote characters are stripped
# and any prefix is kept, so `f"` and `rb'` stay distinguishable from `"` while
# `'` and `"` collapse.
_STRING_DELIMITERS = frozenset({"string_start", "string_end"})
_QUOTE_CHARS = "\"'"

# extension -> language key. Three grammars in the MVP (MVP.md M1); everything
# else takes the coarse path.
_EXT_LANG = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "typescript",   # the TS grammar parses JS; good enough for anchoring
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".jsx": "tsx",
    ".go": "go",
}


@dataclass(frozen=True)
class Grammar:
    key: str
    language: object  # tree_sitter.Language


@lru_cache(maxsize=None)
def _load_grammar(key: str) -> Grammar | None:
    try:
        from tree_sitter import Language
    except ImportError:  # pragma: no cover - exercised only without the dep
        return None
    try:
        if key == "python":
            import tree_sitter_python as mod
            raw = mod.language()
        elif key == "typescript":
            import tree_sitter_typescript as mod
            raw = mod.language_typescript()
        elif key == "tsx":
            import tree_sitter_typescript as mod
            raw = mod.language_tsx()
        elif key == "go":
            import tree_sitter_go as mod
            raw = mod.language()
        else:
            return None
    except ImportError:
        return None
    return Grammar(key=key, language=Language(raw))


def available_languages() -> list[str]:
    """Language keys whose grammar is importable in this environment."""
    return [k for k in ("python", "typescript", "tsx", "go") if _load_grammar(k) is not None]


def language_for_path(path: str) -> str | None:
    lowered = path.lower()
    for ext, key in _EXT_LANG.items():
        if lowered.endswith(ext):
            return key
    return None


def grammar_for_path(path: str) -> Grammar | None:
    key = language_for_path(path)
    return _load_grammar(key) if key else None


def _digest(tokens: list[str]) -> str:
    h = hashlib.blake2b(digest_size=_DIGEST_SIZE)
    h.update(_SEP.join(tokens).encode("utf-8", "replace"))
    return h.hexdigest()


def _is_comment(node) -> bool:
    return "comment" in node.type


def _tokens(node, *, exclude=None) -> list[str]:
    """Pre-order token stream for a subtree: ``depth|field|type`` plus leaf text.

    Three normalisation decisions, each earned by a failing test:

    * **Comments are skipped**, subtree and all. Rewording a comment is not a
      change to what the code does.
    * **Punctuation-only anonymous nodes are dropped.** This is the abstract
      syntax tree rather than the concrete one, and it is what makes the
      fingerprint survive a formatter: a trailing comma in a parameter list, an
      added semicolon, or a brace moved to its own line carry no meaning the tree
      shape does not already encode. Two exceptions are kept, each found by a
      failing test: an anonymous node that fills a named field (tree-sitter
      exposes operators as the ``operator`` field, so ``a + b`` and ``a - b``
      still differ), and an anonymous leaf containing a word character (keywords
      such as ``number``, ``string``, ``async``, ``static`` and ``true`` are
      anonymous leaves under a wrapper node, and dropping them would erase the
      difference between ``a: number`` and ``a: string``).
    * **Depth is encoded**, so the flat sequence reconstructs the tree. Without
      it, two different shapes could serialise identically.

    Iterative rather than recursive: TypeScript and Go trees nest deeply enough
    (long call and binary-expression chains) to exceed Python's default
    recursion limit on real files.
    """
    out: list[str] = []
    # py-tree-sitter builds a fresh Node wrapper on every access, so Python's
    # id() is useless for identity here. Node.id is the underlying node pointer
    # and is stable across wrappers for the same node.
    excluded_id = exclude.id if exclude is not None else None

    cursor = node.walk()
    depth = 0
    visited_children = False
    while True:
        if not visited_children:
            current = cursor.node
            skip = _is_comment(current) or (
                excluded_id is not None and current.id == excluded_id
            )
            if not skip:
                field = cursor.field_name
                leaf = current.child_count == 0
                text = current.text.decode("utf-8", "replace") if leaf else None
                if (
                    current.is_named
                    or field is not None
                    or (leaf and _WORD_RE.search(text or ""))
                ):
                    out.append(f"{depth}|{field or ''}|{current.type}")
                    if leaf:
                        value = text or ""
                        if current.type in _STRING_DELIMITERS:
                            value = value.strip(_QUOTE_CHARS)
                        out.append(value)
                if cursor.goto_first_child():
                    depth += 1
                    continue
            visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif depth == 0:
            break
        else:
            cursor.goto_parent()
            depth -= 1
            visited_children = True
    return out


def coarse_fingerprint(source: bytes) -> str:
    """Whitespace-normalised content hash, used when no grammar is available.

    Line endings are unified, trailing whitespace is dropped and blank lines are
    removed. Comments are *not* stripped, which is precisely why a coarse result
    is a weaker signal and is labelled as one.
    """
    text = source.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [line for line in lines if line.strip()]
    return _digest(lines)


def fingerprint_source(source: bytes, path: str) -> tuple[str, bool]:
    """Fingerprint a whole file. Returns ``(digest, coarse)``."""
    grammar = grammar_for_path(path)
    if grammar is None:
        return coarse_fingerprint(source), True
    from tree_sitter import Parser

    tree = Parser(grammar.language).parse(source)
    return _digest(_tokens(tree.root_node)), False


# --------------------------------------------------------------------------
# Locating a named declaration
# --------------------------------------------------------------------------
#
# Best-effort and deliberately table-driven rather than query-driven: a table of
# declaration node types plus the field that holds the name is a fraction of the
# code of per-language tree-sitter queries and covers the declarations a claim
# is realistically anchored to. A symbol this table cannot find degrades to a
# whole-file comparison (flagged symbol_unresolved) rather than to a wrong
# answer.

# Node types whose name lives in the "name" field.
_NAMED_DECLS = {
    "python": {
        "function_definition", "class_definition",
    },
    "typescript": {
        "function_declaration", "generator_function_declaration",
        "class_declaration", "abstract_class_declaration",
        "interface_declaration", "type_alias_declaration",
        "enum_declaration", "method_definition",
        "public_field_definition", "module",
    },
    "go": {
        "function_declaration", "method_declaration",
    },
}
_NAMED_DECLS["tsx"] = _NAMED_DECLS["typescript"]

# Declarator nodes carry their own "name" field and appear inside a holder
# statement: `const a = 1, b = 2`, `var x int`, `type ( A int; B string )`.
# Matching the declarator directly means the holder needs no table of its own.
_DECLARATOR_TYPES = {
    "variable_declarator", "var_spec", "const_spec", "type_spec",
}


@dataclass(frozen=True)
class SymbolNode:
    """A located declaration, with its signature separated from its body."""
    full_digest: str
    signature_digest: str
    node_type: str
    #: 1-based, inclusive. Carried so a caller can ask whether a diff's hunks
    #: touched this declaration rather than merely its file - the difference
    #: between "a claim about this method" and "a claim about this module".
    start_line: int = 0
    end_line: int = 0


def _name_of(node) -> str | None:
    field = node.child_by_field_name("name")
    if field is None:
        return None
    return field.text.decode("utf-8", "replace")


def _iter_declarations(root, lang: str):
    """Yield ``(name, node)`` for declarations, shallowest first.

    Breadth-first on purpose: a top-level ``foo`` must win over a local
    variable also called ``foo`` buried inside an earlier function. Depth-first
    would resolve by source order, which is the wrong preference.

    Wrapper nodes (``export_statement``, ``decorated_definition``) need no table:
    the walk simply descends through them and matches the declaration inside.
    """
    named = _NAMED_DECLS.get(lang, set())
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node.type in named or node.type in _DECLARATOR_TYPES:
            name = _name_of(node)
            if name:
                yield name, node
        for i in range(node.child_count):
            queue.append(node.child(i))


def find_symbol(source: bytes, path: str, symbol: str) -> SymbolNode | None:
    """Locate *symbol* in *source* and fingerprint it.

    ``symbol`` may be dotted (``Class.method``) to disambiguate a member; each
    segment is resolved in turn within the previous match. Returns None when the
    symbol cannot be located, which callers must treat as "fall back to the
    whole file", never as "the code changed".
    """
    grammar = grammar_for_path(path)
    if grammar is None:
        return None
    lang = language_for_path(path)
    if lang is None:
        return None
    from tree_sitter import Parser

    tree = Parser(grammar.language).parse(source)

    node = tree.root_node
    for segment in symbol.split("."):
        match = None
        for name, candidate in _iter_declarations(node, lang):
            if name == segment:
                match = candidate
                break
        if match is None:
            return None
        node = match

    body = node.child_by_field_name("body")
    full = _digest(_tokens(node))
    signature = _digest(_tokens(node, exclude=body)) if body is not None else full
    return SymbolNode(full_digest=full, signature_digest=signature,
                      node_type=node.type,
                      start_line=node.start_point[0] + 1,
                      end_line=node.end_point[0] + 1)


def symbol_appears_textually(source: bytes, symbol: str) -> bool:
    """Cheap presence test used to separate "renamed away" from "I cannot parse it".

    Without this, a declaration form the table does not cover would be reported
    as ``missing`` - a blocking status - which would make the ledger untrustworthy
    in exactly the way that gets it ignored.

    Matched on word boundaries, not as a substring: renaming ``handler`` to
    ``handlerV2`` must read as gone, and a substring test would say it is still
    there and quietly downgrade the verdict to a whole-file comparison.
    """
    leaf = re.escape(symbol.split(".")[-1]).encode("utf-8")
    return re.search(rb"(?<![A-Za-z0-9_$])" + leaf + rb"(?![A-Za-z0-9_$])", source) is not None
