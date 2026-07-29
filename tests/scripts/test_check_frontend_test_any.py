import importlib.util
from pathlib import Path

import pytest


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_frontend_test_any",
        str(Path(__file__).resolve().parents[2] / "scripts" / "check-frontend-test-any.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


module = _load_module()


@pytest.mark.parametrize(
    "line",
    [
        "+ const x = value as any;",
        "+ let x: any;",
        "+ const xs: any[] = [];",
        "+ const r: Record<string, any> = {};",
        "+ type Foo = any;",
        "+ const xs = <any>value;",
    ],
)
def test_line_introduces_any_flags_explicit_any(line: str) -> None:
    assert module.line_introduces_any(line) is True


@pytest.mark.parametrize(
    "line",
    [
        "+ expect.any(Function)",
        "+ // cast to any later",
        "+ const x = value as unknown;",
        "+ let x: string;",
    ],
)
def test_line_introduces_any_ignores_false_positives(line: str) -> None:
    assert module.line_introduces_any(line) is False


def test_remove_block_comments_strips_commented_any() -> None:
    text = "/* This is a block comment with as any */ const x = 1;"
    assert "as any" not in module.remove_block_comments(text)


@pytest.mark.parametrize(
    "line",
    [
        "- const x = value as any;",
        "+++ b/file.test.ts",
        " const x = value as any;",
    ],
)
def test_line_introduces_any_ignores_non_addition_lines(line: str) -> None:
    assert module.line_introduces_any(line) is False


def test_remove_block_comments_over_strips_string_literal() -> None:
    text = 'const msg = "start /* any */ end";'
    assert "/* any */" not in module.remove_block_comments(text)
