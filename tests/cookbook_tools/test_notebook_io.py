"""Tests for notebook I/O helpers."""

import pathlib

import pytest

from cookbook_tools.notebook_io import (
    extract_frontmatter_text,
    extract_markdown_urls,
    extract_code_endpoints,
    load_notebook,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "minimal.ipynb"


def test_load_notebook_round_trips():
    nb = load_notebook(FIXTURE)
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) == 3


def test_extract_frontmatter_text_finds_yaml_block():
    nb = load_notebook(FIXTURE)
    text = extract_frontmatter_text(nb)
    assert text.startswith("---")
    assert text.rstrip().endswith("---")
    assert "slug: 99-test" in text


def test_extract_frontmatter_missing_raises():
    nb_no_fm = {"cells": [
        {"cell_type": "markdown", "source": ["# hello"]},
    ]}
    with pytest.raises(ValueError, match="frontmatter cell"):
        extract_frontmatter_text(nb_no_fm)


def test_extract_markdown_urls_finds_all_links():
    nb = load_notebook(FIXTURE)
    urls = extract_markdown_urls(nb)
    assert "https://flashalpha.com/pricing" in urls
    assert "https://example.com/spec" in urls


def test_extract_code_endpoints_finds_path_from_comment_marker():
    nb = load_notebook(FIXTURE)
    endpoints = extract_code_endpoints(nb)
    # The fixture's code cell has `# /v1/exposure/gex/SPY` — the helper
    # collects any /v1/* path on a line within a code cell, useful as a
    # static-analysis fallback when cassettes aren't available.
    assert "/v1/exposure/gex/SPY" in endpoints
