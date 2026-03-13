"""
Syntax validation tests — no API key required.

Each notebook is a plain Python file. These tests confirm the files parse
without SyntaxError, catching typos and incomplete edits before they reach CI.
"""

import ast
import pathlib

NOTEBOOKS_DIR = pathlib.Path(__file__).parent.parent / "notebooks"

NOTEBOOK_FILES = sorted(NOTEBOOKS_DIR.glob("*.py"))


def _ids(paths):
    return [p.name for p in paths]


def test_notebooks_dir_is_not_empty():
    assert len(NOTEBOOK_FILES) > 0, f"No .py files found in {NOTEBOOKS_DIR}"


def pytest_generate_tests(metafunc):
    if "notebook_path" in metafunc.fixturenames:
        metafunc.parametrize("notebook_path", NOTEBOOK_FILES, ids=_ids(NOTEBOOK_FILES))


def test_notebook_parses_without_syntax_error(notebook_path):
    source = notebook_path.read_text(encoding="utf-8")
    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise AssertionError(
            f"SyntaxError in {notebook_path.name}: {exc}"
        ) from exc
