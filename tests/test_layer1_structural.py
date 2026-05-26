"""Layer 1: structural checks parametrized over every recipe notebook."""

from __future__ import annotations

import ast
import pathlib
import re

import nbformat
import pytest

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import Frontmatter
from cookbook_tools.notebook_io import (
    extract_markdown_urls,  # noqa: F401
    load_notebook,
)
from cookbook_tools.tier_map import TierMap, tier_covers  # noqa: F401

_REQUIREMENTS = (
    pathlib.Path(__file__).resolve().parents[1] / "requirements.txt"
)


def test_notebook_is_valid_nbformat(recipe_path: pathlib.Path):
    nb = nbformat.read(recipe_path, as_version=4)
    nbformat.validate(nb)


def test_slug_matches_filename(recipe_path: pathlib.Path, recipe_fm: Frontmatter):
    assert recipe_fm.slug == recipe_path.stem, (
        f"frontmatter.slug={recipe_fm.slug!r} != filename stem "
        f"{recipe_path.stem!r}"
    )


def test_top_cell_present_with_correct_signup_utm(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    tier_dir = recipe_path.parent.name
    expected_top = render_top_cell(recipe_fm, tier_dir=tier_dir).rstrip()
    # Top cell is the second cell (after the frontmatter raw cell).
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    assert md_cells, "no markdown cells found"
    rendered_top = "".join(md_cells[0]["source"]) if isinstance(md_cells[0]["source"], list) else md_cells[0]["source"]
    assert expected_top.strip() in rendered_top.strip(), (
        f"top CTA cell content mismatch in {recipe_path.name}"
    )


def test_bottom_cell_present_with_correct_utm(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    expected_bottom = render_bottom_cell(recipe_fm).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    rendered_bottom = "".join(md_cells[-1]["source"]) if isinstance(md_cells[-1]["source"], list) else md_cells[-1]["source"]
    assert expected_bottom.strip() in rendered_bottom.strip(), (
        f"bottom CTA cell content mismatch in {recipe_path.name}"
    )


def test_no_hardcoded_api_key_in_source(recipe_path: pathlib.Path):
    text = recipe_path.read_text(encoding="utf-8")
    # Find any FlashAlpha(...) call and ensure its arg is os.environ[...]
    for match in re.finditer(r"FlashAlpha\(([^)]+)\)", text):
        arg = match.group(1).strip()
        assert "os.environ" in arg or "getenv" in arg, (
            f"FlashAlpha({arg}) — must read from environment, not hardcode"
        )


def test_no_broad_except_hiding_errors(recipe_path: pathlib.Path):
    """Code cells must not silently swallow API errors."""
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if not source.strip():
            continue
        # Skip cells with %% magics (not valid Python on their own).
        if source.lstrip().startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            pytest.fail(f"SyntaxError in {recipe_path.name}: cell does not parse")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Disallow bare except, or `except Exception:` with only `pass`.
                body_is_pass_only = (
                    len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                )
                assert not body_is_pass_only, (
                    f"Bare/empty except in {recipe_path.name} hides errors"
                )


def test_endpoints_used_have_known_tier(
    recipe_fm: Frontmatter, tier_map: TierMap
):
    """Every declared endpoint must resolve to a known tier."""
    # Replace {symbol} placeholder with SPY for lookup; the prefix match
    # ignores everything past the prefix anyway.
    for ep in recipe_fm.endpoints_used:
        concrete = ep.replace("{symbol}", "SPY")
        # Raises KeyError if no rule matches.
        tier_map.required_for(concrete)


def test_imports_present_in_requirements(recipe_path: pathlib.Path):
    """Every top-level import in a code cell must be available."""
    requirements = _REQUIREMENTS.read_text(encoding="utf-8").lower()
    # Stdlib modules we never want to gate on requirements.txt.
    stdlib = {
        "os", "sys", "json", "pathlib", "datetime", "math", "re", "itertools",
        "functools", "collections", "typing", "time", "io", "csv", "textwrap",
    }
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if not source.strip():
            continue
        if source.lstrip().startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [n.name.split(".")[0] for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            for name in names:
                if name in stdlib:
                    continue
                assert name.lower() in requirements, (
                    f"{recipe_path.name} imports {name!r} but it is not in "
                    f"requirements.txt"
                )
