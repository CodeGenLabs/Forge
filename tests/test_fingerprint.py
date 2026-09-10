"""Normalisation properties of the AST fingerprint.

Each test here pins one decision in `_tokens`. Two of them exist because the
naive version failed: a trailing comma added by a formatter flipped the
fingerprint, and dropping every anonymous node erased the difference between
`a: number` and `a: string`. Both would have shown up as drift-ledger noise
rather than as a bug, which is why they are tests and not comments.
"""

from __future__ import annotations

import pytest

from forge.fingerprint import (
    available_languages,
    coarse_fingerprint,
    find_symbol,
    fingerprint_source,
    language_for_path,
    symbol_appears_textually,
)

pytestmark = pytest.mark.skipif(
    not available_languages(), reason="no tree-sitter grammars installed"
)


def sym(source: str, path: str, name: str):
    node = find_symbol(source.encode("utf-8"), path, name)
    assert node is not None, f"{name} not found in {path}"
    return node


# --------------------------------------------------------------------------
# Insensitive to: formatting, comments, quote style
# --------------------------------------------------------------------------

def test_reflow_trailing_comma_and_semicolons_are_absorbed():
    dense = "function f(a: number, b: number): number { return a+b }"
    formatted = (
        "function f(\n"
        "  a: number,\n"          # trailing comma a formatter would add
        "  b: number,\n"
        "): number {\n"
        "  return a + b;\n"       # semicolon a formatter would add
        "}\n"
    )
    assert sym(dense, "a.ts", "f").full_digest == sym(formatted, "a.ts", "f").full_digest


def test_comment_edits_are_absorbed():
    before = "def f(x):\n    # original note\n    return x\n"
    after = "def f(x):\n    # completely rewritten note\n    # and a second line\n    return x\n"
    assert sym(before, "a.py", "f").full_digest == sym(after, "a.py", "f").full_digest


@pytest.mark.parametrize(
    ("path", "name", "double", "single"),
    [
        ("a.ts", "f", 'function f(){ return "a" }', "function f(){ return 'a' }"),
        ("a.py", "f", 'def f():\n    return "a"\n', "def f():\n    return 'a'\n"),
    ],
)
def test_quote_style_is_absorbed(path, name, double, single):
    """Formatters flip quote style routinely; that must not read as drift.

    Found by the perturbation harness: Python's grammar exposes string
    delimiters as *named* nodes, so an earlier version absorbed a quote swap in
    TypeScript and reported it as `shifted` in Python.
    """
    assert sym(double, path, name).full_digest == sym(single, path, name).full_digest


@pytest.mark.parametrize(
    ("prefixed", "plain"),
    [
        ('def f():\n    return f"a{x}"\n', 'def f():\n    return "a{x}"\n'),
        ('def f():\n    return rb"a"\n', 'def f():\n    return b"a"\n'),
    ],
)
def test_string_prefixes_survive_quote_normalisation(prefixed, plain):
    """Stripping quote characters must not strip the prefix: `f"..."` is not
    `"..."`, and a raw string is not a cooked one."""
    assert sym(prefixed, "a.py", "f").full_digest != sym(plain, "a.py", "f").full_digest


# --------------------------------------------------------------------------
# Sensitive to: operators, keywords, literals, types
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("path", "name", "a", "b"),
    [
        ("a.ts", "f", "function f(x){ return x + 1 }", "function f(x){ return x - 1 }"),
        ("a.py", "f", "def f(x):\n    return x > 1\n", "def f(x):\n    return x < 1\n"),
        ("m.go", "F", "package m\nfunc F(a, b int) int { return a * b }\n",
                      "package m\nfunc F(a, b int) int { return a / b }\n"),
    ],
)
def test_operators_are_not_dropped(path, name, a, b):
    """Operators are anonymous tokens, but tree-sitter puts them in the
    `operator` field, and the field rule keeps them."""
    assert sym(a, path, name).full_digest != sym(b, path, name).full_digest


@pytest.mark.parametrize(
    ("path", "name", "a", "b"),
    [
        ("a.ts", "f", "async function f(){ return 1 }", "function f(){ return 1 }"),
        ("a.py", "f", "def f(x):\n    return True\n", "def f(x):\n    return False\n"),
        ("a.ts", "f", 'function f(){ return "a" }', 'function f(){ return "b" }'),
    ],
)
def test_keywords_and_literals_are_not_dropped(path, name, a, b):
    """Keywords are anonymous leaves under a wrapper node. Dropping every
    anonymous node would erase them, which an earlier version did."""
    assert sym(a, path, name).full_digest != sym(b, path, name).full_digest


def test_parameter_type_change_is_visible_in_the_signature():
    a = "function f(a: number){ return 1 }"
    b = "function f(a: string){ return 1 }"
    assert sym(a, "a.ts", "f").signature_digest != sym(b, "a.ts", "f").signature_digest


def test_return_type_change_is_visible_in_the_signature():
    a = "function f(): number { return 1 }"
    b = 'function f(): string { return "1" }'
    assert sym(a, "a.ts", "f").signature_digest != sym(b, "a.ts", "f").signature_digest


def test_go_widened_integer_type_is_visible():
    a = "package m\nfunc F(a int) int { return a }\n"
    b = "package m\nfunc F(a int64) int { return a }\n"
    assert sym(a, "m.go", "F").signature_digest != sym(b, "m.go", "F").signature_digest


# --------------------------------------------------------------------------
# Signature versus body
# --------------------------------------------------------------------------

def test_body_change_keeps_the_signature_stable():
    a = "function f(a: number){ return 1 }"
    b = "function f(a: number){ return 2 }"
    na, nb = sym(a, "a.ts", "f"), sym(b, "a.ts", "f")
    assert na.full_digest != nb.full_digest
    assert na.signature_digest == nb.signature_digest


def test_symbol_without_a_body_reports_signature_equal_to_full():
    node = sym("export const LIMIT = 100;", "a.ts", "LIMIT")
    assert node.signature_digest == node.full_digest


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("path", "source", "name"),
    [
        ("a.py", "class A:\n    def run(self):\n        return 1\n", "A"),
        ("a.py", "class A:\n    def run(self):\n        return 1\n", "A.run"),
        ("a.ts", "export class A {\n  run(x: number) { return x }\n}\n", "A.run"),
        ("a.ts", "export interface Cfg { a: number }\n", "Cfg"),
        ("a.ts", "export type Id = string;\n", "Id"),
        ("a.ts", "export const LIMIT = 1;\n", "LIMIT"),
        ("a.ts", "export enum Kind { A, B }\n", "Kind"),
        ("m.go", "package m\ntype Cfg struct{ A int }\n", "Cfg"),
        ("m.go", "package m\nfunc (c Cfg) Run() int { return 1 }\n", "Run"),
        ("a.py", "@decorator\ndef wrapped(x):\n    return x\n", "wrapped"),
    ],
)
def test_declaration_forms_resolve(path, source, name):
    assert find_symbol(source.encode(), path, name) is not None


def test_shallower_declaration_wins():
    """A top-level `foo` must beat a local `foo` that appears earlier."""
    source = (
        "def other():\n"
        "    foo = 1\n"
        "    return foo\n"
        "\n"
        "def foo(a, b):\n"
        "    return a + b\n"
    )
    node = find_symbol(source.encode(), "a.py", "foo")
    assert node is not None
    assert node.node_type == "function_definition"


def test_unknown_symbol_is_none_not_an_exception():
    assert find_symbol(b"def f():\n    return 1\n", "a.py", "nope") is None


def test_symbol_appears_textually_separates_gone_from_unresolvable():
    source = b"# handler is described here\nexport const other = 1;\n"
    assert symbol_appears_textually(source, "handler")
    assert not symbol_appears_textually(source, "absent")


@pytest.mark.parametrize(
    ("source", "symbol", "present"),
    [
        (b"def foo(): pass", "foo", True),
        (b"def fooRenamed(): pass", "foo", False),      # substring, not the symbol
        (b"def prefix_foo(): pass", "foo", False),
        (b"x = foo(1)", "foo", True),
        (b"obj.foo = 1", "foo", True),
    ],
)
def test_symbol_presence_is_matched_on_word_boundaries(source, symbol, present):
    """Renaming `foo` to `fooRenamed` must read as gone.

    Found by the perturbation harness: a substring test reported the renamed
    declaration as still present, which downgraded a `missing` verdict to a
    whole-file comparison and hid the rename.
    """
    assert symbol_appears_textually(source, symbol) is present


# --------------------------------------------------------------------------
# Coarse fallback
# --------------------------------------------------------------------------

def test_unknown_extension_is_coarse():
    digest, coarse = fingerprint_source(b"fn main() {}\n", "m.rs")
    assert coarse is True and digest


def test_known_extension_is_not_coarse():
    _digest, coarse = fingerprint_source(b"def f():\n    return 1\n", "a.py")
    assert coarse is False


def test_coarse_absorbs_trailing_whitespace_and_blank_lines():
    assert coarse_fingerprint(b"fn main() {}\n") == coarse_fingerprint(b"fn main() {}   \n\n\n")


def test_coarse_absorbs_line_ending_style():
    assert coarse_fingerprint(b"a\r\nb\r\n") == coarse_fingerprint(b"a\nb\n")


def test_coarse_sees_a_real_change():
    assert coarse_fingerprint(b"fn main() {}\n") != coarse_fingerprint(b"fn main() { x(); }\n")


def test_coarse_does_not_absorb_a_reflow():
    """A documented limit: coarse mode is line-based, so moving a brace to its
    own line reads as a change. That is the precision a grammar buys, and why
    the coarse flag has to travel with the verdict."""
    assert coarse_fingerprint(b"fn main() {}\n") != coarse_fingerprint(b"fn main() {\n}\n")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.py", "python"), ("a.pyi", "python"),
        ("a.ts", "typescript"), ("a.cts", "typescript"), ("a.js", "typescript"),
        ("a.tsx", "tsx"), ("a.jsx", "tsx"),
        ("m.go", "go"),
        ("m.rs", None), ("README.md", None), ("a.sql", None),
    ],
)
def test_language_detection(path, expected):
    assert language_for_path(path) == expected


# --------------------------------------------------------------------------
# The zero-grammar claim
# --------------------------------------------------------------------------

def test_everything_degrades_to_coarse_without_grammars(monkeypatch):
    """ARCHITECTURE.md section 6 claims the harness works with no grammars
    installed, just less precisely. This holds that claim to account."""
    from forge import fingerprint as fp

    monkeypatch.setattr(fp, "_load_grammar", lambda key: None)

    digest, coarse = fp.fingerprint_source(b"def f():\n    return 1\n", "a.py")
    assert coarse is True and digest
    assert fp.find_symbol(b"def f():\n    return 1\n", "a.py", "f") is None
    assert fp.available_languages() == []


def test_coarse_classification_still_works_without_grammars(repo, monkeypatch):
    from forge import fingerprint as fp
    from forge.anchor import Status, classify, parse_anchor

    repo.write("a.py", "def f():\n    return 1\n")
    base = repo.commit("initial")
    repo.write("a.py", "def f():\n    return 2\n")
    repo.commit("change")

    monkeypatch.setattr(fp, "_load_grammar", lambda key: None)
    result = classify(repo.root, parse_anchor("a.py#f"), baseline=base)
    assert result.coarse is True
    assert result.symbol_unresolved is True
    assert result.status is Status.STALE
