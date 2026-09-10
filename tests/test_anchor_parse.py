import pytest

from forge.anchor import AnchorError, parse_anchor


def test_path_only():
    a = parse_anchor("src/payments/refund.ts")
    assert (a.path, a.symbol, a.sha, a.is_dir) == ("src/payments/refund.ts", None, None, False)


def test_path_symbol_sha():
    a = parse_anchor("src/payments/refund.ts#computeRefundable@a1b2c3d")
    assert a.path == "src/payments/refund.ts"
    assert a.symbol == "computeRefundable"
    assert a.sha == "a1b2c3d"
    assert str(a) == "src/payments/refund.ts#computeRefundable@a1b2c3d"


def test_dotted_symbol():
    assert parse_anchor("a.ts#Ledger.append").symbol == "Ledger.append"


def test_directory_anchor():
    a = parse_anchor("src/domain/@a1b2c3d")
    assert a.is_dir and a.path == "src/domain/" and a.sha == "a1b2c3d"


def test_scoped_package_path_is_not_mistaken_for_a_revision():
    """The regression this guards: `@acme` is not hex, so it stays in the path."""
    a = parse_anchor("packages/@acme/core/src/index.ts#build")
    assert a.path == "packages/@acme/core/src/index.ts"
    assert a.symbol == "build"
    assert a.sha is None


def test_windows_separators_are_normalised():
    assert parse_anchor(r"src\payments\refund.ts").path == "src/payments/refund.ts"


def test_sha_is_lowercased():
    assert parse_anchor("a.py@A1B2C3D").sha == "a1b2c3d"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "/etc/passwd",
        "C:/Windows/system32",
        "../outside.ts",
        "src/../../outside.ts",
        "src/domain/#Thing",          # directory anchor with a symbol
        "a.ts#not a symbol",
        "a.ts#3illegal",
    ],
)
def test_rejected(bad):
    with pytest.raises(AnchorError):
        parse_anchor(bad)


def test_nul_byte_rejected():
    with pytest.raises(AnchorError):
        parse_anchor("a\0b.ts")
