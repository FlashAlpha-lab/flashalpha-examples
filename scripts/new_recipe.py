"""Scaffold a paired (.py + .ipynb) recipe from frontmatter args."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
import textwrap

import jupytext
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_raw_cell

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import ExpectedArtifacts, Frontmatter


def build_notebook(fm: Frontmatter, *, tier_dir: str) -> nbformat.NotebookNode:
    frontmatter_yaml = textwrap.dedent(f"""\
        ---
        slug: {fm.slug}
        title: {fm.title}
        tier: {fm.tier}
        runtime_budget_seconds: {fm.runtime_budget_seconds}
        max_api_calls: {fm.max_api_calls}
        endpoints_used:
          - /v1/exposure/gex/{{symbol}}
        tier_gated_cells: []
        sdk_version_min: "{fm.sdk_version_min}"
        utm_campaign: {fm.utm_campaign}
        expected_artifacts:
          dataframes: []
          charts: []
        last_validated_live: {fm.last_validated_live.isoformat()}
        ---
    """)

    nb = new_notebook()
    nb.cells = [
        new_raw_cell(frontmatter_yaml.rstrip()),
        new_markdown_cell(render_top_cell(fm, tier_dir=tier_dir).rstrip()),
        new_code_cell(textwrap.dedent("""\
            import os

            from flashalpha import FlashAlpha

            fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])
            # TODO: implement recipe body here.
        """).rstrip()),
        new_markdown_cell(render_bottom_cell(fm).rstrip()),
    ]
    nb["metadata"] = {
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "jupytext": {"formats": "ipynb,py:percent"},
    }
    return nb


def write_pair(nb: nbformat.NotebookNode, out_dir: pathlib.Path, slug: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ipynb_path = out_dir / f"{slug}.ipynb"
    py_path = out_dir / f"{slug}.py"
    with ipynb_path.open("w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    jupytext.write(nb, str(py_path), fmt="py:percent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--tier", required=True, choices=("free", "basic", "growth", "alpha")
    )
    parser.add_argument("--tier-dir", required=True)
    parser.add_argument(
        "--out-root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Repo root containing notebooks/. Defaults to CWD.",
    )
    parser.add_argument("--runtime-budget", type=int, default=60)
    parser.add_argument("--max-api-calls", type=int, default=8)
    parser.add_argument("--sdk-version-min", default="1.0.1")
    args = parser.parse_args(argv)

    fm = Frontmatter(
        slug=args.slug,
        title=args.title,
        tier=args.tier,
        runtime_budget_seconds=args.runtime_budget,
        max_api_calls=args.max_api_calls,
        endpoints_used=["/v1/exposure/gex/{symbol}"],
        tier_gated_cells=[],
        sdk_version_min=args.sdk_version_min,
        utm_campaign=args.slug,
        expected_artifacts=ExpectedArtifacts(),
        last_validated_live=dt.date.today(),
    )
    nb = build_notebook(fm, tier_dir=args.tier_dir)
    out_dir = args.out_root / "notebooks" / args.tier_dir
    write_pair(nb, out_dir, fm.slug)
    print(f"wrote {out_dir / (fm.slug + '.py')}", file=sys.stderr)
    print(f"wrote {out_dir / (fm.slug + '.ipynb')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
