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
    load_notebook,
)
from cookbook_tools.tier_map import TierMap, tier_covers

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


def test_top_cell_matches_rendered_cta_exactly(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    tier_dir = recipe_path.parent.name
    expected_top = render_top_cell(recipe_fm, tier_dir=tier_dir).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    assert md_cells, "no markdown cells found"
    rendered_top = (
        "".join(md_cells[0]["source"])
        if isinstance(md_cells[0]["source"], list)
        else md_cells[0]["source"]
    )
    assert expected_top.strip() == rendered_top.strip(), (
        f"top CTA cell content mismatch in {recipe_path.name}:\n"
        f"expected:\n{expected_top}\n"
        f"got:\n{rendered_top}\n"
    )


def test_bottom_cell_matches_rendered_cta_exactly(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    expected_bottom = render_bottom_cell(recipe_fm).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    rendered_bottom = (
        "".join(md_cells[-1]["source"])
        if isinstance(md_cells[-1]["source"], list)
        else md_cells[-1]["source"]
    )
    assert expected_bottom.strip() == rendered_bottom.strip(), (
        f"bottom CTA cell content mismatch in {recipe_path.name}:\n"
        f"expected:\n{expected_bottom}\n"
        f"got:\n{rendered_bottom}\n"
    )


def test_no_hardcoded_api_key_in_source(recipe_path: pathlib.Path):
    text = recipe_path.read_text(encoding="utf-8")
    # Find any FlashAlpha(...) call and ensure its arg is os.environ[...]
    for match in re.finditer(r"FlashAlpha\(([^)]+)\)", text):
        arg = match.group(1).strip()
        assert "os.environ" in arg or "getenv" in arg, (
            f"FlashAlpha({arg}) — must read from environment, not hardcode"
        )


def test_no_silenced_errors(recipe_path: pathlib.Path):
    """Code cells must not silently swallow API errors. Forbids:
    - `except:` or `except Exception:` with only `pass` body
    - `except:` whose body has no `raise` and no `log.error/critical/exception`
    - `%%capture` cell magics (which suppress all output, including tracebacks)
    """
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = (
            "".join(cell["source"])
            if isinstance(cell["source"], list)
            else cell["source"]
        )
        stripped = source.strip()
        if not stripped:
            continue

        # Forbid %%capture (and its variants like %%capture --no-stderr).
        first_line = stripped.splitlines()[0]
        if first_line.lstrip().startswith("%%capture"):
            pytest.fail(
                f"{recipe_path.name}: cell starts with {first_line!r} — "
                f"%%capture suppresses errors and is forbidden"
            )

        # Skip cells with %% magics for AST parsing (not valid Python).
        if stripped.startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            pytest.fail(f"SyntaxError in {recipe_path.name}: cell does not parse")

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if _except_body_is_silencing(node.body):
                pytest.fail(
                    f"{recipe_path.name}: except handler at line "
                    f"{node.lineno} silently swallows errors — must either "
                    f"`raise` or call a logging function (e.g. "
                    f"`log.error(...)`, `logging.exception(...)`)"
                )


def _except_body_is_silencing(body: list[ast.stmt]) -> bool:
    """True if the except body neither re-raises nor logs at error+ level."""
    # Pure-pass body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True

    has_raise = False
    has_error_log = False
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Raise):
                has_raise = True
            elif isinstance(node, ast.Call):
                fn = _call_func_name(node).lower()
                # logger.error / logger.exception / logger.critical /
                # logging.error / log.error / _log.exception / etc.
                if any(level in fn for level in ("error", "exception", "critical")):
                    has_error_log = True
    return not (has_raise or has_error_log)


def _call_func_name(call: ast.Call) -> str:
    """Best-effort dotted name for a Call. Returns '' if not resolvable."""
    f = call.func
    parts: list[str] = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))


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


def test_mid_gate_cells_precede_gated_calls(
    recipe_path: pathlib.Path,
    recipe_fm: Frontmatter,
    tier_map: TierMap,
):
    """For every cell index in `tier_gated_cells`, the immediately preceding
    cell must be a markdown gate cell naming the endpoint and required tier.
    """
    from cookbook_tools.cta_template import render_gate_cell

    if not recipe_fm.tier_gated_cells:
        pytest.skip("no tier-gated cells declared in this recipe")

    nb = load_notebook(recipe_path)
    cells = nb["cells"]

    for idx in recipe_fm.tier_gated_cells:
        # The gated cell itself must exist and be a code cell.
        assert 0 <= idx < len(cells), (
            f"tier_gated_cells references missing index {idx}"
        )
        gated = cells[idx]
        assert gated["cell_type"] == "code", (
            f"tier_gated_cells[{idx}] points at a {gated['cell_type']!r} "
            f"cell — it should point at a code cell"
        )

        # The preceding cell must be a markdown gate cell.
        assert idx > 0, "tier-gated cell at index 0 cannot have a preceding gate"
        prev = cells[idx - 1]
        assert prev["cell_type"] == "markdown", (
            f"cell preceding tier-gated index {idx} must be a markdown "
            f"gate cell; got {prev['cell_type']!r}"
        )

        # The gated cell's source must mention exactly one /v1/* endpoint;
        # use it to find the required tier and validate the gate cell text.
        source = (
            "".join(gated["source"])
            if isinstance(gated["source"], list)
            else gated["source"]
        )
        m = re.search(r"(/v1/[A-Za-z0-9/_\-{}]+)", source)
        assert m, (
            f"tier-gated cell {idx} has no /v1/* endpoint reference; "
            f"cannot validate gate cell"
        )
        endpoint = m.group(1).replace("{symbol}", "SPY")
        required = tier_map.required_for(endpoint)
        assert not tier_covers(recipe_fm.tier, required), (
            f"cell {idx} declared in tier_gated_cells but endpoint "
            f"{endpoint!r} requires only {required!r}, which the recipe's "
            f"tier {recipe_fm.tier!r} already covers — drop from "
            f"tier_gated_cells"
        )

        expected_gate = render_gate_cell(
            endpoint=endpoint, required_tier=required, fm=recipe_fm
        ).rstrip()
        actual_gate = (
            "".join(prev["source"])
            if isinstance(prev["source"], list)
            else prev["source"]
        ).strip()
        assert expected_gate.strip() == actual_gate, (
            f"gate cell preceding tier-gated cell {idx} doesn't match "
            f"rendered gate.\nexpected:\n{expected_gate}\n"
            f"got:\n{actual_gate}\n"
        )


_PER_CELL_MAX_BYTES = 1 * 1024 * 1024   # 1 MB
_PER_NOTEBOOK_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def test_output_size_within_caps(recipe_path: pathlib.Path):
    """Reject runaway cell outputs (accidentally-pasted screenshots, huge
    DataFrames, etc.)."""
    import json as _json

    nb = load_notebook(recipe_path)
    total_bytes = 0
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs", []):
            blob = _json.dumps(output)
            cell_bytes = len(blob.encode("utf-8"))
            total_bytes += cell_bytes
            assert cell_bytes < _PER_CELL_MAX_BYTES, (
                f"{recipe_path.name}: cell {cell_idx} output is "
                f"{cell_bytes // 1024} KB, exceeds 1 MB cap"
            )
    assert total_bytes < _PER_NOTEBOOK_MAX_BYTES, (
        f"{recipe_path.name}: total cell outputs are "
        f"{total_bytes // 1024} KB, exceeds 5 MB cap"
    )
