"""What the claim-touch rule is allowed to demand, and what it may only suggest.

The incident: on `requests` - 35 modules, 88 import edges, 20 cycles - a one-line
type-annotation change to `models.py` put 10 claims out of 10 into the touch set.
Eight were anchored to files the diff never opened; they were there because those
files import `models.py`. `impact.md` then carried nine honest `Unaffected`
sentences about code the change could not have reached.

`Unaffected` costs one sentence and that price is the point. It is supposed to be
paid for claims the diff touched.
"""

from __future__ import annotations

from datetime import date

import pytest

from forge import change, derive, impact
from forge.cli import main

TODAY = date(2026, 9, 11)

CORE = "def core():\n    return 1\n"
CALLER = "from .core import core\n\n\ndef caller():\n    return core()\n"

CLAIMS = """\

### CON-core - what the core module is for

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/pkg/core.py"]
reviewed: 2026-09-01
```

Prose about the core module, long enough to read like a real claim and to say
something a reader could not get from the file name alone.

### CON-caller - what the calling module is for

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/pkg/caller.py"]
reviewed: 2026-09-01
```

Prose about the calling module, long enough to read like a real claim and to say
something a reader could not get from the file name alone.
"""


@pytest.fixture
def two_modules(repo):
    """`caller.py` imports `core.py`, and a claim is anchored to each."""
    repo.write("src/pkg/__init__.py", "")
    repo.write("src/pkg/core.py", CORE)
    repo.write("src/pkg/caller.py", CALLER)
    main(["init", "--repo", str(repo.root)])
    text = (repo.root / "docs/system/domain.md").read_text(encoding="utf-8")
    repo.write("docs/system/domain.md", text + CLAIMS)
    repo.commit("two modules and two claims")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    change.new_change(repo.root, "touch the core", today=TODAY)
    repo.commit("open a change")
    return repo


def computed(repo):
    return impact.compute_impact(repo.root, change.find_change(repo.root, "1"))


# ---------------------------------------------------------------------------
# An import is not a touch
# ---------------------------------------------------------------------------

def test_an_importer_is_in_the_radius_but_not_the_touch_set(two_modules):
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))

    result = computed(two_modules)
    assert "src/pkg/caller.py" in result.reverse_deps
    assert set(result.touched) == {"CON-core"}
    assert set(result.nearby) == {"CON-caller"}


def test_the_importer_is_reported_with_a_reason(two_modules):
    """Losing the reading value of the blast radius would be the wrong repair.
    The claim is still shown - it is just not owed a sentence."""
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))

    entry = computed(two_modules).nearby["CON-caller"]
    assert "imports something the diff changed" in entry.reasons[0]


def test_editing_the_importer_makes_it_a_touch(two_modules):
    """The narrowing must not lose the case it exists to serve."""
    two_modules.write("src/pkg/caller.py", CALLER.replace("return core()", "return 0"))

    result = computed(two_modules)
    assert "CON-caller" in result.touched
    assert "CON-caller" not in result.nearby


def test_a_claim_that_is_both_is_only_touched(two_modules):
    """Anchored to one file the diff changed and one that merely imports it:
    an obligation outranks a suggestion, and reporting both would ask the
    reader to work out which heading it needs."""
    text = (two_modules.root / "docs/system/domain.md").read_text(encoding="utf-8")
    two_modules.write("docs/system/domain.md", text.replace(
        'anchors:  ["src/pkg/caller.py"]',
        'anchors:  ["src/pkg/caller.py", "src/pkg/core.py"]'))
    two_modules.commit("CON-caller anchors both modules")
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))

    result = computed(two_modules)
    assert "CON-caller" in result.touched
    assert "CON-caller" not in result.nearby


def test_the_account_owes_nothing_for_a_nearby_claim(two_modules):
    """The end-to-end point: the gate passes with only the touched claim filed."""
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))
    two_modules.write(
        "changes/0001-touch-the-core/impact.md",
        "# Impact\n\n## Blast radius\n- src/pkg/core.py\n\n"
        "## Claims touched\n\n### Unaffected\n"
        "- CON-core - the return value changed, the module's purpose did not\n")

    from forge.validate import Issue
    item = change.find_change(two_modules.root, "1")
    issues = impact.check_claim_touch(
        two_modules.root, item, computed(two_modules), Issue)
    assert [i for i in issues if i.level == "ERROR"] == []


# ---------------------------------------------------------------------------
# Built and vendored paths are not source
# ---------------------------------------------------------------------------

def test_bytecode_is_not_in_the_blast_radius(two_modules):
    """`gitio.changed_files` reports untracked files on purpose. A repository
    with no `.gitignore` - a published sdist, say - was reporting
    `__pycache__/*.pyc` as changed source."""
    two_modules.write("src/pkg/__pycache__/core.cpython-313.pyc", b"\x00\x01")
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))

    assert computed(two_modules).changed_files == ["src/pkg/core.py"]


def test_a_vendored_directory_is_not_in_the_blast_radius(two_modules):
    two_modules.write("node_modules/left-pad/index.js", "module.exports = 1\n")
    two_modules.write("src/pkg/core.py", CORE.replace("return 1", "return 2"))

    assert computed(two_modules).changed_files == ["src/pkg/core.py"]


# ---------------------------------------------------------------------------
# An anchor names a symbol, and the diff touched a different one
# ---------------------------------------------------------------------------

MODULE = '''\
def alpha():
    return 1


def beta():
    return 2


def gamma():
    return 3
'''

TWO_CLAIMS = """\

### CON-alpha - what alpha is for

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/pkg/mod.py#alpha"]
reviewed: 2026-09-01
```

Prose about alpha, long enough to read like a real claim and to say something a
reader could not get from the function name alone.

### CON-beta - what beta is for

```claim
kind:     concept
status:   asserted
truth-source: decision
anchors:  ["src/pkg/mod.py#beta"]
reviewed: 2026-09-01
```

Prose about beta, long enough to read like a real claim and to say something a
reader could not get from the function name alone.
"""


@pytest.fixture
def symbols(repo):
    """One module, two functions, one claim anchored to each."""
    repo.write("src/pkg/__init__.py", "")
    repo.write("src/pkg/mod.py", MODULE)
    main(["init", "--repo", str(repo.root)])
    text = (repo.root / "docs/system/domain.md").read_text(encoding="utf-8")
    repo.write("docs/system/domain.md", text + TWO_CLAIMS)
    repo.commit("a module and two claims")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    change.new_change(repo.root, "change alpha", today=TODAY)
    repo.commit("open a change")
    return repo


def touched_of(repo):
    return impact.compute_impact(repo.root, change.find_change(repo.root, "1"))


def test_only_the_claim_about_the_changed_symbol_is_touched(symbols):
    """The measurement: on `requests` this took a one-method change from five
    claims owed a sentence to one."""
    symbols.write("src/pkg/mod.py", MODULE.replace("return 1", "return 11"))

    result = touched_of(symbols)
    assert set(result.touched) == {"CON-alpha"}
    assert set(result.nearby) == {"CON-beta"}


def test_the_untouched_symbol_is_still_reported(symbols):
    """Dropping it entirely would be the wrong repair: the diff did open the
    file this claim points into."""
    symbols.write("src/pkg/mod.py", MODULE.replace("return 1", "return 11"))

    entry = touched_of(symbols).nearby["CON-beta"]
    assert "changed elsewhere" in entry.reasons[0]


def test_a_file_level_anchor_is_touched_by_any_edit_to_its_file(symbols):
    """The narrowing applies to symbol anchors only. A claim that points at a
    whole file is making a claim about the whole file."""
    text = (symbols.root / "docs/system/domain.md").read_text(encoding="utf-8")
    symbols.write("docs/system/domain.md",
                  text.replace('["src/pkg/mod.py#beta"]', '["src/pkg/mod.py"]'))
    symbols.commit("CON-beta anchors the module")
    symbols.write("src/pkg/mod.py", MODULE.replace("return 1", "return 11"))

    assert "CON-beta" in touched_of(symbols).touched


def test_an_unresolvable_symbol_falls_back_to_the_file(symbols):
    """Every way of not knowing falls back to the file. Over-reporting costs a
    sentence; under-reporting costs a claim nobody re-read."""
    text = (symbols.root / "docs/system/domain.md").read_text(encoding="utf-8")
    symbols.write("docs/system/domain.md",
                  text.replace('["src/pkg/mod.py#beta"]', '["src/pkg/mod.py#vanished"]'))
    symbols.commit("CON-beta anchors a symbol that is not there")
    symbols.write("src/pkg/mod.py", MODULE.replace("return 1", "return 11"))

    entry = touched_of(symbols).touched["CON-beta"]
    assert "not resolvable" in entry.reasons[0]


def test_a_language_with_no_grammar_falls_back_to_the_file(symbols):
    symbols.write("src/pkg/thing.rb", "def alpha\n  1\nend\n")
    text = (symbols.root / "docs/system/domain.md").read_text(encoding="utf-8")
    symbols.write("docs/system/domain.md",
                  text.replace('["src/pkg/mod.py#beta"]', '["src/pkg/thing.rb#alpha"]'))
    symbols.commit("a claim on a language with no grammar installed")
    symbols.write("src/pkg/thing.rb", "def alpha\n  2\nend\n")

    entry = touched_of(symbols).touched["CON-beta"]
    assert "not resolvable" in entry.reasons[0]


def test_a_new_file_touches_every_claim_anchored_into_it(symbols):
    """An added file has no hunks to intersect, and the whole thing is new."""
    symbols.write("src/pkg/fresh.py", "def alpha():\n    return 1\n")
    text = (symbols.root / "docs/system/domain.md").read_text(encoding="utf-8")
    symbols.write("docs/system/domain.md",
                  text.replace('["src/pkg/mod.py#beta"]', '["src/pkg/fresh.py#alpha"]'))
    symbols.commit("a claim about a file that does not exist yet")
    symbols.write("src/pkg/fresh.py", "def alpha():\n    return 1\n")

    assert "CON-beta" in touched_of(symbols).touched
