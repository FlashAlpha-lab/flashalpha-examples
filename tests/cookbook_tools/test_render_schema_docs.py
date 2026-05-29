"""Tests for the auto-generated schema doc."""

from __future__ import annotations

import pathlib

from scripts.render_schema_docs import OUT_PATH, render

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_committed_schema_doc_is_in_sync():
    """The committed docs/frontmatter-schema.md must match what
    `render_schema_docs` produces from the current Pydantic models. If
    this fails, run `python -m scripts.render_schema_docs` and commit
    the regenerated file."""
    expected = render()
    actual = OUT_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/frontmatter-schema.md is out of sync with the Pydantic "
        "schema. Run: python -m scripts.render_schema_docs"
    )


def test_render_includes_every_frontmatter_field():
    """Sanity check: the rendered markdown mentions every Pydantic
    field by name."""
    from cookbook_tools.frontmatter import Frontmatter

    text = render()
    for field_name in Frontmatter.model_fields:
        assert f"`{field_name}`" in text, (
            f"field {field_name!r} missing from rendered schema doc"
        )


def test_render_is_deterministic():
    """Two calls produce byte-identical output (no timestamp, no random
    ordering)."""
    assert render() == render()
