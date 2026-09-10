"""The measurement's ground truth has to be true.

`tools/perturb_anchors.py` labels each perturbation neutral or substantive and
derives the false-positive rate from those labels. If a "neutral" perturbation
actually changes behaviour, the rate is measuring the harness's own bug and
reporting it as a defect in the detector - which is exactly what happened on the
first run: whitespace edits inside template literals and docstrings are real
changes, and 17 of 171 "false positives" were that mistake.

So these tests check the labels, not the detector: every neutral perturbation
must leave the fingerprint identical, including on a file that contains a
multi-line literal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from forge.fingerprint import available_languages, fingerprint_source  # noqa: E402
from perturb_anchors import NEUTRAL_PERTURBATIONS  # noqa: E402

pytestmark = pytest.mark.skipif(
    not available_languages(), reason="no tree-sitter grammars installed"
)

TS_WITH_TEMPLATE = """\
// a leading comment
export function render(name: string): string {
  const banner = `
    Hello, ${name}
      indented on purpose
  `;
  return banner.trim();
}

export const LIMIT = 10;
"""

PY_WITH_DOCSTRING = '''\
def render(name):
    """Summary line.

        Indented block that is part of the string.
    """
    template = """
    Hello, %s
      indented on purpose
    """
    return template % name
'''

GO_WITH_RAW_STRING = """\
package m

// a leading comment
func Render(name string) string {
\ttmpl := `
    Hello,
      indented on purpose
`
\treturn tmpl + name
}
"""


@pytest.mark.parametrize("label", sorted(NEUTRAL_PERTURBATIONS))
@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("a.ts", TS_WITH_TEMPLATE),
        ("a.py", PY_WITH_DOCSTRING),
        ("m.go", GO_WITH_RAW_STRING),
    ],
    ids=["typescript", "python", "go"],
)
def test_neutral_perturbations_are_actually_neutral(label, path, source):
    original = source.encode("utf-8")
    perturbed = NEUTRAL_PERTURBATIONS[label](original, path)
    if perturbed is None or perturbed == original:
        pytest.skip(f"{label} does not apply to {path}")

    before, coarse_before = fingerprint_source(original, path)
    after, coarse_after = fingerprint_source(perturbed, path)
    assert coarse_before is False and coarse_after is False
    assert before == after, (
        f"{label} on {path} changed the fingerprint, so it is not neutral and "
        f"must not be counted as a false positive"
    )


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("a.ts", TS_WITH_TEMPLATE),
        ("a.py", PY_WITH_DOCSTRING),
        ("m.go", GO_WITH_RAW_STRING),
    ],
    ids=["typescript", "python", "go"],
)
def test_whitespace_inside_a_multiline_literal_is_left_alone(path, source):
    """The exclusion that makes the labels honest.

    A perturbation that reached inside the literal would be changing a string,
    and the detector would be right to report it.
    """
    original = source.encode("utf-8")
    perturbed = NEUTRAL_PERTURBATIONS["trailing_whitespace"](original, path)
    assert perturbed is not None
    assert b"indented on purpose   " not in perturbed
    assert b"indented on purpose" in perturbed


def test_perturbation_that_reaches_inside_a_literal_would_be_detected():
    """A control: prove the detector *does* see a literal-internal edit.

    Without this, the exclusion above could be hiding a blind spot rather than
    protecting a label.
    """
    original = TS_WITH_TEMPLATE.encode("utf-8")
    tampered = original.replace(b"indented on purpose", b"indented on purpose   ")
    assert tampered != original
    assert fingerprint_source(original, "a.ts")[0] != fingerprint_source(tampered, "a.ts")[0]


# --------------------------------------------------------------------------
# The guards that keep the labels honest
# --------------------------------------------------------------------------

def test_triple_quoted_strings_are_not_requoted():
    """`text[1:-1]` on `\"\"\"Doc.\"\"\"` yields `'\"\"Doc.\"\"'` - a different string.

    This mistake accounted for 13 of 25 "false positives" on Python in an
    earlier run of the harness.
    """
    from perturb_anchors import p_swap_quotes

    assert p_swap_quotes(b'def f():\n    """Doc."""\n    return 1\n', "a.py") is None
    assert p_swap_quotes(b'def f():\n    return "a"\n', "a.py") == b"def f():\n    return 'a'\n"


def test_double_indent_skips_files_with_multiline_literals():
    """Doubling code around a held-back literal breaks the indentation
    relationship; CPython rejected a real sample that way."""
    from perturb_anchors import p_double_indent

    with_literal = b'def f():\n    """D\n    o\n    """\n    return 1\n'
    assert p_double_indent(with_literal, "a.py") is None
    assert p_double_indent(b"def f():\n    return 1\n", "a.py") is not None


def test_still_parses_catches_what_tree_sitter_tolerates():
    """Tree-sitter is error-tolerant, so the guard needs a real parser too."""
    from perturb_anchors import _parse, _still_parses

    broken = b"def f():\nreturn 1\n"
    assert _parse(broken, "a.py") is not None          # tree-sitter accepts it
    assert _still_parses(broken, "a.py") is False      # the guard does not
    assert _still_parses(b"def f():\n    return 1\n", "a.py") is True
