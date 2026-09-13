"""`deps.json`: the in-repository import graph the blast radius is computed from."""

from __future__ import annotations

import pytest

from forge import derive


def deps(repo) -> dict:
    return derive.build_deps(repo.root)


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def test_a_relative_import_is_an_edge(repo):
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/store.py", "VALUE = 1\n")
    repo.write("pkg/api.py", "from .store import VALUE\n")
    repo.commit("two modules")
    assert deps(repo)["edges"]["pkg/api.py"] == ["pkg/store.py"]


def test_from_package_import_submodules_resolves_each_one(repo):
    """`from . import gitio, store` is the case worth spelling out: resolving
    only the `.` points the edge at `__init__.py` and loses both real
    dependencies."""
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/gitio.py", "")
    repo.write("pkg/store.py", "")
    repo.write("pkg/api.py", "from . import gitio, store\n")
    repo.commit("a package-relative import")
    assert deps(repo)["edges"]["pkg/api.py"] == [
        "pkg/__init__.py", "pkg/gitio.py", "pkg/store.py",
    ]


def test_an_attribute_in_an_import_list_is_not_invented_as_a_module(repo):
    """A name in `from X import a, b` may be a submodule or an attribute.
    Each is tried and kept only if a file answers, so nothing is invented."""
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/store.py", "class Claim: pass\n")
    repo.write("pkg/api.py", "from .store import Claim\n")
    repo.commit("an attribute import")
    assert deps(repo)["edges"]["pkg/api.py"] == ["pkg/store.py"]


def test_a_src_layout_resolves_an_absolute_import(repo):
    repo.write("src/pkg/__init__.py", "")
    repo.write("src/pkg/store.py", "")
    repo.write("src/pkg/api.py", "from pkg.store import thing\n")
    repo.commit("a src layout")
    assert deps(repo)["edges"]["src/pkg/api.py"] == ["src/pkg/store.py"]


def test_an_import_that_leaves_the_repository_is_not_an_edge(repo):
    """The graph is about *this* repository's coupling; `yaml` is a fact of
    the lockfile that inventory.json already reports."""
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/api.py", "import yaml\nimport os\n")
    repo.commit("third-party imports")
    assert deps(repo)["edges"] == {}


def test_a_package_init_import_resolves(repo):
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/sub/__init__.py", "")
    repo.write("pkg/api.py", "from .sub import thing\n")
    repo.commit("a subpackage")
    assert deps(repo)["edges"]["pkg/api.py"] == ["pkg/sub/__init__.py"]


# ---------------------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------------------

def test_a_relative_typescript_import_resolves_through_extensions(repo):
    repo.write("src/store.ts", "export const x = 1;\n")
    repo.write("src/api.ts", 'import { x } from "./store";\n')
    repo.commit("typescript")
    assert deps(repo)["edges"]["src/api.ts"] == ["src/store.ts"]


def test_an_index_file_resolves(repo):
    repo.write("src/store/index.ts", "export const x = 1;\n")
    repo.write("src/api.ts", 'import { x } from "./store";\n')
    repo.commit("an index module")
    assert deps(repo)["edges"]["src/api.ts"] == ["src/store/index.ts"]


def test_require_and_dynamic_import_count(repo):
    repo.write("src/store.js", "module.exports = {};\n")
    repo.write("src/other.js", "module.exports = {};\n")
    repo.write("src/api.js",
               'const s = require("./store");\nconst o = import("./other");\n')
    repo.commit("both call shapes")
    assert deps(repo)["edges"]["src/api.js"] == ["src/other.js", "src/store.js"]


def test_a_package_import_is_skipped_and_not_counted_unresolved(repo):
    repo.write("src/api.ts", 'import React from "react";\n')
    repo.commit("a package import")
    result = deps(repo)
    assert result["edges"] == {}
    assert result["unresolved_imports"] == 0


def test_a_dangling_relative_import_is_counted(repo):
    """Reported rather than silently dropped: a graph missing edges quietly
    narrows the blast radius, and a narrower blast radius means a smaller
    claim-touch set than the truth."""
    repo.write("src/api.ts", 'import { x } from "./gone";\n')
    repo.commit("a broken import")
    assert deps(repo)["unresolved_imports"] == 1


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------

def test_a_go_import_resolves_through_the_module_path(repo):
    repo.write("go.mod", "module example.com/app\n\ngo 1.22\n")
    repo.write("pay/pay.go", "package pay\n\nfunc Capture() {}\n")
    repo.write("api/api.go",
               'package api\n\nimport (\n\t"example.com/app/pay"\n)\n\nfunc H() {}\n')
    repo.commit("a go module")
    assert deps(repo)["edges"]["api/api.go"] == ["pay/pay.go"]


def test_a_go_import_edges_to_every_file_in_the_package(repo):
    """A Go import names a package directory; the importer cannot say which
    file it meant."""
    repo.write("go.mod", "module example.com/app\n\ngo 1.22\n")
    repo.write("pay/pay.go", "package pay\n")
    repo.write("pay/refund.go", "package pay\n")
    repo.write("api/api.go", 'package api\n\nimport "example.com/app/pay"\n')
    repo.commit("a multi-file package")
    assert deps(repo)["edges"]["api/api.go"] == ["pay/pay.go", "pay/refund.go"]


def test_a_standard_library_import_is_not_an_edge(repo):
    repo.write("go.mod", "module example.com/app\n\ngo 1.22\n")
    repo.write("api/api.go", 'package api\n\nimport "fmt"\n')
    repo.commit("stdlib only")
    assert deps(repo)["edges"] == {}


# ---------------------------------------------------------------------------
# Cycles and determinism
# ---------------------------------------------------------------------------

def test_a_cycle_is_found(repo):
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/a.py", "from . import b\n")
    repo.write("pkg/b.py", "from . import a\n")
    repo.commit("a cycle")
    cycles = deps(repo)["cycles"]
    assert len(cycles) == 1
    assert set(cycles[0]) == {"pkg/a.py", "pkg/b.py"}


def test_a_cycle_is_rotated_to_a_stable_start(repo):
    """Without rotation the same cycle is written starting from whichever file
    the walk reached first, and the derived file stops being byte-identical
    between runs on different filesystems."""
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/a.py", "from . import b\n")
    repo.write("pkg/b.py", "from . import c\n")
    repo.write("pkg/c.py", "from . import a\n")
    repo.commit("a three-node cycle")
    assert deps(repo)["cycles"] == [["pkg/a.py", "pkg/b.py", "pkg/c.py"]]


def test_the_reverse_index_is_the_inverse_of_the_edges(repo):
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/store.py", "")
    repo.write("pkg/api.py", "from . import store\n")
    repo.write("pkg/cli.py", "from . import store\n")
    repo.commit("two importers")
    result = deps(repo)
    assert result["reverse"]["pkg/store.py"] == ["pkg/api.py", "pkg/cli.py"]


def test_regeneration_is_a_no_op(repo):
    repo.write("pkg/__init__.py", "")
    repo.write("pkg/a.py", "from . import b\n")
    repo.write("pkg/b.py", "")
    repo.commit("modules")
    assert derive.derive_all(repo.root)["deps.json"] is True
    assert derive.derive_all(repo.root)["deps.json"] is False


def test_the_derived_tier_does_not_describe_itself(repo):
    repo.write("pkg/__init__.py", "")
    repo.commit("a package")
    derive.derive_all(repo.root)
    repo.commit("chore: sync derived tier")
    assert all(not path.startswith("docs/system/derived")
               for path in deps(repo)["edges"])


# ---------------------------------------------------------------------------
# A monorepo's own packages are imported by name
# ---------------------------------------------------------------------------

def test_a_workspace_package_import_is_an_edge(repo):
    """The incident: on a 19-package TypeScript monorepo the file importing
    `@acme/contract` had zero recorded edges, and the repository reported
    `671 edges, 0 cycles`. The zero was the cross-package edges being dropped -
    the only ones that could have formed a cycle."""
    repo.write("packages/contract/package.json",
               '{"name": "@acme/contract", "main": "./src/index.ts"}')
    repo.write("packages/contract/src/index.ts", "export type Transport = {}\n")
    repo.write("packages/client/package.json", '{"name": "@acme/client"}')
    repo.write("packages/client/src/createClient.ts",
               "import type { Transport } from '@acme/contract'\n")
    repo.commit("two workspace packages")

    edges = deps(repo)["edges"]
    assert edges["packages/client/src/createClient.ts"] == [
        "packages/contract/src/index.ts"]


def test_a_deep_workspace_import_resolves(repo):
    repo.write("packages/ui/package.json", '{"name": "@acme/ui"}')
    repo.write("packages/ui/src/button.ts", "export const Button = 1\n")
    repo.write("apps/web/package.json", '{"name": "@acme/web"}')
    repo.write("apps/web/main.ts", "import { Button } from '@acme/ui/src/button'\n")
    repo.commit("a deep import across packages")

    assert deps(repo)["edges"]["apps/web/main.ts"] == ["packages/ui/src/button.ts"]


def test_a_third_party_import_is_still_skipped(repo):
    """`react` is a lockfile fact that `inventory.json` already reports. The
    rule that was wrong confused "not relative" with "not in this repository";
    it must not now swing to treating every bare specifier as local."""
    repo.write("packages/ui/package.json", '{"name": "@acme/ui"}')
    repo.write("packages/ui/src/button.ts",
               "import React from 'react'\nimport {x} from '@vendor/thing'\n")
    repo.commit("third-party imports only")

    assert deps(repo)["edges"].get("packages/ui/src/button.ts", []) == []


def test_the_root_manifest_is_not_a_workspace_package(repo):
    """Mapping the root name would make every bare specifier resolve to the
    repository root and wire the graph to itself."""
    repo.write("package.json", '{"name": "sample-monorepo", "workspaces": ["packages/*"]}')
    repo.write("src/a.ts", "import x from 'sample-monorepo'\n")
    repo.commit("a root manifest")

    assert deps(repo)["edges"].get("src/a.ts", []) == []


def test_a_workspace_import_that_resolves_to_nothing_is_counted_unresolved(repo):
    repo.write("packages/contract/package.json", '{"name": "@acme/contract"}')
    repo.write("packages/contract/README.md", "no source here\n")
    repo.write("packages/client/package.json", '{"name": "@acme/client"}')
    repo.write("packages/client/src/a.ts", "import x from '@acme/contract'\n")
    repo.commit("a package with no entry point")

    assert deps(repo)["unresolved_imports"] >= 1


def test_a_malformed_manifest_does_not_stop_the_scan(repo):
    repo.write("packages/broken/package.json", "{not json")
    repo.write("packages/contract/package.json", '{"name": "@acme/contract"}')
    repo.write("packages/contract/src/index.ts", "export const x = 1\n")
    repo.write("packages/client/package.json", '{"name": "@acme/client"}')
    repo.write("packages/client/src/a.ts", "import x from '@acme/contract'\n")
    repo.commit("one unreadable manifest")

    assert deps(repo)["edges"]["packages/client/src/a.ts"] == [
        "packages/contract/src/index.ts"]


# ---------------------------------------------------------------------------
# `it.each` is a test declaration
# ---------------------------------------------------------------------------

def test_a_parameterised_test_is_counted(repo):
    """`it.each([...])('name %s', ...)` puts the table between the modifier and
    the name, and the old pattern expected the name immediately after `it.each`.
    Every `it.each` in a repository was invisible: uncounted, and any `@covers`
    on one was lost to the tag landing on whichever test came next."""
    repo.write("src/a.test.ts",
               "it.each([1, 2])('parameterised %s', (n) => {})\n")
    repo.commit("a parameterised test")

    tests = derive.build_tests(repo.root)
    assert tests["total_tests"] == 1


def test_a_covers_tag_binds_to_the_parameterised_test_below_it(repo):
    repo.write("src/a.test.ts",
               "// @covers REQ-one\n"
               "it.each([1, 2])('parameterised %s', (n) => {})\n\n"
               "it('the next one', () => {})\n")
    repo.commit("a tag above a parameterised test")

    tests = derive.build_tests(repo.root)["files"]["src/a.test.ts"]["tests"]
    by_name = {t["name"]: t["covers"] for t in tests}
    assert by_name["parameterised %s"] == ["REQ-one"]
    assert by_name["the next one"] == []


def test_the_plain_and_modified_forms_still_count(repo):
    repo.write("src/a.test.ts",
               "it('plain', () => {})\n"
               "it.skip('skipped', () => {})\n"
               "test.each([['a']])('table %s', (x) => {})\n"
               "it.concurrent.each([1])('nested modifier %s', (n) => {})\n")
    repo.commit("four shapes")

    assert derive.build_tests(repo.root)["total_tests"] == 4


def test_a_call_that_is_not_a_test_is_not_counted(repo):
    """The optional table group must not turn any `something(...)('str')` into
    a test."""
    repo.write("src/a.test.ts",
               "it('real', () => {})\n"
               "describe('a group', () => {})\n"
               "const f = compose(g)('not a test')\n")
    repo.commit("one test and two things that are not")

    assert derive.build_tests(repo.root)["total_tests"] == 1
