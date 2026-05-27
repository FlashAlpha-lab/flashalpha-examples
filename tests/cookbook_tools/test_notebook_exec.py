"""Tests for in-process notebook execution."""

from __future__ import annotations

import json
import pathlib

import pytest

from cookbook_tools.notebook_exec import (
    execute_notebook_in_process,
    load_code_cells,
)


def _make_nb(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_nb(tmp_path: pathlib.Path, cells: list[dict]) -> pathlib.Path:
    path = tmp_path / "nb.ipynb"
    path.write_text(json.dumps(_make_nb(cells)), encoding="utf-8")
    return path


def test_load_code_cells_skips_markdown_and_magics(tmp_path: pathlib.Path):
    path = _write_nb(tmp_path, [
        {"cell_type": "markdown", "source": ["# title"]},
        {"cell_type": "code", "source": ["x = 1\n"]},
        {"cell_type": "code", "source": ["%timeit x = 2\n"]},   # magic
        {"cell_type": "code", "source": ["%%capture\nx = 3\n"]},  # cell magic
        {"cell_type": "code", "source": ["y = 2\n"]},
    ])
    assert load_code_cells(path) == ["x = 1\n", "y = 2\n"]


def test_load_code_cells_handles_string_source(tmp_path: pathlib.Path):
    """nbformat allows either list-of-lines or single string for source."""
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": "x = 42\n"},
    ])
    assert load_code_cells(path) == ["x = 42\n"]


def test_execute_runs_cells_in_shared_namespace(tmp_path: pathlib.Path):
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": ["x = 5\n"]},
        {"cell_type": "code", "source": ["print(x * 2)\n"]},
    ])
    out = execute_notebook_in_process(path)
    assert "10" in out


def test_execute_captures_stdout(tmp_path: pathlib.Path):
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": ['print("hello world")\n']},
    ])
    out = execute_notebook_in_process(path)
    assert "hello world" in out


def test_execute_no_capture_returns_empty(tmp_path: pathlib.Path):
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": ['print("hello")\n']},
    ])
    out = execute_notebook_in_process(path, capture_stdout=False)
    assert out == ""


def test_execute_raises_on_cell_error(tmp_path: pathlib.Path):
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": ["raise RuntimeError('boom')\n"]},
    ])
    with pytest.raises(RuntimeError, match="boom"):
        execute_notebook_in_process(path)


def test_execute_skips_magic_cells_silently(tmp_path: pathlib.Path):
    """A %% cell magic must not cause SyntaxError; it's just skipped."""
    path = _write_nb(tmp_path, [
        {"cell_type": "code", "source": ["%%timeit\nx = 1\n"]},
        {"cell_type": "code", "source": ['print("after-magic")\n']},
    ])
    out = execute_notebook_in_process(path)
    assert "after-magic" in out
